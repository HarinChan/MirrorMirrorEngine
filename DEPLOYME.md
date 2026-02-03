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


## Deploy on Azure (untested)

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

