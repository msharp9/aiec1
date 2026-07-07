#!/bin/sh
# Wrapper entrypoint for running langgraph-api on Vercel.
#
# Vercel gives the container ~15s to accept TCP on $PORT, but langgraph-api
# needs ~27s to boot. We start a lightweight proxy on Vercel's $PORT (satisfies
# the readiness gate instantly) and move the real server to an internal port
# via the base image's LANGGRAPH_SERVER_PORT override.

set -e

VERCEL_PORT="${PORT:-8000}"   # capture Vercel's port before the base entrypoint rewrites PORT
BACKEND_PORT=9000

python3 /deps/09_Agent_Servers/vercel_port_proxy.py "$VERCEL_PORT" "$BACKEND_PORT" &

# Base /storage/entrypoint.sh does: if [ -n "$LANGGRAPH_SERVER_PORT" ]; then export PORT=$LANGGRAPH_SERVER_PORT; fi
# so uvicorn binds $BACKEND_PORT while the proxy owns $VERCEL_PORT.
export LANGGRAPH_SERVER_PORT="$BACKEND_PORT"

exec /storage/entrypoint.sh
