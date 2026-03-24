import os
import re
import json
import secrets
from dotenv import load_dotenv
from .service.azure_keyvault_service import AzureKeyVaultService as azkv_service
from .service.local_config_service import LocalConfigService

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

            "SQLCIPHER_KEY",

            "TRENDING_LOOKAHEAD_DAYS",
            "MEETING_MIN_DURATION_MINUTES",
            "MEETING_MAX_DURATION_MINUTES",
            "MEETING_MAX_ADVANCE_DAY",
            
            "ADMIN_DASHBOARD_ENABLED"
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

            "SQLCIPHER_KEY",

            "TRENDING_LOOKAHEAD_DAYS",
            "MEETING_MIN_DURATION_MINUTES",
            "MEETING_MAX_DURATION_MINUTES",
            "MEETING_MAX_ADVANCE_DAY",
            
            "ADMIN_DASHBOARD_ENABLED"
        ],
        "KEYVAULT_WRITE_BLACKLIST": [
            "SQLCIPHER_KEY",  # This is a critical secret that should not be stored
            "JWT_SECRET_KEY",  # Auto-generated and stored locally only
            "FLASK_SECRET_KEY",  # Auto-generated and stored locally only
            "ADMIN_DASHBOARD_ENABLED",  # Security setting: only from .env, must not persist
            # key values for keyvault identity.
            "KEYVAULT_CLIENT_ID",
            "KEYVAULT_CLIENT_SECRET",
            "KEYVAULT_TENANT_ID",
        ],
        # Set up keys
        "SUGGESTED_SETUP_KEYs": [ # must be different from required keys
            "WEBEX_ACCESS_TOKEN",
            "WEBEX_CLIENT_ID",
            "WEBEX_CLIENT_SECRET",
            "WEBEX_REDIRECT_URI",

            "KEYVAULT_CLIENT_ID",
            "KEYVAULT_CLIENT_SECRET",
            "KEYVAULT_TENANT_ID",
        ],
        "REQUIRED_SETUP_KEYs": [
            "SQLCIPHER_KEY",
        ],
        "HASHABLE_SETUP_KEYs": [
            "SQLCIPHER_KEY",
        ],
        "INITIAL_SETUP_KEY": "MirrorMirrorSetUpKey",
        "APPDATA_FOLDER": os.path.join((os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or os.path.expanduser("~/.config")), "MirrorMirrorEngine")
    }

    @staticmethod
    def _generate_secret(length: int = 32) -> str:
        """
        Generate a cryptographically secure random secret.
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def factory_reset():
        """
        Resets all configuration to default values. This is a destructive action and should be used with caution.
        It will clear all variables from the settings dictionary, Azure Key Vault, and SQLCipher, effectively returning the application to its initial state.
        """
        # Clear settings dictionary (except for the whitelists and initial setup key)
        keys_to_delete = [
            "safe_get_keys_whitelist",
            "safe_set_keys_whitelist", 
            "KEYVAULT_WRITE_BLACKLIST", 
            "SUGGESTED_SETUP_KEYs", 
            "REQUIRED_SETUP_KEYs", 
            "HASHABLE_SETUP_KEYs", 
            "INITIAL_SETUP_KEY",
        ]
        
        for key_list_name in keys_to_delete:
            key_list = Config.settings.get(key_list_name, [])
            for key in key_list:
                if key in Config.settings:
                    del Config.settings[key]
        if "ADMIN_ACCOUNTS" in Config.settings:
            del Config.settings["ADMIN_ACCOUNTS"]
        
        print("Config settings reset to default (whitelists and initial setup key preserved).")

    @staticmethod
    def initial_setup_completed() -> bool:
        """
        Checks if the initial setup is completed by verifying that all 
        required keys are set and the admin account is valid.
        """
        missing_items = []

        # 1. Check all standard required keys
        for key in Config.settings.get("REQUIRED_SETUP_KEYs", []):
            try:
                value = Config.get_variable(key, "")
                if not value:
                    missing_items.append(f"Missing required variable: '{key}'")
            except EnvironmentError:
                missing_items.append(f"Environment error fetching: '{key}'")

        # 2. Specific check for admin account existence and format
        admin_accounts_raw = Config.get_variable("ADMIN_ACCOUNTS", "")
        
        if not admin_accounts_raw:
            missing_items.append("Missing variable: 'ADMIN_ACCOUNTS'")
        else:
            try:
                admin_account_dict = json.loads(admin_accounts_raw)
                if not isinstance(admin_account_dict, dict) or len(admin_account_dict) == 0:
                    missing_items.append("Invalid state: 'ADMIN_ACCOUNTS' is empty or not a dictionary")
            except json.JSONDecodeError:
                missing_items.append("Format error: 'ADMIN_ACCOUNTS' contains invalid JSON")

        # 3. Report and Return
        if missing_items:
            print("\n--- [MirrorMirror Engine] Initial Setup Incomplete ---")
            for item in missing_items:
                print(f" • {item}")
            print("------------------------------------------------------\n")
            return False

        return True

    @staticmethod
    def get_all_safe_variables(ignore_azure: bool=False, ignore_sqlcipher: bool=False) -> dict:
        """
            Get all variables in the safe get whitelist with their values.
        """
        safe_vars = {}
        for key in Config.settings["safe_get_keys_whitelist"]:
            if Config.get_variable(key, "", ignore_azure, ignore_sqlcipher) != "":
                safe_vars[key] = Config.get_variable(key, "", ignore_azure, ignore_sqlcipher)
        return safe_vars

    @staticmethod
    def safe_get_variable(name:str, default=None, ignore_azure: bool=False, ignore_sqlcipher: bool=False) -> str:
        """
            A safe version of get_variable that returns None instead of throwing an error if the variable is not found.
        """
        if name not in Config.settings["safe_get_keys_whitelist"]:
            print(f"Attempted to access variable '{name}' which is not in the safe get whitelist. Returning default value.")
            return default
        return Config.get_variable(name, default, ignore_azure, ignore_sqlcipher)

    @staticmethod
    def safe_set_variable(name: str, value: str, ignore_azure: bool=False, ignore_sqlcipher: bool=False) -> bool:
        """
            A safe version of set_variable that only allows setting variables in the whitelist and does not throw an error if the variable is not in the whitelist.
        """
        if name not in Config.settings["safe_set_keys_whitelist"]:
            print(f"Attempted to set variable '{name}' which is not in the safe set whitelist. Ignoring.")
            return False
        Config.set_variable(name, value, ignore_azure, ignore_sqlcipher)
        return True

    @staticmethod
    def set_variable(name: str, value: str, ignore_azure: bool=False, ignore_sqlcipher: bool=False):
        """
            Set an environment variable (for testing or dynamic config)
            Set for the following only:
                `settings` dictionary
                `keyvault` tryset if can
            Does not alter environmental variable.
        """
        if name == "FERNET_KEY":
            Config.settings[name] = Fernet.generate_key().decode()
        else:
            Config.settings[name] = value
        if not ignore_azure:
            if name in Config.settings["KEYVAULT_WRITE_BLACKLIST"]:
                print(f"Attempted to set variable '{name}' which is in the Key Vault write blacklist. Skipping writing to Key Vault.")
            else:
                azkv_service.update_secret(name,value)
        if not ignore_sqlcipher:
            LocalConfigService.set_val(name, value)

    @staticmethod
    def get_variable(name:str, default=None, ignore_azure: bool=False, ignore_sqlcipher: bool=False) -> str:
        """
            Get the environment variable.
            Try to retrieve environmental variables in the following order:
            1. OS Environment
            2. SQLCipher encrypted database
            3. Config.py `settings` dictionary
            4. Azure Key Vault (if not ignored and credentials are set)
            5. Auto-generate for JWT_SECRET_KEY and FLASK_SECRET_KEY if not found
            Returns the default value if the variable is not found in any source and default is provided.
            Raises an error if the variable is required but not found and no default is provided
        """
        
        variable = os.getenv(name, None)
        if variable:
            return variable
        if not ignore_sqlcipher:
            variable = LocalConfigService.get_val(name)
            if variable:
                return variable
        if name in Config.settings:
            return Config.settings[name]
        if not ignore_azure:
            if azkv_service.get_credential() is not None:
                variable = azkv_service.get_secret(name, None)
                if variable:
                    return variable
        
        # Auto-generate secret keys if not found
        if name in ["JWT_SECRET_KEY", "FLASK_SECRET_KEY"]:
            generated_secret = Config._generate_secret()
            Config.set_variable(name, generated_secret, ignore_azure=True, ignore_sqlcipher=False)
            return generated_secret
        
        if default is not None:
            return default
        raise EnvironmentError(f"Missing required environment variable: '{name}'")
