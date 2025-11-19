#!/bin/bash
set -euo pipefail

VERSION_FILE="VERSION"

if [[ ! -f "$VERSION_FILE" ]]; then
  echo "VERSION file not found."
  exit 1
fi

current_version=$(cat "$VERSION_FILE" | tr -d '\n')
IFS='.' read -r major minor patch <<< "$current_version"

minor=$((10#$minor + 1))
minor=$(printf "%02d" "$minor")
patch="00"

new_version="${major}.${minor}.${patch}"
echo "$new_version" > "$VERSION_FILE"

git add "$VERSION_FILE"
git add -A

git commit -m "chore: release v${new_version}"

tag_name="v${new_version}"
git tag -a "$tag_name" -m "Release ${new_version}" || {
  echo "Tag $tag_name already exists. Skipping tag creation."
}

current_branch=$(git rev-parse --abbrev-ref HEAD)
git push origin "$current_branch"
git push origin --tags

