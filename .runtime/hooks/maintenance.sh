#!/bin/bash
# maintenance.sh — runs on demand via `entrypoint.sh maintenance`, e.g. from an
# external schedule (cron, ECS scheduled task, k8s CronJob). Not called during
# the normal container lifecycle.
#
# Runs with the virtualenv already activated and APP_ROOT as the working
# directory. Use this for periodic upkeep tasks: pruning stale data,
# vacuuming tables, clearing expired sessions/caches, etc.
#
# Example:
# python manage.py clearsessions
