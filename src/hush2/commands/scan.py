from __future__ import annotations

from pathlib import Path

import click


@click.command("scan")
@click.option("--staged", is_flag=True, help="Only scan git staged files.")
@click.option("--path", "-p", "scan_path", default=None, help="Directory to scan.")
@click.option("--entropy", is_flag=True, help="Also flag high-entropy strings.")
@click.option("--threshold", default=4.5, type=float,
              help="Entropy threshold (default 4.5 bits/char).")
@click.pass_context
def scan_cmd(ctx, staged, scan_path, entropy, threshold):
    from hush2.cli import _open_vault
    from hush2.utils.exit_codes import USER_ERROR
    from hush2.utils.scanning import get_files_to_scan, scan_file

    vault, console = _open_vault(ctx)
    try:
        known_secrets = vault.get_all_secrets()
    finally:
        vault.close()

    scan_dir = Path(scan_path) if scan_path else None
    files = get_files_to_scan(path=scan_dir, staged_only=staged)

    if not files:
        console.info("No files to scan.")
        return

    all_findings = []
    for f in files:
        findings = scan_file(
            f,
            known_secrets=known_secrets,
            entropy_threshold=threshold,
            check_entropy=entropy,
        )
        all_findings.extend(findings)

    if not all_findings:
        console.success(f"Clean — scanned {len(files)} file(s), no issues found.")
        return

    if ctx.obj.get("json"):
        console.print_json([
            {
                "file": f.file,
                "line": f.line_number,
                "secret_name": f.secret_name,
                "kind": f.kind,
                "snippet": f.snippet,
            }
            for f in all_findings
        ])
    else:
        rows = []
        for f in all_findings:
            kind_label = f.kind
            name_label = f.secret_name or "(high entropy)"
            rows.append([f.file, str(f.line_number), name_label, kind_label, f.snippet[:60]])
        console.print_table(
            ["File", "Line", "Secret", "Type", "Snippet"],
            rows,
            title=f"Findings ({len(all_findings)} issues in {len(files)} files)",
        )

    ctx.exit(USER_ERROR)
