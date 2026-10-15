#!/bin/bash
# Runs both processes in a single Render free web service:
# the background reel worker + the gunicorn web server.
set -e
# Render's runtime may only provide python3 (no unversioned python).
# -u = unbuffered so worker logs show up in Render's log stream.
PYBIN=$(command -v python3 || command -v python)
echo "Starting reel worker with $PYBIN"
$PYBIN -u generate_process.py &
exec gunicorn main:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120
