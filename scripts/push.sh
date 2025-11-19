#!/bin/bash
set -euo pipefail

VERSION_FILE="VERSION"

if [[ ! -f "$VERSION_FILE" ]]; then
  echo "VERSION file not found."
  exit 1
fi

current_version=$(cat "$VERSION_FILE" | tr -d '\n')
IFS='.' read -r major minor patch <<< "$current_version"

patch=$((10#$patch + 1))
patch=$(printf "%02d" "$patch")

new_version="${major}.${minor}.${patch}"
echo "$new_version" > "$VERSION_FILE"

git add "$VERSION_FILE"
git add -A

git commit -m "chore: bump version to v${new_version}"

current_branch=$(git rev-parse --abbrev-ref HEAD)
git push origin "$current_branch"

