#!/usr/bin/python
# ansible/plugins/modules/catc_cli_push.py
"""Push CLI to one switch through Catalyst Center Template Programmer.

The CLI is rendered by Ansible (repo templates + ibns filters) and stored as the
content of ONE template per switch (`IBNS2_<hostname>` in the IBNS2 project).
Each push replaces the content, commits a new version (comment = run id and
step) and deploys it, so the template's version history in Catalyst Center is
the audit trail of every IBNS change on that switch.

Exec-mode commands (convert, copy, write memory) use Catalyst Center template
syntax: #MODE_ENABLE ... #MODE_END_ENABLE, and #INTERACTIVE with <IQ>/<R> for
prompts (built by the ibns_cli_exec filter).
"""

DOCUMENTATION = r"""
module: catc_cli_push
short_description: Deploy CLI to one device through a Catalyst Center template
options:
  catc: {description: Catalyst Center login (host, username, password, validate_certs, ca_path), type: dict, required: true}
  device_id: {description: Catalyst Center device UUID (from catc_device), type: str, required: true}
  project: {description: Template project, type: str, required: true}
  template_name: {description: Template name (one per switch), type: str, required: true}
  content: {description: Rendered CLI to push, type: str, required: true}
  comment: {description: Commit comment (run id and step), type: str, required: true}
  language: {description: Template language, type: str, default: JINJA, choices: [JINJA, VELOCITY]}
  timeout: {description: Seconds to wait for each task and the deployment, type: int, default: 600}
  poll_interval: {description: Seconds between checks, type: int, default: 5}
"""

RETURN = r"""
template_id: {description: Template UUID, type: str}
version_committed: {description: True if the content changed and a new version was committed, type: bool}
deployment_id: {description: Deployment UUID, type: str}
deployment_status: {description: SUCCESS / FAILURE as reported by Catalyst Center, type: str}
devices: {description: Per-device deployment detail from Catalyst Center, type: list}
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.catc_client import CatcClient, CatcError, catc_argument_spec, open_url_request


def main():
    module = AnsibleModule(
        argument_spec=catc_argument_spec(
            device_id=dict(type="str", required=True),
            project=dict(type="str", required=True),
            template_name=dict(type="str", required=True),
            content=dict(type="str", required=True),
            comment=dict(type="str", required=True),
            language=dict(type="str", default="JINJA", choices=["JINJA", "VELOCITY"]),
        ),
        supports_check_mode=True,
    )
    p, c = module.params, module.params["catc"]
    if not p["content"].strip():
        module.fail_json(msg="Refusing to push empty content.")
    if module.check_mode:
        module.exit_json(changed=True, content=p["content"].splitlines())
    client = CatcClient(c["host"], c["username"], c["password"],
                        open_url_request(c["validate_certs"], c["ca_path"]),
                        poll_interval=p["poll_interval"], timeout=p["timeout"])
    try:
        template_id, committed = client.upsert_template(p["project"], p["template_name"], p["content"],
                                                        p["comment"], p["language"])
        status = client.deploy(template_id, p["device_id"])
    except CatcError as exc:
        module.fail_json(msg=str(exc))
    result = dict(changed=True, template_id=template_id, version_committed=committed,
                  deployment_id=status.get("deploymentId"), deployment_status=status.get("status"),
                  devices=status.get("devices", []), content=p["content"].splitlines())
    if status.get("status") != "SUCCESS":
        details = [d.get("detailedStatusMessage") for d in status.get("devices", [])]
        module.fail_json(msg=f"Template deployment {status.get('status')}: {details}", **result)
    module.exit_json(**result)


if __name__ == "__main__":
    main()
