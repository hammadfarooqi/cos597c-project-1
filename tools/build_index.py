#!/usr/bin/env python3
"""Regenerate docs/README.md (the document index) from frontmatter, and audit the docs.

The root README.md is the hand-written guide for readers. This script does not touch it.

Usage:
    python3 tools/build_index.py           # rewrite docs/README.md, print the audit
    python3 tools/build_index.py --check    # audit only, change nothing; exit 1 on warnings

Why this exists: a hand-maintained table of contents drifts away from the files it describes.
This script reads the truth out of the files themselves, so the index cannot disagree with them.

Staleness check: a document whose last git commit is newer than its `updated:` date was changed
without its date being bumped. File modification times are not used, because a git checkout
resets them. A file with uncommitted changes counts as changed today.

No third-party packages. The frontmatter parser handles only the subset of YAML this repository
uses: `key: value` and `key: >-` followed by indented lines.
"""

import argparse
import datetime as dt
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "docs" / "README.md"

# Never indexed. code/tau2-bench and code/workbench are upstream code with their own Markdown files.
SKIP_PREFIXES = ("code/tau2-bench", "code/workbench/", "skill-observations", ".claude")
SKIP_ANYWHERE = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".ipynb_checkpoints", ".mypy_cache", ".pytest_cache", "site-packages",
}

# Section order in the generated index, with the heading and blurb for each type.
SECTIONS = [
    ("charter", "Start here", "What the project is. Authoritative on scope."),
    ("milestones", "Milestones", "The master tracker. What is done, what is next, who owns it."),
    ("log", "Logs (append-only)", "Never edited, only added to. These cannot go stale."),
    ("research", "Research", "What we learned about the outside world. These CAN go stale."),
    ("meeting", "Meeting notes", "A dated record of each meeting. Newest last."),
    ("external", "External-facing", "What was submitted or shown to course staff."),
    ("draft", "Drafts", "Written up but not yet submitted. Expect these to change."),
    ("index", "Indexes", "Guides to a folder's contents."),
]

STATUS_MARK = {
    "current": "current",
    "needs-review": "**needs review**",
    "superseded": "~~superseded~~",
}

MILESTONE_ROW = re.compile(
    r"^\|\s*(M[\d.]+)\s*\|.*\|\s*(todo|in progress|blocked|done|dropped)\s*\|[^|]*\|\s*$"
)


def skipped(rel):
    """True if this path lies inside a directory we never index."""
    text = rel.as_posix()
    return text.startswith(SKIP_PREFIXES) or bool(SKIP_ANYWHERE.intersection(rel.parts))


def parse_frontmatter(text):
    """Return (metadata dict, True) or ({}, False) if the file has no frontmatter."""
    if not text.startswith("---\n"):
        return {}, False
    end = text.find("\n---", 4)
    if end == -1:
        return {}, False

    meta, key, buffer = {}, None, []
    for line in text[4:end].split("\n"):
        if line.startswith("  ") and key:           # continuation of a folded block
            buffer.append(line.strip())
            continue
        if key:
            meta[key] = " ".join(buffer).strip()
            key, buffer = None, []
        match = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if not match:
            continue
        name, value = match.group(1), match.group(2).strip()
        if value in (">-", ">", "|", "|-"):
            key = name
        else:
            meta[name] = value
    if key:
        meta[key] = " ".join(buffer).strip()
    return meta, True


def git(*args):
    result = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def last_changed(rel):
    """Date the file's content last changed: today if uncommitted, else its last commit date."""
    if git("status", "--porcelain", "--", str(rel)):
        return dt.date.today()
    stamp = git("log", "-1", "--format=%cs", "--", str(rel))
    return dt.date.fromisoformat(stamp) if stamp else dt.date.today()


def markdown_files():
    for path in sorted(ROOT.rglob("*.md")):
        rel = path.relative_to(ROOT)
        if not skipped(rel):
            yield path, rel


def collect():
    """Return (docs with frontmatter, files missing it)."""
    docs, missing = [], []
    for path, rel in markdown_files():
        # The root README.md is the hand-written reader guide, docs/README.md is generated, and
        # CLAUDE.md is the agent entry point. None is an indexed document or carries frontmatter.
        if str(rel) in ("README.md", "docs/README.md", "CLAUDE.md"):
            continue
        meta, found = parse_frontmatter(path.read_text())
        if not found:
            missing.append(rel)
            continue
        meta["_path"] = rel
        meta["_changed"] = last_changed(rel)
        docs.append(meta)
    return docs, missing


def milestone_counts():
    """Count milestone rows by status in docs/decisions/milestones.md."""
    path = ROOT / "docs/decisions/milestones.md"
    counts = {}
    if path.exists():
        for line in path.read_text().split("\n"):
            match = MILESTONE_ROW.match(line)
            if match:
                counts[match.group(2)] = counts.get(match.group(2), 0) + 1
    return counts


def audit(docs, missing):
    """Return a list of warning strings. Empty list means the docs are clean."""
    today = dt.date.today()
    warnings = [f"NO FRONTMATTER   {rel}" for rel in missing]

    for doc in docs:
        rel = doc["_path"]
        raw = doc.get("updated", "")
        try:
            claimed = dt.date.fromisoformat(raw)
        except ValueError:
            warnings.append(f"BAD DATE         {rel}  updated: {raw!r}")
            continue

        if doc["_changed"] > claimed:
            warnings.append(
                f"DATE NOT BUMPED  {rel}  says {claimed}, last changed {doc['_changed']}"
            )

        # A visible "**Last updated:** DATE" line must agree with the frontmatter.
        body = (ROOT / rel).read_text()
        visible = re.search(r"\*\*Last updated:\*\*\s*(\d{4}-\d{2}-\d{2})", body)
        if visible and visible.group(1) != raw:
            warnings.append(
                f"DATE MISMATCH    {rel}  frontmatter {raw}, body says {visible.group(1)}"
            )

        review = doc.get("review_by")
        if review:
            try:
                due = dt.date.fromisoformat(review)
            except ValueError:
                warnings.append(f"BAD DATE         {rel}  review_by: {review!r}")
                continue
            if due < today:
                warnings.append(
                    f"REVIEW OVERDUE   {rel}  review_by {due} ({(today - due).days}d ago)"
                )

        if doc.get("status") == "needs-review":
            warnings.append(f"FLAGGED          {rel}  status: needs-review")

    # Internal links: Markdown link targets, and repo paths in backticks. Lines holding a URL
    # are skipped, since they may quote paths from other repositories.
    link_re = re.compile(
        r"\]\((?!https?:)([\w./-]+)\)|`((?:docs|code|tools)/[\w./-]+)`"
    )
    for path, rel in markdown_files():
        targets = set()
        for line in path.read_text().split("\n"):
            if "http" in line:
                continue
            for match in link_re.finditer(line):
                targets.add(match.group(1) or match.group(2))
        for target in sorted(targets):
            if (ROOT / target).exists() or (path.parent / target).exists():
                continue
            warnings.append(f"BROKEN LINK      {rel}  ->  {target}")
    return warnings


def link(rel):
    """A link target for repo path `rel`, relative to the folder that holds the index."""
    return os.path.relpath(ROOT / rel, INDEX.parent).replace(os.sep, "/")


def render(docs, warnings):
    today = dt.date.today().isoformat()
    out = [
        "<!-- GENERATED BY tools/build_index.py - DO NOT EDIT BY HAND. -->",
        "<!-- Your changes will be overwritten. Edit the frontmatter in each document instead. -->",
        "",
        "# Document index",
        "",
        "Every project document, with its date and status. For what the project is and how to",
        f"run it, see the [repository README]({link('README.md')}).",
        "",
        f"**Index generated:** {today} · **Documents:** {len(docs)}",
        "",
        f"> **Agents: read [`CLAUDE.md`]({link('CLAUDE.md')}) first.** "
        "It has the read order and the rules.",
        "",
    ]

    counts = milestone_counts()
    if counts:
        total = sum(counts.values())
        parts = [f"{counts[s]} {s}" for s in ("done", "in progress", "blocked", "todo", "dropped")
                 if counts.get(s)]
        out += [
            f"**Milestones:** {counts.get('done', 0)} / {total} done ({', '.join(parts)}). "
            f"See [`docs/decisions/milestones.md`]({link('docs/decisions/milestones.md')}).",
            "",
        ]
    out += ["---", ""]

    if warnings:
        out += [
            f"## ⚠ Audit: {len(warnings)} warning(s)",
            "",
            "```",
            *warnings,
            "```",
            "",
            "Run `python3 tools/build_index.py` after fixing these.",
            "",
            "---",
            "",
        ]
    else:
        out += ["## ✓ Audit clean", "", "---", ""]

    by_type = {}
    for doc in docs:
        by_type.setdefault(doc.get("type", "other"), []).append(doc)

    for type_name, heading, blurb in SECTIONS:
        group = by_type.pop(type_name, [])
        if not group:
            continue
        group.sort(key=lambda d: str(d["_path"]))
        out += [f"## {heading}", "", f"*{blurb}*", ""]
        out += ["| Document | Updated | Status | What it is |", "|---|---|---|---|"]
        for doc in group:
            rel = doc["_path"]
            title = doc.get("title", rel.stem)
            status = STATUS_MARK.get(doc.get("status", ""), doc.get("status", "?"))
            summary = doc.get("summary", "").replace("|", "\\|")
            if doc.get("note"):
                summary += f" **Note:** {doc['note']}"
            out += [f"| [{title}]({link(rel)}) | {doc.get('updated', '?')} | {status} | {summary} |"]
        out += [""]

    for type_name, group in by_type.items():       # any type not in SECTIONS
        out += [f"## {type_name}", ""]
        for doc in sorted(group, key=lambda d: str(d["_path"])):
            out += [f"- [{doc.get('title', doc['_path'].stem)}]({link(doc['_path'])})"]
        out += [""]

    out += [
        "---",
        "",
        "## Also in this repository",
        "",
        "| Path | What it is |",
        "|---|---|",
    ]
    for rel, what in [
        ("code/tau2-bench/", "Our modified copy of τ²-bench. See `code/README.md`."),
        ("code/twins/", "The counterfactual twin generator and the pair scorers."),
        ("code/tau2-bench/data/simulations/", "Experiment results, tracked in git."),
        ("code/workbench/", "Our modified copy of WorkBench. See `code/README.md`."),
        ("code/workbench-m2/", "The gates on WorkBench, and every WorkBench run."),
        ("docs/external/", "The submitted proposal PDFs."),
        ("tools/build_index.py", "Regenerates this file and runs the audit."),
    ]:
        out += [f"| [`{rel}`]({link(rel)}) | {what} |"]
    out += [""]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="audit only; write nothing; exit 1 if there are warnings")
    args = parser.parse_args()

    docs, missing = collect()
    warnings = audit(docs, missing)

    if not args.check:
        INDEX.write_text(render(docs, warnings) + "\n")
        print(f"Wrote {INDEX.relative_to(ROOT)} ({len(docs)} documents).")

    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for warning in warnings:
            print(f"  {warning}")
    else:
        print("\nAudit clean.")

    sys.exit(1 if (args.check and warnings) else 0)


if __name__ == "__main__":
    main()
