release: flask db upgrade
web: gunicorn --workers=2 --threads=3 --timeout 30 --max-requests=300 --max-requests-jitter=100 --graceful-timeout=10 --bind 0.0.0.0:$PORT src.app:app