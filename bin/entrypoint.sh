#!/bin/sh
set -e

alembic upgrade head

exec python3 -m shazam.daemon