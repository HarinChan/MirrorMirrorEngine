import os
import re
from dotenv import load_dotenv
from .service.azure_keyvault_service import AzureKeyVaultService as azkv_service

load_dotenv()

class Config:
    """
    Add any additional configuration variables to the  `settings` dictionary.
    """
    settings = {}
    @staticmethod
    def set_variable(name: str, value: str):
        """
            Set an environment variable (for testing or dynamic config)
            Set for the following only:
                `settings` dictionary
                `keyvault` tryset if can
            Does not alter environmental variable.
        """
        
        settings[name] = value
        azkv_service.update_secret(name,value)

    @staticmethod
    def get_variable(name, default=None):
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
        if name in settings:
            return settings[name]
        if azkv_service.get_credential() is not None:
            variable = azkv_service.get_secret(name, None)
            if variable:
                return variable
        raise EnvironmentError(f"Missing required environment variable: '{name}'")