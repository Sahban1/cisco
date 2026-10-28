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
