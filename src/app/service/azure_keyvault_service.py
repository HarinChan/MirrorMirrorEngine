import os
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient

# 1. Provide the Vault URI (you can also store this in an environment variable)
VAULT_URL = "https://mirrormirrorvault.vault.azure.net/"


class AzureKeyVaultService:

    def get_credential():
        return ClientSecretCredential(
            tenant_id=os.getenv("KEYVAULT_TENANT_ID"),
            client_id=os.getenv("KEYVAULT_CLIENT_ID"),
            client_secret=os.getenv("KEYVAULT_CLIENT_SECRET")
        )

    @staticmethod
    def get_secret(secret_name, default_value=None):
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
    def update_secret(name, value):
        credential = AzureKeyVaultService.get_credential()
        client = SecretClient(vault_url=VAULT_URL, credential=credential)

        print(f"Updating secret '{name}'...")
        
        new_secret = client.set_secret(name, value)

        print(f"Success! Secret '{new_secret.name}' set to new value.")
        print(f"New Version ID: {new_secret.properties.version}")


def main():
    update_secret_name = "TestSecret"
    update_secret_value = "This is a new value for the secret."
    AzureKeyVaultService.update_secret(update_secret_name, update_secret_value)
    print(AzureKeyVaultService.get_secret(update_secret_name))

if __name__ == "__main__":
    main()