#!/usr/bin/env bash
# Renders the terminal SVGs and pushes them to the `output` branch when something changed.
# Run every 30 minutes by assets/systemd/walidozich-terminal.timer. Uses the local `gh` login.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
work="${XDG_STATE_HOME:-$HOME/.local/state}/walidozich-terminal"

git -C "$repo" fetch --quiet origin output
if [ ! -d "$work" ]; then
  git -C "$repo" worktree add --quiet --detach "$work" origin/output
fi
git -C "$work" checkout --quiet --detach origin/output
git -C "$work" reset --quiet --hard origin/output

GITHUB_TOKEN="$(gh auth token)" python3 -I "$repo/assets/gen_terminal.py" "$work"

# The "# synced <time>" line changes every run, so ignore it when deciding whether to commit.
git -C "$work" add -A
if git -C "$work" diff --cached --quiet -I '# synced '; then
  echo "nothing changed"
  exit 0
fi
git -C "$work" -c user.name="walid-terminal-bot" -c user.email="noreply@users.noreply.github.com" \
  commit --quiet -m "chore: render terminal"
git -C "$work" push --quiet origin HEAD:output
echo "published $(git -C "$work" rev-parse --short HEAD)"
