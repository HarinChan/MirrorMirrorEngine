from sqlcipher3 import dbapi2 as sqlite
import os
import json

# static service
class LocalConfigService:
    """
    Sqlcipher to persist a file based encrypted key-value store for config variables.
    """

    sqlcipher_initialized = False
    conn = None

    @staticmethod
    def initialize_sqlcipher():
        if LocalConfigService.sqlcipher_initialized:
            print("Sqlcipher already initialized, skipping.")
            return
        from ..config import Config
        
        # fetch patsh
        appdata_folder = Config.get_variable("APPDATA_FOLDER", "", True, True)
        os.makedirs(appdata_folder, exist_ok=True)
        db_path = os.path.join(appdata_folder, "config.db")
        
        # Connect and set the 'PRAGMA key' immediately
        LocalConfigService.conn = sqlite.connect(db_path, check_same_thread=False)
        LocalConfigService.conn.execute(f"PRAGMA key = '{Config.get_variable('SQLCIPHER_KEY', 'TEST_SQLCIPHER_KEY', True, True)}'")
        
        # Use it like a standard SQL database
        cursor = LocalConfigService.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)")
        LocalConfigService.conn.commit()
        LocalConfigService.sqlcipher_initialized = True

        # read all values from setting and load into sqlcipher
        items_to_load = Config.get_all_safe_variables(False, True) # Load hardcoded configs variabel and keyvault values
        for key, value in items_to_load.items():
            if LocalConfigService.get_val(key) is None: # Don't overwrite existing values in sqlcipher
                LocalConfigService.set_val(key, value)
                print(f"Loaded config variable '{key}' into sqlcipher.")
            else:
                print(f"Config variable '{key}' already exists in sqlcipher, skipping load.")
        print(f"Sqlcipher initialized at {db_path} and config variables loaded.")
        


    # Fast Set/Get
    @staticmethod
    def set_val(key: str, val: any):
        if not LocalConfigService.sqlcipher_initialized:
            LocalConfigService.initialize_sqlcipher()
        # Ensure the value is a string (or supported type)
        if not isinstance(val, (str, int, float, bytes, type(None))):
            val = json.dumps(val)
        cursor = LocalConfigService.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO kv VALUES (?, ?)", (key, val))
        LocalConfigService.conn.commit()

    @staticmethod
    def get_val(key: str, default:str = None):
        if not LocalConfigService.sqlcipher_initialized:
           LocalConfigService.initialize_sqlcipher()
        cursor = LocalConfigService.conn.cursor()
        cursor.execute("SELECT value FROM kv WHERE key = ?", (key,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            return default
    
    @staticmethod
    def delete_val(key: str):
        if not LocalConfigService.sqlcipher_initialized:
            LocalConfigService.initialize_sqlcipher()
        cursor = LocalConfigService.conn.cursor()
        cursor.execute("DELETE FROM kv WHERE key = ?", (key,))
        LocalConfigService.conn.commit()
    
    @staticmethod
    def delete_all():
        if not LocalConfigService.sqlcipher_initialized:
            LocalConfigService.initialize_sqlcipher()
        cursor = LocalConfigService.conn.cursor()
        cursor.execute("DELETE FROM kv")
        LocalConfigService.conn.commit()
