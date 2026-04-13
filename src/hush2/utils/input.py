"""User input helpers — hidden password input, stdin reading."""

from __future__ import annotations

import sys

import click


def read_password(prompt: str = "Password: ") -> str:
    """Read a password from the terminal with hidden input."""
    return click.prompt(prompt, hide_input=True, default="", show_default=False)


def read_secret_value(prompt: str = "Secret value: ") -> str:
    """Read a secret value from the terminal with hidden input."""
    return click.prompt(prompt, hide_input=True, default="", show_default=False)


def read_stdin() -> str:
    """Read all data from stdin."""
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read()
