import pytest
from src.app.service.azure_keyvault_service import AzureKeyVaultService

def test_azure_secret_rotation():
    # requires setting envirobmental variables for KEYVAULT_TENANT_ID, KEYVAULT_CLIENT_ID, and KEYVAULT_CLIENT_SECRET
    # 1. Arrange
    test_name = "TestSecret"
    test_value = "Updated-Value-2026"
    
    # 2. Act
    AzureKeyVaultService.update_secret(test_name, test_value)
    retrieved_value = AzureKeyVaultService.get_secret(test_name)
    
    # 3. Assert (This is the "test" part)
    assert retrieved_value == test_value
    print(f"\n✅ Verified: {test_name} is now {retrieved_value}")