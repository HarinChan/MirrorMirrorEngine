## Development Notes

Python Version: 3.13

Required python libraries:
- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `database`

## Docker Notes

> To build image, run `docker build -t mirror_mirror_engine .`
> To view past images, run `docker images`
> Running the image `docker run -p 5000:5000 mirror_mirror_engine`

## Deploy on Azure 3

## Deploy on Azure 2
[CI/CD Turtorial](https://learn.microsoft.com/en-us/azure/deployment-environments/tutorial-deploy-environments-in-cicd-github)

- [x] 1.1 monitor registration using `az provider show -n Microsoft.DevCenter`
- [x] 1.2
- [x] 1.3
- [x] 1.4
- [x] 1.5
- [x] 1.6 monitor registration using `az provider show -n Microsoft.KeyVault`
- [x] 2.0

- [x] 3.1
- [x] 3.2
- [x] 3.3
- [x] 3.4
- [x] 3.5

- [x] Update Environments to match python flask
> - [x] Update `FunctionApp`
> - [x] Update `SandBox`
- [x] Update .github workflow to match python flask
> - [x] Check `bicep_arm.yml`
> - [x] Check `environment_config.yml`
> - [x] Update `environment_create.yml`
> - [x] Check `environment_delete.yml`
> - [x] Update `environment_update.yml`

- [x] 4.0
- [x] 5.1
- [x] 5.2



```powershell
az devcenter admin catalog create --name Environments --resource-group $env:AZURE_RESOURCE_GROUP --dev-center $env:AZURE_DEVCENTER --git-hub path="/Environments" branch="main" secret-identifier="https://$env:AZURE_KEYVAULT.vault.azure.net/secrets/pat" uri="https://github.com/HarinChan/MirrorMirrorEngine.git"

az devcenter catalog list --dev-center $env:AZURE_DEVCENTER --project $env:AZURE_PROJECT --output table

az devcenter admin catalog list --dev-center-name $env:AZURE_DEVCENTER --resource-group $env:AZURE_RESOURCE_GROUP --max-items --next-token

az devcenter admin catalog show --catalog-name Environments --dev-center $env:AZURE_DEVCENTER --resource-group $env:AZURE_RESOURCE_GROUP
```

```json
[
  {
    "connectionState": "Connected",
    "gitHub": {
      "branch": "main",
      "path": "/Environments",
      "secretIdentifier": "https://MirrorMirrorKeyVault.vault.azure.net/secrets/pat",
      "uri": "https://github.com/HarinChan/MirrorMirrorEngine.git"
    },

    "id": "/subscriptions/d4e2aa96-9aef-4cca-90b7-cf5f71b36665/resourceGroups/MirrorMirrorEngineResourceGroup/providers/Microsoft.DevCenter/devcenters/MirrorMirrorDevCenter/catalogs/Environments",
    "lastConnectionTime": "2026-02-04T22:00:15.7312418Z",
    "lastSyncStats": {
      "added": 2,
      "removed": 0,
      "syncedCatalogItemTypes": [
        "EnvironmentDefinition",
        "ImageDefinition",
        "DataPlatformFile"
      ],
      "synchronizationErrors": 0,
      "unchanged": 0,
      "updated": 0,
      "validationErrors": 0
    },
    "lastSyncTime": "2026-02-04T22:00:51.222878Z",
    "name": "Environments",
    "provisioningState": "Succeeded",
    "resourceGroup": "MirrorMirrorEngineResourceGroup",
    "syncState": "Succeeded",
    "systemData": {
      "createdAt": "2026-02-04T21:25:02.2984765Z",
      "createdBy": "zcabyht@ucl.ac.uk",
      "createdByType": "User",
      "lastModifiedAt": "2026-02-04T21:59:57.8118185Z",
      "lastModifiedBy": "zcabyht@ucl.ac.uk",
      "lastModifiedByType": "User"
    },
    "type": "microsoft.devcenter/devcenters/catalogs"
  }
]
```

#### Constants
###### Unique to HarinChan / Console output:
$env:MY_AZURE_ID="950826f0-bc3f-49c8-817b-0bc9b613d189"
$env:AZURE_SUBSCRIPTION_ID="d4e2aa96-9aef-4cca-90b7-cf5f71b36665"
$env:AZURE_TENANT_ID="1faf88fe-a998-4c5b-93c9-210a11d9a5c2"
or
$env:MY_AZURE_ID=$(az ad signed-in-user show --query id -o tsv)
$env:AZURE_SUBSCRIPTION_ID=$(az account show --query id --output tsv)
$env:AZURE_TENANT_ID=$(az account show --query tenantId --output tsv)

$env:AZURE_DEVCENTER_ID="/subscriptions/d4e2aa96-9aef-4cca-90b7-cf5f71b36665/resourceGroups/MirrorMirrorEngineResourceGroup/providers/Microsoft.DevCenter/devcenters/MirrorMirrorDevCenter"
$env:AZURE_DEVCENTER_PRINCIPAL_ID="c5767dca-bb5c-4807-8813-513727eb1a16"
$env:AZURE_PROJECT_ID="/subscriptions/d4e2aa96-9aef-4cca-90b7-cf5f71b36665/resourceGroups/MirrorMirrorEngineResourceGroup/providers/Microsoft.DevCenter/projects/MirrorMirrorEngineProject"
$env:AZURE_KEYVAULT_ID="/subscriptions/d4e2aa96-9aef-4cca-90b7-cf5f71b36665/resourceGroups/MirrorMirrorEngineResourceGroup/providers/Microsoft.KeyVault/vaults/MirrorMirrorKeyVault"

$env:DEV_AZURE_CLIENT_ID="32741620-abde-4dfe-82e8-9bf96489baa8"
$env:DEV_APPLICATION_ID="0e369113-75aa-4436-befa-ab0d9c4439dc"

$env:TEST_AZURE_CLIENT_ID="571e952e-8534-4d82-93ff-c33a0d2232d4"
$env:TEST_APPLICATION_ID="548e8297-155d-4707-aa82-4b6cdefb494b"

$env:PROD_AZURE_CLIENT_ID="f3d71bb9-4615-4f22-8c8b-7c7de7add9b9"
$env:PROD_APPLICATION_ID="feca61d5-0255-45b7-837e-5625526d20a0"

$env:DEV_SERVICE_PRINCIPAL_ID="2aac7ab4-b41a-42a6-aa4d-6c254a1a57bf"
$env:TEST_SERVICE_PRINCIPAL_ID="49ef5950-83d3-4944-a193-1e39ef8fe447"
$env:PROD_SERVICE_PRINCIPAL_ID="9b0d4806-b31d-4388-bef1-0a68a68bea5b"

###### Manual Constant:
$env:LOCATION="uksouth"
$env:AZURE_RESOURCE_GROUP="MirrorMirrorEngineResourceGroup"
$env:AZURE_DEVCENTER="MirrorMirrorDevCenter"
$env:AZURE_PROJECT="MirrorMirrorEngineProject"
$env:AZURE_KEYVAULT="MirrorMirrorKeyVault"

```powershell
$env:environment_rg=$(az devcenter dev environment show --name $env:ENVIRONMENT_NAME --dev-center $env:AZURE_DEVCENTER --project $env:AZURE_PROJECT --only-show-errors --query resourceGroupId --output tsv 2>&1)

$env:environment_rg=$(az devcenter dev environment create --name $env:ENVIRONMENT_NAME --environment-type $env:ENVIRONMENT_TYPE --dev-center $env:AZURE_DEVCENTER --project $env:AZURE_PROJECT --catalog-name $env:AZURE_CATALOG --environment-definition-name $env:AZURE_CATALOG_ITEM --parameters '{ \"name\": \"$env:ENVIRONMENT_NAME\" }' --only-show-errors --query resourceGroupId --output tsv 2>&1)

