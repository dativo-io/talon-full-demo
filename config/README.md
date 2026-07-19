# Talon configuration

`generated/` is ignored. Populate it from a current Talon checkout:

```bash
TALON_REPO=../talon make bootstrap-config
```

The script copies `examples/product-demo/talon.config.yaml` and `agents/**`, creates a gateway-wide shadow variant, and records the Talon source commit when available.

`mcp-proxy.example.yaml` follows the strict current Talon MCP schema audited at commit `631695d8713337cee3bef79e65225e40ba03c923`. It always sets `mode: intercept`, but the complete scene remains blocked until `docs/BLOCKERS.md` is resolved.
