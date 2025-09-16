#!/bin/bash
# run.sh

# alembic upgrade head

# Calculate workers based on available resources
# WORKERS=${WEB_CONCURRENCY:-$((2 * $(nproc) + 1))}

# exec gunicorn \
#   -w $WORKERS \                    
#   -k uvicorn.workers.UvicornWorker \ 
#   --worker-connections 1000 \   
#   src.api.main:app \
#   --bind 0.0.0.0:${PORT:-8080}

uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT:-8080}