"""Safe environment variable expansion — no shell invocation."""

from __future__ import annotations

import re


def expand_env_vars(s: str, env: dict[str, str]) -> str:
    """Expand $VAR and ${VAR} patterns using the given env dict.

    Does NOT invoke a shell. Missing variables are left as empty strings.
    """
    def replacer(match):
        name = match.group(1) or match.group(2)
        return env.get(name, "")

    return re.sub(r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)", replacer, s)
