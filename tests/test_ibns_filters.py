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
