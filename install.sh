#!/usr/bin/env sh
# Install into ~/.claude/skills/papers. Idempotent.
set -e
DEST="${CLAUDE_SKILLS:-$HOME/.claude/skills}/papers"
SRC="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$DEST" "$HOME/.claude/papers"
for d in references agents scripts tests assets; do
  [ -d "$SRC/$d" ] && rm -rf "$DEST/$d" && cp -R "$SRC/$d" "$DEST/$d"
done
cp "$SRC/SKILL.md" "$DEST/SKILL.md"
cp "$SRC/profile.example.md" "$DEST/profile.example.md"
echo "installed to $DEST"
if [ ! -f "$HOME/.claude/papers/profile.md" ] \
   && [ ! -f "$HOME/.claude/industry-research/profile.md" ]; then
  cp "$SRC/profile.example.md" "$HOME/.claude/papers/profile.md"
  echo "wrote a starter profile to ~/.claude/papers/profile.md — edit it before your first run"
fi
python3 "$DEST/scripts/doctor.py" || true
