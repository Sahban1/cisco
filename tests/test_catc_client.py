# tests/test_catc_client.py
# Run: pytest -q    (from the repo root, inside the venv)
# Tests the Catalyst Center client against a FAKE Catalyst Center (no network).
# The fake answers in the shapes the API documents; confirm them in the lab
# and adjust both the client and these fakes if our version differs.
import importlib.util
import json
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "catc_client", Path(__file__).parent.parent / "ansible/plugins/module_utils/catc_client.py")
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)

DEV = "11111111-2222-3333-4444-555555555555"
DEPLOY = "99999999-8888-7777-6666-555555555555"


class FakeCatc:
    """Minimal in-memory Catalyst Center. Records every call."""

    def __init__(self):
        self.calls, self.templates, self.projects = [], {}, []
        self.expire_token_once = False
        self.rate_limit_once = False
        self.deploy_status = "SUCCESS"
        self.devices = [{"id": DEV, "hostname": "TOR-0042-SW1.rbc.example", "softwareVersion": "17.12.5",
                         "reachabilityStatus": "Reachable", "collectionStatus": "Managed"}]

    def __call__(self, method, url, headers, data):
        path = url.split("https://catc.example", 1)[1]
        body = json.loads(data) if data else None
        self.calls.append((method, path))
        if path == "/dna/system/api/v1/auth/token":
            return 200, json.dumps({"Token": "tok"})
        if self.expire_token_once:
            self.expire_token_once = False
            return 401, "expired"
        if self.rate_limit_once:
            self.rate_limit_once = False
            return 429, "slow down"
        task = lambda data="": (200, json.dumps({"response": {"taskId": "t-" + str(len(self.calls)), "data": data}}))
        if path.startswith("/dna/intent/api/v1/network-device?hostname="):
            q = path.split("=", 1)[1].replace(".*", "").lower()
            hits = [d for d in self.devices if d["hostname"].lower().startswith(q)]
            return 200, json.dumps({"response": hits if path.endswith(".*") else
                                    [d for d in hits if d["hostname"].lower() == q]})
        if path.startswith("/dna/intent/api/v1/task/"):
            tid = path.rsplit("/", 1)[1]
            progress = json.dumps({"fileId": "file-1"}) if tid == "t-cmd" else "done"
            return 200, json.dumps({"response": {"endTime": 1, "isError": False, "progress": progress}})
        if path == "/dna/intent/api/v1/network-device-poller/cli/legit-reads":
            return 200, json.dumps({"response": ["show", "dir"]})
        if path == "/dna/intent/api/v1/network-device-poller/cli/read-request":
            self.last_commands = body["commands"]
            return 200, json.dumps({"response": {"taskId": "t-cmd"}})
        if path == "/dna/intent/api/v1/file/file-1":
            return 200, json.dumps([{"deviceUuid": DEV, "commandResponses": {
                "SUCCESS": {c: f"output of {c}" for c in self.last_commands if "mab" not in c},
                "FAILURE": {c: "% Invalid input" for c in self.last_commands if "mab" in c},
                "BLACKLISTED": {}}}])
        if path.startswith("/dna/intent/api/v1/template-programmer/project?name="):
            return 200, json.dumps([{"id": "proj-1", "name": "IBNS2",
                                     "templates": [{"name": n, "id": t["id"]} for n, t in self.templates.items()]}]
                                   if self.projects else [])
        if path == "/dna/intent/api/v1/template-programmer/project" and method == "POST":
            self.projects.append(body["name"])
            return task("proj-1")
        if path == "/dna/intent/api/v1/template-programmer/project/proj-1/template":
            self.templates[body["name"]] = {"id": "tmpl-1", "content": body["templateContent"], "versions": 0}
            return task()
        if path.startswith("/dna/intent/api/v1/template-programmer/template/") and method == "GET" \
                and "deploy" not in path:
            t = next(t for t in self.templates.values() if t["id"] == path.rsplit("/", 1)[1])
            return 200, json.dumps({"id": t["id"], "templateContent": t["content"]})
        if path == "/dna/intent/api/v1/template-programmer/template" and method == "PUT":
            self.templates[body["name"]]["content"] = body["templateContent"]
            return task()
        if path == "/dna/intent/api/v1/template-programmer/template/version":
            next(t for t in self.templates.values() if t["id"] == body["templateId"])["versions"] += 1
            return task()
        if path == "/dna/intent/api/v1/template-programmer/template/deploy":
            assert body["targetInfo"][0] == {"id": DEV, "type": "MANAGED_DEVICE_UUID", "params": {}}
            return 200, json.dumps({"deploymentId": "Deployment of template started. Id: " + DEPLOY})
        if path == f"/dna/intent/api/v1/template-programmer/template/deploy/status/{DEPLOY}":
            return 200, json.dumps({"status": self.deploy_status, "endTime": "now",
                                    "devices": [{"deviceId": DEV, "status": self.deploy_status,
                                                 "detailedStatusMessage": "ok" if self.deploy_status == "SUCCESS"
                                                 else "line 2: % Invalid input"}]})
        raise AssertionError(f"unexpected call {method} {path}")


def client(fake):
    return cc.CatcClient("catc.example", "user", "pw", fake, sleep=lambda s: None, poll_interval=1, timeout=5)


def test_device_lookup_accepts_fqdn_and_short_name():
    fake = FakeCatc()
    assert client(fake).device("TOR-0042-SW1")["id"] == DEV
    assert client(fake).device("tor-0042-sw1.rbc.example")["id"] == DEV


def test_device_lookup_refuses_unknown():
    try:
        client(FakeCatc()).device("NOPE")
    except cc.CatcError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("unknown device accepted")


def test_command_runner_returns_outputs_and_failures():
    fake = FakeCatc()
    out, failed = client(fake).run_commands(DEV, ["show running-config", "show access-session method mab details"])
    assert out == {"show running-config": "output of show running-config"}
    assert failed == {"show access-session method mab details": "% Invalid input"}


def test_command_runner_refuses_non_read_commands_before_sending():
    fake = FakeCatc()
    try:
        client(fake).run_commands(DEV, ["authentication display config-mode"])
    except cc.CatcError as exc:
        assert "does not accept" in str(exc)
    else:
        raise AssertionError("non-read command accepted")
    assert ("POST", "/dna/intent/api/v1/network-device-poller/cli/read-request") not in fake.calls


def test_command_runner_splits_into_requests_of_five():
    fake = FakeCatc()
    client(fake).run_commands(DEV, [f"show c{i}" for i in range(7)])
    assert fake.calls.count(("POST", "/dna/intent/api/v1/network-device-poller/cli/read-request")) == 2


def test_template_created_committed_and_deployed():
    fake = FakeCatc()
    c = client(fake)
    tid, changed = c.upsert_template("IBNS2", "IBNS2_TOR-0042-SW1", "interface Gi1/0/1\n shutdown", "run1 step")
    assert (tid, changed) == ("tmpl-1", True)
    assert fake.projects == ["IBNS2"] and fake.templates["IBNS2_TOR-0042-SW1"]["versions"] == 1
    status = c.deploy(tid, DEV)
    assert status["status"] == "SUCCESS" and status["deploymentId"] == DEPLOY


def test_unchanged_content_is_not_recommitted_and_changed_content_is():
    fake = FakeCatc()
    c = client(fake)
    c.upsert_template("IBNS2", "T", "a", "1")
    assert c.upsert_template("IBNS2", "T", "a", "2") == ("tmpl-1", False)
    assert c.upsert_template("IBNS2", "T", "b", "3") == ("tmpl-1", True)
    assert fake.templates["T"] == {"id": "tmpl-1", "content": "b", "versions": 2}


def test_failed_deployment_is_reported_not_raised():
    fake = FakeCatc()
    fake.deploy_status = "FAILURE"
    c = client(fake)
    tid, _ = c.upsert_template("IBNS2", "T", "x", "1")
    status = c.deploy(tid, DEV)
    assert status["status"] == "FAILURE"
    assert status["devices"][0]["detailedStatusMessage"].startswith("line 2")


def test_expired_token_and_rate_limit_are_retried():
    fake = FakeCatc()
    c = client(fake)
    c.device("TOR-0042-SW1")
    fake.expire_token_once = True
    fake.rate_limit_once = True
    assert c.device("TOR-0042-SW1")["id"] == DEV
    assert fake.calls.count(("POST", "/dna/system/api/v1/auth/token")) == 2
