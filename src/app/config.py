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
        "dashboard_view_keys_whitelist": [ # must not include itself

        ],
        "dashboard_set_keys_whitelist": [  # must not include itself

        ]
    }

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
            - OS Environment
            - Config Files (if implemented in the future)
            - Azure Key Vault
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