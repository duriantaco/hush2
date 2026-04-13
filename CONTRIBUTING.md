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

Use short, imperative commit messages. Conventional Commits are welcome, but they are not required.

## Versioning And Releases

`hush2` uses semantic versioning once releases are tagged.

For now, versioning is manual. When preparing a release:

1. Update the version in `pyproject.toml`.
2. Update `src/hush2/__init__.py`.
3. Add release notes to `CHANGELOG.md`.
4. Tag the release in git.

Release automation is intentionally not configured yet. Until the repository, release channel, and publishing credentials are in place, manual versioning is lower risk than unverified automation.
