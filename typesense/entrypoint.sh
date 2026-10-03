#!/bin/sh

export LD_PRELOAD=/usr/local/lib/proc_io_shim.so

exec /opt/typesense-server --data-dir /data --api-key "$TYPESENSE_API_KEY"