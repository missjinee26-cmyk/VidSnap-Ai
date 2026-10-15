#!/bin/bash
# Runs both processes in a single Render free web service:
# the background reel worker + the gunicorn web server.
set -e
python generate_process.py &
exec gunicorn main:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120
