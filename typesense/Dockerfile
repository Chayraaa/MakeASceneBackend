# Stage 1: compile the /proc/self/io shim
# Use Debian bookworm to match the glibc in the typesense base image
FROM debian:bookworm-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY proc_io_shim.c .
RUN gcc -shared -fPIC -O2 -o proc_io_shim.so proc_io_shim.c -ldl

# Stage 2: typesense with shim injected
FROM typesense/typesense:27.1
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/proc_io_shim.so /usr/local/lib/proc_io_shim.so
# Wrap the entrypoint so LD_PRELOAD is set before the binary runs and the
# API key env var is expanded at runtime (not compose-parse time)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]
