#!/usr/bin/env python3
"""Generate packs/*.txt and the README catalog block from sources.lock.json.

Stdlib only. Run after scripts/sync_vendor.py.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK_TITLES = {
    "qa": "QA & Software Testing",
    "pm": "Product Management",
    "web": "Web Quality, SEO & AI Visibility",
}
START, END = "<!-- catalog:start -->", "<!-- catalog:end -->"


def description(name):
    text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    fm = text.split("\n---", 1)[0]
    m = re.search(r"(?m)^description:\s*(.*)$", fm)
    v = m.group(1).strip() if m else ""
    if v in (">", "|", ">-", "|-"):
        block = re.search(r"(?ms)^description:\s*[>|]-?\n((?:[ \t]+.*\n?)+)", fm)
        v = " ".join(l.strip() for l in block.group(1).splitlines())
    v = v.strip("\"'").replace("|", "\\|")
    v = re.sub(r"^Use (this skill )?when\s+", "", v, flags=re.I)
    v = v[:1].upper() + v[1:]
    first = re.split(r"(?<=[.!?])\s", v, maxsplit=1)[0]
    return (first[:157] + "...") if len(first) > 160 else first


def main():
    lock = json.loads((ROOT / "sources.lock.json").read_text())
    sources = json.loads((ROOT / "sources.json").read_text())["sources"]
    packs = {p: [] for p in PACK_TITLES}
    by_name = {}
    for sid, e in lock.items():
        for n in e["skills"]:
            packs[e["pack"]].append(n)
            by_name[n] = (sid, e)
    (ROOT / "packs").mkdir(exist_ok=True)
    for p, names in packs.items():
        (ROOT / "packs" / f"{p}.txt").write_text("\n".join(sorted(names)) + "\n")

    total = sum(len(v) for v in packs.values())
    upstream = [s for s in sources if s["mode"] == "upstream"]
    out = [START, ""]
    for p, title in PACK_TITLES.items():
        names = sorted(packs[p])
        out += [f"<details{' open' if p == 'qa' else ''}>",
                f"<summary><b>{title}</b> — {len(names)} skills (<code>--pack {p}</code>)</summary>", "",
                "| Skill | What it does | Source |", "|---|---|---|"]
        for n in names:
            sid, e = by_name[n]
            repo = e["repo"].replace("https://github.com/", "")
            out.append(f"| `{n}` | {description(n)} | [{repo}]({e['repo']}) |")
        out += ["", "</details>", ""]
    for s in upstream:
        out.append(f"**+ Optional upstream pack:** [{s['repo'].replace('https://github.com/', '')}]({s['repo']}) "
                   f"({s['license']}) — {s.get('note', '')} Add with `./install.sh --with-upstream`.")
        out.append("")
    out.append(END)

    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = re.sub(re.escape(START) + r".*?" + re.escape(END), "\n".join(out), text, flags=re.S)
    text = re.sub(r"<!-- count -->\d+<!-- /count -->", f"<!-- count -->{total}<!-- /count -->", text)
    text = re.sub(r"skills-\d+-", f"skills-{total}-", text)
    readme.write_text(text, encoding="utf-8")
    print(f"catalog: {total} skills -> " + ", ".join(f"{p}={len(v)}" for p, v in packs.items()))


if __name__ == "__main__":
    main()
