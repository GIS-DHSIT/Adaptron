"""Tests for CredentialResolver."""
from __future__ import annotations

import json
import os
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from adaptron.connectors.credentials import CredentialResolver
from adaptron.connectors.models import CredentialConfig


@pytest.fixture
def resolver():
    return CredentialResolver()


def test_resolve_direct_credentials(resolver):
    config = CredentialConfig(username="admin", password="secret")
    result = resolver.resolve(config)
    assert result == {"username": "admin", "password": "secret"}


def test_resolve_env_var(resolver, monkeypatch):
    monkeypatch.setenv("MY_CONN_STR", "postgresql://localhost/db")
    config = CredentialConfig(env_var="MY_CONN_STR")
    result = resolver.resolve(config)
    assert result == {"connection_string": "postgresql://localhost/db"}


def test_resolve_env_var_missing_raises(resolver):
    config = CredentialConfig(env_var="NONEXISTENT_VAR_12345")
    # Make sure the var is truly not set
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="NONEXISTENT_VAR_12345"):
            resolver.resolve(config)


def test_resolve_none_returns_empty(resolver):
    result = resolver.resolve(None)
    assert result == {}


def test_resolve_aws_secret_mocked(resolver):
    secret_data = {"username": "db_user", "password": "db_pass"}
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps(secret_data)
    }

    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_client

    with patch.dict("sys.modules", {"boto3": mock_boto3}):
        config = CredentialConfig(aws_secret="my/secret")
        result = resolver.resolve(config)

    assert result == secret_data
    mock_boto3.client.assert_called_once_with("secretsmanager")
    mock_client.get_secret_value.assert_called_once_with(SecretId="my/secret")


def test_resolve_azure_vault_mocked(resolver):
    mock_secret = MagicMock()
    mock_secret.value = "azure_password_123"

    mock_secret_client_cls = MagicMock()
    mock_secret_client_instance = MagicMock()
    mock_secret_client_instance.get_secret.return_value = mock_secret
    mock_secret_client_cls.return_value = mock_secret_client_instance

    mock_credential_cls = MagicMock()

    # Create mock modules
    mock_azure = MagicMock()
    mock_identity = MagicMock()
    mock_identity.DefaultAzureCredential = mock_credential_cls
    mock_keyvault = MagicMock()
    mock_keyvault_secrets = MagicMock()
    mock_keyvault_secrets.SecretClient = mock_secret_client_cls

    modules = {
        "azure": mock_azure,
        "azure.identity": mock_identity,
        "azure.keyvault": mock_keyvault,
        "azure.keyvault.secrets": mock_keyvault_secrets,
    }

    with patch.dict("sys.modules", modules):
        config = CredentialConfig(
            azure_vault="https://myvault.vault.azure.net/secrets/my-secret"
        )
        result = resolver.resolve(config)

    assert result == {"password": "azure_password_123"}
    mock_secret_client_instance.get_secret.assert_called_once_with("my-secret")
