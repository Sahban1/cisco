# IBNS 2.0 repository: every file, in typing order

50 files. Each section ends with something you can run, so you find mistakes early. Paths are relative to the repo root.

## Catalyst Center update: what changed

Every read now goes through Command Runner and every change through Template Programmer; nothing uses SSH. Already typed the earlier version? New files are listed first and are in full in their phase below; changed files are shown as diffs here (`-` remove, `+` add) and in full in their phase.

- **New:** `ansible/plugins/module_utils/catc_client.py`
- **New:** `tests/test_catc_client.py`
- **New:** `ansible/plugins/modules/catc_device.py`
- **New:** `ansible/plugins/modules/catc_cli_read.py`
- **New:** `ansible/plugins/modules/catc_cli_push.py`
- **New:** `ansible/playbooks/roles/ibns_push/tasks/main.yml`
- **New:** `ansible/playbooks/roles/ibns_save/tasks/main.yml`
- **Changed:** `README.md`
- **Changed:** `ansible.cfg`
- **Changed:** `requirements.yml`
- **Changed:** `requirements-ibns.txt`
- **Changed:** `ansible/plugins/filter/ibns_filters.py`
- **Changed:** `tests/test_ibns_filters.py`
- **Changed:** `ansible/playbooks/group_vars/all.yml`
- **Changed:** `ansible/inventories/lab/hosts.yml`
- **Changed:** `ansible/playbooks/roles/inventory_lookup/tasks/main.yml`
- **Changed:** `ansible/playbooks/roles/ibns_collect/tasks/main.yml`
- **Changed:** `ansible/playbooks/roles/ibns_precheck/tasks/main.yml`
- **Changed:** `ansible/playbooks/ibns_classify.yml`
- **Changed:** `ansible/playbooks/roles/ibns_backup/tasks/main.yml`
- **Changed:** `ansible/playbooks/roles/ibns_convert/tasks/main.yml`
- **Changed:** `ansible/playbooks/ibns_stage1_convert.yml`
- **Changed:** `ansible/playbooks/roles/ibns_golden/tasks/main.yml`
- **Changed:** `ansible/playbooks/roles/ibns_rollback_golden/tasks/main.yml`
- **Changed:** `ansible/playbooks/ibns_stage2_golden.yml`
- **Changed:** `ansible/playbooks/ibns_rollback_golden.yml`
- **Changed:** `ansible/playbooks/roles/ibns_cleanup/tasks/main.yml`
- **Changed:** `ansible/playbooks/ibns_stage3_cleanup.yml`
- **Changed:** `ansible/aap_payload/templates/controller_templates.yml`
- **Changed:** `ansible/aap_payload/templates/controller_execution_environments.yml`
- **Changed:** `docs/runbook.md`
- **Changed:** `python/ibns_tools/classify_ports.py`

### Diff: `README.md`

````
--- a/README.md
+++ b/README.md
@@ -8,4 +8,7 @@
 ports, so ports are never without authentication and the golden config can be
 rolled back per port without a reload.
+
+Every read and every change goes through Catalyst Center. Nothing logs into a
+switch over SSH.
 
 ## Run order
@@ -31,4 +34,26 @@
 `dry_run` defaults to true everywhere.
 
+## How the jobs reach switches: Catalyst Center only
+
+| What | Catalyst Center feature | Code |
+| --- | --- | --- |
+| Find the switch, version, reachability | Inventory (`network-device`) | `catc_device` module |
+| Show commands (running config, sessions, AAA, flash) | Command Runner (read-only) | `catc_cli_read` module, `ibns_collect` role |
+| Every change (backup copy, convert, golden, re-point, rollback, cleanup, write memory) | Template Programmer | `catc_cli_push` module, `ibns_push` role |
+
+- Ansible renders the CLI (repo templates and `ibns_*` filters) and pushes it as
+  the content of ONE template per switch, `IBNS2_<hostname>` in project `IBNS2`.
+  Each push commits a new version with comment `<run id> <stage> <step>`, so
+  the template's version history in Catalyst Center records every change.
+- Exec commands use Catalyst Center template syntax: `#MODE_ENABLE` blocks and
+  `#INTERACTIVE` with `<IQ>`/`<R>` for the convert and copy prompts.
+- Hosts run with `ansible_connection: local` (set in `inventory_lookup`); the
+  modules call the Catalyst Center REST API from the controller.
+- The modules use ansible-core only (no collections), so the existing 2.16
+  execution environment works unchanged. AAP jobs carry the DNAC service-ID
+  credential, not a switch login.
+- `authentication display config-mode` is not a show command, so Command
+  Runner refuses it; the config mode is read from the running config instead.
+
 ## Port classification
 
@@ -39,5 +64,5 @@
 | config class | The interface config | `multi-domain`, `dot1x+mab`, `mab-only`, `trunk`, `static-access` |
 | role | The description, via `ibns_description_rules` | `user`, `phone`, `printer`, `ap`, `uplink` |
-| action | Both together, via `ibns_port_roles` | `migrate` (gets a golden template), `hold` (auth port the rules can't vouch for, left on the converted config), `leave` (not an auth port) |
+| action | Both together, via `ibns_port_roles` | `migrate` (gets a golden template), `hold` (auth port the rules can't vouch for, left on the converted config), `leave` (not an auth port), `done` (already on its golden template) |
 
 The template is always chosen by the config class, so the migration never
@@ -92,5 +117,5 @@
 | `ansible/aap_payload/templates/controller_inventories.yml` | Given in full in this repo |
 | `ansible/aap_payload/templates/controller_inventory_source.yml` | Given in full in this repo |
-| `ansible/playbooks/roles/inventory_lookup/tasks/main.yml` | Given in full in this repo |
+| `ansible/playbooks/roles/inventory_lookup/tasks/main.yml` | Given in full in this repo (hosts run locally, no SSH) |
 
 ### Replace (ud00's version doesn't apply)
@@ -106,15 +131,17 @@
 | Path | Purpose |
 | --- | --- |
-| `ansible/plugins/filter/ibns_filters.py` | All parsing and comparison logic |
-| `tests/test_ibns_filters.py` | Unit tests for the filters (`pytest -q`) |
+| `ansible/plugins/filter/ibns_filters.py` | All parsing, comparison and CLI-building logic |
+| `ansible/plugins/module_utils/catc_client.py` | Catalyst Center REST client (Command Runner, Template Programmer) |
+| `ansible/plugins/modules/catc_device.py`, `catc_cli_read.py`, `catc_cli_push.py` | The three Catalyst Center modules every role uses |
+| `tests/test_ibns_filters.py`, `tests/test_catc_client.py` | Unit tests (`pytest -q`); the client tests use a fake Catalyst Center |
 | `ansible/playbooks/group_vars/all.yml` | IBNS settings, safety defaults, golden names |
 | `ansible/playbooks/ibns_target.yml` | Target resolution, imported by every playbook |
 | `ansible/playbooks/ibns_*.yml` | The eight playbooks in the run order above (classify plus the seven stage playbooks) |
-| `ansible/playbooks/roles/ibns_*/tasks/*.yml` | collect, precheck, backup, convert, golden, rollback_golden, postcheck, cleanup, snapshot, report, input_validation |
+| `ansible/playbooks/roles/ibns_*/tasks/*.yml` | collect, precheck, push, save, backup, convert, golden, rollback_golden, postcheck, cleanup, snapshot, report, input_validation |
 | `ansible/templates/ibns2/global.j2`, `interface_templates.j2` | Golden config (draft) |
 | `ansible/inventories/lab/hosts.yml` | Static lab inventory |
 | `python/ibns_tools/ibns_discovery.py` | Discovery, variants, drift |
 | `python/ibns_tools/classify_ports.py` | Port roles from descriptions + config, offline, all sites |
-| `requirements.yml` | Collections for laptop runs |
+| `requirements.yml` | Empty: no collections needed |
 | `docs/runbook.md` | What to do for each outcome |
 
@@ -127,5 +154,5 @@
 `inventories/*/sdwan.yml`, `inventories/plugins/vmanage.py`,
 `inventories/group_vars/all.yml` (replaced by `playbooks/group_vars/all.yml`),
-`inventories/group_vars/cisco_switches.yml` (ud00's vault-encrypted logins),
+`inventories/group_vars/cisco_switches.yml` (ud00's vault-encrypted switch logins; IBNS never logs into switches),
 `cml/topologies/cat9K.yml`, `scripts/orchestrate_workflow.py`.
 
@@ -134,5 +161,7 @@
 ```bash
 source .venv/bin/activate
-export DEVOPS_USERNAME=<lab user>; read -s DEVOPS_PASSWORD && export DEVOPS_PASSWORD
+export DEVOPS_USERNAME=<Catalyst Center user>; read -s DEVOPS_PASSWORD && export DEVOPS_PASSWORD
+export CATC_HOST=<lab Catalyst Center>              # if the inventory has no dnac_host
+export CATC_CA_BUNDLE=<path to RBC CA bundle>       # if the RBC CA isn't trusted by Python
 pytest -q
 python python/ibns_tools/classify_ports.py --config <saved lab config>.cfg
@@ -151,5 +180,11 @@
 - Description rules against real descriptions (`unmatched_descriptions.csv`),
   and which roles each config class is allowed with.
-- The `authentication convert-to new-style` confirmation prompt text.
+- The `authentication convert-to new-style` confirmation prompt text
+  (`ibns_convert_prompt`), pushed through `#INTERACTIVE`.
+- Catalyst Center: the API calls in `catc_client.py` on our version; that
+  Command Runner accepts every command in `ibns_collect` (including
+  `dir flash:`) and what its output looks like; `#MODE_ENABLE`/`#INTERACTIVE`
+  in a JINJA template; whether an API deployment also writes memory.
+- That the DNAC service account may run Command Runner and deploy templates.
 - Golden templates: closed vs low-impact, timers, critical auth with ClearPass down.
 - Session recovery time after re-pointing (`ibns_reauth_wait`).
````

### Diff: `ansible.cfg`

```diff
--- a/ansible.cfg
+++ b/ansible.cfg
@@ -3,4 +3,5 @@
 # anything that enables the dnac inventory plugin), then add the lines marked NEW.
 # AAP reads this file from the project root, so it applies in AAP and on the laptop.
+# No SSH settings: IBNS never logs into switches, everything goes through Catalyst Center.
 
 [defaults]
@@ -8,4 +9,6 @@
 roles_path = ansible/playbooks/roles                    ; NEW if ud00 doesn't set it
 filter_plugins = ansible/plugins/filter                 ; NEW (required: ibns_* filters)
+library = ansible/plugins/modules                       ; NEW (required: catc_* Catalyst Center modules)
+module_utils = ansible/plugins/module_utils             ; NEW (required: catc_client shared by the modules)
 inventory_plugins = ansible/inventories/plugins         ; keep ud00's value if different
 collections_path = ./collections                        ; NEW (laptop: collections installed into the repo)
@@ -15,6 +18,2 @@
 [inventory]
 enable_plugins = dnac, yaml, ini, host_list, auto       ; keep ud00's value if different
-
-[persistent_connection]
-connect_timeout = 30
-command_timeout = 120                                   ; NEW: show running-config and the conversion can be slow
```

### Diff: `requirements.yml`

```diff
--- a/requirements.yml
+++ b/requirements.yml
@@ -2,9 +2,7 @@
 # NEW. Ansible collections for laptop runs:
 #   ansible-galaxy collection install -r requirements.yml -p ./collections
-# In AAP these must already be inside the execution environment image.
+# IBNS needs NO collections: it talks to Catalyst Center through its own modules
+# (ansible/plugins/modules/catc_*.py), which use ansible-core only. That means
+# the existing 2.16 execution environment works as it is.
 ---
-collections:
-  - name: cisco.ios
-  - name: cisco.catalystcenter
-  - name: ansible.netcommon
-  - name: ansible.utils
+collections: []
```

### Diff: `requirements-ibns.txt`

```diff
--- a/requirements-ibns.txt
+++ b/requirements-ibns.txt
@@ -6,5 +6,4 @@
 ansible-lint
 catalystcentersdk
-paramiko
 requests
 pytest
```

### Diff: `ansible/plugins/filter/ibns_filters.py`

```diff
--- a/ansible/plugins/filter/ibns_filters.py
+++ b/ansible/plugins/filter/ibns_filters.py
@@ -64,12 +64,21 @@
 # ------------------------------------------------------------ show parsers --
 
-def ibns_config_mode(output):
-    """Parse `authentication display config-mode` -> legacy | new-style | unknown."""
-    text = _text(output).lower()
-    if "legacy" in text:
-        return "legacy"
-    if "new-style" in text or "new style" in text:
-        return "new-style"
-    return "unknown"
+def ibns_config_mode_from_running(running_config):
+    """Legacy or new-style, worked out from the running config.
+    Used instead of 'authentication display config-mode', which Command Runner
+    does not accept (not a show command). Legacy interface commands win: a
+    switch with any of them has not been converted."""
+    legacy = new = False
+    for parent, children in _blocks(running_config):
+        if not PHYSICAL.match(parent):
+            continue
+        for c in children:
+            if c.startswith(("authentication port-control", "authentication host-mode",
+                             "authentication order", "authentication priority")):
+                legacy = True
+            elif c.startswith(("access-session port-control", "service-policy type control subscriber",
+                               "source template")):
+                new = True
+    return "legacy" if legacy else ("new-style" if new else "unknown")
 
 
@@ -160,5 +169,5 @@
 
 def ibns_flash_free(output):
-    """Parse `dir flash: | include bytes free` -> free bytes (int, 0 if not found)."""
+    """Parse `dir flash:` output -> free bytes (int, 0 if not found)."""
     m = re.search(r"\((\d+) bytes free", _text(output))
     return int(m.group(1)) if m else 0
@@ -231,4 +240,6 @@
 #            listed in the pre-check (fails the switch above ibns_max_held_ports)
 #   leave    not an auth port (trunk, uplink, static) -> never touched
+#   done     already on its golden template (only 'source template' left) ->
+#            nothing to do; the class is read back from the template name
 
 def ibns_port_descriptions(running_config):
@@ -274,6 +285,14 @@
     classes = ibns_classify_ports(running_config)
     descriptions = ibns_port_descriptions(running_config)
+    auth = ibns_interface_auth_lines(running_config)
+    template_class = {}
+    for c, t in reversed(list(port_templates.items())):   # first class listed wins
+        template_class[t] = c
     inventory = {}
     for intf, cls in classes.items():
+        on_golden = [l[len("source template "):] for l in auth.get(intf, [])
+                     if l.startswith("source template ") and l[len("source template "):] in template_class]
+        if on_golden:
+            cls = template_class[on_golden[0]]          # golden port: class from its template
         desc = descriptions.get(intf, "")
         role = next((r for p, r in compiled if desc and p.search(desc)), "")
@@ -299,4 +318,6 @@
             action, template = "hold", ""
             reason = f"role '{role}' is set to migrate: false but the port has auth config"
+        elif on_golden and auth.get(intf) == [f"source template {template}"]:
+            action = "done"
         elif status == "ok":
             action = "migrate"
@@ -340,11 +361,4 @@
 
 
-def ibns_access_ports(port_classes, port_templates):
-    """{interface: class} + {class: template} -> {interface: template} for ports
-    that get a golden template. Classes without a template are left alone."""
-    return {intf: port_templates[cls] for intf, cls in port_classes.items()
-            if cls in AUTH_CLASSES and cls in port_templates}
-
-
 def ibns_repoint_commands(auth_lines, template):
     """Commands to move one interface onto a golden template.
@@ -361,4 +375,46 @@
     cmds = [l for l in saved_lines if not l.startswith("source template ")]
     return cmds + [f"no source template {template}"]
+
+
+# ------------------------------------------- CLI for Catalyst Center push --
+# Catalyst Center templates run in config mode. Exec commands go between
+# #MODE_ENABLE / #MODE_END_ENABLE; a command that asks a question goes inside
+# #INTERACTIVE / #ENDS_INTERACTIVE as  command<IQ>question<R>answer.
+
+def ibns_cli_exec(commands):
+    """[str | {command, prompt, answer}] -> exec-mode block for a template."""
+    lines = ["#MODE_ENABLE"]
+    for c in commands:
+        if isinstance(c, dict) and c.get("prompt"):
+            lines += ["#INTERACTIVE", f"{c['command']}<IQ>{c['prompt']}<R>{c.get('answer', '')}",
+                      "#ENDS_INTERACTIVE"]
+        else:
+            lines.append(c["command"] if isinstance(c, dict) else str(c))
+    lines.append("#MODE_END_ENABLE")
+    return "\n".join(lines)
+
+
+def ibns_cli_interfaces(commands_by_intf):
+    """{interface: [lines]} -> 'interface X' blocks, in interface order."""
+    out = []
+    for intf in sorted(commands_by_intf, key=_intf_key):
+        if commands_by_intf[intf]:
+            out.append(f"interface {intf}")
+            out += [f" {l}" for l in commands_by_intf[intf]]
+    return "\n".join(out)
+
+
+def _intf_key(name):
+    return [int(n) if n.isdigit() else n for n in re.split(r"(\d+)", name)]
+
+
+def ibns_repoint_cli(port_plan, auth_lines):
+    """Stage 2: CLI moving every planned port onto its golden template."""
+    return ibns_cli_interfaces({i: ibns_repoint_commands(auth_lines.get(i, []), t) for i, t in port_plan.items()})
+
+
+def ibns_rollback_cli(port_plan, auth_lines):
+    """Stage 2 rollback: CLI putting every planned port back on its converted lines."""
+    return ibns_cli_interfaces({i: ibns_rollback_commands(auth_lines.get(i, []), t) for i, t in port_plan.items()})
 
 
@@ -499,5 +555,9 @@
     def filters(self):
         return {
-            "ibns_config_mode": ibns_config_mode,
+            "ibns_config_mode_from_running": ibns_config_mode_from_running,
+            "ibns_cli_exec": ibns_cli_exec,
+            "ibns_cli_interfaces": ibns_cli_interfaces,
+            "ibns_repoint_cli": ibns_repoint_cli,
+            "ibns_rollback_cli": ibns_rollback_cli,
             "ibns_aaa_servers": ibns_aaa_servers,
             "ibns_flash_free": ibns_flash_free,
@@ -513,5 +573,4 @@
             "ibns_port_summary": ibns_port_summary,
             "ibns_interface_auth_lines": ibns_interface_auth_lines,
-            "ibns_access_ports": ibns_access_ports,
             "ibns_repoint_commands": ibns_repoint_commands,
             "ibns_rollback_commands": ibns_rollback_commands,
```

### Diff: `tests/test_ibns_filters.py`

```diff
--- a/tests/test_ibns_filters.py
+++ b/tests/test_ibns_filters.py
@@ -148,7 +148,18 @@
 
 
-def test_config_mode():
-    assert f.ibns_config_mode("Current configuration mode is legacy") == "legacy"
-    assert f.ibns_config_mode(["Current configuration mode is new-style"]) == "new-style"
+LEGACY_CONFIG = """
+interface GigabitEthernet1/0/1
+ switchport mode access
+ authentication port-control auto
+ mab
+ dot1x pae authenticator
+!
+"""
+
+
+def test_config_mode_from_running():
+    assert f.ibns_config_mode_from_running(LEGACY_CONFIG) == "legacy"
+    assert f.ibns_config_mode_from_running(CONVERTED_CONFIG) == "new-style"
+    assert f.ibns_config_mode_from_running("hostname x\n") == "unknown"
 
 
@@ -169,8 +180,17 @@
 
 
-def test_access_ports_mapping_skips_trunks():
-    classes = f.ibns_classify_ports(CONVERTED_CONFIG)
-    mapping = f.ibns_access_ports(classes, {"multi-domain": "IBNS2_MDA", "mab-only": "IBNS2_MAB"})
-    assert mapping == {"GigabitEthernet1/0/1": "IBNS2_MDA", "GigabitEthernet1/0/5": "IBNS2_MAB"}
+def test_cli_for_catalyst_center_templates():
+    exec_block = f.ibns_cli_exec([{"command": "authentication convert-to new-style", "prompt": "continue",
+                                   "answer": "yes"}, "write memory"])
+    assert exec_block.splitlines() == [
+        "#MODE_ENABLE", "#INTERACTIVE", "authentication convert-to new-style<IQ>continue<R>yes",
+        "#ENDS_INTERACTIVE", "write memory", "#MODE_END_ENABLE"]
+    lines = f.ibns_interface_auth_lines(CONVERTED_CONFIG)
+    plan = {"GigabitEthernet1/0/5": "IBNS2_MAB", "GigabitEthernet1/0/1": "IBNS2_MDA"}
+    cli = f.ibns_repoint_cli(plan, lines).splitlines()
+    assert cli[0] == "interface GigabitEthernet1/0/1" and cli[1] == " source template IBNS2_MDA"
+    assert "interface GigabitEthernet1/0/5" in cli and " no mab" in cli
+    back = f.ibns_rollback_cli(plan, lines).splitlines()
+    assert back[-1] == " no source template IBNS2_MAB"
 
 
@@ -321,4 +341,13 @@
 
 
+def test_ports_already_on_golden_templates_are_done():
+    golden = DESCRIBED_CONFIG.replace(" access-session port-control auto\n mab\n!\ninterface GigabitEthernet1/0/3",
+                                      " source template IBNS2_MAB\n!\ninterface GigabitEthernet1/0/3")
+    inv = f.ibns_port_inventory(golden, RULES, ROLES, TEMPLATES)
+    assert inv["GigabitEthernet1/0/2"]["config_class"] == "mab-only"     # read back from the template
+    assert inv["GigabitEthernet1/0/2"]["action"] == "done"
+    assert "GigabitEthernet1/0/2" not in f.ibns_port_plan(inv)
+
+
 def test_bad_rule_regex_is_reported():
     try:
```

### Diff: `ansible/playbooks/group_vars/all.yml`

```diff
--- a/ansible/playbooks/group_vars/all.yml
+++ b/ansible/playbooks/group_vars/all.yml
@@ -3,10 +3,23 @@
 # Values marked DECIDE need a team decision; values marked CONFIRM need checking.
 ---
-# ---- switch login ----------------------------------------------------------
-# AAP: the service-ID credential injects DEVOPS_USERNAME / DEVOPS_PASSWORD.
-#      CONFIRM with Gurkirat which service ID logs into switches.
-# Laptop: export DEVOPS_USERNAME and DEVOPS_PASSWORD before running.
-ansible_user: "{{ lookup('ansible.builtin.env', 'DEVOPS_USERNAME') }}"
-ansible_password: "{{ lookup('ansible.builtin.env', 'DEVOPS_PASSWORD') }}"
+# ---- Catalyst Center (every read and every change goes through it) -----------
+# No SSH to switches. Reads: Command Runner. Changes: Template Programmer.
+# AAP: the DNAC service-ID credential injects DEVOPS_USERNAME / DEVOPS_PASSWORD.
+# Laptop: export DEVOPS_USERNAME, DEVOPS_PASSWORD (Catalyst Center login) and
+#         CATC_HOST; CATC_CA_BUNDLE if the RBC CA isn't in the system store.
+# CONFIRM: dnac_host from the dnac inventory plugin is the Catalyst Center
+#          address that manages the switch (else set CATC_HOST).
+catc_host: "{{ dnac_host | default(lookup('ansible.builtin.env', 'CATC_HOST'), true) }}"
+catc:
+  host: "{{ catc_host }}"
+  username: "{{ lookup('ansible.builtin.env', 'DEVOPS_USERNAME') }}"
+  password: "{{ lookup('ansible.builtin.env', 'DEVOPS_PASSWORD') }}"
+  validate_certs: true
+  ca_path: "{{ lookup('ansible.builtin.env', 'CATC_CA_BUNDLE') }}"
+catc_template_project: IBNS2            # Template Programmer project (created if missing)
+catc_template_prefix: IBNS2_            # one template per switch: IBNS2_<hostname>
+catc_template_language: JINJA           # CONFIRM #MODE_ENABLE / #INTERACTIVE work in JINJA on our version
+catc_deploy_timeout: 900                # seconds to wait for a deployment
+ibns_catc_ok_collection: [Managed]      # collection status the pre-check accepts
 
 # ---- safety defaults ---------------------------------------------------------
@@ -21,4 +34,7 @@
 ibns_min_aaa_up: 1                  # RADIUS servers to ClearPass that must be UP
 ibns_min_flash_bytes: 10485760      # 10 MB free for the config backup
+ibns_flash_command: "dir flash:"    # CONFIRM Command Runner accepts 'dir' (else "show flash:")
+ibns_flash_backup: true             # also copy the running config to flash before each change
+ibns_convert_prompt: "continue"     # CONFIRM: text in the convert-to new-style confirmation prompt
 
 # ---- post-check --------------------------------------------------------------
```

### Diff: `ansible/inventories/lab/hosts.yml`

```diff
--- a/ansible/inventories/lab/hosts.yml
+++ b/ansible/inventories/lab/hosts.yml
@@ -1,8 +1,9 @@
 # ansible/inventories/lab/hosts.yml
-# NEW. Static lab inventory for laptop runs until the lab switch is in
-# Catalyst Center. Use with: ansible-playbook -i ansible/inventories/lab/hosts.yml ...
+# NEW. Static lab inventory for laptop runs. The lab switch must be managed by
+# the lab Catalyst Center: every job reaches it through Catalyst Center, never
+# over SSH. Use with: ansible-playbook -i ansible/inventories/lab/hosts.yml ...
 ---
 all:
   hosts:
-    <LAB-SWITCH-HOSTNAME>:
-      ansible_host: <LAB-SWITCH-MGMT-IP>
+    <LAB-SWITCH-HOSTNAME>:                  # exactly as Catalyst Center shows it
+      dnac_host: <LAB-CATALYST-CENTER>      # address of the Catalyst Center that manages it
```

### Diff: `ansible/playbooks/roles/inventory_lookup/tasks/main.yml`

```diff
--- a/ansible/playbooks/roles/inventory_lookup/tasks/main.yml
+++ b/ansible/playbooks/roles/inventory_lookup/tasks/main.yml
@@ -1,8 +1,10 @@
 # roles/inventory_lookup/tasks/main.yml
-# COPIED FROM ud00 AND EDITED. Three changes from the ud00 version:
+# COPIED FROM ud00 AND EDITED. Four changes from the ud00 version:
 #   1. group swim_devices        -> ibns_targets
 #   2. subgroup prefix swim_     -> ibns_
 #   3. controller_host falls back to 'lab' for hosts from the static lab
 #      inventory (they have no dnac_host); the vManage fallback is removed.
+#   4. hosts run LOCALLY (ansible_connection: local): IBNS never logs into a
+#      switch; every task talks to Catalyst Center from the controller.
 ---
 - name: Validate device_list is non-empty and contains no blank entries
@@ -31,6 +33,5 @@
       - ibns_targets
       - "{{ controller_subgroup }}"
-    ansible_network_os: cisco.ios.ios
-    ansible_connection: network_cli
-    ansible_become_method: enable
+    ansible_connection: local
+    ansible_python_interpreter: "{{ ansible_playbook_python }}"
   loop: "{{ device_list }}"
```

### Diff: `ansible/playbooks/roles/ibns_collect/tasks/main.yml`

```diff
--- a/ansible/playbooks/roles/ibns_collect/tasks/main.yml
+++ b/ansible/playbooks/roles/ibns_collect/tasks/main.yml
@@ -1,10 +1,24 @@
 # roles/ibns_collect/tasks/main.yml
-# Read-only. Collects the switch state every stage needs and parses it into the
-# fact `ibns_state` (running config, config mode, AAA servers, sessions,
-# port classes, port inventory from descriptions + config, migration plan,
+# Read-only, through Catalyst Center (no SSH to the switch).
+# Finds the switch in Catalyst Center (fact `ibns_device`), runs the show
+# commands through Command Runner, and parses them into the fact `ibns_state`
+# (running config, config mode, AAA servers, sessions, flash free, port
+# classes, port inventory from descriptions + config, migration plan,
 # interface auth lines).
 ---
-- name: Collect running config, AAA server state and sessions
-  cisco.ios.ios_command:
+- name: Find the switch in Catalyst Center
+  catc_device:
+    catc: "{{ catc }}"
+    hostname: "{{ inventory_hostname }}"
+  register: ibns_catc_device
+
+- name: Keep the Catalyst Center device record
+  ansible.builtin.set_fact:
+    ibns_device: "{{ ibns_catc_device.device }}"
+
+- name: Run show commands through Command Runner
+  catc_cli_read:
+    catc: "{{ catc }}"
+    device_id: "{{ ibns_device.id }}"
     commands:
       - show running-config
@@ -12,12 +26,6 @@
       - show access-session method dot1x details
       - show access-session method mab details
+      - "{{ ibns_flash_command }}"
   register: ibns_raw
-
-- name: Read authentication config mode (legacy or new-style)
-  cisco.ios.ios_command:
-    commands:
-      - authentication display config-mode
-  register: ibns_mode_raw
-  failed_when: false
 
 - name: Parse collected output
@@ -25,11 +33,12 @@
     ibns_state:
       collected_at: "{{ now(utc=true, fmt='%Y-%m-%dT%H:%M:%SZ') }}"
-      running: "{{ ibns_raw.stdout[0] }}"
-      config_mode: "{{ (ibns_mode_raw.stdout | default([''])) | ibns_config_mode }}"
-      aaa_servers: "{{ ibns_raw.stdout[1] | ibns_aaa_servers }}"
-      sessions: "{{ [ibns_raw.stdout[2], ibns_raw.stdout[3]] | ibns_parse_session_details }}"
-      port_classes: "{{ ibns_raw.stdout[0] | ibns_classify_ports }}"
-      port_inventory: "{{ ibns_raw.stdout[0] | ibns_port_inventory(ibns_description_rules, ibns_port_roles, ibns_port_templates, ibns_hold_unmatched) }}"
-      auth_lines: "{{ ibns_raw.stdout[0] | ibns_interface_auth_lines }}"
+      running: "{{ ibns_raw.output[0] }}"
+      config_mode: "{{ ibns_raw.output[0] | ibns_config_mode_from_running }}"
+      aaa_servers: "{{ ibns_raw.output[1] | ibns_aaa_servers }}"
+      sessions: "{{ [ibns_raw.output[2], ibns_raw.output[3]] | ibns_parse_session_details }}"
+      flash_free: "{{ ibns_raw.output[4] | ibns_flash_free }}"
+      port_classes: "{{ ibns_raw.output[0] | ibns_classify_ports }}"
+      port_inventory: "{{ ibns_raw.output[0] | ibns_port_inventory(ibns_description_rules, ibns_port_roles, ibns_port_templates, ibns_hold_unmatched) }}"
+      auth_lines: "{{ ibns_raw.output[0] | ibns_interface_auth_lines }}"
 
 - name: Work out which ports migrate and which are held
```

### Diff: `ansible/playbooks/roles/ibns_precheck/tasks/main.yml`

```diff
--- a/ansible/playbooks/roles/ibns_precheck/tasks/main.yml
+++ b/ansible/playbooks/roles/ibns_precheck/tasks/main.yml
@@ -1,32 +1,29 @@
 # roles/ibns_precheck/tasks/main.yml
-# Read-only gate before any stage. Collects state (ibns_collect) and checks it.
-# Input: ibns_expected_mode = legacy | new-style | any
+# Read-only gate before any stage. Collects state through Catalyst Center
+# (ibns_collect) and checks it.
+# Inputs: ibns_expected_mode = legacy | new-style | any
+#         ibns_check_migration = true (default) | false for stage 3, where ports
+#         are already on golden templates and nothing is left to migrate
 # On failure the switch is reported as "skipped" and removed from the run;
 # other switches in the job carry on.
 ---
-- name: Gather IOS-XE version
-  cisco.ios.ios_facts:
-    gather_subset: min
-
 - name: Collect switch state
   ansible.builtin.include_role:
     name: ibns_collect
 
-- name: Read free flash space
-  cisco.ios.ios_command:
-    commands:
-      - "dir flash: | include bytes free"
-  register: ibns_flash
-
 - name: Start with no failures
   ansible.builtin.set_fact:
     ibns_precheck_failures: []
-    ibns_flash_free: "{{ ibns_flash.stdout[0] | ibns_flash_free }}"
     ibns_aaa_up: "{{ ibns_state.aaa_servers | selectattr('state', 'equalto', 'UP') | list | length }}"
 
+- name: Check Catalyst Center can manage the switch
+  when: ibns_device.reachabilityStatus != 'Reachable' or ibns_device.collectionStatus not in ibns_catc_ok_collection
+  ansible.builtin.set_fact:
+    ibns_precheck_failures: "{{ ibns_precheck_failures + ['Catalyst Center shows ' ~ ibns_device.reachabilityStatus ~ ' / ' ~ ibns_device.collectionStatus] }}"
+
 - name: Check IOS-XE version
-  when: ansible_net_version is version(ibns_min_iosxe, '<')
+  when: ibns_device.softwareVersion is version(ibns_min_iosxe, '<')
   ansible.builtin.set_fact:
-    ibns_precheck_failures: "{{ ibns_precheck_failures + ['IOS-XE ' ~ ansible_net_version ~ ' is below ' ~ ibns_min_iosxe] }}"
+    ibns_precheck_failures: "{{ ibns_precheck_failures + ['IOS-XE ' ~ ibns_device.softwareVersion ~ ' is below ' ~ ibns_min_iosxe] }}"
 
 - name: Check RADIUS servers to ClearPass are UP
@@ -41,15 +38,19 @@
 
 - name: Check free flash for the config backup
-  when: ibns_flash_free | int < ibns_min_flash_bytes | int
+  when: ibns_state.flash_free | int < ibns_min_flash_bytes | int
   ansible.builtin.set_fact:
-    ibns_precheck_failures: "{{ ibns_precheck_failures + ['only ' ~ ibns_flash_free ~ ' bytes free on flash'] }}"
+    ibns_precheck_failures: "{{ ibns_precheck_failures + ['only ' ~ ibns_state.flash_free ~ ' bytes free on flash'] }}"
 
 - name: Check there are access ports to migrate
-  when: ibns_state.port_plan | length == 0
+  when:
+    - ibns_check_migration | default(true) | bool
+    - ibns_state.port_plan | length == 0
   ansible.builtin.set_fact:
     ibns_precheck_failures: "{{ ibns_precheck_failures + ['no access ports to migrate (no auth ports whose description and config agree)'] }}"
 
 - name: Check held ports (description and config disagree, or no rule matched)
-  when: ibns_state.held_ports | length > ibns_max_held_ports | int
+  when:
+    - ibns_check_migration | default(true) | bool
+    - ibns_state.held_ports | length > ibns_max_held_ports | int
   ansible.builtin.set_fact:
     ibns_precheck_failures: "{{ ibns_precheck_failures + [(ibns_state.held_ports | length) ~ ' held port(s), allowed ' ~ ibns_max_held_ports ~ ': ' ~ (ibns_state.held_ports | join(' | '))] }}"
```

### Diff: `ansible/playbooks/ibns_classify.yml`

```diff
--- a/ansible/playbooks/ibns_classify.yml
+++ b/ansible/playbooks/ibns_classify.yml
@@ -41,8 +41,12 @@
         ibns_result:
           stage: classify
-          outcome: "{{ 'ready' if (ibns_state.held_ports | length <= ibns_max_held_ports | int and ibns_state.port_plan | length > 0) else 'NEEDS-FIX' }}"
+          outcome: >-
+            {{ 'NEEDS-FIX' if ibns_state.held_ports | length > ibns_max_held_ports | int else
+               ('ready' if ibns_state.port_plan | length > 0 else
+               ('done' if ibns_summary.action.done | default(0) > 0 else 'NOTHING-TO-MIGRATE')) }}
           detail: >-
             {{ ibns_summary.ports }} ports: migrate {{ ibns_summary.action.migrate | default(0) }},
-            hold {{ ibns_summary.action.hold | default(0) }}, leave {{ ibns_summary.action.leave | default(0) }};
+            hold {{ ibns_summary.action.hold | default(0) }}, leave {{ ibns_summary.action.leave | default(0) }},
+            done {{ ibns_summary.action.done | default(0) }};
             roles {{ ibns_summary.role }};
             held: {{ ibns_state.held_ports }}
```

### Diff: `ansible/playbooks/roles/ibns_backup/tasks/main.yml`

```diff
--- a/ansible/playbooks/roles/ibns_backup/tasks/main.yml
+++ b/ansible/playbooks/roles/ibns_backup/tasks/main.yml
@@ -1,4 +1,5 @@
 # roles/ibns_backup/tasks/main.yml
-# Saves the running config off-box (snapshot store) and on the switch's flash.
+# Saves the running config off-box (snapshot store) and on the switch's flash
+# (through Catalyst Center). Catalyst Center's own config archive is a third copy.
 # Inputs: ibns_stage_tag (e.g. "stage1"), ibns_run_id, ibns_state (from ibns_collect)
 ---
@@ -12,8 +13,9 @@
 
 - name: Copy running config to flash
-  when: not (dry_run | bool)
-  cisco.ios.ios_command:
-    commands:
-      - command: "copy running-config flash:ibns-before-{{ ibns_stage_tag }}-{{ ibns_run_id }}.cfg"
-        prompt: "Destination filename"
-        answer: "\r"
+  when: ibns_flash_backup | bool
+  ansible.builtin.include_role:
+    name: ibns_push
+  vars:
+    ibns_backup_file: "ibns-before-{{ ibns_stage_tag }}-{{ ibns_run_id }}.cfg"
+    ibns_push_step: backup
+    ibns_push_cli: "{{ [{'command': 'copy running-config flash:' ~ ibns_backup_file, 'prompt': 'Destination filename', 'answer': ibns_backup_file}] | ibns_cli_exec }}"
```

### Diff: `ansible/playbooks/roles/ibns_convert/tasks/main.yml`

```diff
--- a/ansible/playbooks/roles/ibns_convert/tasks/main.yml
+++ b/ansible/playbooks/roles/ibns_convert/tasks/main.yml
@@ -1,22 +1,11 @@
 # roles/ibns_convert/tasks/main.yml
-# Stage 1 change. ONE-WAY: there is no command to go back to legacy.
-# Verify the confirmation prompt text on the lab switch and adjust `prompt`.
+# Stage 1 change, pushed through Catalyst Center. ONE-WAY: there is no command
+# to go back to legacy. The command asks for confirmation; ibns_convert_prompt
+# must match the prompt text (VERIFY on the lab switch).
 ---
-- name: Dry run - describe the change
-  when: dry_run | bool
-  ansible.builtin.debug:
-    msg: "DRY RUN: would run 'authentication convert-to new-style' on {{ inventory_hostname }} (one-way, no save)."
-
 - name: Convert legacy auth config to new-style (one-way)
-  when: not (dry_run | bool)
-  cisco.ios.ios_command:
-    commands:
-      - command: authentication convert-to new-style
-        prompt: "continue"
-        answer: "yes"
-  register: ibns_convert_output
-
-- name: Show conversion output
-  when: not (dry_run | bool)
-  ansible.builtin.debug:
-    var: ibns_convert_output.stdout_lines
+  ansible.builtin.include_role:
+    name: ibns_push
+  vars:
+    ibns_push_step: convert
+    ibns_push_cli: "{{ [{'command': 'authentication convert-to new-style', 'prompt': ibns_convert_prompt, 'answer': 'yes'}] | ibns_cli_exec }}"
```

### Diff: `ansible/playbooks/ibns_stage1_convert.yml`

```diff
--- a/ansible/playbooks/ibns_stage1_convert.yml
+++ b/ansible/playbooks/ibns_stage1_convert.yml
@@ -2,7 +2,10 @@
 # RUN ORDER: 3 (change window)
 # Stage 1: convert legacy dot1x config to new-style IN PLACE. ONE-WAY.
+# Every change is pushed through Catalyst Center (roles/ibns_push).
 #   pass -> write memory
-#   fail -> config NOT saved, switch flagged FIX-FORWARD-REQUIRED (runbook:
-#           fix in new-style syntax; console/OOB restore is the last resort)
+#   fail -> no write memory from us, switch flagged FIX-FORWARD-REQUIRED
+#           (runbook: fix in new-style syntax; console/OOB restore is the last
+#           resort). VERIFY in the lab whether a Catalyst Center deployment
+#           saves the config by itself; if it does, a reload won't undo anything.
 ---
 - name: Resolve targets
@@ -46,7 +49,6 @@
         - not (dry_run | bool)
         - ibns_check_passed | bool
-      cisco.ios.ios_command:
-        commands:
-          - write memory
+      ansible.builtin.include_role:
+        name: ibns_save
 
     - name: Report
@@ -65,5 +67,6 @@
       ansible.builtin.fail:
         msg: >-
-          Post-check failed after conversion. Config was NOT saved.
+          Post-check failed after conversion. We did not write memory
+          (check whether Catalyst Center saved it).
           Fix forward in new-style syntax (see docs/runbook.md); console/OOB
           restore is the last resort. Do not reload this switch.
```

### Diff: `ansible/playbooks/roles/ibns_golden/tasks/main.yml`

```diff
--- a/ansible/playbooks/roles/ibns_golden/tasks/main.yml
+++ b/ansible/playbooks/roles/ibns_golden/tasks/main.yml
@@ -1,6 +1,7 @@
 # roles/ibns_golden/tasks/main.yml
-# Stage 2 change: add the golden config ALONGSIDE the converted config, then
-# re-point each access port (template attached first, converted interface lines
-# stripped after), so the port is never without authentication.
+# Stage 2 change, pushed through Catalyst Center: add the golden config
+# ALONGSIDE the converted config, then re-point each planned access port
+# (template attached first, converted interface lines stripped after), so the
+# port is never without authentication. Three pushes: global, templates, ports.
 # Inputs: ibns_state (from pre-check), ibns_run_id
 ---
@@ -18,5 +19,6 @@
     ibns_port_plan: "{{ ibns_state.port_plan }}"
 
-- name: Save the rollback data (converted interface config + plan)
+- name: Save the rollback data (converted interface config + plan; not in dry run, so a dry run never overwrites real rollback data)
+  when: not (dry_run | bool)
   ansible.builtin.include_role:
     name: ibns_snapshot
@@ -29,33 +31,32 @@
     - "stage2-rollback-latest.json"
 
-- name: Dry run - show the rendered golden config and port changes
-  when: dry_run | bool
+- name: List held ports (not touched by this stage)
+  when: ibns_state.held_ports | length > 0
   ansible.builtin.debug:
-    msg:
-      - "--- global.j2 ---"
-      - "{{ lookup('ansible.builtin.template', ibns_template_dir ~ '/global.j2').splitlines() }}"
-      - "--- interface_templates.j2 ---"
-      - "{{ lookup('ansible.builtin.template', ibns_template_dir ~ '/interface_templates.j2').splitlines() }}"
-      - "--- re-point plan ---"
-      - "{{ ibns_port_plan }}"
-      - "--- held ports (not touched) ---"
-      - "{{ ibns_state.held_ports }}"
+    msg: "{{ ibns_state.held_ports }}"
 
 - name: Apply golden global config (policy-map, class-maps, service templates, AAA)
-  when: not (dry_run | bool)
-  cisco.ios.ios_config:
-    src: "{{ ibns_template_dir }}/global.j2"
+  ansible.builtin.include_role:
+    name: ibns_push
+  vars:
+    ibns_push_step: golden-global
+    ibns_push_cli: "{{ lookup('ansible.builtin.template', ibns_template_dir ~ '/global.j2') }}"
 
 - name: Apply golden interface templates
-  when: not (dry_run | bool)
-  cisco.ios.ios_config:
-    src: "{{ ibns_template_dir }}/interface_templates.j2"
+  ansible.builtin.include_role:
+    name: ibns_push
+  vars:
+    ibns_push_step: golden-templates
+    ibns_push_cli: "{{ lookup('ansible.builtin.template', ibns_template_dir ~ '/interface_templates.j2') }}"
 
-- name: Re-point access ports to their golden template
-  when: not (dry_run | bool)
-  cisco.ios.ios_config:
-    parents: "interface {{ item.key }}"
-    lines: "{{ ibns_state.auth_lines[item.key] | ibns_repoint_commands(item.value) }}"
-  loop: "{{ ibns_port_plan | dict2items }}"
-  loop_control:
-    label: "{{ item.key }} -> {{ item.value }}"
+- name: Re-point access ports to their golden template (a failure here is caught by the post-check and rolled back)
+  ansible.builtin.include_role:
+    name: ibns_push
+  vars:
+    ibns_push_step: repoint
+    ibns_push_cli: "{{ ibns_port_plan | ibns_repoint_cli(ibns_state.auth_lines) }}"
+    ibns_push_may_fail: true
+
+- name: Keep the re-point push result for the report
+  ansible.builtin.set_fact:
+    ibns_repoint_error: "{{ ibns_push_error }}"
```

### Diff: `ansible/playbooks/roles/ibns_rollback_golden/tasks/main.yml`

```diff
--- a/ansible/playbooks/roles/ibns_rollback_golden/tasks/main.yml
+++ b/ansible/playbooks/roles/ibns_rollback_golden/tasks/main.yml
@@ -1,22 +1,15 @@
 # roles/ibns_rollback_golden/tasks/main.yml
-# Stage 2 rollback: put each re-pointed port back on its converted config.
-# Saved interface lines are restored FIRST, then the golden template is detached.
-# No reload, no write erase. Golden global objects stay (unused, harmless).
+# Stage 2 rollback, pushed through Catalyst Center: put each re-pointed port back
+# on its converted config. Saved interface lines are restored FIRST, then the
+# golden template is detached. No reload, no write erase. Golden global objects
+# stay (unused, harmless). A failed push is recorded, not fatal: the post-check
+# that follows decides the outcome.
 # Input: ibns_rollback_data (snapshot saved by ibns_golden)
 ---
-- name: Dry run - show rollback commands
-  when: dry_run | bool
-  ansible.builtin.debug:
-    msg: "{{ item.key }}: {{ ibns_rollback_data.auth_lines[item.key] | ibns_rollback_commands(item.value) }}"
-  loop: "{{ ibns_rollback_data.port_plan | dict2items }}"
-  loop_control:
-    label: "{{ item.key }}"
-
-- name: Restore converted auth config on re-pointed ports
-  when: not (dry_run | bool)
-  cisco.ios.ios_config:
-    parents: "interface {{ item.key }}"
-    lines: "{{ ibns_rollback_data.auth_lines[item.key] | ibns_rollback_commands(item.value) }}"
-  loop: "{{ ibns_rollback_data.port_plan | dict2items }}"
-  loop_control:
-    label: "{{ item.key }} <- converted config"
+- name: Re-point ports back to their converted config
+  ansible.builtin.include_role:
+    name: ibns_push
+  vars:
+    ibns_push_step: rollback-golden
+    ibns_push_cli: "{{ ibns_rollback_data.port_plan | ibns_rollback_cli(ibns_rollback_data.auth_lines) }}"
+    ibns_push_may_fail: true
```

### Diff: `ansible/playbooks/ibns_stage2_golden.yml`

```diff
--- a/ansible/playbooks/ibns_stage2_golden.yml
+++ b/ansible/playbooks/ibns_stage2_golden.yml
@@ -2,4 +2,5 @@
 # RUN ORDER: 4 (same change window, after stage 1 passed)
 # Stage 2: add golden config alongside the converted config, re-point ports.
+# Every change is pushed through Catalyst Center (roles/ibns_push).
 #   pass -> write memory
 #   fail -> automatic rollback: re-point ports back to the converted config
@@ -46,7 +47,6 @@
         - not (dry_run | bool)
         - ibns_check_passed | bool
-      cisco.ios.ios_command:
-        commands:
-          - write memory
+      ansible.builtin.include_role:
+        name: ibns_save
 
     - name: Roll back to the converted config (post-check failed)
@@ -82,5 +82,5 @@
                ('golden-applied' if ibns_failed_check is not defined else
                ('ROLLED-BACK' if ibns_check_passed | bool else 'ROLLED-BACK-CHECK-FAILED')) }}
-          detail: "{{ (ibns_failed_check | default(ibns_check)).config_findings + ((ibns_failed_check | default(ibns_check)).sessions.failures | map(attribute='detail') | list) }}"
+          detail: "{{ ([('re-point push failed: ' ~ ibns_repoint_error)] if ibns_repoint_error | default('') else []) + (ibns_failed_check | default(ibns_check)).config_findings + ((ibns_failed_check | default(ibns_check)).sessions.failures | map(attribute='detail') | list) }}"
 
     - name: Flag a rolled-back switch
```

### Diff: `ansible/playbooks/ibns_rollback_golden.yml`

```diff
--- a/ansible/playbooks/ibns_rollback_golden.yml
+++ b/ansible/playbooks/ibns_rollback_golden.yml
@@ -3,4 +3,5 @@
 # found in the next-day check. Uses the rollback data stage 2 saved.
 # Set ibns_rollback_snapshot to a dated file to roll back to a specific run.
+# Pushed through Catalyst Center (roles/ibns_push).
 ---
 - name: Resolve targets
@@ -51,7 +52,6 @@
         - not (dry_run | bool)
         - ibns_check_passed | bool
-      cisco.ios.ios_command:
-        commands:
-          - write memory
+      ansible.builtin.include_role:
+        name: ibns_save
 
     - name: Report
```

### Diff: `ansible/playbooks/roles/ibns_cleanup/tasks/main.yml`

```diff
--- a/ansible/playbooks/roles/ibns_cleanup/tasks/main.yml
+++ b/ansible/playbooks/roles/ibns_cleanup/tasks/main.yml
@@ -1,6 +1,6 @@
 # roles/ibns_cleanup/tasks/main.yml
-# Stage 3: remove converted control-policy objects that nothing references.
-# Never by name pattern: the filter only returns objects with no references,
-# and never anything listed in ibns_golden_names.
+# Stage 3: remove converted control-policy objects that nothing references,
+# pushed through Catalyst Center. Never by name pattern: the filter only returns
+# objects with no references, and never anything listed in ibns_golden_names.
 # Input: ibns_state (from pre-check)
 ---
@@ -14,7 +14,8 @@
 
 - name: Remove unreferenced objects
-  when:
-    - not (dry_run | bool)
-    - ibns_orphans | length > 0
-  cisco.ios.ios_config:
-    lines: "{{ ibns_orphans }}"
+  when: ibns_orphans | length > 0
+  ansible.builtin.include_role:
+    name: ibns_push
+  vars:
+    ibns_push_step: cleanup
+    ibns_push_cli: "{{ ibns_orphans | join('\n') }}"
```

### Diff: `ansible/playbooks/ibns_stage3_cleanup.yml`

```diff
--- a/ansible/playbooks/ibns_stage3_cleanup.yml
+++ b/ansible/playbooks/ibns_stage3_cleanup.yml
@@ -2,6 +2,8 @@
 # RUN ORDER: 6 (separate change, after the soak period and a clean next-day check)
 # Stage 3: remove converted control-policy objects nothing references any more.
+# Every change is pushed through Catalyst Center (roles/ibns_push).
 #   pass -> write memory
-#   fail -> config NOT saved; restore removed objects from the backup taken first
+#   fail -> no write memory from us; restore removed objects from the backup
+#           taken first (the removed lines are in the pushed-stage3-cleanup snapshot)
 ---
 - name: Resolve targets
@@ -18,4 +20,5 @@
     ibns_stage_tag: stage3
     ibns_expected_mode: new-style
+    ibns_check_migration: false
   tasks:
     - name: Pre-check (switch is skipped if this fails)
@@ -45,7 +48,6 @@
         - not (dry_run | bool)
         - ibns_check_passed | bool
-      cisco.ios.ios_command:
-        commands:
-          - write memory
+      ansible.builtin.include_role:
+        name: ibns_save
 
     - name: Report
```

### Diff: `ansible/aap_payload/templates/controller_templates.yml`

```diff
--- a/ansible/aap_payload/templates/controller_templates.yml
+++ b/ansible/aap_payload/templates/controller_templates.yml
@@ -3,6 +3,8 @@
    * Same structure as ud00: one entry per playbook. Keep names in sync with
    * controller_survey_specs.yml (survey keys must equal template names).
-   * CONFIRM with Gurkirat: which credential logs into switches (service_id
-   * below) and how Artifactory snapshot credentials reach the job. */}}
+   * Every IBNS job reaches switches ONLY through Catalyst Center, so the jobs
+   * carry the DNAC service-ID credential (service_id_dnac), not a switch login.
+   * CONFIRM with Gurkirat: that this DNAC account may run Command Runner and
+   * deploy templates, and how Artifactory snapshot credentials reach the job. */}}
 
 app_controller_templates:
@@ -42,5 +44,5 @@
     credentials:
       - "{{ include "aap.resource_names_reserved.vault_app_roles" . }}"
-      - "{{ .Values.HELIOS_APP_CODE }}_service_id_{{ .Values.HELIOS_APP_NAME }}"
+      - "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"
 
   - name: "{{ .Values.HELIOS_APP_CODE }}_ibns_baseline_{{ .Values.HELIOS_APP_NAME }}"
@@ -62,5 +64,5 @@
     credentials:
       - "{{ include "aap.resource_names_reserved.vault_app_roles" . }}"
-      - "{{ .Values.HELIOS_APP_CODE }}_service_id_{{ .Values.HELIOS_APP_NAME }}"
+      - "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"
 
   - name: "{{ .Values.HELIOS_APP_CODE }}_ibns_precheck_{{ .Values.HELIOS_APP_NAME }}"
@@ -82,5 +84,5 @@
     credentials:
       - "{{ include "aap.resource_names_reserved.vault_app_roles" . }}"
-      - "{{ .Values.HELIOS_APP_CODE }}_service_id_{{ .Values.HELIOS_APP_NAME }}"
+      - "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"
 
   - name: "{{ .Values.HELIOS_APP_CODE }}_ibns_stage1_convert_{{ .Values.HELIOS_APP_NAME }}"
@@ -102,5 +104,5 @@
     credentials:
       - "{{ include "aap.resource_names_reserved.vault_app_roles" . }}"
-      - "{{ .Values.HELIOS_APP_CODE }}_service_id_{{ .Values.HELIOS_APP_NAME }}"
+      - "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"
 
   - name: "{{ .Values.HELIOS_APP_CODE }}_ibns_stage2_golden_{{ .Values.HELIOS_APP_NAME }}"
@@ -122,5 +124,5 @@
     credentials:
       - "{{ include "aap.resource_names_reserved.vault_app_roles" . }}"
-      - "{{ .Values.HELIOS_APP_CODE }}_service_id_{{ .Values.HELIOS_APP_NAME }}"
+      - "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"
 
   - name: "{{ .Values.HELIOS_APP_CODE }}_ibns_nextday_check_{{ .Values.HELIOS_APP_NAME }}"
@@ -142,5 +144,5 @@
     credentials:
       - "{{ include "aap.resource_names_reserved.vault_app_roles" . }}"
-      - "{{ .Values.HELIOS_APP_CODE }}_service_id_{{ .Values.HELIOS_APP_NAME }}"
+      - "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"
 
   - name: "{{ .Values.HELIOS_APP_CODE }}_ibns_rollback_golden_{{ .Values.HELIOS_APP_NAME }}"
@@ -162,5 +164,5 @@
     credentials:
       - "{{ include "aap.resource_names_reserved.vault_app_roles" . }}"
-      - "{{ .Values.HELIOS_APP_CODE }}_service_id_{{ .Values.HELIOS_APP_NAME }}"
+      - "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"
 
   - name: "{{ .Values.HELIOS_APP_CODE }}_ibns_stage3_cleanup_{{ .Values.HELIOS_APP_NAME }}"
@@ -182,3 +184,3 @@
     credentials:
       - "{{ include "aap.resource_names_reserved.vault_app_roles" . }}"
-      - "{{ .Values.HELIOS_APP_CODE }}_service_id_{{ .Values.HELIOS_APP_NAME }}"
+      - "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"
```

### Diff: `ansible/aap_payload/templates/controller_execution_environments.yml`

```diff
--- a/ansible/aap_payload/templates/controller_execution_environments.yml
+++ b/ansible/aap_payload/templates/controller_execution_environments.yml
@@ -1,6 +1,6 @@
 ---
 {{/* COPIED FROM ud00 AND EDITED: removed the vManage execution environment.
-   * VERIFY the image tag against ud00 and confirm this image contains the
-   * cisco.ios and cisco.catalystcenter collections; if not, request a new image. */}}
+   * VERIFY the image tag against ud00. IBNS needs no collections (its
+   * Catalyst Center modules use ansible-core only), so this image works as is. */}}
 app_controller_execution_environments:
   # Image with Ansible-core 2.16 - CURRENT VERSION
```

### Diff: `docs/runbook.md`

```diff
--- a/docs/runbook.md
+++ b/docs/runbook.md
@@ -12,5 +12,5 @@
 | `dry-run` | Nothing was changed | Review the output, rerun with Dry Run = false |
 | `converted` | Stage 1 passed and was saved | Continue with stage 2 |
-| `FIX-FORWARD-REQUIRED` | Stage 1 post-check failed; config NOT saved | See "Stage 1 failure" below. Do not reload |
+| `FIX-FORWARD-REQUIRED` | Stage 1 post-check failed; we did not write memory (Catalyst Center may have) | See "Stage 1 failure" below. Do not reload |
 | `golden-applied` | Stage 2 passed and was saved | Next-day check tomorrow morning |
 | `ROLLED-BACK` | Stage 2 failed; ports were re-pointed to the converted config and service checks out | Investigate the failures listed, fix the golden template, retry later |
@@ -21,15 +21,26 @@
 ## Stage 1 failure (FIX-FORWARD-REQUIRED)
 
-The conversion is one-way and the config was not saved.
+The conversion is one-way. We did not write memory, but Catalyst Center may
+have saved the config as part of the deployment (verify in the lab which).
 
 1. Do not reload the switch.
 2. Read the failures in the job output: which endpoints, which check.
 3. Fix forward in new-style syntax on the affected ports (e.g. host mode,
-   missing `mab`, timer), using the converted policy as the reference.
+   missing `mab`, timer), using the converted policy as the reference. Push
+   the fix through Catalyst Center (a template in the IBNS2 project), the
+   same way the jobs do.
 4. Run the pre-check job, then compare sessions with the stage 1 snapshot.
-5. When service is restored, `write memory` and record what was changed.
+5. When service is restored, `write memory` (template) and record what was changed.
 6. Last resort only, with console/OOB access confirmed: restore the legacy
    config from `flash:ibns-before-stage1-<run id>.cfg` per the team's
    recovery procedure (verified in the lab).
+
+## What was pushed, and when
+
+Every change goes through Catalyst Center as a new version of the switch's
+template `IBNS2_<hostname>` (project `IBNS2`). The commit comment is
+`<run id> <stage> <step>`, so the version history is the change record.
+The same CLI and its result are in the snapshot store as
+`pushed-<stage>-<step>-<run id>.txt`.
 
 ## Stage 2 rollback (manual)
```

### Diff: `python/ibns_tools/classify_ports.py`

```diff
--- a/python/ibns_tools/classify_ports.py
+++ b/python/ibns_tools/classify_ports.py
@@ -19,5 +19,5 @@
   ports_classified.csv        one row per port: role, config class, action, reason
   held_ports.csv              ports that will NOT be migrated until fixed
-  switch_summary.csv          per switch: migrate / hold / leave counts, ready yes/no
+  switch_summary.csv          per switch: migrate / hold / leave / done counts, ready or not
   role_vs_class.csv           role x config class counts (spot bad rules fast)
   unmatched_descriptions.csv  description patterns no rule matched, most common first
@@ -131,5 +131,6 @@
         held = sum(r["action"] == "hold" for r in rows)
         print(f"\n{len(rows)} ports: migrate {sum(r['action'] == 'migrate' for r in rows)}, "
-              f"hold {held}, leave {sum(r['action'] == 'leave' for r in rows)}")
+              f"hold {held}, leave {sum(r['action'] == 'leave' for r in rows)}, "
+              f"done {sum(r['action'] == 'done' for r in rows)}")
         return
 
@@ -151,8 +152,9 @@
         all_rows += rows
         counts = Counter(r["action"] for r in rows)
+        ready = "NO" if counts["hold"] > cfg["max_held"] else (
+            "yes" if counts["migrate"] else ("done" if counts["done"] else "nothing to migrate"))
         switches.append({
             "hostname": path.stem, "ports": len(rows), "migrate": counts["migrate"],
-            "hold": counts["hold"], "leave": counts["leave"],
-            "ready": "yes" if counts["hold"] <= cfg["max_held"] and counts["migrate"] > 0 else "NO",
+            "hold": counts["hold"], "leave": counts["leave"], "done": counts["done"], "ready": ready,
         })
         for r in rows:
@@ -168,5 +170,5 @@
     held_rows = [r for r in all_rows if r["action"] == "hold"]
     write_csv(out / "held_ports.csv", held_rows, PORT_FIELDS)
-    write_csv(out / "switch_summary.csv", switches, ["hostname", "ports", "migrate", "hold", "leave", "ready"])
+    write_csv(out / "switch_summary.csv", switches, ["hostname", "ports", "migrate", "hold", "leave", "done", "ready"])
     write_csv(out / "role_vs_class.csv",
               [{"role": k[0], "config_class": k[1], "ports": v} for k, v in sorted(role_class.items())],
@@ -181,5 +183,5 @@
     ready = sum(s["ready"] == "yes" for s in switches)
     print(f"{len(files)} switches, {len(all_rows)} ports: migrate {actions['migrate']}, "
-          f"hold {actions['hold']}, leave {actions['leave']}")
+          f"hold {actions['hold']}, leave {actions['leave']}, done {actions['done']}")
     print(f"switches ready: {ready}/{len(switches)}  (held ports allowed per switch: {cfg['max_held']})")
     print(f"description patterns with no rule: {len(unmatched)}")
```

## Start here

Read first. Run order, port classification and which files to copy, edit or replace.

### `README.md`

````markdown
# IBNS 2.0 migration automation

Converts Catalyst 9300 access switches from legacy dot1x (IBNS 1.0) to IBNS 2.0,
about one site per week. RADIUS is Aruba ClearPass. Built on the same pipeline,
AAP layout and inventory as the ud00 SWIM repo.

Design in one line: convert in place, add the golden config alongside, re-point
ports, so ports are never without authentication and the golden config can be
rolled back per port without a reload.

Every read and every change goes through Catalyst Center. Nothing logs into a
switch over SSH.

## Run order

| # | When | What runs | Changes config? | Where |
| --- | --- | --- | --- | --- |
| 0 | Once, then before each site | `python/ibns_tools/ibns_discovery.py` fetch, group, diff (and `compare` for drift) | No | Laptop |
| 0b | After 0, then before each site | `python/ibns_tools/classify_ports.py` (all sites, offline) and `ibns_classify.yml` (one site, live) | No | Laptop / AAP |
| 1 | 1-2 days before, business hours | `ibns_baseline.yml` | No | AAP / laptop |
| 2 | Day of change, before window | `ibns_precheck.yml` | No | AAP / laptop |
| 3 | Change window | `ibns_stage1_convert.yml` | Yes, one-way | AAP |
| 4 | Same window, after 3 passes | `ibns_stage2_golden.yml` | Yes, auto-rollback | AAP |
| 5 | Next business morning | `ibns_nextday_check.yml` | No | AAP |
| - | Only if needed | `ibns_rollback_golden.yml` | Yes, re-point back | AAP |
| 6 | After soak, separate change | `ibns_stage3_cleanup.yml` | Yes | AAP |

Every playbook first imports `ibns_target.yml`, which turns the survey's
comma-separated hostnames into the `ibns_targets` group (exact match only,
empty list refused, one site per job) and sets one run id for the job.

Every config-changing stage runs: pre-check -> backup -> change -> post-check ->
save only if passed -> report (AAP artifact, forwarded to Odyssey).
`dry_run` defaults to true everywhere.

## How the jobs reach switches: Catalyst Center only

| What | Catalyst Center feature | Code |
| --- | --- | --- |
| Find the switch, version, reachability | Inventory (`network-device`) | `catc_device` module |
| Show commands (running config, sessions, AAA, flash) | Command Runner (read-only) | `catc_cli_read` module, `ibns_collect` role |
| Every change (backup copy, convert, golden, re-point, rollback, cleanup, write memory) | Template Programmer | `catc_cli_push` module, `ibns_push` role |

- Ansible renders the CLI (repo templates and `ibns_*` filters) and pushes it as
  the content of ONE template per switch, `IBNS2_<hostname>` in project `IBNS2`.
  Each push commits a new version with comment `<run id> <stage> <step>`, so
  the template's version history in Catalyst Center records every change.
- Exec commands use Catalyst Center template syntax: `#MODE_ENABLE` blocks and
  `#INTERACTIVE` with `<IQ>`/`<R>` for the convert and copy prompts.
- Hosts run with `ansible_connection: local` (set in `inventory_lookup`); the
  modules call the Catalyst Center REST API from the controller.
- The modules use ansible-core only (no collections), so the existing 2.16
  execution environment works unchanged. AAP jobs carry the DNAC service-ID
  credential, not a switch login.
- `authentication display config-mode` is not a show command, so Command
  Runner refuses it; the config mode is read from the running config instead.

## Port classification

Every physical port gets two labels and one action:

| Label | From | Example |
| --- | --- | --- |
| config class | The interface config | `multi-domain`, `dot1x+mab`, `mab-only`, `trunk`, `static-access` |
| role | The description, via `ibns_description_rules` | `user`, `phone`, `printer`, `ap`, `uplink` |
| action | Both together, via `ibns_port_roles` | `migrate` (gets a golden template), `hold` (auth port the rules can't vouch for, left on the converted config), `leave` (not an auth port), `done` (already on its golden template) |

The template is always chosen by the config class, so the migration never
changes how a port authenticates. The description only decides whether the
port is trusted to migrate. Rules and roles live in
`ansible/playbooks/group_vars/all.yml`; the laptop script and the Ansible jobs
read the same file and run the same code (`ibns_port_inventory`).

Build the rules from real data: run `classify_ports.py` on a discovery run,
read `classify/unmatched_descriptions.csv` (most common patterns first) and
`classify/role_vs_class.csv`, adjust the rules, repeat until held ports are
only real problems.

Pipeline (on push, unchanged from ud00): Helios renders `ansible/aap_payload`,
builds a release bundle and deploys the job templates and surveys to DEV AAP,
then PROD from the release branch. It never launches a job.

## File map

### Copy from ud00 unchanged

| Path | Notes |
| --- | --- |
| `.github/workflows/create-vm-ansible-release-bundle.yml` | Pipeline |
| `helios/deploy.sh` | |
| `ansible/aap_payload/templates/_helpers.tpl` | Naming helpers |
| `ansible/aap_payload/templates/_resource_names.tpl` | |
| `ansible/aap_payload/templates/_resource_names_reserved.tpl` | Do not alter |
| `ansible/aap_payload/templates/controller_projects.yml` | AAP project from Git |
| `ansible/aap_payload/templates/controller_notifications.yml` | NetValidator webhook to Odyssey |
| `ansible/inventories/plugins/dnac.py` | Catalyst Center inventory plugin |
| `ansible/inventories/dev/dnac.yml`, `prod/dnac.yml` (and `sai/dnac.yml` if needed) | Inventory files |
| `ansible/playbooks/noop.yml` | |
| `ansible/playbooks/roles/odyssey_parse_devices/` | Survey string to list |
| `ansible/playbooks/roles/input_validation/` | Hostname and IP checks |
| `ansible/playbooks/roles/dnac_auth/` | Optional, for later Catalyst Center API work |

### Copy from ud00, then edit

| Path | Edit |
| --- | --- |
| `ansible.cfg` | Merge in the NEW lines from this repo's `ansible.cfg` |
| `requirements.txt` | Add the lines in `requirements-ibns.txt` |
| `.gitignore` | Add the lines in `gitignore-additions.txt` |
| `CODEOWNERS` | Owners for this repo |
| `catalog-info.yaml` | Component name and description |
| `ansible/aap_payload/Chart.yaml`, `values.yaml`, `values/` | App name for this repo (ask Gurkirat about app code) |
| `ansible/aap_payload/templates/controller_launch_jobs.yml`, `controller_schedules.yml` | Remove ud00's entries, leave the lists empty |
| `ansible/aap_payload/templates/controller_credentials.yml` | Given in full in this repo |
| `ansible/aap_payload/templates/controller_credential_input_sources.yml` | Given in full in this repo |
| `ansible/aap_payload/templates/controller_execution_environments.yml` | Given in full in this repo |
| `ansible/aap_payload/templates/controller_inventories.yml` | Given in full in this repo |
| `ansible/aap_payload/templates/controller_inventory_source.yml` | Given in full in this repo |
| `ansible/playbooks/roles/inventory_lookup/tasks/main.yml` | Given in full in this repo (hosts run locally, no SSH) |

### Replace (ud00's version doesn't apply)

| Path | |
| --- | --- |
| `README.md` | This file |
| `ansible/aap_payload/templates/controller_templates.yml` | IBNS job templates |
| `ansible/aap_payload/templates/controller_survey_specs.yml` | IBNS surveys |

### New

| Path | Purpose |
| --- | --- |
| `ansible/plugins/filter/ibns_filters.py` | All parsing, comparison and CLI-building logic |
| `ansible/plugins/module_utils/catc_client.py` | Catalyst Center REST client (Command Runner, Template Programmer) |
| `ansible/plugins/modules/catc_device.py`, `catc_cli_read.py`, `catc_cli_push.py` | The three Catalyst Center modules every role uses |
| `tests/test_ibns_filters.py`, `tests/test_catc_client.py` | Unit tests (`pytest -q`); the client tests use a fake Catalyst Center |
| `ansible/playbooks/group_vars/all.yml` | IBNS settings, safety defaults, golden names |
| `ansible/playbooks/ibns_target.yml` | Target resolution, imported by every playbook |
| `ansible/playbooks/ibns_*.yml` | The eight playbooks in the run order above (classify plus the seven stage playbooks) |
| `ansible/playbooks/roles/ibns_*/tasks/*.yml` | collect, precheck, push, save, backup, convert, golden, rollback_golden, postcheck, cleanup, snapshot, report, input_validation |
| `ansible/templates/ibns2/global.j2`, `interface_templates.j2` | Golden config (draft) |
| `ansible/inventories/lab/hosts.yml` | Static lab inventory |
| `python/ibns_tools/ibns_discovery.py` | Discovery, variants, drift |
| `python/ibns_tools/classify_ports.py` | Port roles from descriptions + config, offline, all sites |
| `requirements.yml` | Empty: no collections needed |
| `docs/runbook.md` | What to do for each outcome |

### Don't copy

SWIM and SD-WAN roles and playbooks (`catalystcenter_swim`, `dnac_swim`,
`dnac_golden_image`, `dnac_mark_golden_image`, `filesystem_cleanup`,
`sdwan/vmanage_software_upgrade`, `cml_lab_setup.yml`, `dnac_*.yml`,
`flash_cleanup.yml`, `vmanage_software_update.yml`), `playbooks/vars/`,
`inventories/*/sdwan.yml`, `inventories/plugins/vmanage.py`,
`inventories/group_vars/all.yml` (replaced by `playbooks/group_vars/all.yml`),
`inventories/group_vars/cisco_switches.yml` (ud00's vault-encrypted switch logins; IBNS never logs into switches),
`cml/topologies/cat9K.yml`, `scripts/orchestrate_workflow.py`.

## Laptop runs (lab)

```bash
source .venv/bin/activate
export DEVOPS_USERNAME=<Catalyst Center user>; read -s DEVOPS_PASSWORD && export DEVOPS_PASSWORD
export CATC_HOST=<lab Catalyst Center>              # if the inventory has no dnac_host
export CATC_CA_BUNDLE=<path to RBC CA bundle>       # if the RBC CA isn't trusted by Python
pytest -q
python python/ibns_tools/classify_ports.py --config <saved lab config>.cfg
ansible-playbook ansible/playbooks/ibns_classify.yml -e device_hostnames=<LAB-SWITCH>
ansible-playbook ansible/playbooks/ibns_precheck.yml -e device_hostnames=<LAB-SWITCH>
ansible-playbook ansible/playbooks/ibns_stage1_convert.yml -e device_hostnames=<LAB-SWITCH>            # dry run
ansible-playbook ansible/playbooks/ibns_stage1_convert.yml -e device_hostnames=<LAB-SWITCH> \
  -e dry_run=false -e change_number=CHG0000000                                                          # lab change
```

Snapshots from laptop runs go to `reports/raw/snapshots/<host>/` (git-ignored).

## Verify in the lab before trusting

- Show-command parsers against real output (paste samples into the tests).
- Description rules against real descriptions (`unmatched_descriptions.csv`),
  and which roles each config class is allowed with.
- The `authentication convert-to new-style` confirmation prompt text
  (`ibns_convert_prompt`), pushed through `#INTERACTIVE`.
- Catalyst Center: the API calls in `catc_client.py` on our version; that
  Command Runner accepts every command in `ibns_collect` (including
  `dir flash:`) and what its output looks like; `#MODE_ENABLE`/`#INTERACTIVE`
  in a JINJA template; whether an API deployment also writes memory.
- That the DNAC service account may run Command Runner and deploy templates.
- Golden templates: closed vs low-impact, timers, critical auth with ClearPass down.
- Session recovery time after re-pointing (`ibns_reauth_wait`).
- What reverting a converted switch actually requires (runbook last resort).
````

## Phase 1: foundation (test on the laptop with pytest)

Type these, then run `pytest -q`. All 28 tests should pass before you go further. The Catalyst Center client is tested against a fake Catalyst Center, so no lab is needed yet.

### `ansible.cfg`

```ini
# ansible.cfg
# START FROM ud00's ansible.cfg and MERGE: keep every line ud00 has (especially
# anything that enables the dnac inventory plugin), then add the lines marked NEW.
# AAP reads this file from the project root, so it applies in AAP and on the laptop.
# No SSH settings: IBNS never logs into switches, everything goes through Catalyst Center.

[defaults]
inventory = ansible/inventories/lab/hosts.yml          ; NEW (laptop default; AAP sets its own inventory)
roles_path = ansible/playbooks/roles                    ; NEW if ud00 doesn't set it
filter_plugins = ansible/plugins/filter                 ; NEW (required: ibns_* filters)
library = ansible/plugins/modules                       ; NEW (required: catc_* Catalyst Center modules)
module_utils = ansible/plugins/module_utils             ; NEW (required: catc_client shared by the modules)
inventory_plugins = ansible/inventories/plugins         ; keep ud00's value if different
collections_path = ./collections                        ; NEW (laptop: collections installed into the repo)
retry_files_enabled = False
callback_result_format = yaml

[inventory]
enable_plugins = dnac, yaml, ini, host_list, auto       ; keep ud00's value if different
```

### `requirements.yml`

```yaml
# requirements.yml
# NEW. Ansible collections for laptop runs:
#   ansible-galaxy collection install -r requirements.yml -p ./collections
# IBNS needs NO collections: it talks to Catalyst Center through its own modules
# (ansible/plugins/modules/catc_*.py), which use ansible-core only. That means
# the existing 2.16 execution environment works as it is.
---
collections: []
```

### `requirements-ibns.txt`

```text
# requirements-ibns.txt
# NEW. Lines to ADD to the requirements.txt copied from ud00 (keep all of ud00's
# pinned lines; remove catalystwan only if nothing else needs it).
# Laptop: pip install -r requirements.txt
ansible-core==2.16.7
ansible-lint
catalystcentersdk
requests
pytest
pyyaml
```

### `gitignore-additions.txt`

```text
# gitignore-additions.txt
# Lines to ADD to the .gitignore copied from ud00 (keep all of ud00's lines).
.venv/
collections/
reports/raw/
.pytest_cache/
```

### `ansible/plugins/filter/ibns_filters.py`

```python
# ansible/plugins/filter/ibns_filters.py
"""Ansible filters for the IBNS 2.0 migration.

All parsing and comparison logic lives here so playbooks stay short and the
logic can be unit-tested (tests/test_ibns_filters.py). Pure Python, no extra
dependencies. Runs on the controller (AAP execution environment or laptop).

Verify every parser against real lab output before trusting it: show-command
formats vary between IOS-XE releases.
"""
import re

# ------------------------------------------------------------------ helpers --

INTF_LONG = {
    "Gi": "GigabitEthernet", "Te": "TenGigabitEthernet", "Tw": "TwentyFiveGigE",
    "Fo": "FortyGigabitEthernet", "Hu": "HundredGigE", "Fa": "FastEthernet",
}
PHYSICAL = re.compile(
    r"^interface ((Gigabit|TenGigabit|TwentyFiveGig|FortyGigabit|HundredGig|Fast)"
    r"Ethernet|TwentyFiveGigE|HundredGigE)(\d+/\d+/\d+)$"
)
# Interface-level auth commands (legacy and new-style). These are what the
# golden interface template replaces, and what rollback puts back.
AUTH_LINE = re.compile(
    r"^(authentication |access-session |dot1x |mab( |$)|"
    r"service-policy type control subscriber |source template )"
)
AUTH_CLASSES = {"multi-domain", "dot1x+mab", "dot1x-only", "mab-only", "new-style", "auth-other"}
NON_AUTH_CLASSES = {"trunk", "routed", "port-channel-member", "uplink-module"}


def canonical_intf(name):
    """Gi1/0/1 -> GigabitEthernet1/0/1 (long names pass through)."""
    name = name.strip()
    for short, long in INTF_LONG.items():
        if name.startswith(short) and not name.startswith(long) and re.match(rf"^{short}\d", name):
            return long + name[len(short):]
    return name


def _text(value):
    if isinstance(value, (list, tuple)):
        return "\n".join(str(v) for v in value)
    return str(value or "")


def _blocks(config):
    """Split a running config into (parent, [children]) blocks."""
    out, current = [], None
    for raw in _text(config).splitlines():
        line = raw.rstrip()
        if not line or line.startswith("!"):
            current = None
            continue
        if line[0] == " " and current is not None:
            current[1].append(line.strip())
        else:
            current = (line.strip(), [])
            out.append(current)
    return out


# ------------------------------------------------------------ show parsers --

def ibns_config_mode_from_running(running_config):
    """Legacy or new-style, worked out from the running config.
    Used instead of 'authentication display config-mode', which Command Runner
    does not accept (not a show command). Legacy interface commands win: a
    switch with any of them has not been converted."""
    legacy = new = False
    for parent, children in _blocks(running_config):
        if not PHYSICAL.match(parent):
            continue
        for c in children:
            if c.startswith(("authentication port-control", "authentication host-mode",
                             "authentication order", "authentication priority")):
                legacy = True
            elif c.startswith(("access-session port-control", "service-policy type control subscriber",
                               "source template")):
                new = True
    return "legacy" if legacy else ("new-style" if new else "unknown")


def ibns_aaa_servers(output):
    """Parse `show aaa servers` -> [{host, port, state}]."""
    servers, current = [], None
    for line in _text(output).splitlines():
        m = re.search(r"RADIUS: id \d+, priority \d+, host (\S+?),\s*auth-port (\d+)", line)
        if m:
            current = {"host": m.group(1), "port": m.group(2), "state": "unknown"}
            servers.append(current)
            continue
        m = re.search(r"State: current (\S+?),", line)
        if m and current is not None and current["state"] == "unknown":
            current["state"] = m.group(1).upper()
    return servers


SESSION_ROW = re.compile(
    r"^(\S+)\s+([0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4})\s+(\S+)\s+(\S+)\s+(\S+)",
    re.I,
)


def ibns_parse_session_table(output):
    """Parse the `show access-session` table -> [{interface, mac, method, domain, status}]."""
    sessions = []
    for line in _text(output).splitlines():
        m = SESSION_ROW.match(line.strip())
        if not m:
            continue
        sessions.append({
            "interface": canonical_intf(m.group(1)), "mac": m.group(2).lower(),
            "method": m.group(3).lower(), "domain": m.group(4).upper(),
            "status": "Authorized" if m.group(5).lower().startswith("auth") else m.group(5),
        })
    return sessions


def ibns_parse_session_details(output):
    """Parse `show access-session method <dot1x|mab> details` (one or more outputs)
    -> [{interface, mac, status, domain, method, vlan, acl, critical}].

    Each session block starts with an `Interface:` line. VLAN comes from
    `Vlan Group:  Vlan: N` (or `Vlan Policy: N`); ACL from `ACS ACL:` or `Filter-ID:`.
    The successful method comes from the `Method status list`.
    """
    sessions = []
    text = _text(output)
    for chunk in re.split(r"(?m)^\s*Interface:\s*", text)[1:]:
        lines = chunk.splitlines()
        s = {"interface": canonical_intf(lines[0]), "mac": "", "status": "", "domain": "",
             "method": "", "vlan": "", "acl": "", "critical": False}
        in_methods = False
        for raw in lines[1:]:
            line = raw.strip()
            low = line.lower()
            if low.startswith("mac address:"):
                s["mac"] = line.split(":", 1)[1].strip().lower()
            elif low.startswith("status:"):
                s["status"] = line.split(":", 1)[1].strip()
            elif low.startswith("domain:"):
                s["domain"] = line.split(":", 1)[1].strip().upper()
            elif re.search(r"vlan( group| policy)?:", low):
                m = re.search(r"(\d+)\s*$", line)
                if m:
                    s["vlan"] = m.group(1)
            elif low.startswith(("acs acl:", "filter-id:")):
                s["acl"] = line.split(":", 1)[1].strip()
            elif low.startswith("method status list"):
                in_methods = True
            elif in_methods:
                m = re.match(r"^(dot1x|mab|webauth)\s+(.*)$", low)
                if m and "success" in m.group(2):
                    s["method"] = m.group(1)
            if "critical" in low:
                s["critical"] = True
        if s["mac"]:
            sessions.append(s)
    # One endpoint can appear in both dot1x and mab outputs; keep the successful one.
    best = {}
    for s in sessions:
        key = (s["interface"], s["mac"])
        if key not in best or (s["method"] and not best[key]["method"]):
            best[key] = s
    return list(best.values())


def ibns_flash_free(output):
    """Parse `dir flash:` output -> free bytes (int, 0 if not found)."""
    m = re.search(r"\((\d+) bytes free", _text(output))
    return int(m.group(1)) if m else 0


def ibns_radius_group(running_config):
    """Running config -> AAA server group used for dot1x ('' if none)."""
    m = re.search(r"(?m)^aaa authentication dot1x default group (\S+)", _text(running_config))
    return m.group(1) if m else ""


# ------------------------------------------------------- config inspection --

def _classify(lines, module):
    text = "\n".join(lines)

    def has(prefix):
        return any(l.startswith(prefix) for l in lines)

    if has("channel-group"):
        return "port-channel-member"
    if "no switchport" in lines:
        return "routed"
    if "switchport mode trunk" in lines:
        return "trunk"
    if has(("authentication port-control", "access-session port-control", "dot1x pae",
            "mab", "service-policy type control", "source template")):
        if has("switchport voice vlan") or "multi-domain" in text:
            return "multi-domain"
        dot1x, mab = has("dot1x pae authenticator"), has("mab")
        if dot1x and mab:
            return "dot1x+mab"
        if mab:
            return "mab-only"
        if dot1x:
            return "dot1x-only"
        if has(("service-policy type control", "source template")):
            return "new-style"
        return "auth-other"
    if module != "0":
        return "uplink-module"
    if "shutdown" in lines:
        return "shutdown-static"
    return "static-access"


def ibns_classify_ports(running_config):
    """Running config -> {interface: port_class} for physical ports."""
    result = {}
    for parent, children in _blocks(running_config):
        m = PHYSICAL.match(parent)
        if m:
            result[parent.split()[1]] = _classify(children, m.group(3).split("/")[1])
    return result


# ------------------------------------------- port roles from descriptions --
#
# The config says what a port DOES (its config class above). The description
# says what it is FOR (its role). A port is migrated only when the two agree,
# so a typo in either one holds the port instead of templating it wrongly.
#
#   rules  (ibns_description_rules)  ordered [{match: regex, role: name}],
#          first match wins, case-insensitive, searched anywhere in the text.
#   roles  (ibns_port_roles)  {role: {migrate: bool, expect: [config classes]}}
#
# action per port:
#   migrate  auth port, role agrees, role allows migration -> gets a template
#   hold     auth port the rules can't vouch for -> left on converted config,
#            listed in the pre-check (fails the switch above ibns_max_held_ports)
#   leave    not an auth port (trunk, uplink, static) -> never touched
#   done     already on its golden template (only 'source template' left) ->
#            nothing to do; the class is read back from the template name

def ibns_port_descriptions(running_config):
    """Running config -> {interface: description} for physical ports ('' if none)."""
    result = {}
    for parent, children in _blocks(running_config):
        if PHYSICAL.match(parent):
            desc = next((c[len("description "):] for c in children if c.startswith("description ")), "")
            result[parent.split()[1]] = desc.strip()
    return result


def _compile_rules(rules):
    compiled = []
    for i, rule in enumerate(rules or []):
        try:
            compiled.append((re.compile(str(rule["match"]), re.IGNORECASE), str(rule["role"])))
        except (KeyError, TypeError) as exc:
            raise ValueError(f"description rule {i + 1} needs 'match' and 'role': {rule!r}") from exc
        except re.error as exc:
            raise ValueError(f"description rule {i + 1} has a bad regex {rule['match']!r}: {exc}") from exc
    return compiled


def ibns_description_role(description, rules):
    """One description -> role name, '' when no rule matches."""
    for pattern, role in _compile_rules(rules):
        if description and pattern.search(description):
            return role
    return ""


def ibns_port_inventory(running_config, rules, roles, port_templates, hold_unmatched=True):
    """Running config -> {interface: {description, role, config_class, status,
    action, template, reason}} for every physical port.

    status: ok | mismatch (role and config disagree) | no-rule (description
            matched no rule) | no-description | unknown-role (rule names a role
            missing from ibns_port_roles)
    """
    compiled = _compile_rules(rules)
    roles = roles or {}
    classes = ibns_classify_ports(running_config)
    descriptions = ibns_port_descriptions(running_config)
    auth = ibns_interface_auth_lines(running_config)
    template_class = {}
    for c, t in reversed(list(port_templates.items())):   # first class listed wins
        template_class[t] = c
    inventory = {}
    for intf, cls in classes.items():
        on_golden = [l[len("source template "):] for l in auth.get(intf, [])
                     if l.startswith("source template ") and l[len("source template "):] in template_class]
        if on_golden:
            cls = template_class[on_golden[0]]          # golden port: class from its template
        desc = descriptions.get(intf, "")
        role = next((r for p, r in compiled if desc and p.search(desc)), "")
        spec = roles.get(role) or {}
        expect = list(spec.get("expect") or [])
        if not desc:
            status, reason = "no-description", "port has no description"
        elif not role:
            status, reason = "no-rule", "description matches no rule"
        elif role not in roles:
            status, reason = "unknown-role", f"role '{role}' is not in ibns_port_roles"
        elif expect and cls not in expect:
            status, reason = "mismatch", f"description says {role}, config is {cls} (expected {'/'.join(expect)})"
        else:
            status, reason = "ok", ""

        template = port_templates.get(cls, "") if cls in AUTH_CLASSES else ""
        if not template:
            action = "leave"
            if status == "mismatch":
                reason += "; not an auth port, nothing to migrate"
        elif status == "ok" and not spec.get("migrate", False):
            action, template = "hold", ""
            reason = f"role '{role}' is set to migrate: false but the port has auth config"
        elif on_golden and auth.get(intf) == [f"source template {template}"]:
            action = "done"
        elif status == "ok":
            action = "migrate"
        elif status in ("no-rule", "no-description") and not hold_unmatched:
            action, reason = "migrate", reason + "; migrated on config alone (ibns_hold_unmatched: false)"
        else:
            action, template = "hold", ""

        inventory[intf] = {"description": desc, "role": role, "config_class": cls, "status": status,
                           "action": action, "template": template, "reason": reason}
    return inventory


def ibns_port_plan(inventory):
    """Port inventory -> {interface: golden template} for ports to migrate."""
    return {intf: p["template"] for intf, p in inventory.items() if p["action"] == "migrate"}


def ibns_held_ports(inventory):
    """Port inventory -> ['Gi1/0/7 "PRN-2F": reason', ...] for held ports."""
    return [f'{intf} "{p["description"]}": {p["reason"]}'
            for intf, p in inventory.items() if p["action"] == "hold"]


def ibns_port_summary(inventory):
    """Port inventory -> counts by action, status and role (for reports)."""
    out = {"ports": len(inventory), "action": {}, "status": {}, "role": {}}
    for p in inventory.values():
        for key, value in (("action", p["action"]), ("status", p["status"]), ("role", p["role"] or "-")):
            out[key][value] = out[key].get(value, 0) + 1
    return out


def ibns_interface_auth_lines(running_config):
    """Running config -> {interface: [auth lines exactly as configured]}."""
    result = {}
    for parent, children in _blocks(running_config):
        if PHYSICAL.match(parent):
            result[parent.split()[1]] = [c for c in children if AUTH_LINE.match(c)]
    return result


def ibns_repoint_commands(auth_lines, template):
    """Commands to move one interface onto a golden template.
    Attach the template FIRST, then strip the interface-level auth lines
    (interface commands override templates), so the port is never unauthenticated."""
    cmds = [f"source template {template}"]
    cmds += [f"no {l}" for l in auth_lines if not l.startswith("source template ")]
    return cmds


def ibns_rollback_commands(saved_lines, template):
    """Commands to move one interface back to its saved (converted) config.
    Restore the saved lines FIRST, then detach the golden template."""
    cmds = [l for l in saved_lines if not l.startswith("source template ")]
    return cmds + [f"no source template {template}"]


# ------------------------------------------- CLI for Catalyst Center push --
# Catalyst Center templates run in config mode. Exec commands go between
# #MODE_ENABLE / #MODE_END_ENABLE; a command that asks a question goes inside
# #INTERACTIVE / #ENDS_INTERACTIVE as  command<IQ>question<R>answer.

def ibns_cli_exec(commands):
    """[str | {command, prompt, answer}] -> exec-mode block for a template."""
    lines = ["#MODE_ENABLE"]
    for c in commands:
        if isinstance(c, dict) and c.get("prompt"):
            lines += ["#INTERACTIVE", f"{c['command']}<IQ>{c['prompt']}<R>{c.get('answer', '')}",
                      "#ENDS_INTERACTIVE"]
        else:
            lines.append(c["command"] if isinstance(c, dict) else str(c))
    lines.append("#MODE_END_ENABLE")
    return "\n".join(lines)


def ibns_cli_interfaces(commands_by_intf):
    """{interface: [lines]} -> 'interface X' blocks, in interface order."""
    out = []
    for intf in sorted(commands_by_intf, key=_intf_key):
        if commands_by_intf[intf]:
            out.append(f"interface {intf}")
            out += [f" {l}" for l in commands_by_intf[intf]]
    return "\n".join(out)


def _intf_key(name):
    return [int(n) if n.isdigit() else n for n in re.split(r"(\d+)", name)]


def ibns_repoint_cli(port_plan, auth_lines):
    """Stage 2: CLI moving every planned port onto its golden template."""
    return ibns_cli_interfaces({i: ibns_repoint_commands(auth_lines.get(i, []), t) for i, t in port_plan.items()})


def ibns_rollback_cli(port_plan, auth_lines):
    """Stage 2 rollback: CLI putting every planned port back on its converted lines."""
    return ibns_cli_interfaces({i: ibns_rollback_commands(auth_lines.get(i, []), t) for i, t in port_plan.items()})


def ibns_find_orphans(running_config, protected=None):
    """Control-policy objects nothing references -> ordered `no ...` commands.

    Never deletes by name: an object is removed only if no interface, template or
    remaining policy-map references it, and it isn't in `protected` (golden names).
    Order: policy-maps, then class-maps, then service-templates.
    """
    protected = set(protected or [])
    blocks = _blocks(running_config)
    policies, classes, services = {}, {}, set()
    used_policies = set()
    for parent, children in blocks:
        m = re.match(r"^policy-map type control subscriber (\S+)", parent)
        if m:
            policies[m.group(1)] = children
            continue
        m = re.match(r"^class-map type control subscriber (match-\S+) (\S+)", parent)
        if m:
            classes[m.group(2)] = m.group(1)
            continue
        m = re.match(r"^service-template (\S+)", parent)
        if m:
            services.add(m.group(1))
            continue
        for c in children if (parent.startswith("interface ") or parent.startswith("template ")) else []:
            m = re.match(r"^service-policy type control subscriber (\S+)", c)
            if m:
                used_policies.add(m.group(1))

    orphan_policies = sorted(p for p in policies if p not in used_policies and p not in protected)
    live_text = "\n".join("\n".join(ch) for p, ch in policies.items() if p not in orphan_policies)
    live_text += "\n" + "\n".join("\n".join(ch) for parent, ch in blocks
                                  if parent.startswith("class-map type control subscriber"))

    def referenced(name, text):
        return re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text) is not None

    orphan_classes = sorted(c for c in classes if c not in protected and not referenced(
        c, "\n".join("\n".join(ch) for p, ch in policies.items() if p not in orphan_policies)))
    orphan_services = sorted(s for s in services if s not in protected and not referenced(s, live_text))

    cmds = [f"no policy-map type control subscriber {p}" for p in orphan_policies]
    cmds += [f"no class-map type control subscriber {classes[c]} {c}" for c in orphan_classes]
    cmds += [f"no service-template {s}" for s in orphan_services]
    return cmds


def ibns_config_checks(running_config, port_classes, golden_templates, stage, port_plan=None):
    """Layer-1 config checks. Returns a list of findings (empty = pass).

    stage: 'converted' (after stage 1) or 'golden' (after stage 2).
    port_classes: classes recorded BEFORE the change, so a port can't
    silently change class.
    port_plan: {interface: template} that stage 2 applied. When given, only
    those ports must carry a golden template (held ports stay converted).
    """
    findings = []
    current = ibns_classify_ports(running_config)
    lines = ibns_interface_auth_lines(running_config)
    for intf, cls in port_classes.items():
        auth = lines.get(intf, [])
        if cls in NON_AUTH_CLASSES and auth:
            findings.append(f"{intf}: {cls} port has auth config: {auth[0]}")
        if cls in AUTH_CLASSES:
            if not auth:
                findings.append(f"{intf}: access port lost all auth config")
            expected = (port_plan.get(intf) if port_plan is not None
                        else golden_templates.get(cls))
            if stage == "golden" and expected and f"source template {expected}" not in auth:
                findings.append(f"{intf}: missing golden template {expected}")
        if intf in current and current[intf] in NON_AUTH_CLASSES and cls in AUTH_CLASSES:
            findings.append(f"{intf}: changed from {cls} to {current[intf]}")
    return findings


# ---------------------------------------------------------- comparisons ----

def ibns_compare_sessions(pre, post, max_failures=0):
    """Per-endpoint comparison (layer 2). pre/post: parsed session lists.

    For every endpoint Authorized in `pre`, check it is present on the same
    interface, Authorized, same domain, same method, same VLAN and ACL, and
    not authorized through a critical/fail-open rule. New endpoints are
    reported, never failed.
    """
    post_by_mac = {s["mac"]: s for s in post}
    pre_macs = {s["mac"] for s in pre}
    failures, checked = [], 0
    for s in pre:
        if not str(s.get("status", "")).lower().startswith("auth"):
            continue
        checked += 1
        n = post_by_mac.get(s["mac"])
        if n is None:
            failures.append({"mac": s["mac"], "interface": s["interface"], "check": "still present",
                             "detail": "endpoint not seen after the change"})
            continue
        problems = []
        if n["interface"] != s["interface"]:
            problems.append(("still present", f"moved {s['interface']} -> {n['interface']}"))
        if not str(n.get("status", "")).lower().startswith("auth"):
            problems.append(("still authorized", f"status {n.get('status')}"))
        if s.get("domain") and n.get("domain") != s.get("domain"):
            problems.append(("still authorized", f"domain {s.get('domain')} -> {n.get('domain')}"))
        if s.get("method") and n.get("method") and n["method"] != s["method"]:
            problems.append(("same method", f"{s['method']} -> {n['method']}"))
        if (s.get("vlan"), s.get("acl")) != (n.get("vlan"), n.get("acl")):
            problems.append(("same result", f"vlan/acl {s.get('vlan')}/{s.get('acl')} -> "
                                            f"{n.get('vlan')}/{n.get('acl')}"))
        if n.get("critical") and not s.get("critical"):
            problems.append(("no fail-open", "authorized by critical/fail-open rule"))
        for check, detail in problems:
            failures.append({"mac": s["mac"], "interface": s["interface"], "check": check, "detail": detail})
    new = sorted(m for m in post_by_mac if m not in pre_macs)
    failed_endpoints = len({f["mac"] for f in failures})
    return {
        "checked": checked, "failed_endpoints": failed_endpoints, "failures": failures,
        "new_endpoints": new, "passed": failed_endpoints <= int(max_failures),
    }


def ibns_compare_baseline(baseline, now):
    """Next-day check (layer 3): interfaces that had an authorized session in the
    daytime baseline but have none now."""
    def authorized_ports(sessions):
        return {s["interface"] for s in sessions if str(s.get("status", "")).lower().startswith("auth")}

    before, after = authorized_ports(baseline), authorized_ports(now)
    missing = sorted(before - after)
    return {"baseline_ports": len(before), "ports_now": len(after),
            "ports_missing": missing, "passed": not missing}


class FilterModule(object):
    def filters(self):
        return {
            "ibns_config_mode_from_running": ibns_config_mode_from_running,
            "ibns_cli_exec": ibns_cli_exec,
            "ibns_cli_interfaces": ibns_cli_interfaces,
            "ibns_repoint_cli": ibns_repoint_cli,
            "ibns_rollback_cli": ibns_rollback_cli,
            "ibns_aaa_servers": ibns_aaa_servers,
            "ibns_flash_free": ibns_flash_free,
            "ibns_radius_group": ibns_radius_group,
            "ibns_parse_session_table": ibns_parse_session_table,
            "ibns_parse_session_details": ibns_parse_session_details,
            "ibns_classify_ports": ibns_classify_ports,
            "ibns_port_descriptions": ibns_port_descriptions,
            "ibns_description_role": ibns_description_role,
            "ibns_port_inventory": ibns_port_inventory,
            "ibns_port_plan": ibns_port_plan,
            "ibns_held_ports": ibns_held_ports,
            "ibns_port_summary": ibns_port_summary,
            "ibns_interface_auth_lines": ibns_interface_auth_lines,
            "ibns_repoint_commands": ibns_repoint_commands,
            "ibns_rollback_commands": ibns_rollback_commands,
            "ibns_find_orphans": ibns_find_orphans,
            "ibns_config_checks": ibns_config_checks,
            "ibns_compare_sessions": ibns_compare_sessions,
            "ibns_compare_baseline": ibns_compare_baseline,
        }
```

### `tests/test_ibns_filters.py`

```python
# tests/test_ibns_filters.py
# Run: pytest -q    (from the repo root, inside the venv)
# Replace the SAMPLE_* strings with real output captured from the lab switch.
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "ibns_filters", Path(__file__).parent.parent / "ansible/plugins/filter/ibns_filters.py")
f = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(f)

SAMPLE_DETAILS_DOT1X = """
            Interface:  GigabitEthernet1/0/1
               IIF-ID:  0x1A2B3C
          MAC Address:  0011.2233.4455
         IPv4 Address:  10.1.1.10
            User-Name:  host/pc1
               Status:  Authorized
               Domain:  DATA
       Oper host mode:  multi-domain
       Current Policy:  POLICY_Gi1/0/1

Server Policies:
           Vlan Group:  Vlan: 120
              ACS ACL:  xACSACLx-IP-EMPLOYEE-5f1a

Method status list:
       Method           State
        dot1x           Authc Success
"""
SAMPLE_DETAILS_MAB = """
            Interface:  GigabitEthernet1/0/1
          MAC Address:  aabb.ccdd.eeff
               Status:  Authorized
               Domain:  VOICE
       Current Policy:  POLICY_Gi1/0/1

Server Policies:
           Vlan Group:  Vlan: 121

Method status list:
       Method           State
          mab           Authc Success

            Interface:  GigabitEthernet1/0/5
          MAC Address:  1234.5678.9abc
               Status:  Authorized
               Domain:  DATA

Method status list:
       Method           State
          mab           Authc Success
"""
SAMPLE_TABLE = """
Interface                MAC Address    Method  Domain  Status Fg  Session ID
--------------------------------------------------------------------------------------------
Gi1/0/1                  0011.2233.4455 dot1x   DATA    Auth        0A0B0C0D000000123456789A
Gi1/0/1                  aabb.ccdd.eeff mab     VOICE   Auth        0A0B0C0D000000123456789B

Session count = 2
"""
SAMPLE_AAA = """
RADIUS: id 1, priority 1, host 10.9.9.10, auth-port 1812, acct-port 1813, hostname CPPM1
     State: current UP, duration 81234s, previous duration 0s
RADIUS: id 2, priority 2, host 10.9.9.11, auth-port 1812, acct-port 1813, hostname CPPM2
     State: current DEAD, duration 120s, previous duration 0s
"""
CONVERTED_CONFIG = """
hostname SW-LAB1
!
class-map type control subscriber match-all DOT1X_FAILED
 match method dot1x
 match result-type method dot1x authoritative
!
class-map type control subscriber match-all IN_CRITICAL_AUTH
 match activated-service-template DEFAULT_CRITICAL_DATA_TEMPLATE
!
policy-map type control subscriber POLICY_Gi1/0/1
 event session-started match-all
  10 class always do-until-failure
   10 authenticate using dot1x priority 10
 event authentication-failure match-first
  5 class DOT1X_FAILED do-until-failure
   10 terminate dot1x
!
policy-map type control subscriber POLICY_UNUSED
 event session-started match-all
  10 class always do-until-failure
   10 authenticate using mab priority 20
!
service-template DEFAULT_CRITICAL_DATA_TEMPLATE
service-template UNUSED_TEMPLATE
!
template IBNS2_MDA
 dot1x pae authenticator
 service-policy type control subscriber PMAP_IBNS2_GOLDEN
!
interface GigabitEthernet0/0
 vrf forwarding Mgmt-vrf
!
interface GigabitEthernet1/0/1
 switchport access vlan 120
 switchport mode access
 switchport voice vlan 121
 access-session host-mode multi-domain
 access-session port-control auto
 mab
 dot1x pae authenticator
 service-policy type control subscriber POLICY_Gi1/0/1
!
interface GigabitEthernet1/0/5
 switchport access vlan 120
 switchport mode access
 access-session port-control auto
 mab
 service-policy type control subscriber POLICY_Gi1/0/1
!
interface GigabitEthernet1/0/48
 switchport mode trunk
!
interface GigabitEthernet1/1/1
 switchport mode trunk
!
"""


def test_details_parser_merges_dot1x_and_mab_outputs():
    sessions = f.ibns_parse_session_details([SAMPLE_DETAILS_DOT1X, SAMPLE_DETAILS_MAB])
    by_mac = {s["mac"]: s for s in sessions}
    assert len(sessions) == 3
    assert by_mac["0011.2233.4455"] == {
        "interface": "GigabitEthernet1/0/1", "mac": "0011.2233.4455", "status": "Authorized",
        "domain": "DATA", "method": "dot1x", "vlan": "120", "acl": "xACSACLx-IP-EMPLOYEE-5f1a",
        "critical": False}
    assert by_mac["aabb.ccdd.eeff"]["method"] == "mab"
    assert by_mac["aabb.ccdd.eeff"]["domain"] == "VOICE"


def test_table_parser_and_interface_names():
    rows = f.ibns_parse_session_table(SAMPLE_TABLE)
    assert [r["interface"] for r in rows] == ["GigabitEthernet1/0/1"] * 2
    assert rows[1]["method"] == "mab" and rows[1]["status"] == "Authorized"


def test_aaa_servers():
    servers = f.ibns_aaa_servers(SAMPLE_AAA)
    assert [(s["host"], s["state"]) for s in servers] == [("10.9.9.10", "UP"), ("10.9.9.11", "DEAD")]


LEGACY_CONFIG = """
interface GigabitEthernet1/0/1
 switchport mode access
 authentication port-control auto
 mab
 dot1x pae authenticator
!
"""


def test_config_mode_from_running():
    assert f.ibns_config_mode_from_running(LEGACY_CONFIG) == "legacy"
    assert f.ibns_config_mode_from_running(CONVERTED_CONFIG) == "new-style"
    assert f.ibns_config_mode_from_running("hostname x\n") == "unknown"


def test_classify_ports():
    classes = f.ibns_classify_ports(CONVERTED_CONFIG)
    assert classes == {"GigabitEthernet1/0/1": "multi-domain", "GigabitEthernet1/0/5": "mab-only",
                       "GigabitEthernet1/0/48": "trunk", "GigabitEthernet1/1/1": "trunk"}


def test_repoint_and_rollback_commands_keep_port_protected():
    lines = f.ibns_interface_auth_lines(CONVERTED_CONFIG)["GigabitEthernet1/0/5"]
    repoint = f.ibns_repoint_commands(lines, "IBNS2_MAB")
    assert repoint[0] == "source template IBNS2_MAB"           # template first
    assert "no service-policy type control subscriber POLICY_Gi1/0/1" in repoint
    back = f.ibns_rollback_commands(lines, "IBNS2_MAB")
    assert back[-1] == "no source template IBNS2_MAB"           # template removed last
    assert back[:-1] == lines


def test_cli_for_catalyst_center_templates():
    exec_block = f.ibns_cli_exec([{"command": "authentication convert-to new-style", "prompt": "continue",
                                   "answer": "yes"}, "write memory"])
    assert exec_block.splitlines() == [
        "#MODE_ENABLE", "#INTERACTIVE", "authentication convert-to new-style<IQ>continue<R>yes",
        "#ENDS_INTERACTIVE", "write memory", "#MODE_END_ENABLE"]
    lines = f.ibns_interface_auth_lines(CONVERTED_CONFIG)
    plan = {"GigabitEthernet1/0/5": "IBNS2_MAB", "GigabitEthernet1/0/1": "IBNS2_MDA"}
    cli = f.ibns_repoint_cli(plan, lines).splitlines()
    assert cli[0] == "interface GigabitEthernet1/0/1" and cli[1] == " source template IBNS2_MDA"
    assert "interface GigabitEthernet1/0/5" in cli and " no mab" in cli
    back = f.ibns_rollback_cli(plan, lines).splitlines()
    assert back[-1] == " no source template IBNS2_MAB"


def test_find_orphans_only_unreferenced():
    cmds = f.ibns_find_orphans(CONVERTED_CONFIG, protected=["PMAP_IBNS2_GOLDEN"])
    assert "no policy-map type control subscriber POLICY_UNUSED" in cmds
    assert "no service-template UNUSED_TEMPLATE" in cmds
    assert not any("POLICY_Gi1/0/1" in c for c in cmds)              # still referenced
    assert not any("DOT1X_FAILED" in c for c in cmds)                # used by live policy
    assert not any("DEFAULT_CRITICAL_DATA_TEMPLATE" in c for c in cmds)  # used by class-map
    assert cmds.index("no policy-map type control subscriber POLICY_UNUSED") < \
        cmds.index("no service-template UNUSED_TEMPLATE")


def test_config_checks_detect_problems():
    classes = {"GigabitEthernet1/0/1": "multi-domain", "GigabitEthernet1/0/48": "trunk"}
    golden = {"multi-domain": "IBNS2_MDA"}
    assert f.ibns_config_checks(CONVERTED_CONFIG, classes, golden, "converted") == []
    findings = f.ibns_config_checks(CONVERTED_CONFIG, classes, golden, "golden")
    assert findings == ["GigabitEthernet1/0/1: missing golden template IBNS2_MDA"]


def test_compare_sessions():
    pre = f.ibns_parse_session_details([SAMPLE_DETAILS_DOT1X, SAMPLE_DETAILS_MAB])
    same = f.ibns_compare_sessions(pre, pre)
    assert same["passed"] and same["checked"] == 3 and same["failures"] == []
    post = [dict(s) for s in pre if s["mac"] != "1234.5678.9abc"]
    post[0]["vlan"] = "999"
    post.append({"interface": "GigabitEthernet1/0/9", "mac": "dead.beef.0001", "status": "Authorized",
                 "domain": "DATA", "method": "mab", "vlan": "120", "acl": "", "critical": False})
    result = f.ibns_compare_sessions(pre, post)
    assert not result["passed"]
    assert result["failed_endpoints"] == 2
    assert {x["check"] for x in result["failures"]} == {"still present", "same result"}
    assert result["new_endpoints"] == ["dead.beef.0001"]
    assert f.ibns_compare_sessions(pre, post, max_failures=2)["passed"]


def test_compare_baseline():
    base = f.ibns_parse_session_details([SAMPLE_DETAILS_DOT1X, SAMPLE_DETAILS_MAB])
    now = [s for s in base if s["interface"] != "GigabitEthernet1/0/5"]
    result = f.ibns_compare_baseline(base, now)
    assert result["ports_missing"] == ["GigabitEthernet1/0/5"] and not result["passed"]


def test_flash_free_and_radius_group():
    assert f.ibns_flash_free(["1621966848 bytes total (812345678 bytes free)"]) == 812345678
    assert f.ibns_flash_free("garbage") == 0
    cfg = "aaa new-model\naaa authentication dot1x default group CPPM-TOR\n"
    assert f.ibns_radius_group(cfg) == "CPPM-TOR"
    assert f.ibns_radius_group("hostname x") == ""


# ---- port roles from descriptions (classify) --------------------------------
# Replace with real descriptions from classify/unmatched_descriptions.csv.
DESCRIBED_CONFIG = """
interface GigabitEthernet1/0/1
 description USER-PC-2F-014
 switchport access vlan 120
 switchport mode access
 switchport voice vlan 121
 access-session host-mode multi-domain
 access-session port-control auto
 mab
 dot1x pae authenticator
!
interface GigabitEthernet1/0/2
 description PRN-2F-HR
 switchport access vlan 120
 switchport mode access
 access-session port-control auto
 mab
!
interface GigabitEthernet1/0/3
 description AP-3F-01
 switchport access vlan 120
 switchport mode access
 access-session port-control auto
 mab
 dot1x pae authenticator
!
interface GigabitEthernet1/0/4
 description JOHNS DESK
 switchport access vlan 120
 switchport mode access
 access-session port-control auto
 mab
 dot1x pae authenticator
!
interface GigabitEthernet1/0/5
 switchport access vlan 120
 switchport mode access
 access-session port-control auto
 mab
!
interface GigabitEthernet1/1/1
 description UPLINK TO DIST-SW1
 switchport mode trunk
!
"""
RULES = [
    {"match": r"\b(uplink|dist)\b", "role": "uplink"},
    {"match": r"\b(ap|wap)\b", "role": "ap"},
    {"match": r"\b(prn|printer)\b", "role": "printer"},
    {"match": r"\b(pc|user)\b", "role": "user"},
]
ROLES = {
    "user": {"migrate": True, "expect": ["multi-domain", "dot1x+mab", "dot1x-only"]},
    "printer": {"migrate": True, "expect": ["mab-only", "dot1x+mab"]},
    "ap": {"migrate": False, "expect": ["trunk", "static-access"]},
    "uplink": {"migrate": False, "expect": ["trunk", "port-channel-member"]},
}
TEMPLATES = {"multi-domain": "IBNS2_MDA", "dot1x+mab": "IBNS2_DOT1X_MAB",
             "dot1x-only": "IBNS2_DOT1X_MAB", "mab-only": "IBNS2_MAB"}


def test_port_descriptions():
    d = f.ibns_port_descriptions(DESCRIBED_CONFIG)
    assert d["GigabitEthernet1/0/2"] == "PRN-2F-HR"
    assert d["GigabitEthernet1/0/5"] == ""
    assert f.ibns_description_role("prn-2f-hr", RULES) == "printer"      # case-insensitive
    assert f.ibns_description_role("JOHNS DESK", RULES) == ""


def test_port_inventory_migrates_only_when_description_and_config_agree():
    inv = f.ibns_port_inventory(DESCRIBED_CONFIG, RULES, ROLES, TEMPLATES)
    got = {i: (p["role"], p["config_class"], p["status"], p["action"]) for i, p in inv.items()}
    assert got == {
        "GigabitEthernet1/0/1": ("user", "multi-domain", "ok", "migrate"),
        "GigabitEthernet1/0/2": ("printer", "mab-only", "ok", "migrate"),
        "GigabitEthernet1/0/3": ("ap", "dot1x+mab", "mismatch", "hold"),     # AP with dot1x?
        "GigabitEthernet1/0/4": ("", "dot1x+mab", "no-rule", "hold"),
        "GigabitEthernet1/0/5": ("", "mab-only", "no-description", "hold"),
        "GigabitEthernet1/1/1": ("uplink", "trunk", "ok", "leave"),
    }
    assert f.ibns_port_plan(inv) == {"GigabitEthernet1/0/1": "IBNS2_MDA", "GigabitEthernet1/0/2": "IBNS2_MAB"}
    held = f.ibns_held_ports(inv)
    assert len(held) == 3 and held[0].startswith('GigabitEthernet1/0/3 "AP-3F-01": description says ap')
    summary = f.ibns_port_summary(inv)
    assert summary["action"] == {"migrate": 2, "hold": 3, "leave": 1}


def test_hold_unmatched_false_migrates_on_config_but_still_holds_mismatches():
    inv = f.ibns_port_inventory(DESCRIBED_CONFIG, RULES, ROLES, TEMPLATES, hold_unmatched=False)
    assert inv["GigabitEthernet1/0/4"]["action"] == "migrate"
    assert inv["GigabitEthernet1/0/5"]["action"] == "migrate"
    assert inv["GigabitEthernet1/0/3"]["action"] == "hold"


def test_ports_already_on_golden_templates_are_done():
    golden = DESCRIBED_CONFIG.replace(" access-session port-control auto\n mab\n!\ninterface GigabitEthernet1/0/3",
                                      " source template IBNS2_MAB\n!\ninterface GigabitEthernet1/0/3")
    inv = f.ibns_port_inventory(golden, RULES, ROLES, TEMPLATES)
    assert inv["GigabitEthernet1/0/2"]["config_class"] == "mab-only"     # read back from the template
    assert inv["GigabitEthernet1/0/2"]["action"] == "done"
    assert "GigabitEthernet1/0/2" not in f.ibns_port_plan(inv)


def test_bad_rule_regex_is_reported():
    try:
        f.ibns_description_role("x", [{"match": "(unclosed", "role": "user"}])
    except ValueError as exc:
        assert "rule 1" in str(exc)
    else:
        raise AssertionError("bad regex not reported")


def test_config_checks_ignore_held_ports_when_plan_given():
    classes = f.ibns_classify_ports(CONVERTED_CONFIG)
    plan = {}                                  # Gi1/0/1 and Gi1/0/5 were held
    assert f.ibns_config_checks(CONVERTED_CONFIG, classes, TEMPLATES, "golden", plan) == []
    assert f.ibns_config_checks(CONVERTED_CONFIG, classes, TEMPLATES, "golden") != []


def test_group_vars_rules_compile_and_roles_exist():
    import yaml
    data = yaml.safe_load((Path(__file__).parent.parent / "ansible/playbooks/group_vars/all.yml").read_text())
    rules, roles = data["ibns_description_rules"], data["ibns_port_roles"]
    assert {r["role"] for r in rules} <= set(roles)            # every rule names a defined role
    for desc, role in [("AP-3F-01", "ap"), ("Uplink to DIST1", "uplink"), ("PRN-HR", "printer"),
                       ("PC/PH 2F-14", "phone"), ("USER-2F-14", "user"), ("SPARE", "unused")]:
        assert f.ibns_description_role(desc, rules) == role, desc
```

### `ansible/plugins/module_utils/catc_client.py`

```python
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
```

### `tests/test_catc_client.py`

```python
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
```

### `ansible/plugins/modules/catc_device.py`

```python
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
```

### `ansible/plugins/modules/catc_cli_read.py`

```python
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
```

### `ansible/plugins/modules/catc_cli_push.py`

```python
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
```

## Phase 2: read-only jobs (run against the lab switch)

Then run `ibns_classify.yml`, `ibns_precheck.yml` and `ibns_baseline.yml` against the lab switch. Nothing here changes config; the reads go through Catalyst Center Command Runner.

### `ansible/playbooks/group_vars/all.yml`

```yaml
# ansible/playbooks/group_vars/all.yml   (playbook-side: loads for every inventory, laptop and AAP)
# REPLACES ud00's all.yml (which held CML lab settings and SWIM golden images).
# Values marked DECIDE need a team decision; values marked CONFIRM need checking.
---
# ---- Catalyst Center (every read and every change goes through it) -----------
# No SSH to switches. Reads: Command Runner. Changes: Template Programmer.
# AAP: the DNAC service-ID credential injects DEVOPS_USERNAME / DEVOPS_PASSWORD.
# Laptop: export DEVOPS_USERNAME, DEVOPS_PASSWORD (Catalyst Center login) and
#         CATC_HOST; CATC_CA_BUNDLE if the RBC CA isn't in the system store.
# CONFIRM: dnac_host from the dnac inventory plugin is the Catalyst Center
#          address that manages the switch (else set CATC_HOST).
catc_host: "{{ dnac_host | default(lookup('ansible.builtin.env', 'CATC_HOST'), true) }}"
catc:
  host: "{{ catc_host }}"
  username: "{{ lookup('ansible.builtin.env', 'DEVOPS_USERNAME') }}"
  password: "{{ lookup('ansible.builtin.env', 'DEVOPS_PASSWORD') }}"
  validate_certs: true
  ca_path: "{{ lookup('ansible.builtin.env', 'CATC_CA_BUNDLE') }}"
catc_template_project: IBNS2            # Template Programmer project (created if missing)
catc_template_prefix: IBNS2_            # one template per switch: IBNS2_<hostname>
catc_template_language: JINJA           # CONFIRM #MODE_ENABLE / #INTERACTIVE work in JINJA on our version
catc_deploy_timeout: 900                # seconds to wait for a deployment
ibns_catc_ok_collection: [Managed]      # collection status the pre-check accepts

# ---- safety defaults ---------------------------------------------------------
dry_run: true                       # nothing changes unless the survey sets false
ibns_single_site: true              # one site per job
ibns_max_devices_per_job: 20        # DECIDE
ibns_serial: 5                      # switches changed at the same time within a job
ibns_change_regex: "^CHG[0-9]{7}$"  # CONFIRM ServiceNow change number format

# ---- pre-check thresholds ----------------------------------------------------
ibns_min_iosxe: "17.12.05"          # DECIDE minimum IOS-XE for IBNS 2.0
ibns_min_aaa_up: 1                  # RADIUS servers to ClearPass that must be UP
ibns_min_flash_bytes: 10485760      # 10 MB free for the config backup
ibns_flash_command: "dir flash:"    # CONFIRM Command Runner accepts 'dir' (else "show flash:")
ibns_flash_backup: true             # also copy the running config to flash before each change
ibns_convert_prompt: "continue"     # CONFIRM: text in the convert-to new-style confirmation prompt

# ---- post-check --------------------------------------------------------------
ibns_reauth_wait: 120               # seconds to wait before comparing sessions (lab-tune)
ibns_max_failed_endpoints: 0        # endpoints allowed to fail before rollback

# ---- golden config -------------------------------------------------------------
ibns_template_dir: "{{ playbook_dir }}/../templates/ibns2"
ibns_mode: closed                   # DECIDE: closed | low-impact
ibns_policy_name: PMAP_IBNS2_GOLDEN
ibns_preauth_acl: IBNS2_PREAUTH     # used only in low-impact mode; ACL must already exist
ibns_critical_data_vlan: ""         # empty = critical auth keeps the port's access VLAN
ibns_dot1x_tx_period: 10            # DECIDE (lab-tune MAB fallback timing)
ibns_dot1x_max_reauth_req: 2        # DECIDE
ibns_restart_seconds: 60

# Port class (from the config) -> golden interface template.
# Classes not listed here are never touched. The description must also agree
# (see port roles below) or the port is held.
ibns_port_templates:
  multi-domain: IBNS2_MDA
  dot1x+mab: IBNS2_DOT1X_MAB
  dot1x-only: IBNS2_DOT1X_MAB
  mab-only: IBNS2_MAB

# ---- port roles from interface descriptions ----------------------------------
# A port is migrated only when its DESCRIPTION (role) and its CONFIG (class)
# agree. Everything here is a starting guess: CONFIRM against real descriptions.
# Build the rules from data, not memory:
#   python python/ibns_tools/classify_ports.py --run reports/raw/<date>
#   then read classify/unmatched_descriptions.csv and classify/held_ports.csv
#
# Rules: first match wins. 'match' is a Python regex, case-insensitive,
# searched anywhere in the description. Keep single quotes (no escaping needed).
# Put narrow rules (uplinks, APs) above broad ones (users).
ibns_description_rules:
  - { match: '\b(uplink|upl|dist|core|mdf|idf)\b|^to[-_ ]|\bpo\d+\b', role: uplink }
  - { match: '\b(ap|wap|wifi|wlan|aironet)\b', role: ap }
  - { match: '\b(srv|server|esx|ups|pdu)\b', role: server }
  - { match: '\b(prn|prt|printer|mfp|mfd|plotter)\b', role: printer }
  - { match: '\b(cam|cams|camera|cctv|nvr)\b', role: camera }
  - { match: '\b(atm|kiosk|badge|door|hvac|bms|iot|tv|display)\b', role: facilities }
  - { match: '\b(ph|phone|voip|ipt|ip[-_ ]?phone)\b', role: phone }
  - { match: '\b(pc|desk|wkst|workstation|user|data|teller)\b', role: user }
  - { match: '\b(unused|spare|available|not[-_ ]in[-_ ]use|reserved)\b', role: unused }

# Role -> may it be migrated, and which config classes are consistent with it.
# A port whose config class is not in 'expect' is a mismatch and is HELD.
ibns_port_roles:
  user:       { migrate: true,  expect: [multi-domain, dot1x+mab, dot1x-only] }
  phone:      { migrate: true,  expect: [multi-domain] }
  printer:    { migrate: true,  expect: [mab-only, dot1x+mab, multi-domain] }
  camera:     { migrate: true,  expect: [mab-only, dot1x+mab] }
  facilities: { migrate: true,  expect: [mab-only, dot1x+mab, multi-domain] }
  unused:     { migrate: true,  expect: [multi-domain, dot1x+mab, dot1x-only, mab-only, shutdown-static] }
  ap:         { migrate: false, expect: [trunk, static-access] }
  uplink:     { migrate: false, expect: [trunk, port-channel-member, routed, uplink-module] }
  server:     { migrate: false, expect: [static-access, trunk, shutdown-static] }

ibns_hold_unmatched: true      # true = auth ports with no matching rule are held, not migrated
ibns_max_held_ports: 0         # DECIDE: pre-check fails the switch above this many held ports

# Golden object names. Cleanup never removes these, even when unreferenced.
ibns_golden_names:
  - PMAP_IBNS2_GOLDEN
  - IBNS2_MDA
  - IBNS2_DOT1X_MAB
  - IBNS2_MAB
  - IBNS2_CRITICAL_DATA
  - IBNS2_CRITICAL_VOICE
  - IBNS2_DOT1X_FAILED
  - IBNS2_DOT1X_NO_RESP
  - IBNS2_MAB_FAILED
  - IBNS2_AAA_DOWN_UNAUTHD
  - IBNS2_AAA_DOWN_AUTHD
  - IBNS2_IN_CRITICAL
  - IBNS2_NOT_IN_CRITICAL

# ---- snapshot store ------------------------------------------------------------
# local       = laptop runs (folder below)
# artifactory = AAP runs (jobs on different days must share snapshots)
ibns_snapshot_backend: local
ibns_snapshot_dir: "{{ lookup('ansible.builtin.env', 'IBNS_SNAPSHOT_DIR') | default(playbook_dir ~ '/../../reports/raw/snapshots', true) }}"
ibns_artifactory_url: "https://<ARTIFACTORY_HOST>/artifactory/<GENERIC_REPO>/ibns2"   # CONFIRM
```

### `ansible/inventories/lab/hosts.yml`

```yaml
# ansible/inventories/lab/hosts.yml
# NEW. Static lab inventory for laptop runs. The lab switch must be managed by
# the lab Catalyst Center: every job reaches it through Catalyst Center, never
# over SSH. Use with: ansible-playbook -i ansible/inventories/lab/hosts.yml ...
---
all:
  hosts:
    <LAB-SWITCH-HOSTNAME>:                  # exactly as Catalyst Center shows it
      dnac_host: <LAB-CATALYST-CENTER>      # address of the Catalyst Center that manages it
```

### `ansible/playbooks/roles/inventory_lookup/tasks/main.yml`

```yaml
# roles/inventory_lookup/tasks/main.yml
# COPIED FROM ud00 AND EDITED. Four changes from the ud00 version:
#   1. group swim_devices        -> ibns_targets
#   2. subgroup prefix swim_     -> ibns_
#   3. controller_host falls back to 'lab' for hosts from the static lab
#      inventory (they have no dnac_host); the vManage fallback is removed.
#   4. hosts run LOCALLY (ansible_connection: local): IBNS never logs into a
#      switch; every task talks to Catalyst Center from the controller.
---
- name: Validate device_list is non-empty and contains no blank entries
  ansible.builtin.fail:
    msg: "device_list is empty or contains blank entries. Refusing to match all DNAC devices."
  when: (device_list | length == 0) or ('' in device_list)

- name: Match each survey device against the AAP inventory (case-insensitive exact match required)
  vars:
    matched: "{{ groups['all'] | select('match', '(?i)^' ~ (item | regex_escape) ~ '(\\.|$)') | list }}"
  ansible.builtin.fail:
    msg: >-
      Device '{{ item }}' matched {{ matched | length }} host(s) in inventory:
      [{{ matched | join(', ') }}]. Expected exactly 1 case-insensitive exact match.
  when: matched | length != 1
  loop: "{{ device_list }}"

- name: Add matched inventory hosts to ibns_targets group
  vars:
    matched: "{{ groups['all'] | select('match', '(?i)^' ~ (item | regex_escape) ~ '(\\.|$)') | list }}"
    controller_host: "{{ hostvars[matched[0]].dnac_host | default('lab') }}"
    controller_subgroup: "ibns_{{ controller_host | regex_replace('[^a-zA-Z0-9_]', '_') | lower }}"
  ansible.builtin.add_host:
    name: "{{ matched[0] }}"
    groups:
      - ibns_targets
      - "{{ controller_subgroup }}"
    ansible_connection: local
    ansible_python_interpreter: "{{ ansible_playbook_python }}"
  loop: "{{ device_list }}"
```

### `ansible/playbooks/roles/ibns_input_validation/tasks/main.yml`

```yaml
# roles/ibns_input_validation/tasks/main.yml
# IBNS-specific survey checks. Runs on localhost after the copied
# odyssey_parse_devices + input_validation roles, before inventory_lookup.
---
- name: Validate dry_run is a boolean
  ansible.builtin.assert:
    that:
      - dry_run | string | lower in ['true', 'false']
    fail_msg: "dry_run must be true or false, got '{{ dry_run }}'."

- name: Validate the ServiceNow change number for config-changing stages
  when: ibns_requires_change | default(false) | bool and not (dry_run | bool)
  ansible.builtin.assert:
    that:
      - change_number is defined
      - change_number is match(ibns_change_regex)
    fail_msg: "A valid change number (pattern {{ ibns_change_regex }}) is required when dry_run is false."

- name: Limit how many switches one job may touch
  ansible.builtin.assert:
    that:
      - device_list | length <= ibns_max_devices_per_job | int
    fail_msg: >-
      {{ device_list | length }} switches requested; the limit per job is
      {{ ibns_max_devices_per_job }}. Split the site into smaller jobs.
```

### `ansible/playbooks/roles/ibns_snapshot/tasks/save.yml`

```yaml
# roles/ibns_snapshot/tasks/save.yml
# Saves one snapshot for the current host.
# Inputs: snapshot_name (e.g. "baseline.json"), snapshot_content (string)
# Backend "local" = a folder on the machine running Ansible (laptop runs only:
#   AAP containers are thrown away after each job).
# Backend "artifactory" = a generic Artifactory repo, so AAP jobs on different
#   days can read each other's snapshots (baseline -> next-day check).
---
- name: Save snapshot to local folder
  when: ibns_snapshot_backend == "local"
  delegate_to: localhost
  vars:
    ansible_connection: local
  block:
    - name: Create host snapshot folder
      ansible.builtin.file:
        path: "{{ ibns_snapshot_dir }}/{{ inventory_hostname }}"
        state: directory
        mode: "0700"

    - name: Write snapshot file
      ansible.builtin.copy:
        content: "{{ snapshot_content }}"
        dest: "{{ ibns_snapshot_dir }}/{{ inventory_hostname }}/{{ snapshot_name }}"
        mode: "0600"

- name: Save snapshot to Artifactory
  when: ibns_snapshot_backend == "artifactory"
  ansible.builtin.uri:
    url: "{{ ibns_artifactory_url }}/{{ inventory_hostname }}/{{ snapshot_name }}"
    method: PUT
    body: "{{ snapshot_content }}"
    url_username: "{{ lookup('env', 'ARTIFACTORY_USERNAME') }}"
    url_password: "{{ lookup('env', 'ARTIFACTORY_PASSWORD') }}"
    force_basic_auth: true
    status_code: [200, 201]
    validate_certs: true
  delegate_to: localhost
  vars:
    ansible_connection: local
```

### `ansible/playbooks/roles/ibns_snapshot/tasks/load.yml`

```yaml
# roles/ibns_snapshot/tasks/load.yml
# Loads one snapshot for the current host into the fact `ibns_loaded` (parsed JSON).
# Input: snapshot_name. Fails clearly if the snapshot doesn't exist.
---
- name: Load snapshot from local folder
  when: ibns_snapshot_backend == "local"
  ansible.builtin.set_fact:
    ibns_loaded: "{{ lookup('ansible.builtin.file', ibns_snapshot_dir ~ '/' ~ inventory_hostname ~ '/' ~ snapshot_name) | from_json }}"

- name: Load snapshot from Artifactory
  when: ibns_snapshot_backend == "artifactory"
  block:
    - name: Download snapshot
      ansible.builtin.uri:
        url: "{{ ibns_artifactory_url }}/{{ inventory_hostname }}/{{ snapshot_name }}"
        method: GET
        url_username: "{{ lookup('env', 'ARTIFACTORY_USERNAME') }}"
        url_password: "{{ lookup('env', 'ARTIFACTORY_PASSWORD') }}"
        force_basic_auth: true
        return_content: true
        validate_certs: true
      register: ibns_download
      delegate_to: localhost
      vars:
        ansible_connection: local

    - name: Parse snapshot
      ansible.builtin.set_fact:
        ibns_loaded: "{{ ibns_download.content | from_json }}"
```

### `ansible/playbooks/roles/ibns_collect/tasks/main.yml`

```yaml
# roles/ibns_collect/tasks/main.yml
# Read-only, through Catalyst Center (no SSH to the switch).
# Finds the switch in Catalyst Center (fact `ibns_device`), runs the show
# commands through Command Runner, and parses them into the fact `ibns_state`
# (running config, config mode, AAA servers, sessions, flash free, port
# classes, port inventory from descriptions + config, migration plan,
# interface auth lines).
---
- name: Find the switch in Catalyst Center
  catc_device:
    catc: "{{ catc }}"
    hostname: "{{ inventory_hostname }}"
  register: ibns_catc_device

- name: Keep the Catalyst Center device record
  ansible.builtin.set_fact:
    ibns_device: "{{ ibns_catc_device.device }}"

- name: Run show commands through Command Runner
  catc_cli_read:
    catc: "{{ catc }}"
    device_id: "{{ ibns_device.id }}"
    commands:
      - show running-config
      - show aaa servers
      - show access-session method dot1x details
      - show access-session method mab details
      - "{{ ibns_flash_command }}"
  register: ibns_raw

- name: Parse collected output
  ansible.builtin.set_fact:
    ibns_state:
      collected_at: "{{ now(utc=true, fmt='%Y-%m-%dT%H:%M:%SZ') }}"
      running: "{{ ibns_raw.output[0] }}"
      config_mode: "{{ ibns_raw.output[0] | ibns_config_mode_from_running }}"
      aaa_servers: "{{ ibns_raw.output[1] | ibns_aaa_servers }}"
      sessions: "{{ [ibns_raw.output[2], ibns_raw.output[3]] | ibns_parse_session_details }}"
      flash_free: "{{ ibns_raw.output[4] | ibns_flash_free }}"
      port_classes: "{{ ibns_raw.output[0] | ibns_classify_ports }}"
      port_inventory: "{{ ibns_raw.output[0] | ibns_port_inventory(ibns_description_rules, ibns_port_roles, ibns_port_templates, ibns_hold_unmatched) }}"
      auth_lines: "{{ ibns_raw.output[0] | ibns_interface_auth_lines }}"

- name: Work out which ports migrate and which are held
  ansible.builtin.set_fact:
    ibns_state: "{{ ibns_state | combine({'port_plan': ibns_state.port_inventory | ibns_port_plan, 'held_ports': ibns_state.port_inventory | ibns_held_ports}) }}"

- name: Summarise collected state
  ansible.builtin.debug:
    msg: >-
      {{ inventory_hostname }}: mode={{ ibns_state.config_mode }},
      sessions={{ ibns_state.sessions | length }},
      AAA UP={{ ibns_state.aaa_servers | selectattr('state', 'equalto', 'UP') | list | length }}/{{ ibns_state.aaa_servers | length }},
      ports={{ ibns_state.port_classes | length }},
      migrate={{ ibns_state.port_plan | length }},
      held={{ ibns_state.held_ports | length }}
```

### `ansible/playbooks/roles/ibns_report/tasks/main.yml`

```yaml
# roles/ibns_report/tasks/main.yml
# Publishes the per-switch result as AAP job artifacts (set_stats). The existing
# NetValidator notification webhook forwards job.artifacts to Odyssey.
# Input: ibns_result (dict built by the stage playbook).
---
- name: Publish result as job artifact
  ansible.builtin.set_stats:
    data:
      ibns_results: "{{ {inventory_hostname: ibns_result} }}"
    aggregate: true
    per_host: false

- name: Show result
  ansible.builtin.debug:
    msg:
      - "Host:    {{ inventory_hostname }}"
      - "Stage:   {{ ibns_result.stage }}"
      - "Outcome: {{ ibns_result.outcome }}"
      - "Detail:  {{ ibns_result.detail | default('') }}"
```

### `ansible/playbooks/roles/ibns_precheck/tasks/main.yml`

```yaml
# roles/ibns_precheck/tasks/main.yml
# Read-only gate before any stage. Collects state through Catalyst Center
# (ibns_collect) and checks it.
# Inputs: ibns_expected_mode = legacy | new-style | any
#         ibns_check_migration = true (default) | false for stage 3, where ports
#         are already on golden templates and nothing is left to migrate
# On failure the switch is reported as "skipped" and removed from the run;
# other switches in the job carry on.
---
- name: Collect switch state
  ansible.builtin.include_role:
    name: ibns_collect

- name: Start with no failures
  ansible.builtin.set_fact:
    ibns_precheck_failures: []
    ibns_aaa_up: "{{ ibns_state.aaa_servers | selectattr('state', 'equalto', 'UP') | list | length }}"

- name: Check Catalyst Center can manage the switch
  when: ibns_device.reachabilityStatus != 'Reachable' or ibns_device.collectionStatus not in ibns_catc_ok_collection
  ansible.builtin.set_fact:
    ibns_precheck_failures: "{{ ibns_precheck_failures + ['Catalyst Center shows ' ~ ibns_device.reachabilityStatus ~ ' / ' ~ ibns_device.collectionStatus] }}"

- name: Check IOS-XE version
  when: ibns_device.softwareVersion is version(ibns_min_iosxe, '<')
  ansible.builtin.set_fact:
    ibns_precheck_failures: "{{ ibns_precheck_failures + ['IOS-XE ' ~ ibns_device.softwareVersion ~ ' is below ' ~ ibns_min_iosxe] }}"

- name: Check RADIUS servers to ClearPass are UP
  when: ibns_aaa_up | int < ibns_min_aaa_up | int
  ansible.builtin.set_fact:
    ibns_precheck_failures: "{{ ibns_precheck_failures + ['only ' ~ ibns_aaa_up ~ ' RADIUS server(s) UP, need ' ~ ibns_min_aaa_up] }}"

- name: Check authentication config mode
  when: ibns_expected_mode != 'any' and ibns_state.config_mode != ibns_expected_mode
  ansible.builtin.set_fact:
    ibns_precheck_failures: "{{ ibns_precheck_failures + ['config mode is ' ~ ibns_state.config_mode ~ ', expected ' ~ ibns_expected_mode] }}"

- name: Check free flash for the config backup
  when: ibns_state.flash_free | int < ibns_min_flash_bytes | int
  ansible.builtin.set_fact:
    ibns_precheck_failures: "{{ ibns_precheck_failures + ['only ' ~ ibns_state.flash_free ~ ' bytes free on flash'] }}"

- name: Check there are access ports to migrate
  when:
    - ibns_check_migration | default(true) | bool
    - ibns_state.port_plan | length == 0
  ansible.builtin.set_fact:
    ibns_precheck_failures: "{{ ibns_precheck_failures + ['no access ports to migrate (no auth ports whose description and config agree)'] }}"

- name: Check held ports (description and config disagree, or no rule matched)
  when:
    - ibns_check_migration | default(true) | bool
    - ibns_state.held_ports | length > ibns_max_held_ports | int
  ansible.builtin.set_fact:
    ibns_precheck_failures: "{{ ibns_precheck_failures + [(ibns_state.held_ports | length) ~ ' held port(s), allowed ' ~ ibns_max_held_ports ~ ': ' ~ (ibns_state.held_ports | join(' | '))] }}"

- name: List held ports (left on the converted config, not templated)
  when: ibns_state.held_ports | length > 0
  ansible.builtin.debug:
    msg: "{{ ibns_state.held_ports }}"

- name: Report and skip this switch if any check failed
  when: ibns_precheck_failures | length > 0
  block:
    - name: Report skipped switch
      ansible.builtin.include_role:
        name: ibns_report
      vars:
        ibns_result:
          stage: "{{ ibns_stage_tag | default('precheck') }}"
          outcome: skipped
          detail: "{{ ibns_precheck_failures | join('; ') }}"

    - name: Stop here for this switch
      ansible.builtin.fail:
        msg: "Pre-check failed: {{ ibns_precheck_failures | join('; ') }}"

- name: Pre-check passed
  ansible.builtin.debug:
    msg: "{{ inventory_hostname }}: pre-check passed ({{ ibns_state.sessions | length }} sessions recorded)."
```

### `ansible/playbooks/ibns_target.yml`

```yaml
# ansible/playbooks/ibns_target.yml
# Imported FIRST by every IBNS playbook. Turns the survey hostname list into the
# `ibns_targets` group with the same guardrails as the SWIM repo, and sets one
# run id shared by every switch in the job.
---
- name: Resolve and validate target switches
  hosts: localhost
  gather_facts: false
  connection: local
  tasks:
    - name: Parse survey hostnames into device_list
      ansible.builtin.include_role:
        name: odyssey_parse_devices

    - name: Validate survey input (copied role)
      ansible.builtin.include_role:
        name: input_validation

    - name: Validate IBNS survey input
      ansible.builtin.include_role:
        name: ibns_input_validation

    - name: Match hostnames to inventory (exactly one match each)
      ansible.builtin.include_role:
        name: inventory_lookup

    - name: Refuse targets spread over more than one site
      when: ibns_single_site | bool
      vars:
        ibns_sites: "{{ groups['ibns_targets'] | map('extract', hostvars, 'dnac_site_path') | select('defined') | unique | list }}"
      ansible.builtin.assert:
        that: ibns_sites | length <= 1
        fail_msg: "Targets span {{ ibns_sites | length }} sites: {{ ibns_sites }}. One site per job."

    - name: Set one run id for every switch in this job
      ansible.builtin.set_fact:
        ibns_run_id: "{{ now(utc=true, fmt='%Y%m%dT%H%M%SZ') }}"
```

### `ansible/playbooks/ibns_classify.yml`

```yaml
# ansible/playbooks/ibns_classify.yml
# RUN ORDER: 0b (after discovery, before the baseline; re-run any time)
# Read-only. Classifies every physical port by description (role) and config
# (class), and shows which ports will migrate, which are held and why.
# Fix held ports (description or config) BEFORE the change, or raise
# ibns_max_held_ports for that site on purpose.
---
- name: Resolve targets
  ansible.builtin.import_playbook: ibns_target.yml

- name: Classify ports (read-only)
  hosts: ibns_targets
  gather_facts: false
  vars:
    ibns_run_id: "{{ hostvars['localhost']['ibns_run_id'] }}"
  tasks:
    - name: Collect switch state
      ansible.builtin.include_role:
        name: ibns_collect

    - name: Show every port (interface | role | config class | action | description | reason)
      ansible.builtin.debug:
        msg: "{{ item.key }} | {{ item.value.role or '-' }} | {{ item.value.config_class }} | {{ item.value.action }} | {{ item.value.description }}{{ (' | ' ~ item.value.reason) if item.value.reason else '' }}"
      loop: "{{ ibns_state.port_inventory | dict2items }}"
      loop_control:
        label: "{{ item.key }}"

    - name: Save the port inventory
      ansible.builtin.include_role:
        name: ibns_snapshot
        tasks_from: save
      vars:
        snapshot_name: "classify-{{ ibns_run_id }}.json"
        snapshot_content: "{{ {'collected_at': ibns_state.collected_at, 'port_inventory': ibns_state.port_inventory, 'port_plan': ibns_state.port_plan, 'held_ports': ibns_state.held_ports} | to_nice_json }}"

    - name: Report
      ansible.builtin.include_role:
        name: ibns_report
      vars:
        ibns_summary: "{{ ibns_state.port_inventory | ibns_port_summary }}"
        ibns_result:
          stage: classify
          outcome: >-
            {{ 'NEEDS-FIX' if ibns_state.held_ports | length > ibns_max_held_ports | int else
               ('ready' if ibns_state.port_plan | length > 0 else
               ('done' if ibns_summary.action.done | default(0) > 0 else 'NOTHING-TO-MIGRATE')) }}
          detail: >-
            {{ ibns_summary.ports }} ports: migrate {{ ibns_summary.action.migrate | default(0) }},
            hold {{ ibns_summary.action.hold | default(0) }}, leave {{ ibns_summary.action.leave | default(0) }},
            done {{ ibns_summary.action.done | default(0) }};
            roles {{ ibns_summary.role }};
            held: {{ ibns_state.held_ports }}
```

### `ansible/playbooks/ibns_baseline.yml`

```yaml
# ansible/playbooks/ibns_baseline.yml
# RUN ORDER: 1 (one or two days before the change, DURING BUSINESS HOURS)
# Read-only. Records which ports authenticate and how, for the next-day check.
---
- name: Resolve targets
  ansible.builtin.import_playbook: ibns_target.yml

- name: Capture daytime session baseline (read-only)
  hosts: ibns_targets
  gather_facts: false
  vars:
    ibns_run_id: "{{ hostvars['localhost']['ibns_run_id'] }}"
  tasks:
    - name: Collect switch state
      ansible.builtin.include_role:
        name: ibns_collect

    - name: Save baseline (dated copy and latest)
      ansible.builtin.include_role:
        name: ibns_snapshot
        tasks_from: save
      vars:
        snapshot_name: "{{ item }}"
        snapshot_content: "{{ {'collected_at': ibns_state.collected_at, 'sessions': ibns_state.sessions, 'port_classes': ibns_state.port_classes, 'port_plan': ibns_state.port_plan, 'config_mode': ibns_state.config_mode} | to_nice_json }}"
      loop:
        - "baseline-{{ ibns_run_id }}.json"
        - "baseline-latest.json"

    - name: Report
      ansible.builtin.include_role:
        name: ibns_report
      vars:
        ibns_result:
          stage: baseline
          outcome: recorded
          detail: >-
            {{ ibns_state.sessions | length }} sessions on
            {{ ibns_state.sessions | map(attribute='interface') | unique | list | length }} ports
```

### `ansible/playbooks/ibns_precheck.yml`

```yaml
# ansible/playbooks/ibns_precheck.yml
# RUN ORDER: 2 (day of the change, before the window; safe to run any time)
# Read-only. Same checks every stage runs first, as a standalone go/no-go.
# Run the discovery drift `compare` from your laptop before this.
---
- name: Resolve targets
  ansible.builtin.import_playbook: ibns_target.yml

- name: Pre-check (read-only)
  hosts: ibns_targets
  gather_facts: false
  vars:
    ibns_run_id: "{{ hostvars['localhost']['ibns_run_id'] }}"
    ibns_stage_tag: precheck
    ibns_expected_mode: any
  tasks:
    - name: Run pre-check
      ansible.builtin.include_role:
        name: ibns_precheck

    - name: Report
      ansible.builtin.include_role:
        name: ibns_report
      vars:
        ibns_result:
          stage: precheck
          outcome: passed
          detail: "mode={{ ibns_state.config_mode }}, sessions={{ ibns_state.sessions | length }}"
```

## Phase 3: stage 1, convert (lab only until proven)

Run in dry-run first (it prints the exact CLI each push would send), then for real on the lab switch. Then look at the template `IBNS2_<lab switch>` in Catalyst Center: one version per push.

### `ansible/playbooks/roles/ibns_push/tasks/main.yml`

```yaml
# roles/ibns_push/tasks/main.yml
# The ONLY place IBNS changes a switch. Pushes CLI through Catalyst Center:
# one template per switch (IBNS2_<hostname> in the IBNS2 project). Each push
# replaces its content, commits a new version (comment = run id, stage, step),
# deploys it and checks the result. The template's version history in
# Catalyst Center is the record of every IBNS change on that switch.
# Inputs:
#   ibns_push_step      short name of the step (backup, convert, golden-global, ...)
#   ibns_push_cli       rendered CLI (exec blocks built with the ibns_cli_exec filter)
#   ibns_push_may_fail  true = record a failed deployment instead of failing the
#                       switch, so the post-check and rollback can deal with it
# Output: ibns_push_error ('' when the push worked)
# Dry run: shows the CLI, changes nothing.
---
- name: "Dry run - CLI that would be pushed: {{ ibns_push_step }}"
  when: dry_run | bool
  ansible.builtin.debug:
    msg: "{{ ibns_push_cli.splitlines() }}"

- name: "Push through Catalyst Center: {{ ibns_push_step }}"
  when: not (dry_run | bool)
  catc_cli_push:
    catc: "{{ catc }}"
    device_id: "{{ ibns_device.id }}"
    project: "{{ catc_template_project }}"
    template_name: "{{ catc_template_prefix }}{{ inventory_hostname }}"
    content: "{{ ibns_push_cli }}"
    comment: "{{ ibns_run_id }} {{ ibns_stage_tag | default('') }} {{ ibns_push_step }}"
    language: "{{ catc_template_language }}"
    timeout: "{{ catc_deploy_timeout }}"
  register: ibns_push_result
  failed_when: >-
    ibns_push_result.deployment_status | default('') != 'SUCCESS'
    and not (ibns_push_may_fail | default(false) | bool)

- name: Record the push result ('' = deployed successfully, or dry run)
  ansible.builtin.set_fact:
    ibns_push_error: >-
      {{ '' if (dry_run | bool or ibns_push_result.deployment_status | default('') == 'SUCCESS')
         else ibns_push_result.msg | default('push failed') }}

- name: Keep the pushed CLI with the run's snapshots
  when: not (dry_run | bool)
  ansible.builtin.include_role:
    name: ibns_snapshot
    tasks_from: save
  vars:
    snapshot_name: "pushed-{{ ibns_stage_tag | default('manual') }}-{{ ibns_push_step }}-{{ ibns_run_id }}.txt"
    snapshot_content: "{{ ibns_push_cli ~ '\n\n! result: ' ~ (ibns_push_error or 'SUCCESS') }}"
```

### `ansible/playbooks/roles/ibns_save/tasks/main.yml`

```yaml
# roles/ibns_save/tasks/main.yml
# Saves the config (write memory) through Catalyst Center, then asks Catalyst
# Center to resync the switch so its inventory and config archive are current.
# Call only after a passed post-check. Note: a Catalyst Center deployment may
# already save the config itself (UI option "Copy running config to startup
# config", on by default). VERIFY in the lab what an API deployment does.
---
- name: Save the config
  ansible.builtin.include_role:
    name: ibns_push
  vars:
    ibns_push_step: save
    ibns_push_cli: "{{ ['write memory'] | ibns_cli_exec }}"

- name: Resync the switch in Catalyst Center
  when: not (dry_run | bool)
  catc_device:
    catc: "{{ catc }}"
    hostname: "{{ inventory_hostname }}"
    sync: true
  failed_when: false
```

### `ansible/playbooks/roles/ibns_backup/tasks/main.yml`

```yaml
# roles/ibns_backup/tasks/main.yml
# Saves the running config off-box (snapshot store) and on the switch's flash
# (through Catalyst Center). Catalyst Center's own config archive is a third copy.
# Inputs: ibns_stage_tag (e.g. "stage1"), ibns_run_id, ibns_state (from ibns_collect)
---
- name: Save running config to the snapshot store
  ansible.builtin.include_role:
    name: ibns_snapshot
    tasks_from: save
  vars:
    snapshot_name: "running-before-{{ ibns_stage_tag }}-{{ ibns_run_id }}.cfg"
    snapshot_content: "{{ ibns_state.running }}"

- name: Copy running config to flash
  when: ibns_flash_backup | bool
  ansible.builtin.include_role:
    name: ibns_push
  vars:
    ibns_backup_file: "ibns-before-{{ ibns_stage_tag }}-{{ ibns_run_id }}.cfg"
    ibns_push_step: backup
    ibns_push_cli: "{{ [{'command': 'copy running-config flash:' ~ ibns_backup_file, 'prompt': 'Destination filename', 'answer': ibns_backup_file}] | ibns_cli_exec }}"
```

### `ansible/playbooks/roles/ibns_convert/tasks/main.yml`

```yaml
# roles/ibns_convert/tasks/main.yml
# Stage 1 change, pushed through Catalyst Center. ONE-WAY: there is no command
# to go back to legacy. The command asks for confirmation; ibns_convert_prompt
# must match the prompt text (VERIFY on the lab switch).
---
- name: Convert legacy auth config to new-style (one-way)
  ansible.builtin.include_role:
    name: ibns_push
  vars:
    ibns_push_step: convert
    ibns_push_cli: "{{ [{'command': 'authentication convert-to new-style', 'prompt': ibns_convert_prompt, 'answer': 'yes'}] | ibns_cli_exec }}"
```

### `ansible/playbooks/roles/ibns_postcheck/tasks/main.yml`

```yaml
# roles/ibns_postcheck/tasks/main.yml
# Layer 1 (config checks) + layer 2 (per-endpoint session comparison).
# Inputs:
#   ibns_pre          state captured before the change (sessions, port_classes, port_plan)
#   ibns_check_stage  converted | golden
# Output: ibns_check (details) and ibns_check_passed (bool). Does not fail the
# host itself; the stage playbook decides what to do with the result.
---
- name: Wait for endpoints to re-authenticate
  when: not (dry_run | bool)
  ansible.builtin.pause:
    seconds: "{{ ibns_reauth_wait }}"

- name: Collect state after the change
  ansible.builtin.include_role:
    name: ibns_collect

- name: Compare with the state before the change
  ansible.builtin.set_fact:
    ibns_check:
      config_findings: "{{ ibns_state.running | ibns_config_checks(ibns_pre.port_classes, ibns_port_templates, ibns_check_stage, ibns_pre.port_plan) }}"
      aaa_up: "{{ ibns_state.aaa_servers | selectattr('state', 'equalto', 'UP') | list | length }}"
      sessions: "{{ ibns_pre.sessions | ibns_compare_sessions(ibns_state.sessions, ibns_max_failed_endpoints) }}"

- name: Decide pass or fail
  ansible.builtin.set_fact:
    ibns_check_passed: >-
      {{ (ibns_check.config_findings | length == 0)
         and (ibns_check.aaa_up | int >= ibns_min_aaa_up | int)
         and (ibns_check.sessions.passed | bool) }}

- name: Show post-check result
  ansible.builtin.debug:
    msg:
      - "Passed:            {{ ibns_check_passed }}"
      - "Config findings:   {{ ibns_check.config_findings }}"
      - "RADIUS servers UP: {{ ibns_check.aaa_up }}"
      - "Endpoints checked: {{ ibns_check.sessions.checked }}, failed: {{ ibns_check.sessions.failed_endpoints }}"
      - "Failures:          {{ ibns_check.sessions.failures }}"
      - "New endpoints:     {{ ibns_check.sessions.new_endpoints | length }}"

- name: Save post-check snapshot
  ansible.builtin.include_role:
    name: ibns_snapshot
    tasks_from: save
  vars:
    snapshot_name: "postcheck-{{ ibns_check_stage }}-{{ ibns_run_id }}.json"
    snapshot_content: "{{ {'state': {'sessions': ibns_state.sessions, 'port_classes': ibns_state.port_classes, 'port_plan': ibns_state.port_plan, 'config_mode': ibns_state.config_mode}, 'check': ibns_check, 'passed': ibns_check_passed} | to_nice_json }}"
```

### `ansible/playbooks/ibns_stage1_convert.yml`

```yaml
# ansible/playbooks/ibns_stage1_convert.yml
# RUN ORDER: 3 (change window)
# Stage 1: convert legacy dot1x config to new-style IN PLACE. ONE-WAY.
# Every change is pushed through Catalyst Center (roles/ibns_push).
#   pass -> write memory
#   fail -> no write memory from us, switch flagged FIX-FORWARD-REQUIRED
#           (runbook: fix in new-style syntax; console/OOB restore is the last
#           resort). VERIFY in the lab whether a Catalyst Center deployment
#           saves the config by itself; if it does, a reload won't undo anything.
---
- name: Resolve targets
  ansible.builtin.import_playbook: ibns_target.yml
  vars:
    ibns_requires_change: true

- name: Stage 1 - convert to new-style
  hosts: ibns_targets
  gather_facts: false
  serial: "{{ ibns_serial | default(5) }}"
  vars:
    ibns_run_id: "{{ hostvars['localhost']['ibns_run_id'] }}"
    ibns_stage_tag: stage1
    ibns_expected_mode: legacy
  tasks:
    - name: Pre-check (switch is skipped if this fails)
      ansible.builtin.include_role:
        name: ibns_precheck

    - name: Keep the state from before the change
      ansible.builtin.set_fact:
        ibns_pre: "{{ ibns_state }}"

    - name: Back up the config
      ansible.builtin.include_role:
        name: ibns_backup

    - name: Convert
      ansible.builtin.include_role:
        name: ibns_convert

    - name: Post-check (config checks + per-endpoint sessions)
      ansible.builtin.include_role:
        name: ibns_postcheck
      vars:
        ibns_check_stage: converted

    - name: Save config (post-check passed)
      when:
        - not (dry_run | bool)
        - ibns_check_passed | bool
      ansible.builtin.include_role:
        name: ibns_save

    - name: Report
      ansible.builtin.include_role:
        name: ibns_report
      vars:
        ibns_result:
          stage: stage1-convert
          outcome: "{{ 'dry-run' if dry_run | bool else ('converted' if ibns_check_passed | bool else 'FIX-FORWARD-REQUIRED') }}"
          detail: "{{ ibns_check.config_findings + (ibns_check.sessions.failures | map(attribute='detail') | list) }}"

    - name: Flag a failed conversion
      when:
        - not (dry_run | bool)
        - not (ibns_check_passed | bool)
      ansible.builtin.fail:
        msg: >-
          Post-check failed after conversion. We did not write memory
          (check whether Catalyst Center saved it).
          Fix forward in new-style syntax (see docs/runbook.md); console/OOB
          restore is the last resort. Do not reload this switch.
```

## Phase 4: stage 2, golden config and rollback

Dry-run shows the rendered config, the port plan and the held ports. Prove the automatic rollback in the lab by breaking the golden template on purpose.

### `ansible/templates/ibns2/global.j2`

```jinja
{# ansible/templates/ibns2/global.j2
   Golden IBNS 2.0 global config. DRAFT: replace with the approved standard.
   Added ALONGSIDE the converted config; nothing here removes existing objects.
   Inputs: ibns_radius_group (found on the switch), ibns_policy_name,
           ibns_critical_data_vlan, ibns_restart_seconds #}
aaa accounting identity default start-stop group {{ ibns_radius_group }}
!
service-template IBNS2_CRITICAL_DATA
{% if ibns_critical_data_vlan %}
 vlan {{ ibns_critical_data_vlan }}
{% endif %}
service-template IBNS2_CRITICAL_VOICE
 voice vlan
!
class-map type control subscriber match-all IBNS2_AAA_DOWN_UNAUTHD
 match result-type aaa-timeout
 match authorization-status unauthorized
class-map type control subscriber match-all IBNS2_AAA_DOWN_AUTHD
 match result-type aaa-timeout
 match authorization-status authorized
class-map type control subscriber match-all IBNS2_DOT1X_FAILED
 match method dot1x
 match result-type method dot1x authoritative
class-map type control subscriber match-all IBNS2_DOT1X_NO_RESP
 match method dot1x
 match result-type method dot1x agent-not-found
class-map type control subscriber match-all IBNS2_MAB_FAILED
 match method mab
 match result-type method mab authoritative
class-map type control subscriber match-any IBNS2_IN_CRITICAL
 match activated-service-template IBNS2_CRITICAL_DATA
 match activated-service-template IBNS2_CRITICAL_VOICE
class-map type control subscriber match-none IBNS2_NOT_IN_CRITICAL
 match activated-service-template IBNS2_CRITICAL_DATA
 match activated-service-template IBNS2_CRITICAL_VOICE
!
policy-map type control subscriber {{ ibns_policy_name }}
 event session-started match-all
  10 class always do-until-failure
   10 authenticate using dot1x priority 10
 event authentication-failure match-first
  5 class IBNS2_DOT1X_FAILED do-until-failure
   10 terminate dot1x
   20 authenticate using mab priority 20
  10 class IBNS2_AAA_DOWN_UNAUTHD do-until-failure
   10 activate service-template IBNS2_CRITICAL_DATA
   20 activate service-template IBNS2_CRITICAL_VOICE
   30 authorize
   40 pause reauthentication
  20 class IBNS2_AAA_DOWN_AUTHD do-until-failure
   10 pause reauthentication
   20 authorize
  30 class IBNS2_DOT1X_NO_RESP do-until-failure
   10 terminate dot1x
   20 authenticate using mab priority 20
  40 class IBNS2_MAB_FAILED do-until-failure
   10 terminate mab
   20 authentication-restart {{ ibns_restart_seconds }}
  60 class always do-until-failure
   10 terminate dot1x
   20 terminate mab
   30 authentication-restart {{ ibns_restart_seconds }}
 event aaa-available match-all
  10 class IBNS2_IN_CRITICAL do-until-failure
   10 clear-session
  20 class IBNS2_NOT_IN_CRITICAL do-until-failure
   10 resume reauthentication
 event agent-found match-all
  10 class always do-until-failure
   10 terminate mab
   20 authenticate using dot1x priority 10
 event inactivity-timeout match-all
  10 class always do-until-failure
   10 clear-session
 event violation match-all
  10 class always do-until-failure
   10 restrict
```

### `ansible/templates/ibns2/interface_templates.j2`

```jinja
{# ansible/templates/ibns2/interface_templates.j2
   Golden interface templates, one per port class (see ibns_port_templates).
   DRAFT: replace with the approved standard and tune timers in the lab.
   closed mode     = no traffic before authentication (access-session closed)
   low-impact mode = pre-auth ACL allows DHCP/DNS etc. before authentication #}
{% for name, host_mode, methods in [
     ('IBNS2_MDA', 'multi-domain', ['dot1x', 'mab']),
     ('IBNS2_DOT1X_MAB', 'multi-auth', ['dot1x', 'mab']),
     ('IBNS2_MAB', 'multi-auth', ['mab']) ] %}
template {{ name }}
{% if 'dot1x' in methods %}
 dot1x pae authenticator
 dot1x timeout tx-period {{ ibns_dot1x_tx_period }}
 dot1x max-reauth-req {{ ibns_dot1x_max_reauth_req }}
{% endif %}
 mab
 access-session host-mode {{ host_mode }}
{% if ibns_mode == 'closed' %}
 access-session closed
{% else %}
 ip access-group {{ ibns_preauth_acl }} in
{% endif %}
 access-session port-control auto
 authentication periodic
 authentication timer reauthenticate server
 authentication timer inactivity server dynamic
 service-policy type control subscriber {{ ibns_policy_name }}
!
{% endfor %}
```

### `ansible/playbooks/roles/ibns_golden/tasks/main.yml`

```yaml
# roles/ibns_golden/tasks/main.yml
# Stage 2 change, pushed through Catalyst Center: add the golden config
# ALONGSIDE the converted config, then re-point each planned access port
# (template attached first, converted interface lines stripped after), so the
# port is never without authentication. Three pushes: global, templates, ports.
# Inputs: ibns_state (from pre-check), ibns_run_id
---
- name: Find the RADIUS server group this switch uses for dot1x
  ansible.builtin.set_fact:
    ibns_radius_group: "{{ ibns_state.running | ibns_radius_group }}"

- name: Require a RADIUS server group
  ansible.builtin.assert:
    that: ibns_radius_group | length > 0
    fail_msg: "No 'aaa authentication dot1x default group' found; can't render the golden config."

- name: Plan which ports get which golden template (description and config agree)
  ansible.builtin.set_fact:
    ibns_port_plan: "{{ ibns_state.port_plan }}"

- name: Save the rollback data (converted interface config + plan; not in dry run, so a dry run never overwrites real rollback data)
  when: not (dry_run | bool)
  ansible.builtin.include_role:
    name: ibns_snapshot
    tasks_from: save
  vars:
    snapshot_name: "{{ item }}"
    snapshot_content: "{{ {'run_id': ibns_run_id, 'port_plan': ibns_port_plan, 'auth_lines': ibns_state.auth_lines, 'port_classes': ibns_state.port_classes, 'sessions': ibns_state.sessions} | to_nice_json }}"
  loop:
    - "stage2-rollback-{{ ibns_run_id }}.json"
    - "stage2-rollback-latest.json"

- name: List held ports (not touched by this stage)
  when: ibns_state.held_ports | length > 0
  ansible.builtin.debug:
    msg: "{{ ibns_state.held_ports }}"

- name: Apply golden global config (policy-map, class-maps, service templates, AAA)
  ansible.builtin.include_role:
    name: ibns_push
  vars:
    ibns_push_step: golden-global
    ibns_push_cli: "{{ lookup('ansible.builtin.template', ibns_template_dir ~ '/global.j2') }}"

- name: Apply golden interface templates
  ansible.builtin.include_role:
    name: ibns_push
  vars:
    ibns_push_step: golden-templates
    ibns_push_cli: "{{ lookup('ansible.builtin.template', ibns_template_dir ~ '/interface_templates.j2') }}"

- name: Re-point access ports to their golden template (a failure here is caught by the post-check and rolled back)
  ansible.builtin.include_role:
    name: ibns_push
  vars:
    ibns_push_step: repoint
    ibns_push_cli: "{{ ibns_port_plan | ibns_repoint_cli(ibns_state.auth_lines) }}"
    ibns_push_may_fail: true

- name: Keep the re-point push result for the report
  ansible.builtin.set_fact:
    ibns_repoint_error: "{{ ibns_push_error }}"
```

### `ansible/playbooks/roles/ibns_rollback_golden/tasks/main.yml`

```yaml
# roles/ibns_rollback_golden/tasks/main.yml
# Stage 2 rollback, pushed through Catalyst Center: put each re-pointed port back
# on its converted config. Saved interface lines are restored FIRST, then the
# golden template is detached. No reload, no write erase. Golden global objects
# stay (unused, harmless). A failed push is recorded, not fatal: the post-check
# that follows decides the outcome.
# Input: ibns_rollback_data (snapshot saved by ibns_golden)
---
- name: Re-point ports back to their converted config
  ansible.builtin.include_role:
    name: ibns_push
  vars:
    ibns_push_step: rollback-golden
    ibns_push_cli: "{{ ibns_rollback_data.port_plan | ibns_rollback_cli(ibns_rollback_data.auth_lines) }}"
    ibns_push_may_fail: true
```

### `ansible/playbooks/ibns_stage2_golden.yml`

```yaml
# ansible/playbooks/ibns_stage2_golden.yml
# RUN ORDER: 4 (same change window, after stage 1 passed)
# Stage 2: add golden config alongside the converted config, re-point ports.
# Every change is pushed through Catalyst Center (roles/ibns_push).
#   pass -> write memory
#   fail -> automatic rollback: re-point ports back to the converted config
#           (no reload), re-check, report ROLLED-BACK
---
- name: Resolve targets
  ansible.builtin.import_playbook: ibns_target.yml
  vars:
    ibns_requires_change: true

- name: Stage 2 - apply golden config
  hosts: ibns_targets
  gather_facts: false
  serial: "{{ ibns_serial | default(5) }}"
  vars:
    ibns_run_id: "{{ hostvars['localhost']['ibns_run_id'] }}"
    ibns_stage_tag: stage2
    ibns_expected_mode: new-style
  tasks:
    - name: Pre-check (switch is skipped if this fails)
      ansible.builtin.include_role:
        name: ibns_precheck

    - name: Keep the state from before the change
      ansible.builtin.set_fact:
        ibns_pre: "{{ ibns_state }}"

    - name: Back up the config
      ansible.builtin.include_role:
        name: ibns_backup

    - name: Apply golden config and re-point ports
      ansible.builtin.include_role:
        name: ibns_golden

    - name: Post-check (config checks + per-endpoint sessions)
      ansible.builtin.include_role:
        name: ibns_postcheck
      vars:
        ibns_check_stage: golden

    - name: Save config (post-check passed)
      when:
        - not (dry_run | bool)
        - ibns_check_passed | bool
      ansible.builtin.include_role:
        name: ibns_save

    - name: Roll back to the converted config (post-check failed)
      when:
        - not (dry_run | bool)
        - not (ibns_check_passed | bool)
      block:
        - name: Keep the failed check for the report
          ansible.builtin.set_fact:
            ibns_failed_check: "{{ ibns_check }}"
            ibns_rollback_data:
              port_plan: "{{ ibns_port_plan }}"
              auth_lines: "{{ ibns_pre.auth_lines }}"

        - name: Re-point ports back to the converted config
          ansible.builtin.include_role:
            name: ibns_rollback_golden

        - name: Check the rollback restored service
          ansible.builtin.include_role:
            name: ibns_postcheck
          vars:
            ibns_check_stage: converted

    - name: Report
      ansible.builtin.include_role:
        name: ibns_report
      vars:
        ibns_result:
          stage: stage2-golden
          outcome: >-
            {{ 'dry-run' if dry_run | bool else
               ('golden-applied' if ibns_failed_check is not defined else
               ('ROLLED-BACK' if ibns_check_passed | bool else 'ROLLED-BACK-CHECK-FAILED')) }}
          detail: "{{ ([('re-point push failed: ' ~ ibns_repoint_error)] if ibns_repoint_error | default('') else []) + (ibns_failed_check | default(ibns_check)).config_findings + ((ibns_failed_check | default(ibns_check)).sessions.failures | map(attribute='detail') | list) }}"

    - name: Flag a rolled-back switch
      when: ibns_failed_check is defined
      ansible.builtin.fail:
        msg: "Golden config failed its post-check and was rolled back. Investigate before retrying."
```

### `ansible/playbooks/ibns_rollback_golden.yml`

```yaml
# ansible/playbooks/ibns_rollback_golden.yml
# RUN ONLY WHEN NEEDED (manual): undo stage 2 on a switch, e.g. after an issue
# found in the next-day check. Uses the rollback data stage 2 saved.
# Set ibns_rollback_snapshot to a dated file to roll back to a specific run.
# Pushed through Catalyst Center (roles/ibns_push).
---
- name: Resolve targets
  ansible.builtin.import_playbook: ibns_target.yml
  vars:
    ibns_requires_change: true

- name: Roll back golden config to the converted config
  hosts: ibns_targets
  gather_facts: false
  serial: "{{ ibns_serial | default(5) }}"
  vars:
    ibns_run_id: "{{ hostvars['localhost']['ibns_run_id'] }}"
    ibns_stage_tag: rollback-golden
  tasks:
    - name: Collect switch state
      ansible.builtin.include_role:
        name: ibns_collect

    - name: Load the rollback data saved by stage 2
      ansible.builtin.include_role:
        name: ibns_snapshot
        tasks_from: load
      vars:
        snapshot_name: "{{ ibns_rollback_snapshot | default('stage2-rollback-latest.json') }}"

    - name: Prepare rollback inputs
      ansible.builtin.set_fact:
        ibns_rollback_data: "{{ ibns_loaded }}"
        ibns_pre: "{{ ibns_loaded }}"

    - name: Back up the current config
      ansible.builtin.include_role:
        name: ibns_backup

    - name: Re-point ports back to the converted config
      ansible.builtin.include_role:
        name: ibns_rollback_golden

    - name: Post-check against the state saved before stage 2
      ansible.builtin.include_role:
        name: ibns_postcheck
      vars:
        ibns_check_stage: converted

    - name: Save config (rollback verified)
      when:
        - not (dry_run | bool)
        - ibns_check_passed | bool
      ansible.builtin.include_role:
        name: ibns_save

    - name: Report
      ansible.builtin.include_role:
        name: ibns_report
      vars:
        ibns_result:
          stage: rollback-golden
          outcome: "{{ 'dry-run' if dry_run | bool else ('rolled-back' if ibns_check_passed | bool else 'ROLLBACK-CHECK-FAILED') }}"
          detail: "{{ ibns_check.config_findings + (ibns_check.sessions.failures | map(attribute='detail') | list) }}"
```

## Phase 5: next-day check and stage 3 cleanup

### `ansible/playbooks/ibns_nextday_check.yml`

```yaml
# ansible/playbooks/ibns_nextday_check.yml
# RUN ORDER: 5 (next business morning, after users are back)
# Read-only. Layer 3: ports that authenticated in the daytime baseline but not
# now, plus config checks. Issues are fixed per port or with a planned rollback.
---
- name: Resolve targets
  ansible.builtin.import_playbook: ibns_target.yml

- name: Next-day check (read-only)
  hosts: ibns_targets
  gather_facts: false
  vars:
    ibns_run_id: "{{ hostvars['localhost']['ibns_run_id'] }}"
    ibns_nextday_stage: "{{ ibns_completed_stage | default('golden') }}"
  tasks:
    - name: Collect switch state
      ansible.builtin.include_role:
        name: ibns_collect

    - name: Load the daytime baseline
      ansible.builtin.include_role:
        name: ibns_snapshot
        tasks_from: load
      vars:
        snapshot_name: "baseline-latest.json"

    - name: Compare with the baseline
      ansible.builtin.set_fact:
        ibns_nextday:
          ports: "{{ ibns_loaded.sessions | ibns_compare_baseline(ibns_state.sessions) }}"
          config_findings: "{{ ibns_state.running | ibns_config_checks(ibns_loaded.port_classes, ibns_port_templates, ibns_nextday_stage, ibns_loaded.port_plan | default(none)) }}"

    - name: Save next-day snapshot
      ansible.builtin.include_role:
        name: ibns_snapshot
        tasks_from: save
      vars:
        snapshot_name: "nextday-{{ ibns_run_id }}.json"
        snapshot_content: "{{ ibns_nextday | to_nice_json }}"

    - name: Report
      ansible.builtin.include_role:
        name: ibns_report
      vars:
        ibns_result:
          stage: nextday-check
          outcome: "{{ 'clean' if (ibns_nextday.ports.passed and ibns_nextday.config_findings | length == 0) else 'ISSUES' }}"
          detail: "missing ports: {{ ibns_nextday.ports.ports_missing }}; config: {{ ibns_nextday.config_findings }}"
```

### `ansible/playbooks/roles/ibns_cleanup/tasks/main.yml`

```yaml
# roles/ibns_cleanup/tasks/main.yml
# Stage 3: remove converted control-policy objects that nothing references,
# pushed through Catalyst Center. Never by name pattern: the filter only returns
# objects with no references, and never anything listed in ibns_golden_names.
# Input: ibns_state (from pre-check)
---
- name: Find unreferenced policy-maps, class-maps and service templates
  ansible.builtin.set_fact:
    ibns_orphans: "{{ ibns_state.running | ibns_find_orphans(ibns_golden_names) }}"

- name: Show what would be removed
  ansible.builtin.debug:
    msg: "{{ ibns_orphans if ibns_orphans | length > 0 else 'Nothing to clean up.' }}"

- name: Remove unreferenced objects
  when: ibns_orphans | length > 0
  ansible.builtin.include_role:
    name: ibns_push
  vars:
    ibns_push_step: cleanup
    ibns_push_cli: "{{ ibns_orphans | join('\n') }}"
```

### `ansible/playbooks/ibns_stage3_cleanup.yml`

```yaml
# ansible/playbooks/ibns_stage3_cleanup.yml
# RUN ORDER: 6 (separate change, after the soak period and a clean next-day check)
# Stage 3: remove converted control-policy objects nothing references any more.
# Every change is pushed through Catalyst Center (roles/ibns_push).
#   pass -> write memory
#   fail -> no write memory from us; restore removed objects from the backup
#           taken first (the removed lines are in the pushed-stage3-cleanup snapshot)
---
- name: Resolve targets
  ansible.builtin.import_playbook: ibns_target.yml
  vars:
    ibns_requires_change: true

- name: Stage 3 - clean up unreferenced converted config
  hosts: ibns_targets
  gather_facts: false
  serial: "{{ ibns_serial | default(5) }}"
  vars:
    ibns_run_id: "{{ hostvars['localhost']['ibns_run_id'] }}"
    ibns_stage_tag: stage3
    ibns_expected_mode: new-style
    ibns_check_migration: false
  tasks:
    - name: Pre-check (switch is skipped if this fails)
      ansible.builtin.include_role:
        name: ibns_precheck

    - name: Keep the state from before the change
      ansible.builtin.set_fact:
        ibns_pre: "{{ ibns_state }}"

    - name: Back up the config
      ansible.builtin.include_role:
        name: ibns_backup

    - name: Remove unreferenced objects
      ansible.builtin.include_role:
        name: ibns_cleanup

    - name: Post-check (nothing should change for endpoints)
      ansible.builtin.include_role:
        name: ibns_postcheck
      vars:
        ibns_check_stage: golden

    - name: Save config (post-check passed)
      when:
        - not (dry_run | bool)
        - ibns_check_passed | bool
      ansible.builtin.include_role:
        name: ibns_save

    - name: Report
      ansible.builtin.include_role:
        name: ibns_report
      vars:
        ibns_result:
          stage: stage3-cleanup
          outcome: "{{ 'dry-run' if dry_run | bool else ('cleaned' if ibns_check_passed | bool else 'CHECK-FAILED-NOT-SAVED') }}"
          detail: "removed {{ ibns_orphans | length }} objects; {{ ibns_check.config_findings }}"
```

## Phase 6: AAP payload (after the playbooks work on the laptop)

Push to the dev branch; Helios creates these in DEV AAP.

### `ansible/aap_payload/templates/controller_templates.yml`

```yaml
{{/* This file is a template for your AAP project's job template objects.
   * REPLACES ud00's controller_templates.yml (SWIM, CML, flash cleanup, vManage).
   * Same structure as ud00: one entry per playbook. Keep names in sync with
   * controller_survey_specs.yml (survey keys must equal template names).
   * Every IBNS job reaches switches ONLY through Catalyst Center, so the jobs
   * carry the DNAC service-ID credential (service_id_dnac), not a switch login.
   * CONFIRM with Gurkirat: that this DNAC account may run Command Runner and
   * deploy templates, and how Artifactory snapshot credentials reach the job. */}}

app_controller_templates:
  - name: "{{ .Values.HELIOS_APP_CODE }}_noop_{{ .Values.HELIOS_APP_NAME }}"
    job_type: "run"
    playbook: "ansible/playbooks/noop.yml"
    inventory: "{{ include "aap.resource_names.inventory_by_env" . }}"
    execution_environment: "{{ .Values.HELIOS_APP_CODE }}_Ansible2.16ExecEnv_{{ .Values.HELIOS_APP_NAME }}"
    extra_vars:
      helios:
        app_code: "{{ .Values.HELIOS_APP_CODE }}"
        repo_name: "{{ .Values.HELIOS_REPO_NAME }}"
        vault_env: "{{ .Values.VAULT_ENV }}"
    project: "{{ include "aap.resource_names.project" . }}"
    survey_enabled: true
    description: "Template for a noop job which does nothing. Useful for testing the AAP job execution framework."
    state: "present"
    verbosity: {{ .Values.job_template_verbosity | default 0 }}
    credentials: []

  - name: "{{ .Values.HELIOS_APP_CODE }}_ibns_classify_{{ .Values.HELIOS_APP_NAME }}"
    job_type: "run"
    playbook: "ansible/playbooks/ibns_classify.yml"
    inventory: "{{ include "aap.resource_names.inventory_by_env" . }}"
    execution_environment: "{{ .Values.HELIOS_APP_CODE }}_Ansible2.16ExecEnv_{{ .Values.HELIOS_APP_NAME }}"
    extra_vars:
      helios:
        app_code: "{{ .Values.HELIOS_APP_CODE }}"
        repo_name: "{{ .Values.HELIOS_REPO_NAME }}"
        vault_env: "{{ .Values.VAULT_ENV }}"
      ibns_snapshot_backend: "artifactory"
    project: "{{ include "aap.resource_names.project" . }}"
    survey_enabled: true
    description: "IBNS 0 - Read-only. Classify every port by description and config; list ports that will migrate and ports held for a fix."
    state: "present"
    verbosity: {{ .Values.job_template_verbosity | default 0 }}
    credentials:
      - "{{ include "aap.resource_names_reserved.vault_app_roles" . }}"
      - "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"

  - name: "{{ .Values.HELIOS_APP_CODE }}_ibns_baseline_{{ .Values.HELIOS_APP_NAME }}"
    job_type: "run"
    playbook: "ansible/playbooks/ibns_baseline.yml"
    inventory: "{{ include "aap.resource_names.inventory_by_env" . }}"
    execution_environment: "{{ .Values.HELIOS_APP_CODE }}_Ansible2.16ExecEnv_{{ .Values.HELIOS_APP_NAME }}"
    extra_vars:
      helios:
        app_code: "{{ .Values.HELIOS_APP_CODE }}"
        repo_name: "{{ .Values.HELIOS_REPO_NAME }}"
        vault_env: "{{ .Values.VAULT_ENV }}"
      ibns_snapshot_backend: "artifactory"
    project: "{{ include "aap.resource_names.project" . }}"
    survey_enabled: true
    description: "IBNS 1 - Read-only. Capture the daytime session baseline for a site (run during business hours)."
    state: "present"
    verbosity: {{ .Values.job_template_verbosity | default 0 }}
    credentials:
      - "{{ include "aap.resource_names_reserved.vault_app_roles" . }}"
      - "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"

  - name: "{{ .Values.HELIOS_APP_CODE }}_ibns_precheck_{{ .Values.HELIOS_APP_NAME }}"
    job_type: "run"
    playbook: "ansible/playbooks/ibns_precheck.yml"
    inventory: "{{ include "aap.resource_names.inventory_by_env" . }}"
    execution_environment: "{{ .Values.HELIOS_APP_CODE }}_Ansible2.16ExecEnv_{{ .Values.HELIOS_APP_NAME }}"
    extra_vars:
      helios:
        app_code: "{{ .Values.HELIOS_APP_CODE }}"
        repo_name: "{{ .Values.HELIOS_REPO_NAME }}"
        vault_env: "{{ .Values.VAULT_ENV }}"
      ibns_snapshot_backend: "artifactory"
    project: "{{ include "aap.resource_names.project" . }}"
    survey_enabled: true
    description: "IBNS 2 - Read-only go/no-go pre-check before the change window."
    state: "present"
    verbosity: {{ .Values.job_template_verbosity | default 0 }}
    credentials:
      - "{{ include "aap.resource_names_reserved.vault_app_roles" . }}"
      - "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"

  - name: "{{ .Values.HELIOS_APP_CODE }}_ibns_stage1_convert_{{ .Values.HELIOS_APP_NAME }}"
    job_type: "run"
    playbook: "ansible/playbooks/ibns_stage1_convert.yml"
    inventory: "{{ include "aap.resource_names.inventory_by_env" . }}"
    execution_environment: "{{ .Values.HELIOS_APP_CODE }}_Ansible2.16ExecEnv_{{ .Values.HELIOS_APP_NAME }}"
    extra_vars:
      helios:
        app_code: "{{ .Values.HELIOS_APP_CODE }}"
        repo_name: "{{ .Values.HELIOS_REPO_NAME }}"
        vault_env: "{{ .Values.VAULT_ENV }}"
      ibns_snapshot_backend: "artifactory"
    project: "{{ include "aap.resource_names.project" . }}"
    survey_enabled: true
    description: "IBNS 3 - Stage 1: convert legacy dot1x to new-style in place (one-way). Saves only if the post-check passes."
    state: "present"
    verbosity: {{ .Values.job_template_verbosity | default 0 }}
    credentials:
      - "{{ include "aap.resource_names_reserved.vault_app_roles" . }}"
      - "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"

  - name: "{{ .Values.HELIOS_APP_CODE }}_ibns_stage2_golden_{{ .Values.HELIOS_APP_NAME }}"
    job_type: "run"
    playbook: "ansible/playbooks/ibns_stage2_golden.yml"
    inventory: "{{ include "aap.resource_names.inventory_by_env" . }}"
    execution_environment: "{{ .Values.HELIOS_APP_CODE }}_Ansible2.16ExecEnv_{{ .Values.HELIOS_APP_NAME }}"
    extra_vars:
      helios:
        app_code: "{{ .Values.HELIOS_APP_CODE }}"
        repo_name: "{{ .Values.HELIOS_REPO_NAME }}"
        vault_env: "{{ .Values.VAULT_ENV }}"
      ibns_snapshot_backend: "artifactory"
    project: "{{ include "aap.resource_names.project" . }}"
    survey_enabled: true
    description: "IBNS 4 - Stage 2: add golden config alongside, re-point access ports. Rolls back automatically if the post-check fails."
    state: "present"
    verbosity: {{ .Values.job_template_verbosity | default 0 }}
    credentials:
      - "{{ include "aap.resource_names_reserved.vault_app_roles" . }}"
      - "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"

  - name: "{{ .Values.HELIOS_APP_CODE }}_ibns_nextday_check_{{ .Values.HELIOS_APP_NAME }}"
    job_type: "run"
    playbook: "ansible/playbooks/ibns_nextday_check.yml"
    inventory: "{{ include "aap.resource_names.inventory_by_env" . }}"
    execution_environment: "{{ .Values.HELIOS_APP_CODE }}_Ansible2.16ExecEnv_{{ .Values.HELIOS_APP_NAME }}"
    extra_vars:
      helios:
        app_code: "{{ .Values.HELIOS_APP_CODE }}"
        repo_name: "{{ .Values.HELIOS_REPO_NAME }}"
        vault_env: "{{ .Values.VAULT_ENV }}"
      ibns_snapshot_backend: "artifactory"
    project: "{{ include "aap.resource_names.project" . }}"
    survey_enabled: true
    description: "IBNS 5 - Read-only. Next-morning comparison against the daytime baseline."
    state: "present"
    verbosity: {{ .Values.job_template_verbosity | default 0 }}
    credentials:
      - "{{ include "aap.resource_names_reserved.vault_app_roles" . }}"
      - "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"

  - name: "{{ .Values.HELIOS_APP_CODE }}_ibns_rollback_golden_{{ .Values.HELIOS_APP_NAME }}"
    job_type: "run"
    playbook: "ansible/playbooks/ibns_rollback_golden.yml"
    inventory: "{{ include "aap.resource_names.inventory_by_env" . }}"
    execution_environment: "{{ .Values.HELIOS_APP_CODE }}_Ansible2.16ExecEnv_{{ .Values.HELIOS_APP_NAME }}"
    extra_vars:
      helios:
        app_code: "{{ .Values.HELIOS_APP_CODE }}"
        repo_name: "{{ .Values.HELIOS_REPO_NAME }}"
        vault_env: "{{ .Values.VAULT_ENV }}"
      ibns_snapshot_backend: "artifactory"
    project: "{{ include "aap.resource_names.project" . }}"
    survey_enabled: true
    description: "IBNS rollback (manual) - re-point ports from the golden config back to the converted config. No reload."
    state: "present"
    verbosity: {{ .Values.job_template_verbosity | default 0 }}
    credentials:
      - "{{ include "aap.resource_names_reserved.vault_app_roles" . }}"
      - "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"

  - name: "{{ .Values.HELIOS_APP_CODE }}_ibns_stage3_cleanup_{{ .Values.HELIOS_APP_NAME }}"
    job_type: "run"
    playbook: "ansible/playbooks/ibns_stage3_cleanup.yml"
    inventory: "{{ include "aap.resource_names.inventory_by_env" . }}"
    execution_environment: "{{ .Values.HELIOS_APP_CODE }}_Ansible2.16ExecEnv_{{ .Values.HELIOS_APP_NAME }}"
    extra_vars:
      helios:
        app_code: "{{ .Values.HELIOS_APP_CODE }}"
        repo_name: "{{ .Values.HELIOS_REPO_NAME }}"
        vault_env: "{{ .Values.VAULT_ENV }}"
      ibns_snapshot_backend: "artifactory"
    project: "{{ include "aap.resource_names.project" . }}"
    survey_enabled: true
    description: "IBNS 6 - Stage 3 (after soak): remove converted config nothing references."
    state: "present"
    verbosity: {{ .Values.job_template_verbosity | default 0 }}
    credentials:
      - "{{ include "aap.resource_names_reserved.vault_app_roles" . }}"
      - "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"
```

### `ansible/aap_payload/templates/controller_survey_specs.yml`

```yaml
{{/* This file is a template for your AAP project's survey specs.
   * REPLACES ud00's controller_survey_specs.yml.
   * Each key must equal a job template name in controller_templates.yml.
   * Read-only jobs ask for hostnames only; config-changing jobs also ask for
   * the change number and dry_run (default true). */}}
---
app_controller_survey_specs:
  "{{ .Values.HELIOS_APP_CODE }}_ibns_classify_{{ .Values.HELIOS_APP_NAME }}":
    name: "IBNS classify ports"
    description: "Read-only port classification (description + config)"
    spec:
      - question_name: "Device Hostnames"
        question_description: "Enter device hostnames, comma separated (one site)"
        required: true
        type: "text"
        variable: "device_hostnames"

  "{{ .Values.HELIOS_APP_CODE }}_ibns_baseline_{{ .Values.HELIOS_APP_NAME }}":
    name: "IBNS baseline"
    description: "Read-only daytime session baseline"
    spec:
      - question_name: "Device Hostnames"
        question_description: "Enter device hostnames, comma separated (one site)"
        required: true
        type: "text"
        variable: "device_hostnames"

  "{{ .Values.HELIOS_APP_CODE }}_ibns_precheck_{{ .Values.HELIOS_APP_NAME }}":
    name: "IBNS pre-check"
    description: "Read-only go/no-go checks"
    spec:
      - question_name: "Device Hostnames"
        question_description: "Enter device hostnames, comma separated (one site)"
        required: true
        type: "text"
        variable: "device_hostnames"

  "{{ .Values.HELIOS_APP_CODE }}_ibns_stage1_convert_{{ .Values.HELIOS_APP_NAME }}":
    name: "IBNS stage 1 - convert"
    description: "Convert legacy dot1x to new-style in place (one-way)"
    spec:
      - question_name: "Device Hostnames"
        question_description: "Enter device hostnames, comma separated (one site)"
        required: true
        type: "text"
        variable: "device_hostnames"
      - question_name: "Change Number"
        question_description: "ServiceNow change number (required when Dry Run is false)"
        required: false
        type: "text"
        variable: "change_number"
      - question_name: "Dry Run"
        question_description: "true = show what would change, change nothing"
        required: true
        type: "multiplechoice"
        variable: "dry_run"
        default: "true"
        choices:
          - "true"
          - "false"

  "{{ .Values.HELIOS_APP_CODE }}_ibns_stage2_golden_{{ .Values.HELIOS_APP_NAME }}":
    name: "IBNS stage 2 - golden config"
    description: "Add golden config alongside and re-point access ports"
    spec:
      - question_name: "Device Hostnames"
        question_description: "Enter device hostnames, comma separated (one site)"
        required: true
        type: "text"
        variable: "device_hostnames"
      - question_name: "Change Number"
        question_description: "ServiceNow change number (required when Dry Run is false)"
        required: false
        type: "text"
        variable: "change_number"
      - question_name: "Dry Run"
        question_description: "true = show rendered config and port plan, change nothing"
        required: true
        type: "multiplechoice"
        variable: "dry_run"
        default: "true"
        choices:
          - "true"
          - "false"

  "{{ .Values.HELIOS_APP_CODE }}_ibns_nextday_check_{{ .Values.HELIOS_APP_NAME }}":
    name: "IBNS next-day check"
    description: "Read-only comparison against the daytime baseline"
    spec:
      - question_name: "Device Hostnames"
        question_description: "Enter device hostnames, comma separated (one site)"
        required: true
        type: "text"
        variable: "device_hostnames"
      - question_name: "Completed Stage"
        question_description: "Last stage completed on these switches"
        required: true
        type: "multiplechoice"
        variable: "ibns_completed_stage"
        default: "golden"
        choices:
          - "converted"
          - "golden"

  "{{ .Values.HELIOS_APP_CODE }}_ibns_rollback_golden_{{ .Values.HELIOS_APP_NAME }}":
    name: "IBNS rollback golden"
    description: "Re-point ports back to the converted config (no reload)"
    spec:
      - question_name: "Device Hostnames"
        question_description: "Enter device hostnames, comma separated (one site)"
        required: true
        type: "text"
        variable: "device_hostnames"
      - question_name: "Change Number"
        question_description: "ServiceNow change number (required when Dry Run is false)"
        required: false
        type: "text"
        variable: "change_number"
      - question_name: "Rollback Snapshot"
        question_description: "Leave empty for the latest stage 2 run, or enter stage2-rollback-<run id>.json"
        required: false
        type: "text"
        variable: "ibns_rollback_snapshot"
      - question_name: "Dry Run"
        question_description: "true = show rollback commands, change nothing"
        required: true
        type: "multiplechoice"
        variable: "dry_run"
        default: "true"
        choices:
          - "true"
          - "false"

  "{{ .Values.HELIOS_APP_CODE }}_ibns_stage3_cleanup_{{ .Values.HELIOS_APP_NAME }}":
    name: "IBNS stage 3 - cleanup"
    description: "Remove converted config nothing references"
    spec:
      - question_name: "Device Hostnames"
        question_description: "Enter device hostnames, comma separated (one site)"
        required: true
        type: "text"
        variable: "device_hostnames"
      - question_name: "Change Number"
        question_description: "ServiceNow change number (required when Dry Run is false)"
        required: false
        type: "text"
        variable: "change_number"
      - question_name: "Dry Run"
        question_description: "true = list what would be removed, change nothing"
        required: true
        type: "multiplechoice"
        variable: "dry_run"
        default: "true"
        choices:
          - "true"
          - "false"
```

### `ansible/aap_payload/templates/controller_credentials.yml`

```yaml
{{/* This file is a template for your AAP project's credential objects. You'll typically change this file
   * when adding, removing, or updating credentials for connecting to your project's VM hosts.
   * Config reference: See internal AAP docs for credentials configuration
   * See also: controller_credential_input_source.yml */}}
{{/* COPIED FROM ud00 AND EDITED: the two vManage credentials and the commented
   * networkview_db credential were removed. Everything else is unchanged. */}}

app_controller_credentials:
  - name:            "{{ .Values.HELIOS_APP_CODE }}_service_id_{{ .Values.HELIOS_APP_NAME }}"
    description:     "service_id. Sourced from RBC Vault."
    credential_type: "RBC - DevOps ID"
  - name:            "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"
    description:     "DNAC Service ID to Login to DNAC."
    credential_type: "RBC - DevOps ID"
  - name:            "{{ .Values.HELIOS_APP_CODE }}_dnac_dev_id_{{ .Values.HELIOS_APP_NAME }}"
    description:     "DNAC Dev ID."
    credential_type: "RBC - DevOps ID"
  - name: "{{ .Values.HELIOS_APP_CODE }}_Artifactory_{{ .Values.HELIOS_APP_NAME }}"
    description: "Use to download our custom Ansible Execution Environment"
    credential_type: "Container Registry"
```

### `ansible/aap_payload/templates/controller_credential_input_sources.yml`

```yaml
{{/* This file is a template for your AAP project's credential input source objects. You'll typically change this file
   * when adding, removing, or updating credentials for connecting to your project's VM hosts.
   * Config reference: See internal AAP docs for credential input sources configuration
   * See also: controller_credentials.yml */}}
{{/* COPIED FROM ud00 AND EDITED: removed the vManage (prod and DEV/lab) blocks and
   * the commented networkview_db blocks. Keep every remaining block exactly as in
   * ud00. VERIFY against ud00 while typing: the dnac_dev_id blocks and the
   * Artifactory password block were only partly visible in the recording. */}}

{{- $ssh_cred_linux := include "aap.resource_names.ssh_cred_linux" . -}}

app_controller_credential_input_sources:
  - target_credential: "{{ .Values.HELIOS_APP_CODE }}_service_id_{{ .Values.HELIOS_APP_NAME }}"
    input_field_name: "devops_username"
    metadata:
      secret_backend: "ansible"
      secret_path: "{{ .Values.HELIOS_APP_CODE }}/{{ .Values.VAULT_ENV }}/SERVICE_ID"
      secret_key: "username"
      auth_path: ""
      secret_version: ""
    description: "SERVICE_ID. Sourced from RBC Vault."
  - target_credential: "{{ .Values.HELIOS_APP_CODE }}_service_id_{{ .Values.HELIOS_APP_NAME }}"
    input_field_name: "devops_password"
    metadata:
      secret_backend: "ansible"
      secret_path: "{{ .Values.HELIOS_APP_CODE }}/{{ .Values.VAULT_ENV }}/SERVICE_ID"
      secret_key: "password"
      auth_path: ""
      secret_version: ""
    description: "devops_password. Sourced from RBC Vault."
    # Read-only access to Artifactory

  - target_credential: "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"
    input_field_name: "devops_username"
    metadata:
      secret_backend: "ansible"
      secret_path: "{{ .Values.HELIOS_APP_CODE }}/{{ .Values.VAULT_ENV }}/DNAC"
      secret_key: "username"
      auth_path: ""
      secret_version: ""
    description: "DNAC username. Sourced from RBC Vault."
  - target_credential: "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"
    input_field_name: "devops_password"
    metadata:
      secret_backend: "ansible"
      secret_path: "{{ .Values.HELIOS_APP_CODE }}/{{ .Values.VAULT_ENV }}/DNAC"
      secret_key: "password"
      auth_path: ""
      secret_version: ""
    description: "DNAC password. Sourced from RBC Vault."

  # dnac_dev_id: copy both blocks (username + password) from ud00 unchanged here.

  - target_credential: "{{ .Values.HELIOS_APP_CODE }}_Artifactory_{{ .Values.HELIOS_APP_NAME }}"
    input_field_name: "username"
    metadata:
      auth_path: ""
      secret_key: "id"
      secret_path: "{{ .Values.HELIOS_APP_CODE }}/{{ .Values.VAULT_ENV }}/HELIOS/SERVICE_ID"
      secret_backend: "ansible"
      secret_version: ""
  - target_credential: "{{ .Values.HELIOS_APP_CODE }}_Artifactory_{{ .Values.HELIOS_APP_NAME }}"
    input_field_name: "password"
    metadata:
      auth_path: ""
      secret_key: "password"
      secret_path: "{{ .Values.HELIOS_APP_CODE }}/{{ .Values.VAULT_ENV }}/HELIOS/SERVICE_ID"
      secret_backend: "ansible"
      secret_version: ""
```

### `ansible/aap_payload/templates/controller_execution_environments.yml`

```yaml
---
{{/* COPIED FROM ud00 AND EDITED: removed the vManage execution environment.
   * VERIFY the image tag against ud00. IBNS needs no collections (its
   * Catalyst Center modules use ansible-core only), so this image works as is. */}}
app_controller_execution_environments:
  # Image with Ansible-core 2.16 - CURRENT VERSION
  # TODO: Pin image by SHA256 digest for supply chain security (e.g., image@sha256:<hash>)
  - name: "{{ .Values.HELIOS_APP_CODE }}_Ansible2.16ExecEnv_{{ .Values.HELIOS_APP_NAME }}"
    state: present
    image: docker-secure-ud00.rbcartifactory.fg.rbc.com/aap/execution-environments/ud00-ee-ansible-execution-environment:0.0.13
    credential: "{{ .Values.HELIOS_APP_CODE }}_Artifactory_{{ .Values.HELIOS_APP_NAME }}"
    description: "CURRENT VERSION - With Python 3.11 and ansible-core 2.16.7."
```

### `ansible/aap_payload/templates/controller_inventories.yml`

```yaml
{{/* This file is a template for your AAP project's inventory objects. You'll typically change this file
   * when adding, removing, or updating inventory files for your project's VM hosts.
   * Config reference: See internal AAP docs for inventories configuration
   * See also: controller_inventory_source.yml */}}
{{/* COPIED FROM ud00 AND EDITED: removed the SD-WAN vManage inventory and the
   * SD-WAN certification inventory. The two remaining entries are unchanged. */}}

app_controller_inventories:
  - name:         "{{ include "aap.resource_names.inventory_by_env" . }}"
    description:  "{{ .Values.aap.controller_host.env_name }} host inventory for {{ .Values.HELIOS_APP_NAME }}."
    organization: "{{ .Values.HELIOS_APP_CODE }}"
    state:        "present"

  - name:         "{{ .Values.HELIOS_APP_CODE }}_lab_inventory{{ .Values.HELIOS_APP_NAME }}"
    description:  "Inventory for the lab controllers"
    organization: "{{ .Values.HELIOS_APP_CODE }}"
    state:        "present"
```

### `ansible/aap_payload/templates/controller_inventory_source.yml`

```yaml
{{/* This file is a template for your AAP project's inventory object sources. You'll typically change this file
   * when adding, removing, or updating inventory files for your project's VM hosts.
   * Config reference: https://rbcgithub.fg.rbc.com/rbc-to/apg0-ansible-docs/blob/main/references/helios/templates/inventory_sources.md
   * See also: controller_inventory.yml */}}
{{/* COPIED FROM ud00 AND EDITED: kept only the Catalyst Center (dnac.yml) source;
   * removed the two SD-WAN vManage sources. The remaining entry is unchanged. */}}

app_controller_inventory_sources:
  - name:                  "{{ include "aap.resource_names.inventory_source_by_env" . }}"
    description:           "{{ .Values.aap.controller_host.env_name }} environment host inventory source from RBC GitHub."
    inventory:             "{{ include "aap.resource_names.inventory_by_env" . }}"
    organization:          "{{ .Values.HELIOS_APP_CODE }}"
    source:                "scm"
    source_project:        "{{ include "aap.resource_names.project" . }}"
    source_path:           "ansible/inventories/{{ .Values.aap.controller_host.env_name | lower }}/dnac.yml"
    overwrite:             false
    update_on_launch:      false
    credential:            "{{ .Values.HELIOS_APP_CODE }}_service_id_dnac_{{ .Values.HELIOS_APP_NAME }}"
    execution_environment: "{{ .Values.HELIOS_APP_CODE }}_Ansible2.16ExecEnv_{{ .Values.HELIOS_APP_NAME }}"
    extra_vars:
      helios:
        app_code: "{{ .Values.HELIOS_APP_CODE }}"
        repo_name: "{{ .Values.HELIOS_REPO_NAME }}"
        vault_env: "{{ .Values.VAULT_ENV }}"
```

## Docs, discovery and classify

Laptop tools. `classify_ports.py` needs no switch access: it reads the configs `ibns_discovery.py fetch` saved.

### `docs/runbook.md`

```markdown
# IBNS 2.0 runbook

What to do for each job outcome. Job outcomes appear in the AAP job output and
in Odyssey (via the NetValidator webhook, `ibns_results` artifact).

## Outcomes

| Outcome | Meaning | Action |
| --- | --- | --- |
| `ready` / `NEEDS-FIX` | Classify result (read-only) | `NEEDS-FIX`: see "Held ports" below |
| `skipped` | Pre-check failed; nothing was changed | Fix the reason shown (ClearPass down, wrong mode, flash full, held ports), rerun |
| `dry-run` | Nothing was changed | Review the output, rerun with Dry Run = false |
| `converted` | Stage 1 passed and was saved | Continue with stage 2 |
| `FIX-FORWARD-REQUIRED` | Stage 1 post-check failed; we did not write memory (Catalyst Center may have) | See "Stage 1 failure" below. Do not reload |
| `golden-applied` | Stage 2 passed and was saved | Next-day check tomorrow morning |
| `ROLLED-BACK` | Stage 2 failed; ports were re-pointed to the converted config and service checks out | Investigate the failures listed, fix the golden template, retry later |
| `ROLLED-BACK-CHECK-FAILED` | Stage 2 failed and the rollback check also failed | Treat as stage 1 failure on the affected ports |
| `clean` / `ISSUES` | Next-day check result | `ISSUES`: fix per port, or run the rollback job |
| `cleaned` / `CHECK-FAILED-NOT-SAVED` | Stage 3 result | If failed: restore removed objects from the stage 3 backup |

## Stage 1 failure (FIX-FORWARD-REQUIRED)

The conversion is one-way. We did not write memory, but Catalyst Center may
have saved the config as part of the deployment (verify in the lab which).

1. Do not reload the switch.
2. Read the failures in the job output: which endpoints, which check.
3. Fix forward in new-style syntax on the affected ports (e.g. host mode,
   missing `mab`, timer), using the converted policy as the reference. Push
   the fix through Catalyst Center (a template in the IBNS2 project), the
   same way the jobs do.
4. Run the pre-check job, then compare sessions with the stage 1 snapshot.
5. When service is restored, `write memory` (template) and record what was changed.
6. Last resort only, with console/OOB access confirmed: restore the legacy
   config from `flash:ibns-before-stage1-<run id>.cfg` per the team's
   recovery procedure (verified in the lab).

## What was pushed, and when

Every change goes through Catalyst Center as a new version of the switch's
template `IBNS2_<hostname>` (project `IBNS2`). The commit comment is
`<run id> <stage> <step>`, so the version history is the change record.
The same CLI and its result are in the snapshot store as
`pushed-<stage>-<step>-<run id>.txt`.

## Stage 2 rollback (manual)

Run the `ibns_rollback_golden` job with the site's hostnames. It re-points
ports back to the converted config using the saved snapshot; no reload.
Golden global objects stay on the switch, unused, until stage 3.

## Held ports

A held port has auth config but its description and config don't agree, or
no rule matches its description. Stage 2 leaves it on the converted config
(still authenticating) and the pre-check fails the switch while held ports
exceed `ibns_max_held_ports`.

| Status | Example | Fix |
| --- | --- | --- |
| `mismatch` | Description "AP-3F-01", config dot1x+mab | Check the port in Catalyst Center / on the switch. Fix whichever is wrong: the description (normal change) or the config (separate change) |
| `no-rule` | Description "JOHNS DESK" | Add a rule to `ibns_description_rules` (commit, pipeline redeploys) or fix the description to the standard |
| `no-description` | Blank | Add a description |
| `unknown-role` | Rule names a role missing from `ibns_port_roles` | Add the role |

Check a description against the rules from the laptop:
`python python/ibns_tools/classify_ports.py --test "JOHNS DESK"`

Never raise `ibns_max_held_ports` just to get a switch through: do it only for
a site where the held ports are understood and listed in the change.

## Before every change window

1. Daytime baseline captured (`ibns_baseline`) within the last 2 days.
2. Discovery drift check from the laptop shows no drift for the site:
   `python python/ibns_tools/ibns_discovery.py compare --old <discovery run> --new <today>`
3. `ibns_classify` shows `ready` for every switch (no held ports, or held ports
   listed in the change).
4. ServiceNow change approved; Odyssey task opened; console/OOB access confirmed.
5. `ibns_precheck` passes for every switch.
```

### `python/ibns_tools/ibns_discovery.py`

```python
#!/usr/bin/env python3
"""IBNS discovery: pull running configs from Catalyst Center, group switches into
config variants, show how each variant differs from the baseline, and detect
drift between two runs.

Read-only toward Catalyst Center and the switches: token request plus GETs only.

Steps
  fetch    Pull running configs of matching switches into <run>/configs/ and
           write <run>/devices.csv. Resumable (skips saved configs unless --refresh).
  group    Fingerprint each switch's auth config and write to <run>/variants/:
             global_variants.csv + global_variants/<id>.txt  global AAA/auth config
             port_profiles.csv   + port_profiles/<id>.txt    per-port auth config
             batches.csv   switches sharing a global variant AND port profiles
             switches.csv  one row per switch
             ports.csv     one row per physical port (class + profile)
  diff     For every variant, list the lines it adds or lacks compared with the
           baseline (the most common variant). Writes <run>/variants/diff/.
  compare  Compare two runs and list switches and ports whose fingerprint changed,
           appeared or disappeared. Run before each site's change window.

Golden config mapping: one global template per global variant you keep, one
interface template per port class. Batches = switches you can migrate together.

Credentials (environment variables only, never on the command line):
  CATC_HOST       Catalyst Center hostname (no https://)
  CATC_USER       read-only service account
  CATC_PASS       its password
  CATC_VERSION    API version for the SDK, matching your Catalyst Center (e.g. 2.3.7.6)
  CATC_CA_BUNDLE  path to the internal CA bundle for TLS verification

Typical use (one dated folder per run):
  python ibns_discovery.py fetch   --run reports/raw/2026-10-26 --limit 5
  python ibns_discovery.py group   --run reports/raw/2026-10-26
  python ibns_discovery.py diff    --run reports/raw/2026-10-26
  python ibns_discovery.py compare --old reports/raw/2026-10-26 --new reports/raw/2026-11-09

Keep reports/raw/ out of Git: it holds real configs and hostnames.
Note: Catalyst Center masks secrets in returned configs; that's fine here, because
secrets are normalized away anyway.
"""
import argparse
import csv
import difflib
import hashlib
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

# ================================================================ clients ====


class SdkClient:
    """Uses Cisco's catalystcentersdk (same library as the cisco.catalystcenter
    Ansible collection). Handles token refresh and rate-limit retries itself."""

    def __init__(self, host, user, password, verify, version):
        try:
            from catalystcentersdk import CatalystCenterAPI
        except ImportError:
            sys.exit("catalystcentersdk not installed: pip install catalystcentersdk "
                     "(or use --client requests)")
        kwargs = dict(base_url=f"https://{host}", username=user, password=password, verify=verify)
        if version:
            kwargs["version"] = version
        self.api = CatalystCenterAPI(**kwargs)

    def devices(self, family="Switches and Hubs", page=500):
        offset = 1                                  # this API's offset starts at 1
        while True:
            batch = self.api.devices.get_device_list(family=family, offset=offset, limit=page).response
            yield from batch
            if len(batch) < page:
                return
            offset += page

    def running_config(self, device_id):
        return self.api.devices.get_device_config_by_id(device_id).response


class RequestsClient:
    """Fallback with plain `requests`, for when the SDK isn't available."""

    def __init__(self, host, user, password, verify, version=None):
        import requests

        self.base = f"https://{host}"
        self.auth = (user, password)
        self.session = requests.Session()
        self.session.verify = verify
        self._login()

    def _login(self):
        r = self.session.post(f"{self.base}/dna/system/api/v1/auth/token", auth=self.auth, timeout=60)
        r.raise_for_status()
        self.session.headers.update({"X-Auth-Token": r.json()["Token"], "Accept": "application/json"})

    def _get(self, path, params=None, retries=5):
        for attempt in range(retries):
            r = self.session.get(f"{self.base}{path}", params=params, timeout=120)
            if r.status_code == 401:                # token expired (about 1 hour)
                self._login()
                continue
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(int(r.headers.get("Retry-After", 5 * 2 ** attempt)))
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError(f"GET {path} failed after {retries} attempts")

    def devices(self, family="Switches and Hubs", page=500):
        offset = 1
        while True:
            batch = self._get("/dna/intent/api/v1/network-device",
                              {"family": family, "offset": offset, "limit": page})["response"]
            yield from batch
            if len(batch) < page:
                return
            offset += page

    def running_config(self, device_id):
        return self._get(f"/dna/intent/api/v1/network-device/{device_id}/config")["response"]


# ================================================================== fetch ====


def safe_name(name):
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def cmd_fetch(args):
    host, user, password = (os.environ.get(k) for k in ("CATC_HOST", "CATC_USER", "CATC_PASS"))
    if not (host and user and password):
        sys.exit("Set CATC_HOST, CATC_USER and CATC_PASS first.")
    verify = False if args.insecure else os.environ.get("CATC_CA_BUNDLE", True)
    client_cls = SdkClient if args.client == "sdk" else RequestsClient
    catc = client_cls(host, user, password, verify, os.environ.get("CATC_VERSION"))

    run = Path(args.run)
    (run / "configs").mkdir(parents=True, exist_ok=True)
    platform = re.compile(args.platform)
    hostname = re.compile(args.hostname, re.I)
    devices = [d for d in catc.devices()
               if platform.search(d.get("platformId") or "") and hostname.search(d.get("hostname") or "")]
    if args.limit:
        devices = devices[: args.limit]
    print(f"{len(devices)} devices match platform /{args.platform}/ and hostname /{args.hostname}/")

    rows = []
    for i, d in enumerate(devices, 1):
        name = safe_name(d.get("hostname") or d["id"])
        path = run / "configs" / f"{name}.cfg"
        status = "cached"
        if args.refresh or not path.exists():
            try:
                path.write_text(catc.running_config(d["id"]))
                status = "ok"
            except Exception as exc:                # keep going; reported in devices.csv
                status = f"error: {exc}"
            time.sleep(args.delay)
        rows.append({
            "hostname": d.get("hostname"), "id": d["id"],
            "management_ip": d.get("managementIpAddress"), "platform": d.get("platformId"),
            "software": d.get("softwareVersion"), "serial": d.get("serialNumber"),
            "reachability": d.get("reachabilityStatus"), "fetch_status": status,
        })
        print(f"[{i}/{len(devices)}] {name}: {status}")

    write_csv(run / "devices.csv", rows)
    errors = sum(1 for r in rows if r["fetch_status"].startswith("error"))
    print(f"Done. {len(rows) - errors} configs saved, {errors} errors. See {run / 'devices.csv'}")


# ================================================================== group ====

# Global (non-interface) config that belongs to the auth design.
GLOBAL_AUTH = re.compile(
    r"^(aaa |radius |radius-server |dot1x |authentication |access-session |mab |"
    r"device-tracking |ip device tracking|epm |service-template |"
    r"policy-map type control |class-map type control |parameter-map type webauth |"
    r"ip radius |template )"
)
# Interface lines that define a port's auth behaviour (the profile fingerprint).
INTF_AUTH = re.compile(
    r"^(authentication |access-session |dot1x |mab|service-policy type control |"
    r"source template |device-tracking|ip device tracking|switchport port-security)"
)
# Physical ports (x/y/z). Management Gi0/0 and AppGigabitEthernet are skipped.
PHYSICAL = re.compile(
    r"^interface ((Gigabit|TenGigabit|TwentyFiveGig|FortyGigabit|HundredGig|Fast)"
    r"Ethernet|TwentyFiveGigE|HundredGigE)(\d+/\d+/\d+)$"
)
NEW_STYLE = ("policy-map type control subscriber", "class-map type control subscriber",
             "service-template ")

SECRETS = re.compile(r"\b(key|password|secret|pac key)( [0-9])? \S+")
IPV4 = re.compile(r"\b\d{1,3}(\.\d{1,3}){3}\b")
NAMED = re.compile(r"^(radius server|server name|aaa group server radius) \S+")
GROUP_REF = re.compile(r"\bgroup (?!radius\b|tacacs\+|server\b)\S+")     # site-named AAA server groups
SITE_VLAN = re.compile(r"^(switchport (access|voice) vlan) \d+")
ANY_VLAN = re.compile(r"\bvlan \d+")
SKIP_FOR_BATCH = {"trunk", "routed", "port-channel-member", "uplink-module"}


def blocks(config):
    """Split a config into (parent_line, [child_lines]) blocks."""
    out, current = [], None
    for raw in config.splitlines():
        line = raw.rstrip()
        if not line or line.startswith("!"):
            current = None
            continue
        if line[0] == " " and current is not None:
            current[1].append(line.strip())
        else:
            current = (line.strip(), [])
            out.append(current)
    return out


def normalize(line, normalize_vlans):
    """Replace site-specific values so the same design fingerprints the same everywhere."""
    line = SECRETS.sub(lambda m: f"{m.group(1)}{m.group(2) or ''} <SECRET>", line)
    line = IPV4.sub("<IP>", line)
    line = NAMED.sub(lambda m: f"{m.group(1)} <NAME>", line)
    line = GROUP_REF.sub("group <NAME>", line)
    line = SITE_VLAN.sub(lambda m: f"{m.group(1)} <N>", line)
    if normalize_vlans:
        line = ANY_VLAN.sub("vlan <N>", line)
    return line


def classify(lines, module):
    """Port class, used to pick the golden interface template."""
    text = "\n".join(lines)

    def has(prefix):
        return any(l.startswith(prefix) for l in lines)

    if has("channel-group"):
        return "port-channel-member"
    if "no switchport" in lines:
        return "routed"
    if "switchport mode trunk" in lines:
        return "trunk"
    if has(("authentication port-control", "access-session port-control", "dot1x pae",
            "mab", "service-policy type control", "source template")):
        if has("switchport voice vlan") or "multi-domain" in text:
            return "multi-domain"
        dot1x, mab = has("dot1x pae authenticator"), has("mab")
        if dot1x and mab:
            return "dot1x+mab"
        if mab:
            return "mab-only"
        if dot1x:
            return "dot1x-only"
        if has(("service-policy type control", "source template")):
            return "new-style"
        return "auth-other"
    if module != "0":                                # network-module ports (x/1/y)
        return "uplink-module"
    if "shutdown" in lines:
        return "shutdown-static"
    return "static-access"


def short_hash(text):
    return hashlib.sha1(text.encode()).hexdigest()[:8]


def analyse(name, config, normalize_vlans):
    hostname, global_lines, ports, mode = name, [], [], "legacy"
    for parent, children in blocks(config):
        if parent.startswith("hostname "):
            hostname = parent.split(None, 1)[1]
        if parent.startswith(NEW_STYLE):
            mode = "new-style"
        m = PHYSICAL.match(parent)
        if m:
            port_class = classify(children, m.group(3).split("/")[1])
            auth_lines = sorted(normalize(c, normalize_vlans) for c in children if INTF_AUTH.match(c))
            text = "\n".join([f"# class: {port_class}"] + auth_lines)
            ports.append((parent.split()[1], port_class, short_hash(text), text))
        elif GLOBAL_AUTH.match(parent):
            global_lines.append("\n".join([normalize(parent, normalize_vlans)] +
                                          [" " + normalize(c, normalize_vlans) for c in children]))
    global_text = "\n".join(sorted(global_lines))
    return hostname, mode, short_hash(global_text), global_text, ports


def cmd_group(args):
    run = Path(args.run)
    files = sorted((run / "configs").glob("*.cfg"))
    if not files:
        sys.exit(f"No .cfg files in {run / 'configs'}")
    out = run / "variants"
    for sub in ("global_variants", "port_profiles"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    global_members, global_text = defaultdict(list), {}
    profile_ports, profile_switches = Counter(), defaultdict(set)
    profile_text, profile_class = {}, {}
    batch_members, batch_key = defaultdict(list), {}
    switch_rows, port_rows = [], []

    for f in files:
        hostname, mode, gid, gtext, ports = analyse(f.stem, f.read_text(errors="replace"),
                                                    args.normalize_vlans)
        global_members[gid].append((hostname, mode))
        global_text[gid] = gtext
        classes, auth_profiles = Counter(), set()
        for intf, port_class, pid, ptext in ports:
            profile_ports[pid] += 1
            profile_switches[pid].add(hostname)
            profile_text[pid], profile_class[pid] = ptext, port_class
            classes[port_class] += 1
            if port_class not in SKIP_FOR_BATCH:
                auth_profiles.add(pid)
            port_rows.append({"hostname": hostname, "interface": intf, "class": port_class, "profile": pid})
        profiles = ",".join(sorted(auth_profiles))
        bid = short_hash(f"{gid}|{profiles}")
        batch_members[bid].append(hostname)
        batch_key[bid] = (gid, profiles)
        switch_rows.append({"hostname": hostname, "config_mode": mode, "global_variant": gid,
                            "batch": bid, **{f"ports_{k}": v for k, v in sorted(classes.items())}})

    rows = []
    for gid, members in sorted(global_members.items(), key=lambda kv: -len(kv[1])):
        (out / "global_variants" / f"{gid}.txt").write_text(global_text[gid] + "\n")
        modes = Counter(m for _, m in members)
        rows.append({"global_variant": gid, "switches": len(members), "legacy": modes["legacy"],
                     "new_style": modes["new-style"], "examples": " ".join(h for h, _ in members[:5])})
    write_csv(out / "global_variants.csv", rows)

    rows = []
    for pid, count in profile_ports.most_common():
        (out / "port_profiles" / f"{pid}.txt").write_text(profile_text[pid] + "\n")
        rows.append({"profile": pid, "class": profile_class[pid], "ports": count,
                     "switches": len(profile_switches[pid])})
    write_csv(out / "port_profiles.csv", rows)

    rows = []
    for bid, members in sorted(batch_members.items(), key=lambda kv: -len(kv[1])):
        gid, profiles = batch_key[bid]
        rows.append({"batch": bid, "switches": len(members), "global_variant": gid,
                     "auth_profiles": profiles, "examples": " ".join(members[:10])})
    write_csv(out / "batches.csv", rows)
    write_csv(out / "switches.csv", switch_rows)
    write_csv(out / "ports.csv", port_rows)

    print(f"{len(files)} switches -> {len(global_members)} global variants, "
          f"{len(profile_ports)} port profiles, {len(batch_members)} batches")
    for gid, members in sorted(global_members.items(), key=lambda kv: -len(kv[1]))[:5]:
        print(f"  global variant {gid}: {len(members)} switches")
    print(f"Reports in {out}")


# =================================================================== diff ====


def changed_lines(base_text, other_text):
    """Lines added to / missing from `other` compared with `base` (structure-aware)."""
    diff = list(difflib.unified_diff(base_text.splitlines(), other_text.splitlines(), lineterm="", n=1))
    added = [l[1:] for l in diff if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:] for l in diff if l.startswith("-") and not l.startswith("---")]
    return diff, added, removed


def cmd_diff(args):
    out = Path(args.run) / "variants"
    gv = read_csv(out / "global_variants.csv")
    pp = read_csv(out / "port_profiles.csv")
    if not gv:
        sys.exit("Run `group` first.")
    (out / "diff").mkdir(exist_ok=True)

    base = args.reference or gv[0]["global_variant"]        # most common = baseline
    base_text = (out / "global_variants" / f"{base}.txt").read_text()
    rows = []
    for v in gv:
        gid = v["global_variant"]
        diff, added, removed = changed_lines(base_text, (out / "global_variants" / f"{gid}.txt").read_text())
        if gid != base:
            (out / "diff" / f"global_{gid}.diff").write_text("\n".join(diff) + "\n")
        rows.append({"global_variant": gid, "switches": v["switches"], "is_baseline": gid == base,
                     "lines_added": len(added), "lines_missing": len(removed),
                     "first_change": (added + removed + [""])[0]})
    write_csv(out / "diff" / "global_diff_summary.csv", rows)

    # Port profiles: compare each profile with the most common profile of the same class.
    by_class = defaultdict(list)
    for p in pp:
        by_class[p["class"]].append(p)
    rows = []
    for cls, profiles in by_class.items():
        ref = profiles[0]["profile"]
        ref_text = (out / "port_profiles" / f"{ref}.txt").read_text()
        for p in profiles:
            diff, added, removed = changed_lines(ref_text, (out / "port_profiles" / f"{p['profile']}.txt").read_text())
            if p["profile"] != ref:
                (out / "diff" / f"port_{p['profile']}.diff").write_text("\n".join(diff) + "\n")
            rows.append({"class": cls, "profile": p["profile"], "ports": p["ports"],
                         "is_class_baseline": p["profile"] == ref,
                         "added": " | ".join(added), "missing": " | ".join(removed)})
    write_csv(out / "diff" / "port_diff_summary.csv", rows)

    print(f"Baseline global variant: {base}")
    for r in [r for r in rows if not r["is_class_baseline"]][:10]:
        print(f"  {r['class']:<16} {r['profile']} ({r['ports']} ports): "
              f"+[{r['added'] or '-'}] -[{r['missing'] or '-'}]")
    print(f"Diffs in {out / 'diff'}")


# ================================================================ compare ====


def cmd_compare(args):
    old, new = Path(args.old) / "variants", Path(args.new) / "variants"
    old_sw = {r["hostname"]: r for r in read_csv(old / "switches.csv")}
    new_sw = {r["hostname"]: r for r in read_csv(new / "switches.csv")}
    if not old_sw or not new_sw:
        sys.exit("Both runs need `group` output (variants/switches.csv).")

    rows = []
    for host in sorted(set(old_sw) | set(new_sw)):
        o, n = old_sw.get(host), new_sw.get(host)
        if not o:
            rows.append({"hostname": host, "change": "new switch", "detail": n["global_variant"]})
        elif not n:
            rows.append({"hostname": host, "change": "missing", "detail": "not in new run"})
        else:
            if o["global_variant"] != n["global_variant"]:
                rows.append({"hostname": host, "change": "global config changed",
                             "detail": f"{o['global_variant']} -> {n['global_variant']}"})
            if o["config_mode"] != n["config_mode"]:
                rows.append({"hostname": host, "change": "config mode changed",
                             "detail": f"{o['config_mode']} -> {n['config_mode']}"})

    old_ports = {(r["hostname"], r["interface"]): r for r in read_csv(old / "ports.csv")}
    new_ports = {(r["hostname"], r["interface"]): r for r in read_csv(new / "ports.csv")}
    for key in sorted(set(old_ports) & set(new_ports)):
        o, n = old_ports[key], new_ports[key]
        if o["profile"] != n["profile"]:
            rows.append({"hostname": key[0], "change": f"port {key[1]} changed",
                         "detail": f"{o['class']}/{o['profile']} -> {n['class']}/{n['profile']}"})

    dest = Path(args.new) / "variants" / "drift.csv"
    write_csv(dest, rows or [{"hostname": "", "change": "no drift", "detail": ""}])
    changed_hosts = {r["hostname"] for r in rows}
    print(f"{len(changed_hosts)} switches with changes ({len(rows)} findings). See {dest}")
    for r in rows[:15]:
        print(f"  {r['hostname']}: {r['change']} {r['detail']}")


# ================================================================= common ====


def write_csv(path, rows):
    fields = []
    for r in rows:
        fields += [k for k in r if k not in fields]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, restval=0)
        w.writeheader()
        w.writerows(rows)


def read_csv(path):
    if not Path(path).exists():
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="pull running configs from Catalyst Center (read-only)")
    f.add_argument("--run", required=True, help="run folder, e.g. reports/raw/2026-10-26")
    f.add_argument("--client", choices=("sdk", "requests"), default="sdk")
    f.add_argument("--platform", default=r"C9300", help="regex on platformId")
    f.add_argument("--hostname", default="", help="regex on hostname, e.g. one site's prefix")
    f.add_argument("--limit", type=int, default=0, help="only the first N devices (testing)")
    f.add_argument("--delay", type=float, default=0.5, help="seconds between config requests")
    f.add_argument("--refresh", action="store_true", help="re-fetch configs already saved")
    f.add_argument("--insecure", action="store_true", help="skip TLS verification (lab only)")
    f.set_defaults(func=cmd_fetch)

    g = sub.add_parser("group", help="fingerprint configs into variants and port profiles")
    g.add_argument("--run", required=True)
    g.add_argument("--normalize-vlans", action="store_true",
                   help="treat all VLAN numbers as equal (e.g. critical VLANs differ per site)")
    g.set_defaults(func=cmd_group)

    d = sub.add_parser("diff", help="show how each variant differs from the baseline")
    d.add_argument("--run", required=True)
    d.add_argument("--reference", help="global variant id to use as baseline (default: most common)")
    d.set_defaults(func=cmd_diff)

    c = sub.add_parser("compare", help="detect drift between two runs")
    c.add_argument("--old", required=True)
    c.add_argument("--new", required=True)
    c.set_defaults(func=cmd_compare)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
```

### `python/ibns_tools/classify_ports.py`

```python
#!/usr/bin/env python3
# python/ibns_tools/classify_ports.py
"""Classify every access-switch port by description AND config, offline.

Reads configs already pulled by ibns_discovery.py (no switch or Catalyst
Center access) and uses the SAME rules and code as the Ansible jobs:
  rules: ansible/playbooks/group_vars/all.yml  (ibns_description_rules,
         ibns_port_roles, ibns_port_templates, ibns_hold_unmatched)
  logic: ansible/plugins/filter/ibns_filters.py (ibns_port_inventory)
So what this script says will migrate is what stage 2 will migrate.

Usage (from the repo root, venv active):
  python python/ibns_tools/classify_ports.py --run reports/raw/2026-10-26
  python python/ibns_tools/classify_ports.py --run reports/raw/2026-10-26 --hostname '^TOR-0042'
  python python/ibns_tools/classify_ports.py --config lab-switch.cfg          # one file, prints a table
  python python/ibns_tools/classify_ports.py --test "PRN-2F-HR"             # which rule a description hits

Writes to <run>/classify/:
  ports_classified.csv        one row per port: role, config class, action, reason
  held_ports.csv              ports that will NOT be migrated until fixed
  switch_summary.csv          per switch: migrate / hold / leave / done counts, ready or not
  role_vs_class.csv           role x config class counts (spot bad rules fast)
  unmatched_descriptions.csv  description patterns no rule matched, most common first
                              (digits shown as #) - use it to write the rules

Keep reports/raw/ out of Git: it holds real configs and hostnames.
"""
import argparse
import csv
import importlib.util
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml  # installed with ansible-core

REPO = Path(__file__).resolve().parents[2]
FILTERS = REPO / "ansible/plugins/filter/ibns_filters.py"
VARS = REPO / "ansible/playbooks/group_vars/all.yml"


def load_filters():
    spec = importlib.util.spec_from_file_location("ibns_filters", FILTERS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_rules(path):
    data = yaml.safe_load(Path(path).read_text()) or {}
    missing = [k for k in ("ibns_description_rules", "ibns_port_roles", "ibns_port_templates") if k not in data]
    if missing:
        sys.exit(f"{path} is missing: {', '.join(missing)}")
    return {
        "rules": data["ibns_description_rules"],
        "roles": data["ibns_port_roles"],
        "templates": data["ibns_port_templates"],
        "hold_unmatched": bool(data.get("ibns_hold_unmatched", True)),
        "max_held": int(data.get("ibns_max_held_ports", 0)),
    }


def pattern_of(description):
    """'PRN-2F-014' -> 'prn-#f-#' so similar descriptions group together."""
    return re.sub(r"\d+", "#", description.lower()).strip()


def write_csv(path, rows, fields):
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


PORT_FIELDS = ["hostname", "interface", "description", "role", "config_class",
               "status", "action", "template", "reason"]


def classify_file(f, cfg_path, cfg):
    inventory = f.ibns_port_inventory(cfg_path.read_text(errors="replace"), cfg["rules"],
                                      cfg["roles"], cfg["templates"], cfg["hold_unmatched"])
    return [{"hostname": cfg_path.stem, "interface": intf, **port} for intf, port in inventory.items()]


def print_table(rows):
    widths = {k: max(len(k), *(len(str(r[k])) for r in rows)) for k in
              ("interface", "role", "config_class", "action", "description")}
    head = "  ".join(k.upper().ljust(widths[k]) for k in widths)
    print(head + "  REASON")
    print("-" * len(head))
    for r in rows:
        print("  ".join(str(r[k] or "-").ljust(widths[k]) for k in widths) + "  " + r["reason"])


def cmd_test(f, cfg, description):
    role = f.ibns_description_role(description, cfg["rules"])
    for i, rule in enumerate(cfg["rules"], 1):
        if re.search(str(rule["match"]), description, re.IGNORECASE):
            print(f'"{description}" -> role {role} (rule {i}: {rule["match"]})')
            spec = cfg["roles"].get(role, {})
            print(f"  migrate: {spec.get('migrate')}  expect: {spec.get('expect')}")
            return
    print(f'"{description}" -> no rule matches (port would be held if it has auth config)')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--run", help="discovery run folder with configs/*.cfg")
    src.add_argument("--config", help="one saved running config; prints a port table")
    src.add_argument("--test", metavar="DESCRIPTION", help="show which rule a description matches")
    ap.add_argument("--hostname", help="only switches whose name matches this regex (with --run)")
    ap.add_argument("--vars", default=str(VARS), help=f"rules file (default {VARS.relative_to(REPO)})")
    args = ap.parse_args()

    f = load_filters()
    cfg = load_rules(args.vars)
    try:
        f.ibns_description_role("", cfg["rules"])          # validates every regex up front
    except ValueError as exc:
        sys.exit(str(exc))

    if args.test:
        cmd_test(f, cfg, args.test)
        return

    if args.config:
        rows = classify_file(f, Path(args.config), cfg)
        print_table(rows)
        held = sum(r["action"] == "hold" for r in rows)
        print(f"\n{len(rows)} ports: migrate {sum(r['action'] == 'migrate' for r in rows)}, "
              f"hold {held}, leave {sum(r['action'] == 'leave' for r in rows)}, "
              f"done {sum(r['action'] == 'done' for r in rows)}")
        return

    run = Path(args.run)
    files = sorted((run / "configs").glob("*.cfg"))
    if args.hostname:
        files = [p for p in files if re.search(args.hostname, p.stem)]
    if not files:
        sys.exit(f"No matching .cfg files in {run / 'configs'}")

    out = run / "classify"
    out.mkdir(parents=True, exist_ok=True)
    all_rows, switches = [], []
    role_class = Counter()
    unmatched = defaultdict(lambda: {"count": 0, "example": "", "classes": Counter(), "switches": set()})

    for path in files:
        rows = classify_file(f, path, cfg)
        all_rows += rows
        counts = Counter(r["action"] for r in rows)
        ready = "NO" if counts["hold"] > cfg["max_held"] else (
            "yes" if counts["migrate"] else ("done" if counts["done"] else "nothing to migrate"))
        switches.append({
            "hostname": path.stem, "ports": len(rows), "migrate": counts["migrate"],
            "hold": counts["hold"], "leave": counts["leave"], "done": counts["done"], "ready": ready,
        })
        for r in rows:
            role_class[(r["role"] or "-", r["config_class"])] += 1
            if r["status"] in ("no-rule", "no-description"):
                u = unmatched[pattern_of(r["description"]) or "(blank)"]
                u["count"] += 1
                u["example"] = u["example"] or r["description"]
                u["classes"][r["config_class"]] += 1
                u["switches"].add(r["hostname"])

    write_csv(out / "ports_classified.csv", all_rows, PORT_FIELDS)
    held_rows = [r for r in all_rows if r["action"] == "hold"]
    write_csv(out / "held_ports.csv", held_rows, PORT_FIELDS)
    write_csv(out / "switch_summary.csv", switches, ["hostname", "ports", "migrate", "hold", "leave", "done", "ready"])
    write_csv(out / "role_vs_class.csv",
              [{"role": k[0], "config_class": k[1], "ports": v} for k, v in sorted(role_class.items())],
              ["role", "config_class", "ports"])
    write_csv(out / "unmatched_descriptions.csv",
              [{"pattern": p, "ports": u["count"], "switches": len(u["switches"]), "example": u["example"],
                "config_classes": "; ".join(f"{c}={n}" for c, n in u["classes"].most_common())}
               for p, u in sorted(unmatched.items(), key=lambda kv: -kv[1]["count"])],
              ["pattern", "ports", "switches", "example", "config_classes"])

    actions = Counter(r["action"] for r in all_rows)
    ready = sum(s["ready"] == "yes" for s in switches)
    print(f"{len(files)} switches, {len(all_rows)} ports: migrate {actions['migrate']}, "
          f"hold {actions['hold']}, leave {actions['leave']}, done {actions['done']}")
    print(f"switches ready: {ready}/{len(switches)}  (held ports allowed per switch: {cfg['max_held']})")
    print(f"description patterns with no rule: {len(unmatched)}")
    print(f"written to {out}/")


if __name__ == "__main__":
    main()
```
