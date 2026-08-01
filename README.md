# Indian Investment App

A FastAPI-based planning app for Danish-resident NRIs who want to analyze Indian savings, investment options, and tax implications.

## Features

- Analyze Indian savings and interest income
- Estimate Denmark and India tax considerations
- Generate structured planning output
- Display a user-friendly report in the frontend
- Deterministic tax and investment logic (no OpenAI calls)
- Optional LLM explanation layer can be added later

## Project Structure

```txt
indian-investment-app/
├── main.py                 # Uvicorn entry point
├── app/
│   ├── main.py             # FastAPI app factory
│   ├── config.py           # Environment settings
│   ├── schemas.py          # Request/response models
│   ├── routes/             # API routes
│   └── services/           # Formatting, response builder, input adapter
├── agent/
│   └── agent_logic.py      # Deterministic planning logic
├── static/
│   └── index.html          # Frontend UI
├── tests/
├── Procfile                # Render/Heroku-style deploy
├── render.yaml             # Render blueprint
├── railway.toml            # Railway deploy config
└── requirements.txt
```

## Local Development

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
uvicorn main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) for the UI.

### Environment Variables

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug logging and error tracebacks |
| `PORT` | `8000` | Server port |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `STATIC_DIR` | `static` | Static files directory |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Frontend UI |
| GET | `/api/health` | Health check |
| POST | `/api/agent` | Run planner |
| POST | `/analyze` | Compatibility alias for `/api/agent` |

## Tests

### Recommended: run from Cursor (no typing)

1. Press `Ctrl+Shift+P`
2. Type **Run Task**
3. Choose **Run Tests**

Or press `Ctrl+Shift+B` if **Run Tests** is the default build task.

### Or type this manually (do not paste from terminal history)

Type these **4 characters** with your keyboard, then Enter:

```text
t.bat
```

Do **not** include `PS C:\Users\...>` — that prefix is the shell prompt, not part of the command. Pasting it causes the `Get-Process` error you saw.

### Other options

Double-click `run_tests.bat` in File Explorer.

```powershell
.\run_tests.bat
```

```powershell
.\.venv\Scripts\python.exe -m pytest
```

If `.venv` is missing, `run_tests.bat` creates it and installs dependencies.

<details>
<summary>Other options (activation, macOS/Linux)</summary>

```powershell
# PowerShell activation (may require: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser)
.venv\Scripts\Activate.ps1
python -m pytest

# cmd-style activation in PowerShell
.venv\Scripts\activate.bat
python -m pytest
```

macOS/Linux:

```bash
source .venv/bin/activate
python -m pytest
```

</details>

## Deployment

### Render

1. Connect this repository in Render.
2. Use the included `render.yaml` blueprint, or create a Web Service with:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Set `DEBUG=false` in environment variables.

### Railway

1. Connect the repository in Railway.
2. Railway reads `railway.toml` for start command and health check.
3. Ensure `PORT` is provided by the platform (Railway sets this automatically).

## Disclaimer

This app provides educational planning output only. It is not tax, legal, or investment advice. Verify all decisions with qualified advisers in Denmark and India.
