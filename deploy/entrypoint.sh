#!/bin/sh
set -eu

flask --app app db upgrade

if [ "${SEED_REFERENCE_DATA:-false}" = "true" ]; then
  flask --app app seed
fi

exec "$@"
