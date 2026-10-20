# OpenShell — Full Demo case

This optional case uses the same Full Demo workflow as n8n, Copilot and
Zendesk: prepare, start, status, run, approve or reject, present, stop.
It does not create a second Talon runtime, evidence store or approval system.

## Status

Talon PR #501 was merged at da61c47866a3d6aea787c762360f62f6b99089a2.
The latest release checked (v1.10.0) predates it. The new full-demo adapters
require the canonical main-repo runner at:
talon/examples/openshell/showcase/demo.sh

Until that runner ships and the version-pinned real-runtime lane is green, this
is draft integration wiring and must not be described as a released showcase.
Do not substitute talon/scripts/openshell-live.sh: it starts a separate Talon
fixture and is an engineering test, not this shared customer demo.

## Usage

OpenShell is optional. Existing demos work without it. On a supported Linux
host with Docker, a checkout of compatible Talon, and the required Full Demo
provider configuration:

    export TALON_OPENSHELL_ENABLED=1
    export TALON_OPENSHELL_PROVIDER_MODE=mock
    make real-prepare
    make real-start
    make real-status
    make demo-openshell-buyer

While the first shell waits at the Talon Action Gateway reviewer decision:

    make status-openshell-approval
    make approve-openshell
    # or: make reject-openshell

After the run has completed, project exactly the same signed session:

    make present-openshell-all
    make real-stop

Technical view: make demo-openshell-tech
No-key real-runtime validation: make openshell-validate

## Canonical main-Talon runner contract

The Full Demo adapter runs the canonical shell entry point with one argument.

- prepare: inject an OpenShell overlay into the existing generated YAML and
  agent directory, including TLS, identity binding and action catalog, without
  starting another Talon.
- start: initialize pinned OpenShell runtime and mock dependencies; attach to
  the existing Talon gateway.
- status: check real OpenShell, the middleware, action path and versions; refuse
  if any of these are missing.
- run: execute the genuine Go SDK agent within released OpenShell, using the
  supplied session and stable operation prefix; wait for reviewer decision.
- approval-status/approve/reject: call Talon's own reviewer API outside the
  sandbox; approval alone must not dispatch.
- validate: run deterministic no-key CI against the actual OpenShell runtime.
- stop: stop only OpenShell-owned demo resources; leave Talon shared services
  for the existing Full Demo lifecycle.

Full Demo exports these environment variables to the canonical runner:

    TALON_SHOWCASE_EMBEDDED=1
    TALON_SHOWCASE_CONFIG_DIR=<generated/full-demo/config>
    TALON_SHOWCASE_TALON_DATA_DIR=<shared/.state/talon>
    TALON_SHOWCASE_TALON_URL=<shared gateway URL>
    TALON_SHOWCASE_TALON_BIN=<active compatible talon binary>
    TALON_SHOWCASE_RUN_DIR=<private .state/openshell directory>
    TALON_SHOWCASE_AGENT=sandboxed-support
    TALON_SHOWCASE_PROVIDER_MODE=mock|real
    TALON_SHOWCASE_SESSION=openshell-<fresh run ID> (on run/approval)
    TALON_SHOWCASE_OPERATION_PREFIX=openshell-refund-<fresh run ID>
    TALON_SHOWCASE_RUN_START=<shared demo start timestamp>

On completed run only, write a JSON result locator under:
<run-dir>/<session>.result.json

Required JSON fields: session_id, runtime_ref, refund_operation_id.
Do not misrepresent this locator as cryptographic proof. Full Demo presenters
re-export and verify current-session Talon HMAC evidence, assert verified
workload identity, tool filtering, response settlements and action lifecycle,
and verify the specific refund operation using Talon's own CLI.

The runner must independently check mock downstream call count, approval
precedence and replay safety. A synthetic provider does not prove real-provider
inference. A synthetic refund is not a real payment.

## Evidence/provenance doctrine

OpenShell owns sandbox containment, network policy and credential injection.
Talon owns company model policy, Action Gateway approval and dispatch, and
signed records. A Talon HMAC of imported OpenShell events proves only that
Talon recorded an external assertion. The sandbox must never possess Talon,
provider, or reviewer credentials. Only a human reviewer outside the sandbox
can authorize a refund.

This demo differs from the existing n8n support-resolution case. That case
authorizes a synthetic finance handoff through a separate demo-side approval
gate; it does not demonstrate Talon's exact Action Gateway refund dispatch.

## Release-readiness gate

Do not declare a self-service showcase until the actual SDK agent passes
inside released OpenShell, the customer setup path uses verified published
Talon/agent artifacts (not Go builds or cloned source), and real failed/allowed/
denied/approved behavior is machine-checked against the same signed session.
The published-artifact requirement is owned by Talon's #462 epic, not a new
installation system in this repo. This advanced integration need not meet the
60-second quickstart timing promise.
