import pytest
from src.app.config import Config
from src.app.service.local_config_service import LocalConfigService
import os

@pytest.fixture(scope="module", autouse=True)
def setup_sqlcipher():
    # Initialize sqlcipher and load existing config variables before tests
    # change appdata folder to local
    Config.settings["APPDATA_FOLDER"] = os.path.join(os.getcwd(), "test_appdata_folder")
    LocalConfigService.initialize_sqlcipher()
    yield
    # Cleanup after tests if needed

def test_sqlcipher_set_and_get():
    # Test setting and getting a variable through sqlcipher
    test_key = "TEST_SQLCIPHER_KEY"
    test_value = "test_value_123"
    
    LocalConfigService.set_val(test_key, test_value)
    retrieved_value = LocalConfigService.get_val(test_key)
    assert retrieved_value == test_value, "Sqlcipher get/set failed"