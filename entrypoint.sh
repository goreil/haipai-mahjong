#!/bin/sh
# Fix ownership of mounted volumes (created as root by Docker)
chown -R appuser:appuser /app/data /app/mortal_analysis 2>/dev/null || true

# Drop to non-root user
exec gosu appuser "$@"
