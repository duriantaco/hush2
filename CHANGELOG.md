# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and the project follows Semantic Versioning once releases are tagged.

## [0.1.1](https://github.com/duriantaco/hush2/compare/v0.1.0...v0.1.1) (2026-04-14)


### Bug Fixes

* harden vault import, masking, salt handling, and command launch errors ([ba4a8ae](https://github.com/duriantaco/hush2/commit/ba4a8aeddf52910381157b92a0a739ef1b855e25))


### Documentation

* sharpen hush2 positioning and onboarding ([28a01b1](https://github.com/duriantaco/hush2/commit/28a01b1682dc44ec68f368c258be2384aa83cd39))

## [Unreleased]

### Changed

- README positioning, install guidance, and onboarding flow now emphasize `hush2` as a local, agent-safe secrets runner for terminal workflows.
- Documentation now includes a trust checklist built around `doctor`, `scan --staged`, and `backup`.

### Fixed

- `.env` export and import now round-trip escaped values more reliably.
- Empty secret values no longer break output masking.
- Opening an existing vault now fails cleanly when the salt file is missing or invalid instead of silently recreating it.
- `run` and `NAME -- CMD` now report subprocess launch failures as CLI errors instead of surfacing raw exceptions.

## [0.1.0] - 2026-04-13

### Added

- Local and global encrypted vaults with environment-specific selection.
- Secret injection into child processes with default stdout and stderr masking.
- Tag-based execution and listing, secret history, rollback, generation, import, export, audit, scan, backup, restore, and shell completion commands.
- `doctor` diagnostics and repair tooling for legacy mixed-key corruption.
- Vault-authenticated unlock flow that fails closed on wrong passwords.

### Changed

- Requested names in the `NAME -- CMD` exec pattern are now vault-only by default.
- Parent-environment fallback for requested names now requires explicit `--allow-env-fallback`.
- Repository documentation now includes contribution guidance, security policy, and CI coverage.

### Fixed

- `scan` now exits non-zero when leaked secrets are found.
- `untag` no longer reports success when nothing was actually removed.
- restore flows now preserve unlockability more reliably on systems without working keychain storage.
