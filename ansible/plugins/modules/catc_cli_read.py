#!/usr/bin/python
# ansible/plugins/modules/catc_cli_read.py
"""Run read-only commands on one switch through Catalyst Center Command Runner."""

DOCUMENTATION = r"""
module: catc_cli_read
short_description: Run read-only (show) commands through Catalyst Center Command Runner
options:
  catc: {description: Catalyst Center login (host, username, password, validate_certs, ca_path), type: dict, required: true}
  device_id: {description: Catalyst Center device UUID (from catc_device), type: str, required: true}
  commands: {description: Commands to run, in order, type: list, elements: str, required: true}
  check_keywords: {description: Refuse commands whose first word Command Runner does not accept, type: bool, default: true}
  allow_failed: {description: Commands allowed to fail without failing the task, type: list, elements: str, default: []}
  timeout: {description: Seconds to wait for each Command Runner task, type: int, default: 600}
  poll_interval: {description: Seconds between task checks, type: int, default: 5}
"""

RETURN = r"""
output: {description: Output of each command, in the order given ('' if it failed). Not called stdout - Ansible expects stdout to be a string, type: list}
outputs: {description: command -> output, type: dict}
failed_commands: {description: command -> error, type: dict}
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.catc_client import CatcClient, CatcError, catc_argument_spec, open_url_request


def main():
    module = AnsibleModule(
        argument_spec=catc_argument_spec(
            device_id=dict(type="str", required=True),
            commands=dict(type="list", elements="str", required=True),
            check_keywords=dict(type="bool", default=True),
            allow_failed=dict(type="list", elements="str", default=[]),
        ),
        supports_check_mode=True,           # read-only: runs in check mode too
    )
    p, c = module.params, module.params["catc"]
    client = CatcClient(c["host"], c["username"], c["password"],
                        open_url_request(c["validate_certs"], c["ca_path"]),
                        poll_interval=p["poll_interval"], timeout=p["timeout"])
    try:
        outputs, failures = client.run_commands(p["device_id"], p["commands"], p["check_keywords"])
    except CatcError as exc:
        module.fail_json(msg=str(exc))
    output = [outputs.get(cmd, "") for cmd in p["commands"]]
    blocking = {k: v for k, v in failures.items() if k not in p["allow_failed"]}
    if blocking:
        module.fail_json(msg=f"Command Runner failed: {blocking}", output=output, outputs=outputs,
                         failed_commands=failures)
    module.exit_json(changed=False, output=output, outputs=outputs, failed_commands=failures)


if __name__ == "__main__":
    main()
