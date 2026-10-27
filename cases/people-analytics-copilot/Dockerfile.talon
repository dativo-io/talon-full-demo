# A minimal runtime for the Talon binary with the standard public TLS trust store.
# Unlike raw debian:bookworm-slim, this image can validate OpenAI's HTTPS chain.
FROM debian:bookworm-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*
