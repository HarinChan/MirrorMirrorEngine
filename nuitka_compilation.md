1. Install build deps
```
pip install -r requirements.txt
pip install nuitka ordered-set zstandard
```

2. Set runtime env vars:
```
export FLASK_SECRET_KEY='change-me'
export JWT_SECRET_KEY='change-me-too'
export SQLALCHEMY_DATABASE_URI='sqlite:///penpals_db/penpals.db'
```

3. Build executable
```
python -m nuitka app.py \
  --standalone \
  --follow-imports \
  --assume-yes-for-downloads \
  --output-dir=build \
  --include-package=src \
  --include-package=flask \
  --include-package=flask_sqlalchemy \
  --include-package=flask_jwt_extended \
  --include-package=sqlalchemy \
  --include-package=chromadb \
  --include-package=requests
```

4. Run
```
./build/app.dist/app
```