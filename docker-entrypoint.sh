#!/bin/bash
# Set up cron job from CRON_SCHEDULE env variable

CRON_SCHEDULE="${CRON_SCHEDULE:-0 0 * * *}" # Default: daily at midnight

echo "$CRON_SCHEDULE uv run /app/main.py >> /app/cron.log 2>&1" > /etc/cron.d/smt-data-exporter
chmod 0644 /etc/cron.d/smt-data-exporter

# Apply cron job
crontab /etc/cron.d/smt-data-exporter

# Run the script once on container startup
uv run /app/main.py

# Start cron in foreground
cron -f
