#!/usr/bin/env python3
"""Refresh skills/ from the upstreams listed in sources.json.

For every source with mode=vendor: shallow-clone the repo, copy the listed
skill folders into skills/, apply renames, copy the upstream LICENSE into
licenses/, and record the exact commit in sources.lock.json.

Stdlib only. Usage: python3 scripts/sync_vendor.py [--only <source-id>]
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
LICENSES = ROOT / "licenses"
SKIP = {".git", ".github", "node_modules", "__pycache__", ".DS_Store"}


def clone(repo, dest):
    subprocess.run(["git", "clone", "-q", "--depth", "1", repo, str(dest)], check=True)
    sha = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"],
                         check=True, capture_output=True, text=True).stdout.strip()
    return sha


def list_skills(base, spec):
    if spec == "*":
        return sorted(p.name for p in base.iterdir() if (p / "SKILL.md").is_file())
    return spec


def rename_frontmatter(skill_md, new_name):
    text = skill_md.read_text(encoding="utf-8")
    text, n = re.subn(r"(?m)^name:\s*.*$", f"name: {new_name}", text, count=1)
    if n != 1:
        sys.exit(f"cannot rename {skill_md}: no name field")
    skill_md.write_text(text, encoding="utf-8")


def copy_skill(src, dest):
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=lambda d, names: [n for n in names if n in SKIP])


def main():
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    sources = json.loads((ROOT / "sources.json").read_text())["sources"]
    lock_path = ROOT / "sources.lock.json"
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else {}
    SKILLS.mkdir(exist_ok=True)
    LICENSES.mkdir(exist_ok=True)

    owner = {}  # skill name -> source id, to catch collisions across sources
    for sid, entry in lock.items():
        if sid != only:
            for name in entry.get("skills", []):
                owner[name] = sid

    for src in sources:
        if src["mode"] != "vendor" or (only and src["id"] != only):
            continue
        with tempfile.TemporaryDirectory() as tmp:
            checkout = Path(tmp) / "repo"
            sha = clone(src["repo"], checkout)
            base = checkout / src["path"] if src["path"] else checkout
            for old in lock.get(src["id"], {}).get("skills", []):
                shutil.rmtree(SKILLS / old, ignore_errors=True)
            names = []
            for rel in list_skills(base, src["skills"]):
                folder = (base / rel).resolve()
                if not (folder / "SKILL.md").is_file():
                    sys.exit(f"{src['id']}: {rel} has no SKILL.md")
                name = src.get("rename", {}).get(rel, Path(rel).name)
                if name in owner:
                    sys.exit(f"name collision: {name} from {src['id']} and {owner[name]}")
                owner[name] = src["id"]
                copy_skill(folder, SKILLS / name)
                if name != Path(rel).name or rel == ".":
                    rename_frontmatter(SKILLS / name / "SKILL.md", name)
                names.append(name)
            for lic in ("LICENSE", "LICENSE.md", "LICENSE.txt", "NOTICE", "NOTICE.md"):
                if (checkout / lic).is_file():
                    suffix = "NOTICE" if lic.startswith("NOTICE") else "LICENSE"
                    shutil.copy(checkout / lic, LICENSES / f"{src['id']}.{suffix}")
            lock[src["id"]] = {"repo": src["repo"], "commit": sha, "license": src["license"],
                               "pack": src["pack"], "skills": sorted(names)}
            print(f"{src['id']:<34} {len(names):>3} skills  @ {sha[:10]}")

    lock_path.write_text(json.dumps(dict(sorted(lock.items())), indent=2) + "\n")
    print(f"total vendored: {sum(len(e['skills']) for e in lock.values())}")


if __name__ == "__main__":
    main()
