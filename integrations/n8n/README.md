# n8n integration

This directory contains a real, credential-free workflow export for the pinned `n8n:2.30.4` runtime:

- `quarterly-compliance-workflow.json` — importable workflow graph;
- `compose.yaml` — loopback-only UI runtime for Ubuntu/Linux rehearsals;
- `workflow-spec.md` — human-readable behavior and truth contract.

The workflow reads the three synthetic Markdown sections under `cases/quarterly-report`, processes them sequentially through Talon's `document-summary` identity, writes each completed summary, and stops cleanly when Talon returns `403 session_budget_exceeded`. Completed files remain available and `status.json` records which next section was not sent.

## Credential-free clean-import validation

```bash
make n8n-validate
```

This command uses pinned n8n `2.30.4` and mock Talon's allow-then-budget-deny contract to:

1. render an ephemeral Header Auth credential outside the repository;
2. import the committed workflow into a clean n8n runtime;
3. execute it sequentially;
4. verify one completed summary and a zero-cost budget denial;
5. export the workflow and assert that no credential value was included;
6. import that export into a second clean runtime;
7. execute and verify the same contract again.

The repository CI runs this exact sequence. No provider key is needed.

## Real Talon + Anthropic demo

Prepare the real stack with both provider keys once:

```bash
export OPENAI_API_KEY='sk-...'
export ANTHROPIC_API_KEY='sk-ant-...'
make real-prepare
make real-start
```

Run for a buyer:

```bash
make demo-n8n-buyer
```

Run for platform, security, or engineering reviewers:

```bash
make demo-n8n-tech
```

Re-present the same completed Talon session without rerunning n8n:

```bash
make present-n8n
make present-n8n-tech
make present-n8n-all
```

The real runner stages the pinned `document-summary` session cap from its canonical `$0.01` value to `$0.00301` for this one run. Talon's pinned pre-request estimate for `claude-haiku-4-5` is `$0.003`, so the first section can run and completed spend makes a later request cross the staged boundary. The runner validates the pinned source and canonical value before editing, restores the original agent file on every normal or error exit, and recovers an interrupted prior stage before starting another run.

The presenter does not trust that staging metadata as proof. It fails closed unless completed `*.summary.md` files, `status.json`, `document-summary` attribution, allowed work followed by `session_budget_exceeded`, zero provider cost on the denied request, valid Talon signatures, and the signed denial's `{limit, spent, estimate}` arithmetic all agree.

## Optional UI import

The automated CLI runner is the canonical demo path. To inspect the same workflow in the n8n UI:

```bash
source .env
source .state/demo-run.env
mkdir -p .state/n8n-config .state/n8n-output
bash scripts/render-n8n-credential.sh
cp integrations/n8n/quarterly-compliance-workflow.json .state/n8n-config/workflow.json
docker compose -f integrations/n8n/compose.yaml up
```

The Compose runtime uses Linux host networking because Talon deliberately binds only to host loopback. `N8N_LISTEN_ADDRESS=127.0.0.1` keeps the n8n UI loopback-only as well. Import `/demo/config/credential.json` and `/demo/config/workflow.json` using n8n's CLI or UI; never commit the generated credential file.

A manual UI run does not automatically stage the demo budget. Use the automated `make demo-n8n-*` path for the deterministic budget scene.

## Truth boundary

Session budgets are soft caps. The accurate claim is:

> Completed requests consumed session budget, so Talon denied the next request before provider dispatch. The denied request added zero provider cost, and the workflow preserved completed output.

The staged cap is a transparent demo policy change, not a hidden product claim. Do not claim atomic reservation, guaranteed no-overshoot behavior, or that a denied request reverses cost already incurred by completed requests.
