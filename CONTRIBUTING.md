# Contributing

Thanks for helping testers and PMs get better results from their agents.

## Add or fix an original skill
1. Create `skills/<kebab-case-name>/SKILL.md`. The `name` field must equal the folder name.
2. Start `description` with **"Use when …"** and list concrete triggers. Keep it under 1024 characters. If it contains `: `, wrap it in quotes, or Antigravity will silently skip the skill.
3. Body: when to use, a step-by-step procedure, copy-paste commands, a checklist, and common pitfalls. Put long material in `references/`.
4. Security skills must be defensive and state that testing requires authorization.

## Suggest a third-party skill
Open an issue or PR adding the upstream to `sources.json` (repo, path, skills, license). Only MIT, Apache-2.0, BSD or similar permissive licenses are vendored. Anything else goes in with `mode: upstream`.

## Before you open a PR
```bash
python3 scripts/sync_vendor.py --only <source-id>   # only if you touched sources.json
python3 scripts/build_catalog.py
python3 scripts/validate.py
```
CI runs the same checks plus an installer smoke test.
