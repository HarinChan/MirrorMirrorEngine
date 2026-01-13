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

# dto
For any get request, dto should be use exclusively.

## Deploy on Azure

## Api end points

# ChromaDb service
Profile and post use chroma db service to optimize search and do matching.  
