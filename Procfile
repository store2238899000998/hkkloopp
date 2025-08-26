web: gunicorn api.main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
worker: python main.py
