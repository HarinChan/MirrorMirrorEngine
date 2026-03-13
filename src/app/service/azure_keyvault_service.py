import os
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient
from ..helper import PenpalsHelper as helper
import re

# 1. Provide the Vault URI (you can also store this in an environment variable)
VAULT_URL = "https://mirrormirrorvault.vault.azure.net/"


class AzureKeyVaultService:
    """
    Service class to interact with Azure Key Vault for secret management.
    If Azure Key Vault credentials are not set, it will log a warning and return default values for secrets and will not throw any warnings.
    """

    def sanitize_name(name: str) -> str:
        name = re.sub(r'[_ ]', '-', name)
        name = re.sub(r'[^a-zA-Z0-9-]', '', name)
        name = name.strip('-')
        return name

    def get_credential():
        tenant_id=helper.get_env_variable("KEYVAULT_TENANT_ID",""),
        client_id=helper.get_env_variable("KEYVAULT_CLIENT_ID",""),
        client_secret=helper.get_env_variable("KEYVAULT_CLIENT_SECRET","")
        if not tenant_id or not client_id or not client_secret:
            print("WARNING: Azure Key Vault credentials not fully set. Secrets will not be accessible.")
            return None
        return ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )

    @staticmethod
    def get_secret(secret_name: str, default_value=None):
        secret_name = AzureKeyVaultService.sanitize_name(secret_name)
        credential = AzureKeyVaultService.get_credential()
        if credential is None:
            print("WARNING: Azure Key Vault credentials not set. Returning default value.")
            return default_value
        client = SecretClient(vault_url=VAULT_URL, credential=credential)
        try:
            # 3. Fetch the secret by its name
            retrieved_secret = client.get_secret(secret_name)
            return retrieved_secret.value
        except Exception as e:
            print(f"Failed to fetch secret: {e}")
            return default_value

    @staticmethod
    def update_secret(name: str, value: str):
        name = AzureKeyVaultService.sanitize_name(name)
        credential = AzureKeyVaultService.get_credential()
        if credential is None:
            print("WARNING: Azure Key Vault credentials not set. Cannot update secret.")
            return
        client = SecretClient(vault_url=VAULT_URL, credential=credential)

        print(f"Updating secret '{name}'...")
        
        new_secret = client.set_secret(name, value)

        print(f"Success! Secret '{new_secret.name}' set to new value.")
        print(f"New Version ID: {new_secret.properties.version}")