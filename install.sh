#!/usr/bin/env bash
# awesome-qa-agent-skills installer — Claude Code + Antigravity in one go.
#
#   ./install.sh                      # all packs, Claude Code + Antigravity
#   ./install.sh --pack qa,pm         # only some packs (qa, pm, web)
#   ./install.sh --claude-only        # or --antigravity-only
#   ./install.sh --with-upstream      # also fetch the 77-skill PM pack from upstream
#   ./install.sh --copy               # copy instead of symlink
#   ./install.sh --uninstall          # remove only what this script installed
#   ./install.sh --dry-run
#
# Bash 3.2 compatible (stock macOS). Never overwrites a skill it did not create.
set -euo pipefail

REPO_URL="https://github.com/mejbaurbahar/awesome-qa-agent-skills.git"
HOME_DIR="${AQS_HOME:-$HOME/.awesome-qa-agent-skills}"
MANIFEST="$HOME_DIR/.installed"
CLAUDE_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
AGY_DIR="${ANTIGRAVITY_SKILLS_DIR:-$HOME/.gemini/config/skills}"

PACKS="qa,pm,web"; DO_CLAUDE=1; DO_AGY=1; MODE=link; UPSTREAM=0; DRY=0; UNINSTALL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --pack|--packs) PACKS="$2"; shift ;;
    --claude-only) DO_AGY=0 ;;
    --antigravity-only) DO_CLAUDE=0 ;;
    --copy) MODE=copy ;;
    --with-upstream) UPSTREAM=1 ;;
    --uninstall) UNINSTALL=1 ;;
    --dry-run) DRY=1 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

say() { printf '%s\n' "$*"; }
run() { if [ "$DRY" = 1 ]; then say "  [dry-run] $*"; else "$@"; fi; }

# Locate the repo: use this checkout if we are inside one, else clone/update.
# When piped (curl | bash) BASH_SOURCE is not a file, so never trust the cwd.
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/sources.lock.json" ]; then
  REPO="$SCRIPT_DIR"
else
  REPO="$HOME_DIR/repo"
  if [ -d "$REPO/.git" ]; then run git -C "$REPO" pull -q --ff-only
  else run mkdir -p "$HOME_DIR"; run git clone -q --depth 1 "$REPO_URL" "$REPO"; fi
fi

if [ "$UNINSTALL" = 1 ]; then
  [ -f "$MANIFEST" ] || { say "nothing to uninstall"; exit 0; }
  n=0
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    if [ -L "$p" ] || [ -d "$p" ]; then run rm -rf "$p"; n=$((n+1)); fi
  done < "$MANIFEST"
  run rm -f "$MANIFEST"
  say "removed $n skill entries"; exit 0
fi

pack_skills() {  # print skill names for the selected packs
  local p
  for p in $(printf '%s' "$PACKS" | tr ',' ' '); do
    [ -f "$REPO/packs/$p.txt" ] || { echo "unknown pack: $p" >&2; exit 2; }
    cat "$REPO/packs/$p.txt"
  done
}

installed=0; skipped=0
place() {  # place <source-dir> <target-root>
  local src="$1" root="$2" name dest
  name="$(basename "$src")"; dest="$root/$name"
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if grep -qxF "$dest" "$MANIFEST" 2>/dev/null; then run rm -rf "$dest"
    else skipped=$((skipped+1)); say "  skip $name (already exists in $root, not ours)"; return; fi
  fi
  if [ "$MODE" = copy ]; then run cp -R "$src" "$dest"; else run ln -s "$src" "$dest"; fi
  if [ "$DRY" = 0 ] && ! grep -qxF "$dest" "$MANIFEST" 2>/dev/null; then echo "$dest" >> "$MANIFEST"; fi
  installed=$((installed+1))
}

run mkdir -p "$HOME_DIR"; [ "$DRY" = 1 ] || touch "$MANIFEST"
TARGETS=""
[ "$DO_CLAUDE" = 1 ] && TARGETS="$TARGETS $CLAUDE_DIR"
[ "$DO_AGY" = 1 ] && TARGETS="$TARGETS $AGY_DIR"

for root in $TARGETS; do
  run mkdir -p "$root"
  say "-> $root"
  for name in $(pack_skills); do place "$REPO/skills/$name" "$root"; done
done

if [ "$UPSTREAM" = 1 ]; then
  UP="$HOME_DIR/upstream/product-manager-skills"
  if [ -d "$UP/.git" ]; then run git -C "$UP" pull -q --ff-only
  else run mkdir -p "$HOME_DIR/upstream"; run git clone -q --depth 1 https://github.com/deanpeters/Product-Manager-Skills.git "$UP"; fi
  say "-> upstream PM pack (deanpeters/Product-Manager-Skills, CC BY-NC-SA 4.0)"
  for root in $TARGETS; do
    for d in "$UP"/skills/*/; do [ -f "$d/SKILL.md" ] && place "${d%/}" "$root"; done
  done
fi

say ""
say "done: $installed installed, $skipped skipped (existing skills were left untouched)."
say "Restart Claude Code / Antigravity to load them. Uninstall: $0 --uninstall"
