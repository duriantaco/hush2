from __future__ import annotations

import click


@click.command("doctor")
@click.option("--repair", is_flag=True, help="Repair recoverable corruption in-place.")
@click.option(
    "--force",
    is_flag=True,
    help="Allow destructive cleanup when a legacy vault has no readable records.",
)
@click.pass_context
def doctor_cmd(ctx, repair, force):
    from hush2.cli import _open_vault_raw
    from hush2.utils.exit_codes import AUTH_FAILED, ERROR, USER_ERROR

    vault, console = _open_vault_raw(ctx)
    try:
        health = vault.inspect_health()

        if repair:
            try:
                repair_result = vault.repair(force=force)
            except ValueError as exc:
                if str(exc) == "bad_key":
                    console.error(
                        "Cannot repair because the provided password/key is incorrect."
                    )
                    ctx.exit(AUTH_FAILED)
                    return
                if str(exc) == "ambiguous":
                    console.error(
                        "Legacy vault contains only unreadable records. "
                        "Re-run with --repair --force if you want to drop them."
                    )
                    ctx.exit(USER_ERROR)
                    return
                raise
            except RuntimeError:
                console.error("Repair did not complete cleanly.")
                ctx.exit(ERROR)
                return

            health_after = vault.inspect_health()
            if ctx.obj.get("json", False):
                console.print_json({"health": health_after, "repair": repair_result})
                return

            _print_health(console, health_after)
            _print_repair_result(console, repair_result, False)
            return

        _print_health(console, health)

        if health["status"] == "bad_key":
            ctx.exit(AUTH_FAILED)
        elif health["status"] != "ok":
            ctx.exit(ERROR)
    finally:
        vault.close()


def _print_health(console, health: dict) -> None:
    if console.mode.value == "json":
        console.print_json(health)
        return

    status = health["status"]
    if status == "ok":
        console.success("Vault is healthy.")
    elif status == "legacy_unverified":
        console.warn("Vault is readable but missing verification metadata.")
    elif status == "corrupted":
        console.error("Vault contains unreadable records but can be repaired.")
    elif status == "ambiguous":
        console.error(
            "Vault contains only unreadable legacy records. "
            "This may be a wrong password or unrecoverable corruption."
        )
    else:
        console.error("Provided password/key does not authenticate this vault.")

    rows = []
    for name in health["current"]["corrupted"]:
        rows.append(["current", name, "-"])
    for entry in health["history"]["corrupted"]:
        rows.append(["history", entry["name"], str(entry["version"])])

    if rows:
        console.print_table(
            ["Section", "Secret", "Version"],
            rows,
            title="Unreadable Records",
        )

    if status in {"ok", "legacy_unverified"}:
        console.info(
            f"Current secrets: {len(health['current']['decryptable'])}, "
            f"history entries: {len(health['history']['decryptable'])}"
        )


def _print_repair_result(console, repair_result: dict, use_json: bool) -> None:
    if use_json:
        console.print_json(repair_result)
        return

    console.success(
        f"Repair complete ({repair_result['status_before']} -> {repair_result['status_after']})."
    )
    if repair_result["restored_current"]:
        restored = ", ".join(
            f"{entry['name']}<=v{entry['from_version']}"
            for entry in repair_result["restored_current"]
        )
        console.info(f"Restored current secrets: {restored}")
    if repair_result["removed_current"]:
        console.warn(
            f"Removed unreadable current secrets: {', '.join(repair_result['removed_current'])}"
        )
    if repair_result["removed_history"]:
        console.warn(
            "Removed unreadable history entries: "
            + ", ".join(
                f"{entry['name']}@v{entry['version']}"
                for entry in repair_result["removed_history"]
            )
        )
    if repair_result["initialized_verifier"]:
        console.info("Initialized verification metadata for this vault.")
