#!/usr/bin/env python3
"""Restructure the PurduePlant GitHub board: milestones > sprints > sized, tagged issues.

Usage (needs Python 3 and the GitHub CLI `gh`, logged in with issue-write access):
    python apply.py --dry-run            # no GitHub calls; writes rendered issues to ./preview
    python apply.py                      # apply to the repo of the current directory
    python apply.py --repo OWNER/REPO    # or name the repo explicitly
    python apply.py --sync               # only refresh the task lists in sprint trackers
Safe to re-run: existing issues are found by a hidden key and are not overwritten
(your ticked checkboxes are kept). Use --force-bodies to rewrite bodies.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import plan_data as P

DAYS = {"S": 1, "M": 3, "L": 5}
SIZE_TEXT = {"S": "Small (~1 day)", "M": "Medium (~3 days)", "L": "Large (~1 week)"}
WHERE_LABEL = {"r": "where:remote", "h": "where:lab-hardware", "n": "where:lab-network"}
WHERE_TEXT = {"r": "Remote (no lab access needed)", "h": "Lab: hardware bench", "n": "Lab: plant/lab network"}
WHERE_SHORT = {"r": "remote", "h": "lab-hw", "n": "lab-net"}
KEY_RE = re.compile(r"<!-- plant-key: ([\w-]+) -->")
TASKS_RE = re.compile(r"<!-- tasks:start -->.*?<!-- tasks:end -->", re.S)

ARGS = None
REPO = None


# ------------------------------------------------------------------ helpers
def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:4])} failed: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout


def pause():
    time.sleep(ARGS.delay)


def where_labels(t):
    return [WHERE_LABEL[c] for c in t["where"]]


def where_text(t):
    return " + ".join(WHERE_TEXT[c] for c in t["where"])


def task_labels(t):
    labels = [f"sprint:{t['sprint']}", f"size:{t['size']}", *where_labels(t), *t["area"], *t["flags"]]
    if t["sprint"] == 0 and not t["done"] and not t["deps"]:
        labels.append("status:ready")
    return sorted(set(labels))


def milestone_title(sprint):
    return P.MILESTONES[P.SPRINTS[sprint]["ms"]]["title"]


def ref(key, nums):
    return f"#{nums[key]}" if key in nums else "(new)"


def bullet(items, mark=" "):
    return "\n".join(f"- [{mark}] {i}" for i in items)


# ---------------------------------------------------------------- rendering
def render_task(t, nums):
    s = P.SPRINTS[t["sprint"]]
    done = t["done"]
    mark = "x" if done else " "
    head = [f"**Sprint {t['sprint']}:** {s['name']}  |  **Milestone:** {milestone_title(t['sprint'])}",
            f"**Size:** {SIZE_TEXT[t['size']]}  |  **Where:** {where_text(t)}"]
    if t["out"]:
        head.append(f"**Deliverable / output:** `{t['out']}`" if "deliverable" in t["flags"] else f"**Output:** `{t['out']}`")
    if t["deps"]:
        head.append("**Depends on:** " + ", ".join(ref(d, nums) for d in t["deps"]))
    status = "Completed before this restructure." if done else "Not started."
    head.append(f"**Status:** {status} (see the `status:` label; tick the boxes below as you go)")
    lines = [f"<!-- plant-key: {t['key']} -->", "\n\n".join(head), "",
             "## User story",
             f"As a **{t['role']}**, I want {t['want']}, so that {t['so']}.", ""]
    if t["note"]:
        lines += ["## Notes", t["note"], ""]
    lines += ["## Acceptance criteria", bullet(t["ac"], mark), ""]
    verify = t["verify"] or ["Record what was checked and how in `docs/VERIFIED.md`; list anything not checked as UNVERIFIED."]
    lines += ["## Verification", "\n".join(f"- {v}" for v in verify), ""]
    io = []
    if t["reads"]:
        io.append(f"- **Read:** {t['reads']}")
    if t["out"]:
        io.append(f"- **Produce:** `{t['out']}`")
    if io:
        lines += ["## Inputs and outputs", "\n".join(io), ""]
    lines += ["## Agent guidance"]
    if t["where"] == "r":
        lines.append("- **Remote-safe:** can be done without lab access (files, research, docs, code that is compile-checked only).")
    else:
        lines.append("- **Needs the lab:** the agent prepares, then a human performs the lab steps.")
        if t["human"]:
            lines.append(f"- **Human steps:** {t['human']}")
        lines.append("- Mark UNVERIFIED anything not confirmed on real hardware or the real network.")
    lines += ["", "## Guardrails", "\n".join(f"- {g}" for g in P.GUARDRAILS), "",
              "## Done when", bullet(["All acceptance criteria ticked", "Docs updated (CHANGELOG, VERIFIED: what was verified vs not)",
                                      "`status:` label updated and issue closed"], mark)]
    return "\n".join(lines) + "\n"


def tasks_section(n, nums, state):
    ts = [t for t in P.TASKS if t["sprint"] == n]
    rows = []
    for t in ts:
        closed = state.get(t["key"], "closed" if t["done"] else "open") == "closed"
        rows.append(f"- [{'x' if closed else ' '}] {ref(t['key'], nums)} {t['title']} (`{t['size']}`, {' + '.join(WHERE_SHORT[c] for c in t['where'])})")
    days = sum(DAYS[t["size"]] for t in ts)
    remote = sum(DAYS[t["size"]] for t in ts if t["where"] == "r")
    return ("<!-- tasks:start -->\n" + "\n".join(rows) +
            f"\n\nEstimated effort: **{days} days** ({remote} remote, {days - remote} involving the lab). "
            "Sizes: S = 1 day, M = 3 days, L = 1 week.\n<!-- tasks:end -->")


def render_tracker(n, nums, state):
    s = P.SPRINTS[n]
    m = P.MILESTONES[s["ms"]]
    sib = ", ".join(str(x) for x in m["sprints"])
    return "\n".join([
        f"<!-- plant-key: sprint-{n} -->",
        f"**Milestone:** {m['title']} (sprints {sib})  |  **Label:** `sprint:{n}`", "",
        "## Goal", s["goal"], "",
        "## Tasks", tasks_section(n, nums, state), "",
        "## Exit criteria (sprint gate)", bullet(s["exit"] + [f"Owner approves moving to {'Sprint ' + str(n + 1) if n < 7 else 'release'}"]), "",
        "## How progress is shown",
        "- Task list above: tick a task here when its issue is closed (or run `python apply.py --sync`).",
        "- Each task's own checkboxes show as `x of y` in the issue list.",
        "- Milestone page shows overall percent complete.",
        f"- Filter this sprint's tasks with the label `sprint:{n}`.", ""])


# ----------------------------------------------------------------- dry run
def validate():
    keys = [t["key"] for t in P.TASKS]
    assert len(keys) == len(set(keys)), "duplicate task keys"
    for t in P.TASKS:
        assert t["size"] in DAYS and set(t["where"]) <= set(WHERE_LABEL) and t["sprint"] in P.SPRINTS, t["key"]
        for d in t["deps"]:
            assert d in keys, f"{t['key']} depends on unknown {d}"
    names = {l[0] for l in P.LABELS}
    for t in P.TASKS:
        for l in task_labels(t):
            assert l in names, f"label {l} (in {t['key']}) is not defined in LABELS"


def dry_run():
    validate()
    out = Path("preview")
    out.mkdir(exist_ok=True)
    nums = {}
    for t in P.TASKS:
        (out / f"{t['key']}.md").write_text(f"TITLE: {t['title']}\nLABELS: {','.join(task_labels(t))}\nMILESTONE: {milestone_title(t['sprint'])}\n\n{render_task(t, nums)}", encoding="utf-8")
    for n in P.SPRINTS:
        (out / f"sprint-{n}.md").write_text(render_tracker(n, nums, {}), encoding="utf-8")
    print(f"{len(P.LABELS)} labels, {len(P.MILESTONES)} milestones, {len(P.SPRINTS)} sprint trackers, {len(P.TASKS)} tasks "
          f"({sum(t['done'] for t in P.TASKS)} already done). Rendered to ./preview")
    for n, s in P.SPRINTS.items():
        ts = [t for t in P.TASKS if t["sprint"] == n]
        d = sum(DAYS[t["size"]] for t in ts)
        r = sum(DAYS[t["size"]] for t in ts if t["where"] == "r")
        print(f"  Sprint {n} [{P.MILESTONES[s['ms']]['title'][:2]}] {s['name']}: {len(ts)} tasks, {d} days ({r} remote)")


# ------------------------------------------------------------------- apply
def list_issues():
    return json.loads(gh("issue", "list", "--repo", REPO, "--state", "all", "--limit", "1000",
                         "--json", "number,title,state,body"))


def find_existing(key, title, issues):
    for i in issues:
        m = KEY_RE.search(i["body"] or "")
        if m and m.group(1) == key:
            return i, True
    for i in issues:
        if key.startswith("sprint-") and re.match(rf"^Sprint {key[7:]}:", i["title"]):
            return i, False
        if P.LEGACY_TITLES.get(i["title"]) == key:
            return i, False
    return None, False


def write_body(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    return f.name


def upsert(key, title, body, labels, milestone, issues, nums, state, sprint_tracker=False):
    existing, managed = find_existing(key, title, issues)
    lab = ",".join(labels)
    if existing is None:
        path = write_body(body)
        out = gh("issue", "create", "--repo", REPO, "--title", title, "--body-file", path,
                 "--label", lab, "--milestone", milestone).strip()
        nums[key] = int(out.rstrip("/").split("/")[-1])
        state[key] = "open"
        print(f"  created #{nums[key]} {title}")
        pause()
        return True
    n = existing["number"]
    nums[key] = n
    state[key] = existing["state"].lower()
    args = ["issue", "edit", str(n), "--repo", REPO, "--add-label", lab, "--milestone", milestone]
    if managed and not ARGS.force_bodies:
        if sprint_tracker:   # keep ticked exit criteria; refresh only the task list
            new = TASKS_RE.sub(lambda _m: tasks_block(body), existing["body"] or "")
            args += ["--body-file", write_body(new)]
    else:
        args += ["--title", title, "--body-file", write_body(body)]
    gh(*args)
    print(f"  updated #{n} {title}")
    pause()
    return not (managed and not ARGS.force_bodies)


def tasks_block(body):
    return TASKS_RE.search(body).group(0)


def ensure_labels():
    print("Labels")
    for name, color, desc in P.LABELS:
        gh("label", "create", name, "--color", color, "--description", desc, "--repo", REPO, "--force")
    pause()


def ensure_milestones():
    print("Milestones")
    have = {m["title"]: m for m in json.loads(gh("api", f"repos/{REPO}/milestones?state=all&per_page=100"))}
    for m in P.MILESTONES:
        if m["title"] in have:
            gh("api", "-X", "PATCH", f"repos/{REPO}/milestones/{have[m['title']]['number']}", "--silent", "-f", f"description={m['desc']}")
            print(f"  exists: {m['title']}")
        else:
            gh("api", f"repos/{REPO}/milestones", "--silent", "-f", f"title={m['title']}", "-f", f"description={m['desc']}")
            print(f"  created: {m['title']}")
        pause()


def close_done(nums, state):
    for t in P.TASKS:
        if t["done"] and state.get(t["key"]) != "closed":
            gh("issue", "close", str(nums[t["key"]]), "--repo", REPO, "--reason", "completed",
               "--comment", f"Completed before the restructure. {t['note'] or ''}".strip())
            state[t["key"]] = "closed"
            print(f"  closed #{nums[t['key']]} {t['title']}")
            pause()


def delete_old_milestones():
    print("Old milestones")
    have = {m["title"]: m for m in json.loads(gh("api", f"repos/{REPO}/milestones?state=all&per_page=100"))}
    for title in P.OLD_MILESTONES:
        m = have.get(title)
        if not m:
            continue
        if m["open_issues"] + m["closed_issues"] == 0:
            gh("api", "-X", "DELETE", f"repos/{REPO}/milestones/{m['number']}", "--silent")
            print(f"  deleted empty milestone: {title}")
        else:
            print(f"  kept (still has issues): {title}")
        pause()


def apply_all():
    validate()
    ensure_labels()
    ensure_milestones()
    issues = list_issues()
    nums, state = {}, {}
    print("Task issues")
    written = set()
    for t in P.TASKS:
        if upsert(t["key"], t["title"], render_task(t, nums), task_labels(t), milestone_title(t["sprint"]), issues, nums, state):
            written.add(t["key"])
    # dependency numbers were not all known when each body was first rendered; refresh those bodies
    print("Dependency references")
    for t in P.TASKS:
        if t["deps"] and t["key"] in written:
            gh("issue", "edit", str(nums[t["key"]]), "--repo", REPO, "--body-file", write_body(render_task(t, nums)))
            pause()
    close_done(nums, state)
    print("Sprint trackers")
    for n, s in P.SPRINTS.items():
        key = f"sprint-{n}"
        title = f"Sprint {n}: {s['name']}"
        upsert(key, title, render_tracker(n, nums, state), ["sprint", f"sprint:{n}"], milestone_title(n), issues, nums, state, True)
    delete_old_milestones()
    print("Done. Open https://github.com/%s/milestones" % REPO)


def sync_only():
    issues = list_issues()
    nums, state = {}, {}
    for t in P.TASKS:
        i, _ = find_existing(t["key"], t["title"], issues)
        if i:
            nums[t["key"]], state[t["key"]] = i["number"], i["state"].lower()
    for n in P.SPRINTS:
        i, _ = find_existing(f"sprint-{n}", "", issues)
        if not i:
            print(f"  no tracker for sprint {n}; run without --sync first")
            continue
        new = TASKS_RE.sub(lambda _m: tasks_block(render_tracker(n, nums, state)), i["body"] or "")
        gh("issue", "edit", str(i["number"]), "--repo", REPO, "--body-file", write_body(new))
        print(f"  synced task list for sprint {n}")
        pause()


def main():
    global ARGS, REPO
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--force-bodies", action="store_true", help="rewrite issue bodies (resets ticked checkboxes)")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between GitHub writes (avoid rate limits)")
    ARGS = ap.parse_args()
    if ARGS.dry_run:
        return dry_run()
    REPO = ARGS.repo or gh("repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner").strip()
    print(f"Repo: {REPO}")
    sync_only() if ARGS.sync else apply_all()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, AssertionError) as e:
        sys.exit(f"ERROR: {e}")
