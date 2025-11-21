# Changelog

## v1.11.00 - 2025-11-21

- 2a6b850 chore: bump version to v1.10.01
- d647ba8 Fix Docker timezone configuration and healthcheck port
- 7ca75d2 Remove app_data.json from git tracking
## v1.10.00 - 2025-11-21

- e1ae953 Ensure auto_update_interval_hours is initialized in config.json
- 08a5adf Remove duplicate last_updates.json file
- 8883498 Move last update times to separate app_data.json file
- 1d452a5 Optimize tracking updates to deduplicate tracking numbers
- 72d6013 Add auto-update scheduler and last update time tracking
## v1.09.00 - 2025-11-21

- No commits recorded since the previous release.
## v1.08.00 - 2025-11-21

- ec3d2f9 Fix cURL parser to extract cookies from -b flag
- f5f7244 chore: bump version to v1.07.02
- 6180fd9 chore: bump version to v1.07.01
- de2c9bf Fix Hide Delivered checkbox functionality
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

- **Fix**: Configure Docker container timezone to use Asia/Jerusalem (fixes 2-hour time difference issue).
- **Fix**: Correct healthcheck port in docker-compose.yml from 8000 to 8004.
- **Fix**: Ensure `auto_update_interval_hours` is automatically initialized in `config.json` if missing (defaults to 6 hours).
- **Refactor**: Moved last update times from `config.json` to separate `app_data.json` file for better separation of configuration and runtime data.
- **Optimization**: Deduplicate tracking numbers before API calls to prevent duplicate requests when multiple orders share the same tracking number. This applies to both Cainiao and Doar Israel bulk updates and auto-updates.
- **Feature**: Added automatic background scheduler that updates both Cainiao and Doar Israel tracking every 6 hours (configurable via `auto_update_interval_hours` in `config.json`).
- **Feature**: Added "Cainiao last update" and "Doar Israel last update" time displays next to "Total Orders" in the UI.
- **Feature**: Last update times are now persistent in `config.json` and survive server restarts.
- **Feature**: Last update times automatically refresh when manual bulk updates are triggered or when auto-updates run.
- **Feature**: Update time display refreshes every minute and shows relative time (e.g., "5 min ago", "2h 30m ago").
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
