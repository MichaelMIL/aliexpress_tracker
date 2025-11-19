# Changelog

## v1.05.00 - 2025-11-19

- e4e7cc1 Extend release script to publish GitHub releases
## v1.04.00 - 2025-11-19

- 06fcba2 Link version badge and automate release notes
Entries are automatically prepended by `scripts/release.sh`.

## Unreleased

- Enhanced `scripts/release.sh` to automatically capture commit history and prepend release notes to `CHANGELOG.md`.
- Added `.cursor/rules` to enforce documenting changes in `CHANGELOG.md` prior to every commit.
- Made the `version-badge` in the header a link to the GitHub repository.
- Updated `scripts/release.sh` to create a GitHub release via `gh release create` (when the GitHub CLI is available) after tagging and pushing.
- Added client-side version checking that compares the local build with the latest version on GitHub and highlights the badge when an update is available.
