release: flask db upgrade
web: gunicorn --workers=1 --threads=4 --timeout 30 --max-requests=500 --max-requests-jitter=50 --preload --bind 0.0.0.0:$PORT src.app:app