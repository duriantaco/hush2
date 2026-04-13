from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Finding:
    file: str
    line_number: int
    secret_name: str | None = None
    kind: str = "exact"
    snippet: str = ""


SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".woff2",
    ".ttf", ".eot", ".mp3", ".mp4", ".wav", ".avi", ".mov", ".pdf",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".jar", ".war", ".ear",
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe", ".bin",
}

SKIP_DIRS = {
    "node_modules", ".git", ".hush2", ".psst", "dist", "build",
    "__pycache__", ".venv", "venv", ".tox", ".eggs",
}

MAX_FILE_SIZE = 1_000_000


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq: dict[str, int] = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    length = len(s)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


def scan_file(
    path: Path,
    known_secrets: dict[str, str] | None = None,
    entropy_threshold: float = 4.5,
    check_entropy: bool = False,
    min_secret_length: int = 4,
) -> list[Finding]:
    findings: list[Finding] = []

    if path.suffix in SKIP_EXTENSIONS:
        return findings
    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return findings
    except OSError:
        return findings

    try:
        content = path.read_text(errors="ignore")
    except Exception:
        return findings

    for line_no, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue

        if known_secrets:
            for name, value in known_secrets.items():
                if len(value) >= min_secret_length and value in stripped:
                    findings.append(Finding(
                        file=str(path),
                        line_number=line_no,
                        secret_name=name,
                        kind="exact",
                        snippet=stripped[:120],
                    ))

        if check_entropy:
            for token in _extract_tokens(stripped):
                if len(token) >= 16 and shannon_entropy(token) >= entropy_threshold:
                    findings.append(Finding(
                        file=str(path),
                        line_number=line_no,
                        secret_name=None,
                        kind="entropy",
                        snippet=token[:80],
                    ))

    return findings


def _extract_tokens(line: str) -> list[str]:
    import re
    tokens = []
    for match in re.finditer(r"""(['"])([^'"]{16,})\1""", line):
        tokens.append(match.group(2))
    for match in re.finditer(r"[=:]\s*([A-Za-z0-9+/=_\-]{16,})", line):
        tokens.append(match.group(1))
    return tokens


def get_files_to_scan(
    path: Path | None = None,
    staged_only: bool = False,
) -> list[Path]:
    if staged_only:
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True, text=True, check=True,
            )
            return [Path(f) for f in result.stdout.strip().splitlines() if f]
        except Exception:
            return []

    if path:
        scan_dir = path
    else:
        scan_dir = Path.cwd()

    try:
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True, text=True, check=True,
            cwd=scan_dir,
        )
        files = [scan_dir / f for f in result.stdout.strip().splitlines() if f]
        return [f for f in files if _should_scan(f)]
    except Exception:
        pass

    files = []
    for f in scan_dir.rglob("*"):
        if f.is_file() and _should_scan(f):
            files.append(f)
    return files


def _should_scan(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if path.suffix in SKIP_EXTENSIONS:
        return False
    return True
