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
