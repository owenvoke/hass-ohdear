# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com), and this project adheres to [Semantic Versioning](https://semver.org).

## Unreleased

### Added
- Monitor several sites from one Oh Dear account, each added as a site subentry
- Choose sites from a list instead of entering their IDs
- Re-authentication when the API token stops working
- `summary` and `latest_run_ended_at` attributes on check sensors

### Changed
- Require Home Assistant 2026.9 or later
- Existing entries are merged into one entry per API token, keeping entity IDs and history
- Sensors are only created for checks the site has
- Check sensors are unavailable while their check is disabled, instead of reporting `unavailable` as a state

### Fixed
- Network errors in the config flow showed an unknown error
- Update failures are now reported to Home Assistant, which retries them

## v0.1.11 - 2024-07-16

### Fixed
- Resolve invalid `timedelta`
- Resolve using seconds instead of minutes for `timedelta`

## v0.1.10 - 2023-11-01

### Fixed
- Resolve use of translation strings

## v0.1.9 - 2023-11-01

### Fixed
- Ensure that updates to configuration are actually applied

## v0.1.8 - 2023-10-20

### Fixed
- Ensure only the current config entry is removed

## v0.1.7 - 2023-07-05

### Fixed
- Resolve invalid return type

## v0.1.6 - 2023-07-05

### Added
- Add support to update interval

## v0.1.5 - 2022-11-07

### Changed
- Remove unnecessary logging

### Fixed
- Resolve undefined key

## v0.1.4 - 2022-11-07

### Added
- Allow customising the scan interval (default is every 5 minutes)

## v0.1.3 - 2022-11-07

### Fixed
- Resolve issues with setting devices to unavailable

## v0.1.2 - 2022-11-07

### Added
- Add service device information

## v0.1.1 - 2022-11-06

### Changed
- Use unique entity name

## v0.1.0 - 2022-11-06

### Added
- Initial release
