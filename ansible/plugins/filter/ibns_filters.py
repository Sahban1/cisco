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
