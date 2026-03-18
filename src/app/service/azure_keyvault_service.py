import os
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import re

# 1. Provide the Vault URI (you can also store this in an environment variable)
VAULT_URL = "https://mirrormirrorvault.vault.azure.net/"


class AzureKeyVaultService:
    """
    Service class to interact with Azure Key Vault for secret management.
    If Azure Key Vault credentials are not set, it will log a warning and return default values for secrets and will not throw any warnings.
    """

    static_credential = None
    get_credentials_attempt = 0
    max_credential_attempts = None

    @staticmethod
    def sanitize_name(name: str) -> str:
        name = re.sub(r'[_ ]', '-', name)
        name = re.sub(r'[^a-zA-Z0-9-]', '', name)
        name = name.strip('-')
        return name

    @staticmethod
    def refresh_config():
        AzureKeyVaultService.static_credential = None
        AzureKeyVaultService.get_credentials_attempt = 0
        AzureKeyVaultService.max_credential_attempts = None

    @staticmethod
    def get_credential():
        from ..config import Config

        # default credentials fetching
        if AzureKeyVaultService.static_credential != None:
            return AzureKeyVaultService.static_credential
        if AzureKeyVaultService.max_credential_attempts is None:
            AzureKeyVaultService.max_credential_attempts = Config.get_variable("KEYVAULT_MAX_CREDENTIAL_ATTEMPTS", 3, True, False)
        if AzureKeyVaultService.get_credentials_attempt >= AzureKeyVaultService.max_credential_attempts:
            # print("WARNING: Maximum attempts to get Azure Key Vault credentials reached. Returning None.")
            return None
        AzureKeyVaultService.get_credentials_attempt += 1

        # can attempt to fetch
        tenant_id=Config.get_variable("KEYVAULT_TENANT_ID","",True,False) # ignore azure but tries LocalConfigService
        client_id=Config.get_variable("KEYVAULT_CLIENT_ID","",True,False) # ignore azure but tries LocalConfigService
        client_secret=Config.get_variable("KEYVAULT_CLIENT_SECRET","",True,False) # ignore azure but tries LocalConfigService

        if not (tenant_id == "" or client_id=="" or client_secret==""):
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
        else:
            credential = DefaultAzureCredential() # will get the webapp's credential
        try:
            # Test if we can get a token (this will throw an error if credentials are not set)
            credential.get_token("https://vault.azure.net/.default")
            AzureKeyVaultService.static_credential = credential
            return credential
        except Exception as e:
            # print(f"WARNING: Azure Key Vault credentials not fully set. Secrets will not be accessible.")
            return None

    @staticmethod
    def get_secret(secret_name: str, default_value=None):
        secret_name = AzureKeyVaultService.sanitize_name(secret_name)
        credential = AzureKeyVaultService.get_credential()
        if credential is None:
            # print("WARNING: Azure Key Vault credentials not set. Returning default value.")
            return default_value
        client = SecretClient(vault_url=VAULT_URL, credential=credential)
        try:
            # 3. Fetch the secret by its name
            retrieved_secret = client.get_secret(secret_name)
            return retrieved_secret.value
        except Exception as e:
            # print(f"Failed to fetch secret '{secret_name}'. Returning default value {default_value}.")
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