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
