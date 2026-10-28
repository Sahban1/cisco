#!/usr/bin/python
# ansible/plugins/modules/catc_device.py
"""Look up one switch in Catalyst Center by hostname; optionally resync it."""

DOCUMENTATION = r"""
module: catc_device
short_description: Look up a managed device in Catalyst Center (and optionally resync it)
options:
  catc: {description: Catalyst Center login (host, username, password, validate_certs, ca_path), type: dict, required: true}
  hostname: {description: Device hostname as in the inventory, type: str, required: true}
  sync: {description: Ask Catalyst Center to resync the device inventory and config archive, type: bool, default: false}
  timeout: {description: Seconds to wait for a resync task, type: int, default: 600}
  poll_interval: {description: Seconds between task checks, type: int, default: 5}
"""

EXAMPLES = r"""
- name: Find the switch in Catalyst Center
  catc_device:
    catc: "{{ catc }}"
    hostname: "{{ inventory_hostname }}"
  register: ibns_catc_device
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.catc_client import CatcClient, CatcError, catc_argument_spec, open_url_request

KEEP = ("id", "hostname", "managementIpAddress", "softwareVersion", "platformId", "family", "role",
        "reachabilityStatus", "collectionStatus", "serialNumber", "lastUpdated")


def main():
    module = AnsibleModule(
        argument_spec=catc_argument_spec(hostname=dict(type="str", required=True),
                                         sync=dict(type="bool", default=False)),
        supports_check_mode=True,
    )
    p, c = module.params, module.params["catc"]
    client = CatcClient(c["host"], c["username"], c["password"],
                        open_url_request(c["validate_certs"], c["ca_path"]),
                        poll_interval=p["poll_interval"], timeout=p["timeout"])
    try:
        found = client.device(p["hostname"])
        device = {k: found.get(k) for k in KEEP}
        if p["sync"] and not module.check_mode:
            client.sync(device["id"])
            module.exit_json(changed=True, device=device, synced=True)
        module.exit_json(changed=False, device=device, synced=False)
    except CatcError as exc:
        module.fail_json(msg=str(exc))


if __name__ == "__main__":
    main()
