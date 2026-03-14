import os
import re
from dotenv import load_dotenv
from .service.azure_keyvault_service import AzureKeyVaultService as azkv_service

load_dotenv()

class Config:
    """
    Add any additional configuration variables to the  `settings` dictionary.
    """
    settings = {
        "safe_get_keys_whitelist": [ # must not include itself
            "JWT_SECRET_KEY",
            "FLASK_SECRET_KEY",

            "WEBEX_ACCESS_TOKEN",
            "WEBEX_CLIENT_ID",
            "WEBEX_CLIENT_SECRET",
            "WEBEX_REDIRECT_URI",
            
            "KEYVAULT_CLIENT_ID",
            "KEYVAULT_CLIENT_SECRET",
            "KEYVAULT_TENANT_ID",
        ],
        "safe_set_keys_whitelist": [  # must not include itself
            "JWT_SECRET_KEY",
            "FLASK_SECRET_KEY",
            
            "WEBEX_ACCESS_TOKEN",
            "WEBEX_CLIENT_ID",
            "WEBEX_CLIENT_SECRET",
            "WEBEX_REDIRECT_URI",

            "KEYVAULT_CLIENT_ID",
            "KEYVAULT_CLIENT_SECRET",
            "KEYVAULT_TENANT_ID",
        ]
    }

    @staticmethod
    def get_all_safe_variables() -> dict:
        """
            Get all variables in the safe get whitelist with their values.
        """
        return {key: Config.get_variable(key, "") for key in Config.settings["safe_get_keys_whitelist"]}

    @staticmethod
    def safe_get_variable(name:str, default=None, ignore_azure: bool=False) -> str:
        """
            A safe version of get_variable that returns None instead of throwing an error if the variable is not found.
        """
        if name not in Config.settings["safe_get_keys_whitelist"]:
            print(f"Attempted to access variable '{name}' which is not in the safe get whitelist. Returning default value.")
            return default
        return Config.get_variable(name, default, ignore_azure)

    @staticmethod
    def safe_set_variable(name: str, value: str, ignore_azure: bool=False) -> bool:
        """
            A safe version of set_variable that only allows setting variables in the whitelist and does not throw an error if the variable is not in the whitelist.
        """
        if name not in Config.settings["safe_set_keys_whitelist"]:
            print(f"Attempted to set variable '{name}' which is not in the safe set whitelist. Ignoring.")
            return False
        Config.set_variable(name, value, ignore_azure)
        return True

    @staticmethod
    def set_variable(name: str, value: str, ignore_azure: bool=False):
        """
            Set an environment variable (for testing or dynamic config)
            Set for the following only:
                `settings` dictionary
                `keyvault` tryset if can
            Does not alter environmental variable.
        """
        
        Config.settings[name] = value
        if not ignore_azure:
            azkv_service.update_secret(name,value)

    @staticmethod
    def get_variable(name:str, default=None, ignore_azure: bool=False) -> str:
        """
            Get the environment variable.
            Try to retrieve environmental variables in the following order:
            1. OS Environment
            2. Config
            3. Azure Key Vault (if not ignored and credentials are set)
            Returns the default value if the variable is not found in any source and default is provided.
            Raises an error if the variable is required but not found and no default is provided
        """
        
        variable = os.getenv(name, None)
        if variable:
            return variable
        if name in Config.settings:
            return Config.settings[name]
        if not ignore_azure:
            if azkv_service.get_credential() is not None:
                variable = azkv_service.get_secret(name, None)
                if variable:
                    return variable
        if default is not None:
            return default
        raise EnvironmentError(f"Missing required environment variable: '{name}'")