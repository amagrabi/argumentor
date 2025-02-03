# ArguMentor

<!-- <p align="center">
    <img width="400" height="400" src="demo.gif" alt="Demo">
</p> -->

Platform to train reasoning and decision-making skills. Users can answer interesting questions, construct arguments and get AI-driven feedback to improve and track their progress.

## Installation

Create and activate a virtual environment, for example via [uv](https://docs.astral.sh/uv/getting-started/installation/):

```sh
uv venv
source .venv/bin/activate
```

Install dependencies in editable mode:

```sh
uv pip install -e .
```

Start app:

```sh
python -m src.app
```

## Development

Install dev dependencies:

```sh
uv pip install -e ".[dev]"
```

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
