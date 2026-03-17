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
    cursor = None

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
        LocalConfigService.conn = sqlite.connect(db_path)
        LocalConfigService.conn.execute(f"PRAGMA key = '{Config.get_variable('SQLCIPHER_KEY', 'TEST_SQLCIPHER_KEY', True, True)}'")
        
        # Use it like a standard SQL database
        LocalConfigService.cursor = LocalConfigService.conn.cursor()
        LocalConfigService.cursor.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)")
        LocalConfigService.conn.commit()
        LocalConfigService.sqlcipher_initialized = True

        # read all values from setting and load into sqlcipher
        for key, value in Config.settings.items():
            LocalConfigService.set_val(key, value)
            print(f"Loaded config variable '{key}' into sqlcipher.")
        print(f"Sqlcipher initialized at {db_path} and config variables loaded.")
        


    # Fast Set/Get
    @staticmethod
    def set_val(key: str, val: any):
        if not LocalConfigService.sqlcipher_initialized:
            LocalConfigService.initialize_sqlcipher()
        # Ensure the value is a string (or supported type)
        if not isinstance(val, (str, int, float, bytes, type(None))):
            val = json.dumps(val)
        LocalConfigService.cursor.execute("INSERT OR REPLACE INTO kv VALUES (?, ?)", (key, val))
        LocalConfigService.conn.commit()

    @staticmethod
    def get_val(key: str, default:str = None):
        if not LocalConfigService.sqlcipher_initialized:
           LocalConfigService.initialize_sqlcipher()
        LocalConfigService.cursor.execute("SELECT value FROM kv WHERE key = ?", (key,))
        result = LocalConfigService.cursor.fetchone()
        if result:
            return result[0]
        else:
            return default
