#!/bin/sh

echo "BEFORE: LD_PRELOAD='$LD_PRELOAD'"

export LD_PRELOAD=/usr/local/lib/proc_io_shim.so

echo "AFTER: LD_PRELOAD='$LD_PRELOAD'"
echo "SHIM:"
ls -l /usr/local/lib/proc_io_shim.so

exec /opt/typesense-server --data-dir /data --api-key "$TYPESENSE_API_KEY"