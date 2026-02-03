## Test
Testcases should be put in `/src/test` and should be structured accordingly to `/src/app`. We do not need to strive for 100% test coverage, just enough to make sure the required cases from the frontend are covered.

We will be using the `pytest` and `coverage` library. (pip install)

## To Run main App

`python src/app.py`



## To Test
`python src/test/main.py`
run test with coverage

`coverage run -m pytest`

`coverage report`

## dto
For any get request, dto should be use exclusively.
