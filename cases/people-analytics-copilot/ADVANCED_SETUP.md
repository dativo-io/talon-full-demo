# Advanced setup: real inference and diagnostics

Default CI is credential-free and exercises real Talon LLM/MCP gateways with a deterministic **fake OpenAI-compatible provider**. This proves the protocol path, not real model behavior.

## Opt-in external OpenAI smoke

Use fictional data and a disposable provider credential on a trusted development host. **Billable calls may occur.**

```bash
read -rs -p "OpenAI API key: " OPENAI_API_KEY; echo
export OPENAI_API_KEY
bash scripts/test-people-analytics-real-provider.sh
# For interactive LIVE dashboard:
bash scripts/people-analytics-isolated.sh live
unset OPENAI_API_KEY
```

The runtime's Talon MCP proxy and LLM gateway are separate processes sharing the same agent key/state. In LIVE mode `HR_AI_TRACE` reports the app-observed requests/responses sent via Talon's OpenAI-compatible endpoint, including model, response ID, tool call names and token usage. **This is not a packet capture of OpenAI TLS traffic.**

Logs do not include full prompts/responses by default. `HR_DEMO_TRACE_PAYLOADS=1` opts in to bounded previews only for this fictional fixture; never enable it for production HR, credentials or customer prompts. The convenience launcher temporarily passes the provider key into an initialization container environment to vault it; privileged Docker users could inspect that environment.

## Troubleshooting

```bash
bash scripts/people-analytics-isolated.sh logs
bash scripts/people-analytics-isolated.sh reapply
make people-analytics-validate
bash scripts/test-people-analytics-talon.sh
```

`reapply` validates agent config before restarting MCP/LLM services. An invalid MCP proxy policy may still be rejected at startup; check logs and restore the previous policy. Do not treat a failed restart as a successful policy proof.

## Boundaries

Talon evidence is tamper-evident provided signing keys remain secure. Backend SQL is limited to two reviewed, cohort-size-filtered aggregate shapes. Docker controls the network/volume boundary, not Talon. The privileged HR process can still reach the database, and a direct bypass never creates Talon evidence.
