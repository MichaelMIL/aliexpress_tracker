# Changelog

## v1.07.00 - 2025-11-19

- 0f3fec5 Add colored tracking badges
## v1.06.00 - 2025-11-19

- f7b0848 chore: bump version to v1.05.01
- 5150e32 Highlight version badge when update available
## v1.05.00 - 2025-11-19

- e4e7cc1 Extend release script to publish GitHub releases
## v1.04.00 - 2025-11-19

- 06fcba2 Link version badge and automate release notes
Entries are automatically prepended by `scripts/release.sh`.

## Unreleased

- **Fix**: Fixed cURL parser to properly extract cookies from `-b` or `--cookie` flags in addition to Cookie headers.
- **Fix**: Fixed "Hide Delivered" checkbox functionality to properly filter out delivered orders from the table.
- Enhanced `scripts/release.sh` to automatically capture commit history and prepend release notes to `CHANGELOG.md`.
- Added `.cursor/rules` to enforce documenting changes in `CHANGELOG.md` prior to every commit.
- Made the `version-badge` in the header a link to the GitHub repository.
- Updated `scripts/release.sh` to create a GitHub release via `gh release create` (when the GitHub CLI is available) after tagging and pushing.
- Added client-side version checking that compares the local build with the latest version on GitHub and highlights the badge when an update is available.
- Added color-coded dots next to tracking numbers so identical tracking numbers share the same color for quick visual grouping.
- Improved the tracking color generator to vary saturation/lightness for more noticeable differences between similar tracking numbers.
- Display tracking numbers inside colored badges instead of dots for clearer grouping.
