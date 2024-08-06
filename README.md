# AVATARS-AI-API
FastAPI service powering AVATARS-AI app

## Getting Started

1. Activate virtual-env
```zsh
cd AVATARS-AI-API
python3 -m venv apienv
. apienv/bin/activate
```

2. Install dependencies
```zsh
pip install -r requirements.txt
```

3. Start server
```zsh
uvicorn main:app --reload
```

4. Open API docs
```zsh
http://127.0.0.1:8000/v1/documentation
```
