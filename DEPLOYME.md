## Development Notes

Python Version: 3.14

## Docker Notes (not even required)

> To build image, run `docker build -t mirror_mirror_engine .`
> To view past images, run `docker images`
> Running the image `docker run -p 5000:5000 mirror_mirror_engine`

## Deploy on Azure 3 - Webapp
yeah, this is much simpler.

#### Constants
```powershell
$env:MY_AZURE_ID=$(az ad signed-in-user show --query id -o tsv)
$env:AZURE_SUBSCRIPTION_ID=$(az account show --query id --output tsv)
$env:AZURE_TENANT_ID=$(az account show --query tenantId --output tsv)

$env:MY_AZURE_ID="950826f0-bc3f-49c8-817b-0bc9b613d189"
$env:AZURE_SUBSCRIPTION_ID="d4e2aa96-9aef-4cca-90b7-cf5f71b36665"
$env:AZURE_TENANT_ID="1faf88fe-a998-4c5b-93c9-210a11d9a5c2"

$env:LOCATION="uksouth"
$env:AZURE_RESOURCE_GROUP="MirrorMirrorEngineResourceGroup"
$env:WEBAPP_NAME="MirrorMirrorWebApp"

$env:WEBAPP_CLIENT_ID="81d9b8b6-cadb-4cdd-8ac8-d5e131d21fd2"

$env:WEBAPP_ID="/subscriptions/d4e2aa96-9aef-4cca-90b7-cf5f71b36665/resourceGroups/MirrorMirrorEngineResourceGroup/providers/Microsoft.Web/sites/MirrorMirrorWebApp"
```

```powershell
az login --service-principal --username $env:WEBAPP_CLIENT_ID --password $env:WEBAPP_CLIENT_SECRET --tenant $env:AZURE_TENANT_ID

az login --service-principal --subscription $env:AZURE_SUBSCRIPTION_ID --client $env:WEBAPP_CLIENT_ID --tenant $env:AZURE_TENANT_ID

az role assignment create --assignee <SERVICE_PRINCIPAL_APP_ID> --role Contributor --scope /subscriptions/$env:AZURE_SUBSCRIPTION_ID

az role assignment create --assignee $env:WEBAPP_CLIENT_ID --role Contributor --scope /subscriptions/$env:AZURE_SUBSCRIPTION_ID
```

## Deploy on Azure 2 - Function App
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
- [ ] Update .github workflow to match python flask
> - [x] Check `bicep_arm.yml`
> - [x] Check `environment_config.yml`
> - [ ] Update `environment_create.yml`
> - [x] Check `environment_delete.yml`
> - [ ] Update `environment_update.yml`

- [ ] 4.0
- [ ] 4.1


```powershell
az devcenter admin catalog create --name Environments --resource-group $env:AZURE_RESOURCE_GROUP --dev-center $env:AZURE_DEVCENTER --git-hub path="/Environments" branch="main" secret-identifier="https://$env:AZURE_KEYVAULT.vault.azure.net/secrets/pat" uri="https://github.com/HarinChan/MirrorMirrorEngine.git"

az functionapp deployment source config-zip --name ci-branch-main-1095874243 --src publish.zip --subscription d4e2aa96-9aef-4cca-90b7-cf5f71b36665 --resource-group mirrormirrorengineproject-ci-branch-main-1095874243
```


#### Constants
###### Unique to HarinChan / Console output:
echo $env:MY_AZURE_ID=`950826f0-bc3f-49c8-817b-0bc9b613d189`
echo $env:AZURE_SUBSCRIPTION_ID=`d4e2aa96-9aef-4cca-90b7-cf5f71b36665`
echo $env:AZURE_TENANT_ID=`1faf88fe-a998-4c5b-93c9-210a11d9a5c2`
or
echo $env:MY_AZURE_ID=$(az ad signed-in-user show --query id -o tsv)
echo $env:AZURE_SUBSCRIPTION_ID=$(az account show --query id --output tsv)
echo $env:AZURE_TENANT_ID=$(az account show --query tenantId --output tsv)

echo $env:AZURE_DEVCENTER_ID="/subscriptions/d4e2aa96-9aef-4cca-90b7-cf5f71b36665/resourceGroups/MirrorMirrorEngineResourceGroup/providers/Microsoft.DevCenter/devcenters/MirrorMirrorDevCenter"
echo $env:AZURE_DEVCENTER_PRINCIPAL_ID="c5767dca-bb5c-4807-8813-513727eb1a16"
echo $env:AZURE_PROJECT_ID="/subscriptions/d4e2aa96-9aef-4cca-90b7-cf5f71b36665/resourceGroups/MirrorMirrorEngineResourceGroup/providers/Microsoft.DevCenter/projects/MirrorMirrorEngineProject"
echo $env:AZURE_KEYVAULT_ID="/subscriptions/d4e2aa96-9aef-4cca-90b7-cf5f71b36665/resourceGroups/MirrorMirrorEngineResourceGroup/providers/Microsoft.KeyVault/vaults/MirrorMirrorKeyVault"




```
az keyvault create --name $env:AZURE_KEYVAULT --resource-group $env:AZURE_RESOURCE_GROUP --location $env:LOCATION --enable-rbac-authorization true
```

###### Manual Constant:
echo $env:LOCATION="uksouth"
echo $env:AZURE_RESOURCE_GROUP="MirrorMirrorEngineResourceGroup"
echo $env:AZURE_DEVCENTER="MirrorMirrorDevCenter"
echo $env:AZURE_PROJECT="MirrorMirrorEngineProject"
echo $env:AZURE_KEYVAULT="MirrorMirrorKeyVault"

```az devcenter admin project create --name $env:AZURE_PROJECT --resource-group $env:AZURE_RESOURCE_GROUP --location $env:LOCATION --dev-center-id $env:AZURE_DEVCENTER_ID```
## Deploy on Azure 1

Device set up:
- Install Azure CLI via `https://learn.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest`

Constants: (replace all instance below when altered)
- Resource Group: `MirrorMirrorEngineResourceGroup`
- App service plan: `mirrorMirrorEngineServicePlan`
- API name: `mirrorMirrorEnginePython`
- ACR name: `mirrormirroracr`
- Image Name: `mirror_mirror_engine`

#### Initial Steps. (should be completed on the website)
1. login to Azure `az login`
2. create resources group `az group create --name MirrorMirrorEngineResourceGroup --location uksouth`
3. Move on to A or B

#### A. Deploy from Github
1. create app service plan `az appservice plan create --name mirrorMirrorEngineServicePlan --resource-group DefaultResourceGroup-SUK --sku B1 --is-linux`
2. create webapp `az webapp create --resource-group MirrorMirrorEngineResourceGroup --plan mirrorMirrorEngineServicePlan --name mirrorMirrorEnginePython --runtime "PYTHON|3.8"`
3. navigate to project root, add remote group repository `az webapp deployment source config-local-git --name mirrorMirrorEnginePython --resource-group MirrorMirrorEngineResourceGroup`
4. deploy `git remote add azure <Your-Git-Remote-URL>`

#### B. Deploy from Docker
1. create acr `az acr create --resource-group MirrorMirrorEngineResourceGroup --name mirrormirroracr --sku Basic`
2. login to acr `az acr login --name mirrormirroracr`
3. push image `docker push mirrormirroracr.azurecr.io/mirror_mirror_engine:latest`

#### Result

Endpoint will be available at `http://<your-app-name>.azurewebsites.net` (app name dependant on)

