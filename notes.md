## Development Notes

Python Version: 3.13

Required python libraries:
- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `database`

Testcases should be put in `/src/test` and should be structured accordingly to `/src/app`. We do not need to strive for 100% test coverage, just enough to make sure the required cases from the frontend are covered.

## To Run

`python src/app.py`

## dto
For any get request, dto should be use exclusively.

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

## Api end points

## ChromaDb service
Profile and post use chroma db service to optimize search and do matching.  

## Copy from Penpals.Backend checklist
- [x] account.py (copied under `blueprint/account.py`)
- [x] app.py (raw)
- [x] chromadb_service.py (copied under `chromadb/chromadb_service.py`)
- [x] classroom.py (copied under `blueprint/classroom.py`)
- [ ] engine_handler.py (do not need to copy, usage not needed)
- [ ] find_open_port.py (do not need to copy, unused)
- [ ] init_db.py (do not need to copy, unsused)
- [x] main.py (raw)
- [x] model.py (copied under `model/*` split into different classes)
- [x] penpals_helper.py (as `helper`)
