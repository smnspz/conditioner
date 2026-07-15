#!/usr/bin/env bash

if [[ "$1" == "prod" ]]; then
    npx wrangler d1 migrations apply conditioner --remote
elif [[ "$1" == "local" ]]; then
    npx wrangler d1 migrations apply conditioner --local
else
    echo "Usage: $0 <local|prod>"
    exit 1
fi
