# Changelog

## v1.04.00 - 2025-11-19

- 06fcba2 Link version badge and automate release notes
Entries are automatically prepended by `scripts/release.sh`.

## Unreleased

- Enhanced `scripts/release.sh` to automatically capture commit history and prepend release notes to `CHANGELOG.md`.
- Added `.cursor/rules` to enforce documenting changes in `CHANGELOG.md` prior to every commit.
- Made the `version-badge` in the header a link to the GitHub repository.
