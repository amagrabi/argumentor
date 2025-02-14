# ArguMentor

<!-- <p align="center">
    <img width="400" height="400" src="demo.gif" alt="Demo">
</p> -->

ArguMentor is a platform to train reasoning and decision-making skills. Users can construct arguments to challenging questions, improve with AI-driven feedback and track their progress.

## Installation

### Option 1: Docker

```sh
docker compose --build
docker compose up
```

Access the application at `http://localhost:8000`.

### Option 2: Python

Create and activate a virtual environment, for example via [uv](https://docs.astral.sh/uv/getting-started/installation/):

```sh
uv venv
source .venv/bin/activate
```

Install dependencies in editable mode:

```sh
uv pip install -e .
```

Install PostGreSQL:

```sh
brew install postgresql
```

Create a database:

```sh
brew services start postgresql
psql -U postgres -c "CREATE DATABASE argumentor;"
```

Start app:

```sh
DEV=true USE_LLM_EVALUATOR=false python -m src.app
```

Start app in production:

```sh
gunicorn --bind localhost:8000 src.app:app
```

## Development

Install dev dependencies:

```sh
uv pip install -e ".[dev]"
```

Create a `.env` file from `.env_template` and specify values.

Install pre-commit hooks for auto-formatting:

```sh
pre-commit install
```

Run tests:

```sh
pytest tests/
```

Recreate db for local development:

```sh
flask recreate_db
```
