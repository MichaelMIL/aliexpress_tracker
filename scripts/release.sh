#!/bin/bash
set -euo pipefail

VERSION_FILE="VERSION"
CHANGELOG_FILE="CHANGELOG.md"

if [[ ! -f "$VERSION_FILE" ]]; then
  echo "VERSION file not found."
  exit 1
fi

current_version=$(tr -d '\n' < "$VERSION_FILE")
IFS='.' read -r major minor patch <<< "$current_version"

minor=$((10#$minor + 1))
minor=$(printf "%02d" "$minor")
patch="00"

prev_tag=$(git describe --tags --abbrev=0 2>/dev/null || true)
if [[ -n "${prev_tag}" ]]; then
  changelog=$(git log --oneline "${prev_tag}"..HEAD)
else
  changelog=$(git log --oneline)
fi

if [[ -z "${changelog}" ]]; then
  formatted_changes="- No commits recorded since the previous release."
else
  formatted_changes=$(printf '%s\n' "$changelog" | sed 's/^/- /')
fi

release_date=$(date +%Y-%m-%d)
new_version="${major}.${minor}.${patch}"

release_notes_section=$(cat <<EOF
## v${new_version} - ${release_date}

${formatted_changes}

EOF
)

echo "$new_version" > "$VERSION_FILE"

existing_changelog=""
if [[ -f "$CHANGELOG_FILE" ]]; then
  existing_changelog=$(tail -n +2 "$CHANGELOG_FILE" 2>/dev/null || true)
fi

{
  echo "# Changelog"
  echo
  printf "%s" "$release_notes_section"
  if [[ -n "${existing_changelog}" ]]; then
    printf "%s\n" "$existing_changelog"
  fi
} > "$CHANGELOG_FILE"

echo "Release notes for v${new_version}:"
printf "%s\n" "$formatted_changes"

git add "$VERSION_FILE" "$CHANGELOG_FILE"
git add -A

git commit -m "chore: release v${new_version}"

tag_name="v${new_version}"
git tag -a "$tag_name" -m "Release ${new_version}" -m "${formatted_changes}" || {
  echo "Tag $tag_name already exists. Skipping tag creation."
}

current_branch=$(git rev-parse --abbrev-ref HEAD)
git push origin "$current_branch"
git push origin --tags

if command -v gh >/dev/null 2>&1; then
  release_body="$release_notes_section"
  echo "Creating GitHub release ${tag_name}..."
  gh release create "$tag_name" --title "$tag_name" --notes "$release_body" || {
    echo "Failed to create GitHub release via gh CLI."
  }
else
  echo "GitHub CLI (gh) not found; skipping GitHub release creation."
fi

