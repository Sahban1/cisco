# ansible/plugins/module_utils/catc_client.py
"""Small Catalyst Center REST client shared by the catc_* modules.

Every IBNS read and write goes through Catalyst Center: reads through Command
Runner, changes through Template Programmer. No SSH to switches.

Pure Python standard library. The HTTP call is passed in as `request`, so the
same code runs inside Ansible (open_url, see open_url_request below) and in the
unit tests with a fake Catalyst Center (tests/test_catc_client.py).

Endpoints used. VERIFY each one on our Catalyst Center version in the lab:
  POST /dna/system/api/v1/auth/token                                  login
  GET  /dna/intent/api/v1/network-device?hostname=                    device lookup
  PUT  /dna/intent/api/v1/network-device/sync?forceSync=false         resync inventory
  GET  /dna/intent/api/v1/network-device-poller/cli/legit-reads       allowed read keywords
  POST /dna/intent/api/v1/network-device-poller/cli/read-request      Command Runner
  GET  /dna/intent/api/v1/task/{id}                                   task status
  GET  /dna/intent/api/v1/file/{id}                                   Command Runner output
  GET  /dna/intent/api/v1/template-programmer/project?name=           project and its templates
  POST /dna/intent/api/v1/template-programmer/project                 create project
  GET  /dna/intent/api/v1/template-programmer/template/{id}           template content
  POST /dna/intent/api/v1/template-programmer/project/{id}/template   create template
  PUT  /dna/intent/api/v1/template-programmer/template                update template
  POST /dna/intent/api/v1/template-programmer/template/version        commit (version)
  POST /dna/intent/api/v1/template-programmer/template/deploy         deploy
  GET  /dna/intent/api/v1/template-programmer/template/deploy/status/{id}
"""
import base64
import json
import re
import time

UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")

CATC_OPTIONS = dict(
    host=dict(type="str", required=True),
    username=dict(type="str", required=True),
    password=dict(type="str", required=True, no_log=True),
    validate_certs=dict(type="bool", default=True),
    ca_path=dict(type="str", default=""),
)


def catc_argument_spec(**extra):
    """Argument spec every catc_* module shares: one `catc` dict for the login."""
    spec = dict(
        catc=dict(type="dict", required=True, options=CATC_OPTIONS, no_log=False),
        timeout=dict(type="int", default=600),
        poll_interval=dict(type="int", default=5),
    )
    spec.update(extra)
    return spec


def open_url_request(validate_certs=True, ca_path=""):
    """Request function for use inside Ansible modules (no extra packages)."""
    from ansible.module_utils.urls import open_url
    from ansible.module_utils.six.moves.urllib.error import HTTPError

    def request(method, url, headers, data):
        try:
            resp = open_url(url, method=method, headers=headers, data=data, validate_certs=validate_certs,
                            ca_path=ca_path or None, timeout=120)
            return resp.getcode(), resp.read().decode("utf-8", "replace")
        except HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", "replace") if exc.fp else str(exc)
    return request


class CatcError(Exception):
    pass


class CatcClient(object):
    def __init__(self, host, username, password, request, sleep=time.sleep, poll_interval=5, timeout=600):
        base = host if host.startswith("http") else "https://" + host
        self.base = base.rstrip("/")
        self.username, self.password = username, password
        self.request, self.sleep = request, sleep
        self.poll_interval, self.timeout = poll_interval, timeout
        self.token = None

    # ------------------------------------------------------------ plumbing --
    def login(self):
        basic = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        status, text = self.request("POST", self.base + "/dna/system/api/v1/auth/token",
                                    {"Authorization": "Basic " + basic, "Content-Type": "application/json"}, None)
        if status != 200:
            raise CatcError(f"Catalyst Center login failed: HTTP {status}")
        self.token = json.loads(text)["Token"]

    def call(self, method, path, body=None, retries=6):
        for attempt in range(retries):
            if self.token is None:
                self.login()
            headers = {"Content-Type": "application/json", "Accept": "application/json",
                       "X-Auth-Token": self.token}
            data = json.dumps(body) if body is not None else None
            status, text = self.request(method, self.base + path, headers, data)
            if status == 401:                       # token expired: log in again once
                self.token = None
                continue
            if status in (429, 502, 503, 504):      # rate limit / busy: back off and retry
                self.sleep(min(60, 5 * 2 ** attempt))
                continue
            if status >= 400:
                raise CatcError(f"{method} {path} -> HTTP {status}: {text[:500]}")
            return json.loads(text) if text and text.strip() else {}
        raise CatcError(f"{method} {path} failed after {retries} attempts")

    def wait_task(self, task_id, what="task"):
        waited = 0
        while True:
            task = self.call("GET", f"/dna/intent/api/v1/task/{task_id}").get("response", {})
            if task.get("isError"):
                raise CatcError(f"{what} failed: {task.get('failureReason') or task.get('progress')}")
            if task.get("endTime"):
                return task
            if waited >= self.timeout:
                raise CatcError(f"{what} did not finish in {self.timeout}s (task {task_id})")
            self.sleep(self.poll_interval)
            waited += self.poll_interval

    @staticmethod
    def task_id(resp):
        task = resp.get("response", resp)
        if not task.get("taskId"):
            raise CatcError(f"no taskId in response: {resp}")
        return task["taskId"]

    # ------------------------------------------------------------- devices --
    def device(self, hostname):
        """One managed device by hostname (exact, case-insensitive; FQDN allowed)."""
        name = hostname.lower()
        for query in (hostname, hostname + ".*"):
            items = self.call("GET", f"/dna/intent/api/v1/network-device?hostname={query}").get("response", [])
            found = [d for d in items if str(d.get("hostname", "")).lower() in (name,)
                     or str(d.get("hostname", "")).lower().startswith(name + ".")]
            if len(found) == 1:
                return found[0]
            if len(found) > 1:
                raise CatcError(f"{hostname} matches {len(found)} devices in Catalyst Center")
        raise CatcError(f"{hostname} not found in Catalyst Center")

    def sync(self, device_id):
        return self.wait_task(self.task_id(self.call(
            "PUT", "/dna/intent/api/v1/network-device/sync?forceSync=false", [device_id])), "inventory resync")

    # ------------------------------------------------------ command runner --
    def legit_reads(self):
        return set(self.call("GET", "/dna/intent/api/v1/network-device-poller/cli/legit-reads").get("response", []))

    def run_commands(self, device_id, commands, check_keywords=True, max_per_request=5):
        """Command Runner (read-only). Returns ({command: output}, {command: error})."""
        if check_keywords:
            allowed = self.legit_reads()
            refused = [c for c in commands if c.split()[0] not in allowed]
            if refused:
                raise CatcError(f"Command Runner does not accept: {refused} (allowed keywords: {sorted(allowed)})")
        outputs, failures = {}, {}
        for i in range(0, len(commands), max_per_request):
            chunk = commands[i:i + max_per_request]
            task = self.wait_task(self.task_id(self.call(
                "POST", "/dna/intent/api/v1/network-device-poller/cli/read-request",
                {"commands": chunk, "deviceUuids": [device_id]})), "Command Runner")
            file_id = json.loads(task["progress"])["fileId"]
            results = self.call("GET", f"/dna/intent/api/v1/file/{file_id}")
            entry = next((r for r in results if r.get("deviceUuid") == device_id), None)
            if entry is None:
                raise CatcError(f"Command Runner returned no result for device {device_id}")
            resp = entry.get("commandResponses", {})
            outputs.update(resp.get("SUCCESS", {}))
            failures.update(resp.get("FAILURE", {}))
            failures.update({c: "BLACKLISTED" for c in resp.get("BLACKLISTED", {})})
        for c in commands:
            if c not in outputs and c not in failures:
                failures[c] = "no output returned"
        return outputs, failures

    # ------------------------------------------------- template programmer --
    def project(self, name, create=True):
        found = self.call("GET", f"/dna/intent/api/v1/template-programmer/project?name={name}")
        if found:
            return found[0]
        if not create:
            raise CatcError(f"template project {name} not found")
        self.wait_task(self.task_id(self.call("POST", "/dna/intent/api/v1/template-programmer/project",
                                              {"name": name, "description": "IBNS 2.0 automation (managed from Git)"})),
                       "create project")
        return self.call("GET", f"/dna/intent/api/v1/template-programmer/project?name={name}")[0]

    def upsert_template(self, project_name, name, content, comment, language="JINJA"):
        """Create or update a template and commit a new version when the content
        changed. Returns (template_id, changed)."""
        project = self.project(project_name)
        existing = next((t for t in project.get("templates", []) if t.get("name") == name), None)
        body = {
            "name": name, "description": "IBNS 2.0 automation - content is replaced on every push",
            "tags": [], "author": "ibns-automation",
            "deviceTypes": [{"productFamily": "Switches and Hubs"}],
            "softwareType": "IOS-XE", "softwareVariant": "XE", "softwareVersion": "",
            "language": language, "templateContent": content, "templateParams": [],
            "rollbackTemplateContent": "", "rollbackTemplateParams": [],
            "projectName": project_name, "projectId": project["id"],
        }
        if existing is None:
            self.wait_task(self.task_id(self.call(
                "POST", f"/dna/intent/api/v1/template-programmer/project/{project['id']}/template", body)),
                "create template")
            project = self.project(project_name, create=False)
            existing = next(t for t in project.get("templates", []) if t.get("name") == name)
        else:
            current = self.call("GET", f"/dna/intent/api/v1/template-programmer/template/{existing['id']}")
            if current.get("templateContent", "") == content:
                return existing["id"], False
            body["id"] = existing["id"]
            self.wait_task(self.task_id(self.call("PUT", "/dna/intent/api/v1/template-programmer/template", body)),
                           "update template")
        self.wait_task(self.task_id(self.call("POST", "/dna/intent/api/v1/template-programmer/template/version",
                                              {"templateId": existing["id"], "comments": comment})),
                       "commit template")
        return existing["id"], True

    def deploy(self, template_id, device_id):
        """Deploy a committed template to one device and wait for the result."""
        resp = self.call("POST", "/dna/intent/api/v1/template-programmer/template/deploy", {
            "templateId": template_id, "forcePushTemplate": True, "isComposite": False,
            "targetInfo": [{"id": device_id, "type": "MANAGED_DEVICE_UUID", "params": {}}],
        })
        failed = resp.get("failedTargets") or []
        if failed:
            raise CatcError(f"deployment refused: {failed}")
        match = UUID.search(str(resp.get("deploymentId", "")))
        if not match:
            raise CatcError(f"no deployment id in response: {resp}")
        deployment_id = match.group(0)
        waited = 0
        while True:
            status = self.call("GET", f"/dna/intent/api/v1/template-programmer/template/deploy/status/{deployment_id}")
            if status.get("endTime") and status.get("status") not in ("IN_PROGRESS", "INIT", None):
                status["deploymentId"] = deployment_id
                return status
            if waited >= self.timeout:
                raise CatcError(f"deployment {deployment_id} did not finish in {self.timeout}s")
            self.sleep(self.poll_interval)
            waited += self.poll_interval
