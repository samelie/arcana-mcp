#!/usr/bin/env bash
# Release arcana-mcp: validate, sync to public repo, create GitHub release → triggers PyPI publish.
#
# Usage:
#   ./scripts/release.sh           # release current version from pyproject.toml
#   ./scripts/release.sh 0.2.0     # bump to 0.2.0 first, then release
#
# Prerequisites:
#   - gh CLI authenticated
#   - On main branch with clean working tree
#   - packages/arcana-mcp changes committed and pushed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="$(dirname "$SCRIPT_DIR")"
MONOREPO_ROOT="$(cd "$PKG_DIR/../.." && pwd)"
PUBLIC_REPO="samelie/arcana-mcp"

cd "$PKG_DIR"

# --- Helpers ---
die() { echo "ERROR: $1" >&2; exit 1; }
info() { echo "→ $1"; }

# --- Preflight checks ---
command -v gh >/dev/null || die "gh CLI not found"
[[ "$(git -C "$MONOREPO_ROOT" branch --show-current)" == "main" ]] || die "not on main branch"

# Check for uncommitted changes in arcana-mcp
if ! git -C "$MONOREPO_ROOT" diff --quiet -- packages/arcana-mcp/; then
  die "uncommitted changes in packages/arcana-mcp/ — commit and push first"
fi

# --- Version ---
CURRENT_VERSION=$(python3 -c "
import re
text = open('pyproject.toml').read()
print(re.search(r'version\s*=\s*\"(.+?)\"', text).group(1))
")

if [[ -n "${1:-}" ]]; then
  NEW_VERSION="$1"
  info "bumping $CURRENT_VERSION → $NEW_VERSION"

  # Update pyproject.toml
  sed -i '' "s/^version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml

  # Commit the bump
  git -C "$MONOREPO_ROOT" add packages/arcana-mcp/pyproject.toml
  git -C "$MONOREPO_ROOT" commit -m "arcana-mcp v$NEW_VERSION"
  git -C "$MONOREPO_ROOT" push

  CURRENT_VERSION="$NEW_VERSION"
else
  info "releasing v$CURRENT_VERSION (from pyproject.toml)"
fi

TAG="v$CURRENT_VERSION"

# Check tag doesn't already exist on the public repo
if gh release view "$TAG" --repo "$PUBLIC_REPO" &>/dev/null; then
  die "release $TAG already exists on $PUBLIC_REPO"
fi

# --- Wait for sync ---
info "waiting for monorepo sync to push to $PUBLIC_REPO..."

# Find the sync workflow run (triggered by our push)
ATTEMPTS=0
MAX_ATTEMPTS=30
SYNC_STATUS=""

while [[ $ATTEMPTS -lt $MAX_ATTEMPTS ]]; do
  SYNC_STATUS=$(gh run list \
    --repo samelie/samelie-monorepo \
    --workflow "sync-public-packages.yaml" \
    --limit 1 \
    --json status,conclusion \
    --jq '.[0] | .status + ":" + .conclusion' 2>/dev/null || echo "unknown:")

  STATUS="${SYNC_STATUS%%:*}"
  CONCLUSION="${SYNC_STATUS##*:}"

  if [[ "$STATUS" == "completed" ]]; then
    if [[ "$CONCLUSION" == "success" ]]; then
      info "sync completed successfully"
      break
    else
      die "sync workflow failed (conclusion: $CONCLUSION)"
    fi
  fi

  ATTEMPTS=$((ATTEMPTS + 1))
  echo "  sync status: $STATUS (attempt $ATTEMPTS/$MAX_ATTEMPTS)"
  sleep 10
done

[[ $ATTEMPTS -lt $MAX_ATTEMPTS ]] || die "timed out waiting for sync"

# --- Verify remote is up to date ---
REMOTE_VERSION=$(gh api "repos/$PUBLIC_REPO/contents/pyproject.toml" --jq '.content' | base64 -d | grep "^version" | sed 's/version = "\(.*\)"/\1/')
[[ "$REMOTE_VERSION" == "$CURRENT_VERSION" ]] || die "remote version ($REMOTE_VERSION) != local ($CURRENT_VERSION) — sync may not have completed"

# --- Create release ---
info "creating release $TAG on $PUBLIC_REPO"
gh release create "$TAG" \
  --repo "$PUBLIC_REPO" \
  --title "$TAG" \
  --notes "Release $CURRENT_VERSION" \
  --latest

info "release created — PyPI publish workflow will trigger automatically"
info "monitor: gh run list --repo $PUBLIC_REPO --limit 3"
