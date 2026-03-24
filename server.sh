#!/usr/bin/env bash

# activate virtual environment
source venv/bin/activate

echo "Using Python: $(which python)"

# 2) start the server in the background
uvicorn server:app --reload &
UVICORN_PID=$!

echo "Server started (PID=$UVICORN_PID)"
echo "Type 'q' or 'quit' to stop."

# 3) listen input "q" or "quit" to stop the server
while true; do
  read -r input
  if [[ "$input" == "q" || "$input" == "quit" ]]; then
    echo "Stopping server..."
    kill "$UVICORN_PID"
    wait "$UVICORN_PID" 2>/dev/null || true
    break
  fi
done

# 4) deactivate venv
deactivate venv

echo "Server stopped and venv deactivated."