## Development Notes

Python Version: 3.13

Required python libraries:
- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `database`

Testcases should be put in `/src/test` and should be structured accordingly to `/src/app`. We do not need to strive for 100% test coverage, just enough to make sure the required cases from the frontend are covered.

## To Run

`python src/app/app.py`

## dto
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

# ChromaDb service
Profile and post use chroma db service to optimize search and do matching.  

# Copy from Penpals.Backend checklist
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

# Dumps

idk dump
``` python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy


# app is for /router
# db is for /model


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
app.secret_key = 'your_secret_key'  # Change this to something secure!

db = SQLAlchemy(app)
with app.app_context():
    db.create_all()  # Create database tables

app.run(debug=True)
```