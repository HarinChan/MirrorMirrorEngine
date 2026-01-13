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

## Deploy on Azure

## Api end points

# Run
Run `python src\app\main.py`
