# ArguMentor

<!-- <p align="center">
    <img width="400" height="400" src="demo.gif" alt="Demo">
</p> -->

Platform to train reasoning skills and make better decisions.


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

Start game:
```sh
argumentor
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
