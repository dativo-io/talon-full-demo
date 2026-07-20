# n8n integration

The Compose environment is pinned to `n8n:2.30.4`, binds only to `127.0.0.1:5678`, requires an operator-supplied encryption key, and commits no credentials.

The repository intentionally contains a workflow specification rather than an untested hand-authored export. Build and run the workflow in the pinned n8n UI, export it without credentials, import it into a clean container running the same version, reconnect the Header Auth credential, and rerun before committing any workflow JSON. Until that sequence is completed, n8n is a tested deployment contract and implementation specification—not a finished workflow artifact.
