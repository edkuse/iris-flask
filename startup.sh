#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Start the application
gunicorn -w 4 -k uvicorn.workers.UvicornWorker run:app
