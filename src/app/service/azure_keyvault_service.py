import os
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient
import re

# 1. Provide the Vault URI (you can also store this in an environment variable)
VAULT_URL = "https://mirrormirrorvault.vault.azure.net/"


class AzureKeyVaultService:

    def sanitize_name(name: str) -> str:
        name = re.sub(r'[_ ]', '-', name)
        name = re.sub(r'[^a-zA-Z0-9-]', '', name)
        name = name.strip('-')
        return name

    def get_credential():
        return ClientSecretCredential(
            tenant_id=os.getenv("KEYVAULT_TENANT_ID"),
            client_id=os.getenv("KEYVAULT_CLIENT_ID"),
            client_secret=os.getenv("KEYVAULT_CLIENT_SECRET")
        )

    @staticmethod
    def get_secret(secret_name: str, default_value=None):
        secret_name = AzureKeyVaultService.sanitize_name(secret_name)
        credential = AzureKeyVaultService.get_credential()
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
        client = SecretClient(vault_url=VAULT_URL, credential=credential)

        print(f"Updating secret '{name}'...")
        
        new_secret = client.set_secret(name, value)

        print(f"Success! Secret '{new_secret.name}' set to new value.")
        print(f"New Version ID: {new_secret.properties.version}")