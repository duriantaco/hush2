from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from hush2.vault.crypto import derive_key, generate_salt
from hush2.vault.vault import Vault


TEST_PASSWORD = "test-password-for-hush2"


@pytest.fixture
def vault_salt():
    return generate_salt()


@pytest.fixture
def vault_key(vault_salt):
    return derive_key(TEST_PASSWORD, vault_salt)


@pytest.fixture
def vault_dir(tmp_path):
    d = tmp_path / ".hush2" / "envs" / "default"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def vault(vault_dir, vault_key, vault_salt):
    (vault_dir / "salt").write_bytes(vault_salt)
    v = Vault(vault_dir, vault_key)
    v.open()
    yield v
    v.close()


@pytest.fixture
def cli_runner():
    return CliRunner(mix_stderr=False)


@pytest.fixture
def cli_env(vault_dir, vault_salt):
    (vault_dir / "salt").write_bytes(vault_salt)
    key = derive_key(TEST_PASSWORD, vault_salt)
    v = Vault(vault_dir, key)
    v.open()
    v.close()
    return {"HUSH2_PASSWORD": TEST_PASSWORD}
