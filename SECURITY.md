# Security Policy

## Supported Versions

`hush2` is pre-1.0 software. Until `1.0.0`, only the latest code on the default branch should be considered supported for security fixes.

## Reporting A Vulnerability

Do not open a public issue for security-sensitive reports.

Use a private reporting channel first:

- GitHub private vulnerability reporting or a draft security advisory, if it is enabled for the repository
- otherwise, contact the maintainer privately before any public disclosure

If you are publishing this repository publicly, enable GitHub private vulnerability reporting before announcing the project.

## Security Boundary

`hush2` is a local encrypted secrets manager and runtime injector. It improves secret handling for local development and agent workflows, but it does not provide strong process isolation.

Current security properties:

- secret values are encrypted at rest with AES-256-GCM
- vault keys are derived from the vault password with PBKDF2-HMAC-SHA256 and a per-vault salt
- vault passwords may come from the OS keychain or from `HUSH2_PASSWORD`
- requested names in `NAME -- CMD` are vault-only by default unless `--allow-env-fallback` is passed
- command output is masked by default for `run` and the bare exec pattern

Current non-goals and limits:

- child processes still receive real secret values in their environment
- output masking is terminal hygiene, not a sandbox or exfiltration defense
- anyone who can unlock the vault and run `get`, `export`, or `run --no-mask` can intentionally reveal secrets
- corrupted legacy data can sometimes be repaired, but unreadable ciphertext cannot be reconstructed

Please keep reports scoped to what the code actually promises today.
