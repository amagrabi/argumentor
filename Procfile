release: flask db upgrade
web: gunicorn --workers=2 --timeout 30 --max-requests=1000 --max-requests-jitter=50 --bind 0.0.0.0:$PORT src.app:app