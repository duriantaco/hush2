# Contributing

Thanks for contributing to `hush2`.

## Development Setup

`hush2` targets Python 3.10+.

Create a virtual environment, then install the package in editable mode with the dev dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

Run the full test suite before opening a pull request:

```bash
pytest -q
```

## Project Standards

- Keep product and security claims aligned with the actual code. Do not describe `hush2` as stronger or broader than it is.
- Add or update tests for behavior changes, especially around vault unlock, command execution, masking, backup/restore, and audit behavior.
- Prefer focused changes over broad refactors during early development.
- Preserve the current threat-model caveats:
  - `run` and `NAME -- CMD` inject real secrets into the child process environment.
  - output masking reduces accidental disclosure in terminal output, but it is not process isolation.
  - `get`, `export`, and `--no-mask` intentionally reveal secret values.

## Pull Requests

Before opening a pull request:

- run `pytest -q`
- update `README.md` if the user-facing behavior changed
- update `SECURITY.md` if the security boundary changed
- update `CHANGELOG.md` for notable user-facing changes

Use Conventional Commit messages for merged changes whenever possible. `release-please` uses them to decide version bumps and release notes:

- `feat:` for user-facing features
- `fix:` for bug fixes
- `docs:` for documentation changes
- add `!` or a `BREAKING CHANGE:` footer for breaking changes

Short, imperative commit subjects are still preferred.

## Versioning And Releases

`hush2` uses semantic versioning once releases are tagged.

`release-please` now manages version bumps, changelog updates, and release PRs for normal development on `main`.

In normal use:

1. Merge changes with Conventional Commit messages.
2. Let `release-please` open the release PR.
3. Merge the release PR to cut the next version and GitHub release.

Manual version edits should be reserved for exceptional cases such as repository bootstrapping or repairing a bad release.
