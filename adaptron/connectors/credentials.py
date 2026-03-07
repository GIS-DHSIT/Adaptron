"""Credential resolver with support for env vars, AWS Secrets Manager, and Azure Key Vault."""
from __future__ import annotations

import json
import os
from typing import Any

from adaptron.connectors.models import CredentialConfig


class CredentialResolver:
    """Resolves credentials from multiple sources in priority order."""

    def resolve(self, config: CredentialConfig | None) -> dict[str, Any]:
        """Resolve credentials from the given config.

        Priority order:
        1. None config -> {}
        2. Direct username/password
        3. Environment variable -> connection_string
        4. AWS Secrets Manager
        5. Azure Key Vault
        """
        if config is None:
            return {}

        # Direct credentials
        if config.username is not None or config.password is not None:
            return {"username": config.username, "password": config.password}

        # Environment variable
        if config.env_var is not None:
            value = os.environ.get(config.env_var)
            if value is None:
                raise ValueError(
                    f"Environment variable '{config.env_var}' is not set"
                )
            return {"connection_string": value}

        # AWS Secrets Manager
        if config.aws_secret is not None:
            return self._resolve_aws(config.aws_secret)

        # Azure Key Vault
        if config.azure_vault is not None:
            return self._resolve_azure(config.azure_vault)

        return {}

    def _resolve_aws(self, secret_name: str) -> dict[str, Any]:
        """Resolve credentials from AWS Secrets Manager."""
        try:
            import boto3  # noqa: F811
        except ImportError:
            raise RuntimeError(
                "boto3 is required for AWS Secrets Manager support. "
                "Install it with: pip install boto3"
            )

        client = boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=secret_name)
        secret_string = response["SecretString"]
        return json.loads(secret_string)

    def _resolve_azure(self, vault_url: str) -> dict[str, Any]:
        """Resolve credentials from Azure Key Vault."""
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
        except ImportError:
            raise RuntimeError(
                "azure-identity and azure-keyvault-secrets are required for "
                "Azure Key Vault support. Install them with: "
                "pip install azure-identity azure-keyvault-secrets"
            )

        # Parse secret name from vault URL
        # Expected format: https://<vault-name>.vault.azure.net/secrets/<secret-name>
        parts = vault_url.rstrip("/").split("/")
        secret_name = parts[-1]

        # Extract base vault URL (everything before /secrets/)
        vault_base_url = vault_url.split("/secrets/")[0]

        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=vault_base_url, credential=credential)
        secret = client.get_secret(secret_name)
        return {"password": secret.value}
