## Development Notes

Python Version: 3.13

Required python libraries:
- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `database`

Testcases should be put in `/src/test` and should be structured accordingly to `/src/app`. We do not need to strive for 100% test coverage, just enough to make sure the required cases from the frontend are covered.

Running the app in dev mode in root directory:
```uvicorn src.app.main:app --reload```
# Model Notes
Each entity also has a "metadata" value to package any derivitive / interpretation of the class.
e.g. profile -> classroom, adding grades, age, etc.
Model should be made generalized.

# dto
For any get request, dto should be use exclusively.

## Deploy on Azure (untested)

Steps 1-5 can and should idealy be completed on the Azure website.
1. login `az login`
2. create resources group `az group create --name mirroMirrorEngineResourceGroup --location eastus`
3. create app service plan `az appservice plan create --name mirroMirrorEngineServicePlan --resource-group mirroMirrorEngineResourceGroup --sku B1 --is-linux`
4. create webapp `az webapp create --resource-group mirroMirrorEngineResourceGroup --plan mirroMirrorEngineServicePlan --name mirroMirrorEnginePython --runtime "PYTHON|3.8"`
5. set up deployment `az webapp deployment source config-local-git --name mirroMirrorEnginePython --resource-group mirroMirrorEngineResourceGroup`

Step 2-6 should ran on your device at root.
6. navigate to project root, add remote group repository `az webapp deployment source config-local-git --name mirroMirrorEnginePython --resource-group mirroMirrorEngineResourceGroup`
7. deploy `git remote add azure <Your-Git-Remote-URL>`

Endpoint will be available at `http://<your-app-name>.azurewebsites.net`

## Api end points

# Run
Run `python src\app\main.py`
