# hush2

`hush2` is a local, agent-safe secrets runner for developers who live in the terminal.

It stores secrets in an AES-256-GCM encrypted SQLite vault, injects them into subprocesses as environment variables, masks them from command output by default, and includes recovery tooling when older vault data goes bad.

The sharpest use case is simple: run a deploy script, migration, test harness, or agent-written command with only the secrets it needs, without pasting values into prompts, shell history, or plaintext `.env` files.

## Why Use hush2

- Keep API keys, database URLs, and tokens out of prompts, shell history, and plaintext `.env` files.
- Run agent-written commands with secrets available at runtime instead of pasting values into chat.
- Inject only the requested secrets with `hush2 NAME -- cmd`, or inject the active vault with `hush2 run`.
- Mask secret values from child-process output by default.
- Scan your repository for real leaked secret values from your vault.
- Recover from older mixed-key corruption with `hush2 doctor`.

## Best For

- Solo developers and small teams working primarily from the terminal.
- AI-assisted or agent-driven workflows where command execution is common but secret handling is risky.
- Local development setups where you want explicit secret provenance and auditability.

`hush2` is not a hosted team secrets platform. It is a local developer tool focused on safe runtime injection, masking, scanning, and recovery on one machine.

## Features

- Local encrypted vault per project: `.hush2/envs/<env>/vault.db`
- Optional global vault: `~/.hush2/envs/<env>/vault.db`
- AES-256-GCM encryption at rest
- PBKDF2-HMAC-SHA256 key derivation with a per-vault salt
- Password lookup through the OS keychain when available
- `HUSH2_PASSWORD` fallback for CI, headless shells, or machines without keychain support
- Secret injection into subprocesses with stdout/stderr masking
- Secret history and rollback
- Secret tags and tag-filtered execution
- `.env` import and export
- Secret generation
- Audit log
- Exact-value secret scanning plus optional entropy detection
- Backup, restore, and vault repair diagnostics

## Install

From a local checkout today:

```bash
pipx install .
```

Or with `uv`:

```bash
uv tool install .
```

Or with plain `pip`:

```bash
python -m pip install .
```

For development:

```bash
python -m pip install -e '.[dev]'
```

## Quick Start

The core workflow is:

1. Create a vault for the current project.
2. Save the secrets the command actually needs.
3. Run the command through `hush2`.

Create a vault in your current project:

```bash
hush2 init
```

Add secrets:

```bash
hush2 set OPENAI_API_KEY sk-live-abc123
hush2 set DATABASE_URL postgres://user:pass@host/db --tag db --tag prod
```

Read or list them:

```bash
hush2 get OPENAI_API_KEY
hush2 list
hush2 list --tag prod
```

Run commands with secrets injected:

```bash
hush2 run ./deploy.sh
hush2 OPENAI_API_KEY DATABASE_URL -- python app.py
```

For agent-written commands, prefer the explicit pattern:

```bash
hush2 OPENAI_API_KEY -- python agent_task.py
```

That keeps secret selection narrow and makes provenance obvious in the audit log.

Check vault health:

```bash
hush2 doctor
```

## Trust Checklist

Before relying on `hush2` in a repo, do these once:

```bash
hush2 doctor
hush2 scan --staged
hush2 backup
```

- `doctor` confirms the vault is readable and authentication metadata is healthy.
- `scan --staged` checks staged changes for exact secret leaks from your vault.
- `backup` gives you a recoverable snapshot before larger migrations or imports.

## How hush2 Works

1. `hush2 init` creates a local vault in `.hush2/envs/default/` unless you pass `--env` or `--global`.
2. `hush2 set` encrypts the secret value and stores it in SQLite.
3. `hush2 run` or `hush2 NAME -- command` decrypts only the requested secrets for the child process.
4. Child process output is masked by default unless you opt out with `--no-mask`.
5. Named secret requests in the exec pattern are vault-only unless you explicitly pass `--allow-env-fallback`.
6. `hush2 doctor` can diagnose unreadable records and repair recoverable legacy corruption.

The combination that makes `hush2` distinctive is local encrypted storage plus explicit runtime injection plus default masking plus exact-value leak scanning.

## Common Commands

| Command | Description |
|---------|-------------|
| `init` | Create a new vault in the current project or globally |
| `set NAME [VALUE]` | Store or update a secret |
| `get NAME` | Print a secret value |
| `list` | List secrets |
| `list envs` | List available environments |
| `rm NAME [NAME...]` | Delete secrets |
| `run CMD...` | Run a command with all vault secrets injected |
| `NAME [NAME...] -- CMD` | Inject only specific secrets |
| `--allow-env-fallback NAME -- CMD` | Explicitly allow missing requested names to come from the parent environment |
| `import FILE` | Import `.env` values from a file |
| `import --stdin` | Import `.env` values from stdin |
| `import --from-env` | Import matching values from the current environment |
| `export` | Export secrets in `.env` format |
| `tag NAME TAG...` | Add tags to a secret |
| `untag NAME TAG...` | Remove tags from a secret |
| `history NAME` | Show previous versions of a secret |
| `rollback NAME --to N` | Restore an older version |
| `generate` | Generate passwords, tokens, keys, or UUIDs |
| `audit` | Show the audit log |
| `scan` | Scan files for exact secret leaks and optional high-entropy values |
| `backup [FILE]` | Write a vault backup file |
| `restore FILE` | Restore a backup into a vault |
| `doctor` | Diagnose vault health |
| `doctor --repair` | Repair recoverable legacy corruption |
| `completion bash|zsh|fish` | Emit shell completion scripts |

## Running Commands With Secrets

Inject every secret in the active vault:

```bash
hush2 run ./deploy.sh
```

Inject only named secrets:

```bash
hush2 OPENAI_API_KEY DATABASE_URL -- python app.py
```

Requested names in the `NAME -- CMD` pattern are resolved from the active vault by default. If a requested name is missing, `hush2` fails instead of silently falling back to the parent shell environment.

Inject secrets by tag:

```bash
hush2 --tag prod -- ./deploy.sh
hush2 run --tag db -- python migrate.py
```

If you intentionally want a requested name to come from the parent environment, opt in explicitly:

```bash
export TEMP_TOKEN=abc123
hush2 --allow-env-fallback TEMP_TOKEN -- python script.py
```

### Output Masking

Masking is enabled by default for `run` and the `NAME -- CMD` exec pattern.

```bash
hush2 run sh -c 'echo $OPENAI_API_KEY'
# [REDACTED]

hush2 run --mask-style partial sh -c 'echo $OPENAI_API_KEY'
# sk...23

hush2 run --mask-style hash sh -c 'echo $OPENAI_API_KEY'
# [sha:a2c62cb9]

hush2 run --no-mask sh -c 'echo $OPENAI_API_KEY'
# prints the real value
```

Use `--no-mask` only when you intentionally want the child process output to contain real secrets.

## Environments And Vault Scope

Create environment-specific vaults:

```bash
hush2 init --env staging
hush2 --env staging set API_KEY value
hush2 --env staging run ./deploy.sh
```

Create a global vault:

```bash
hush2 init --global
hush2 --global set SHARED_TOKEN value
```

Local vault lookup walks upward from the current working directory until it finds `.hush2/`, which makes nested project commands work as expected.

## Import And Export

Import from a `.env` file:

```bash
hush2 import .env
```

Import from stdin:

```bash
cat .env | hush2 import --stdin
```

Import from the current shell environment:

```bash
hush2 import --from-env --pattern '^(OPENAI|STRIPE|AWS_)'
```

Export in `.env` format:

```bash
hush2 export
hush2 export --env-file .env.secure
hush2 export --tag prod
```

This makes migration practical: you can adopt `hush2` without locking yourself into a proprietary format, and you can keep backups before larger changes.

## Secret History, Rollback, And Tags

Version history is recorded when you update a secret:

```bash
hush2 history OPENAI_API_KEY
hush2 rollback OPENAI_API_KEY --to 1
```

Tags can organize execution and listing:

```bash
hush2 set STRIPE_KEY sk-live-abc --tag payments --tag prod
hush2 tag DATABASE_URL db prod
hush2 list --tag prod
hush2 --tag prod -- ./deploy.sh
```

## Secret Generation

```bash
hush2 generate --type password --length 32
hush2 generate --type token --encoding hex --length 32
hush2 generate --type key
hush2 generate --type uuid
hush2 generate --type password --save SESSION_SECRET --tag app
```

## Scanning For Leaks

`hush2 scan` checks files for real secret values from your vault, which avoids many regex-based false positives.

```bash
hush2 scan
hush2 scan --path ./src
hush2 scan --staged
hush2 scan --entropy --threshold 4.5
```

If leaks are found, `scan` exits non-zero.

## Backup, Restore, And Repair

Create a backup:

```bash
hush2 backup
hush2 backup my-vault.bak
```

Restore a backup:

```bash
hush2 restore my-vault.bak
hush2 restore my-vault.bak --env staging
```

Diagnose and repair legacy corruption:

```bash
hush2 doctor
hush2 doctor --repair
hush2 doctor --repair --force
```

Repair behavior:

- If a current secret is unreadable but a previous version is still decryptable, `doctor --repair` restores the newest readable history entry.
- If unreadable records have no readable replacement, `doctor --repair --force` can remove them.
- If keychain storage is unavailable, restored or new vaults may require `HUSH2_PASSWORD` for future unlocks.

## CI And Headless Use

If the OS keychain is unavailable or you want deterministic non-interactive unlocks, set `HUSH2_PASSWORD`:

```bash
export HUSH2_PASSWORD=my-vault-password
hush2 run ./ci-script.sh
```

This is the current behavior in the codebase today and is required on systems where `keyring` cannot store or retrieve the vault password.

## Bringing It Into A Workflow

If you are evaluating `hush2`, start with one concrete flow instead of moving every secret at once:

1. Pick one command you already run locally, such as a deploy, migration, or integration test script.
2. Move only the secrets that command needs into `hush2`.
3. Run it with `hush2 NAME -- cmd` first, then expand to `hush2 run` if that repo benefits from full-vault injection.
4. Add `hush2 scan --staged` to your pre-commit or release routine.
5. Keep a fresh `hush2 backup` before bulk imports, environment migrations, or recovery operations.

## Security Notes

- Secrets are encrypted at rest with AES-256-GCM.
- Keys are derived from the vault password with PBKDF2-HMAC-SHA256 and a per-vault salt.
- Secret values are only decrypted when commands need them.
- `HUSH2_PASSWORD` is removed from child process environments before command execution.
- `get`, `export`, and `run --no-mask` intentionally reveal values when asked to do so.
- Requested names in `NAME -- CMD` are vault-only by default so secret provenance is explicit and auditable.
- Recovery tooling can salvage readable legacy data, but truly unreadable secrets cannot be reconstructed.
- `hush2` reduces accidental disclosure in local workflows, but it does not isolate child processes from secrets they are given.

## Project Docs

- See [CONTRIBUTING.md](CONTRIBUTING.md) for local setup, test expectations, and versioning policy.
- See [SECURITY.md](SECURITY.md) for the supported reporting process and the current security boundary.
- See [CHANGELOG.md](CHANGELOG.md) for the initial baseline and future release notes.
