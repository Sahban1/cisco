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
