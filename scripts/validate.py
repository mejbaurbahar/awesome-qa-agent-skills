#!/usr/bin/env python3
"""Validate every skill so it loads in BOTH Claude Code and Antigravity.

Checks: SKILL.md exists, frontmatter parses under strict YAML rules (the
Antigravity loader silently drops a skill whose unquoted value contains
": "), name equals the folder, description is present and <= 1024 chars,
every skill is accounted for in sources.lock.json, and nothing leaks a
private local path or credential. Stdlib only, Python 3.9+.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEAK_RE = re.compile(
    r"(/Users/[A-Za-z0-9._-]+/|/home/[a-z0-9._-]+/|~/qa-agent|gh[opsu]_[A-Za-z0-9]{20,}|"
    r"sk-ant-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|[A-Za-z0-9._%+-]+@gmail\.com)"
)
LEAK_ALLOW = re.compile(r"(you|user|example|name|your)@gmail\.com|/Users/(you|me|name|username|USER)/", re.I)


def frontmatter(text):
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    return text[3:end] if end != -1 else None


def strict_yaml_errors(fm):
    """Top-level `key: value` lines whose unquoted plain value contains ': '."""
    errors = []
    for i, line in enumerate(fm.splitlines(), 1):
        m = re.match(r"^([A-Za-z0-9_-]+):\s+(.*)$", line)
        if not m:
            continue
        value = m.group(2).strip()
        if not value or value[0] in "\"'|>[{&*!":
            continue
        if ": " in value or value.endswith(":") or " #" in value:
            errors.append(f"line {i}: unquoted value for '{m.group(1)}' contains ': ' or ' #'")
    return errors


def field(fm, key):
    m = re.search(rf"(?m)^{key}:\s*(.*)$", fm)
    if not m:
        return None
    v = m.group(1).strip()
    if v in (">", "|", ">-", "|-"):
        block = re.search(rf"(?ms)^{key}:\s*[>|]-?\n((?:[ \t]+.*\n?)+)", fm)
        return " ".join(l.strip() for l in block.group(1).splitlines()) if block else ""
    return v.strip("\"'")


def main():
    lock = json.loads((ROOT / "sources.lock.json").read_text())
    known = {n for e in lock.values() for n in e["skills"]}
    problems = []
    skills = sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir())
    for d in skills:
        md = d / "SKILL.md"
        if not md.is_file():
            problems.append(f"{d.name}: missing SKILL.md")
            continue
        text = md.read_text(encoding="utf-8")
        fm = frontmatter(text)
        if fm is None:
            problems.append(f"{d.name}: no frontmatter")
            continue
        problems += [f"{d.name}: {e}" for e in strict_yaml_errors(fm)]
        if field(fm, "name") != d.name:
            problems.append(f"{d.name}: name field '{field(fm, 'name')}' != folder")
        desc = field(fm, "description")
        if not desc:
            problems.append(f"{d.name}: missing description")
        elif len(desc) > 1024:
            problems.append(f"{d.name}: description {len(desc)} chars > 1024")
        if d.name not in known:
            problems.append(f"{d.name}: not listed in sources.lock.json")
        for f in d.rglob("*"):
            if f.is_file() and f.suffix in {".md", ".py", ".js", ".cjs", ".sh", ".json", ".yaml", ".yml", ".txt"}:
                for m in LEAK_RE.finditer(f.read_text(encoding="utf-8", errors="ignore")):
                    if not LEAK_ALLOW.search(m.group(0)):
                        problems.append(f"{f.relative_to(ROOT)}: possible private data '{m.group(0)}'")
    for p in problems:
        print("FAIL", p)
    print(f"{len(skills)} skills checked, {len(problems)} problem(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
