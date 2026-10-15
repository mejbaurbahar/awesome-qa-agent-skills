#!/usr/bin/env python3
"""Generate packs/*.txt, categories/*.txt and the README catalog.

Every skill gets exactly one category: its own `metadata.category` if it has
one, otherwise the mapping in categories.json. Fails on any uncategorized or
unknown-category skill. Stdlib only. Run after scripts/sync_vendor.py.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START, END = "<!-- catalog:start -->", "<!-- catalog:end -->"


def frontmatter(name):
    text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    return text.split("\n---", 1)[0]


def own_category(fm):
    m = re.search(r"(?m)^metadata:\s*\n((?:[ \t]+.*\n?)+)", fm)
    if m:
        c = re.search(r"(?m)^[ \t]+category:\s*[\"']?([a-z0-9-]+)", m.group(1))
        if c:
            return c.group(1)
    return None


def description(fm):
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


def anchor(title):
    # GitHub drops emoji/punctuation but keeps the space after a leading emoji, so the slug starts with '-'.
    return re.sub(r"[^a-z0-9 -]", "", title.lower()).replace(" ", "-")


def write_lists(folder, mapping):
    d = ROOT / folder
    d.mkdir(exist_ok=True)
    for old in d.glob("*.txt"):
        if old.stem not in mapping:
            old.unlink()
    for key, names in mapping.items():
        (d / f"{key}.txt").write_text("\n".join(sorted(names)) + "\n")


def main():
    lock = json.loads((ROOT / "sources.lock.json").read_text())
    sources = json.loads((ROOT / "sources.json").read_text())["sources"]
    cfg = json.loads((ROOT / "categories.json").read_text())
    cats = {c["id"]: c for c in cfg["categories"]}

    skill_src, packs = {}, {}
    for sid, e in lock.items():
        for n in e["skills"]:
            skill_src[n] = e
            packs.setdefault(e["pack"], []).append(n)

    by_cat, errors = {c: [] for c in cats}, []
    for n in sorted(skill_src):
        fm = frontmatter(n)
        cat = own_category(fm) or cfg["assign"].get(n)
        if not cat:
            errors.append(f"{n}: no category (add it to categories.json 'assign')")
        elif cat not in cats:
            errors.append(f"{n}: unknown category '{cat}'")
        else:
            by_cat[cat].append((n, description(fm), skill_src[n]))
    stale = sorted(set(cfg["assign"]) - set(skill_src))
    errors += [f"categories.json assigns missing skill '{n}'" for n in stale]
    if errors:
        print("\n".join("FAIL " + e for e in errors))
        sys.exit(1)

    write_lists("packs", packs)
    write_lists("categories", {c: [n for n, _, _ in v] for c, v in by_cat.items() if v})

    total = len(skill_src)
    out = [START, "", "**Jump to a category** · install just one with `./install.sh --category <id>`", ""]
    out += ["| Category | Skills | `--category` |", "|---|---:|---|"]
    for g in cfg["groups"]:
        out.append(f"| **{g['title']}** | | |")
        for c in cfg["categories"]:
            if c["group"] == g["id"] and by_cat[c["id"]]:
                t = f"{c['emoji']} {c['title']}"
                out.append(f"| &nbsp;&nbsp;[{t}](#{anchor(t)}) | {len(by_cat[c['id']])} | `{c['id']}` |")
    out.append("")
    for g in cfg["groups"]:
        out += [f"### {g['title']}", ""]
        for c in cfg["categories"]:
            rows = by_cat[c["id"]]
            if c["group"] != g["id"] or not rows:
                continue
            out += [f"#### {c['emoji']} {c['title']}", "", f"*{c['blurb']}*", "",
                    "<details>", f"<summary>{len(rows)} skills</summary>", "",
                    "| Skill | What it does | Source |", "|---|---|---|"]
            for n, desc, e in rows:
                repo = e["repo"].replace("https://github.com/", "")
                out.append(f"| `{n}` | {desc} | [{repo}]({e['repo']}) |")
            out += ["", "</details>", ""]
    for s in (s for s in sources if s["mode"] == "upstream"):
        out += [f"**➕ Optional upstream pack:** [{s['repo'].replace('https://github.com/', '')}]({s['repo']}) "
                f"({s['license']}) — {s.get('note', '')} Add with `./install.sh --with-upstream`.", ""]
    out.append(END)

    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: "\n".join(out), text, flags=re.S)
    text = re.sub(r"<!-- count -->\d+<!-- /count -->", f"<!-- count -->{total}<!-- /count -->", text)
    text = re.sub(r"skills-\d+-", f"skills-{total}-", text)
    readme.write_text(text, encoding="utf-8")
    used = sum(1 for v in by_cat.values() if v)
    print(f"catalog: {total} skills in {used} categories; packs " +
          ", ".join(f"{p}={len(v)}" for p, v in sorted(packs.items())))


if __name__ == "__main__":
    main()
