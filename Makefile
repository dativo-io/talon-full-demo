SHELL := /usr/bin/env bash

.PHONY: all check-go build test vet fmt fmt-check shell-check validate-local integration-local ci clean env bootstrap-config preflight live-check real-prepare real-start real-smoke real-support present-support present-support-tech present-support-all demo-support-buyer demo-support-tech real-zendesk present-zendesk present-zendesk-tech present-zendesk-all demo-zendesk-buyer demo-zendesk-tech zendesk-package zendesk-zcli-package verify-zendesk-installed copilot-install real-copilot present-copilot present-copilot-tech present-copilot-all demo-copilot-buyer demo-copilot-tech n8n-validate real-n8n present-n8n present-n8n-tech present-n8n-all demo-n8n-buyer demo-n8n-tech real-status real-stop

all: test

check-go:
	@go version >/dev/null || { \
		echo >&2; \
		echo "Go 1.23.0 or newer is required." >&2; \
		echo "Inspect the locally installed launcher with: GOTOOLCHAIN=local go version" >&2; \
		echo "Install a current Go release from https://go.dev/dl/ and retry." >&2; \
		exit 1; \
	}

build: check-go
	mkdir -p bin
	go build -o bin/copilot-session-shim ./cmd/copilot-session-shim
	go build -o bin/zendesk-adapter ./cmd/zendesk-adapter
	go build -o bin/release-mcp-server ./cmd/release-mcp-server

test: check-go
	go test ./...
	node --test integrations/zendesk-app/test/*.test.cjs

vet: check-go
	go vet ./...

fmt:
	gofmt -w cmd internal

fmt-check:
	@files="$$(find cmd internal -name '*.go' -type f -print)"; \
	unformatted="$$(gofmt -l $$files)"; \
	if [[ -n "$$unformatted" ]]; then echo "Go files need gofmt:" >&2; echo "$$unformatted" >&2; exit 1; fi

shell-check:
	bash -n scripts/*.sh

validate-local: check-go fmt-check vet build test shell-check
	bash ./scripts/test-real-demo-env-loader.sh
	./scripts/validate-local.sh

integration-local: build
	./scripts/test-integration-local.sh

# Executable proof against a REAL Talon server built from source (no mock):
# the MCP forbidden-tool scene, the signed-evidence chain, and the
# session-budget engine. Needs a dativo-io/talon checkout (TALON_REPO,
# default ../talon). Run before presenting.
live-check:
	./scripts/test-live-talon.sh

# Simplified real-case path. Only real-prepare needs provider keys:
#   export OPENAI_API_KEY='sk-...'
#   export ANTHROPIC_API_KEY='sk-ant-...'
#   make real-prepare real-start
real-prepare:
	bash ./scripts/real-demo.sh prepare

real-start:
	bash ./scripts/real-stack.sh start

# Original direct smoke command retained for troubleshooting and compatibility.
real-smoke:
	bash ./scripts/real-stack.sh smoke

# Fresh, isolated real support run plus evidence-backed audience projections.
real-support:
	bash ./scripts/real-support.sh

present-support:
	bash ./scripts/present-support.sh buyer

present-support-tech:
	bash ./scripts/present-support.sh technical

present-support-all:
	bash ./scripts/present-support.sh all

demo-support-buyer:
	SUPPORT_DEMO_OUTPUT=quiet bash ./scripts/real-support.sh
	bash ./scripts/present-support.sh buyer

demo-support-tech:
	bash ./scripts/real-support.sh
	bash ./scripts/present-support.sh technical

# Real local Zendesk adapter path. This proves adapter -> Talon -> provider.
real-zendesk:
	bash ./scripts/real-zendesk.sh

present-zendesk:
	bash ./scripts/present-zendesk.sh buyer

present-zendesk-tech:
	bash ./scripts/present-zendesk.sh technical

present-zendesk-all:
	bash ./scripts/present-zendesk.sh all

demo-zendesk-buyer:
	ZENDESK_DEMO_OUTPUT=quiet bash ./scripts/real-zendesk.sh
	bash ./scripts/present-zendesk.sh buyer

demo-zendesk-tech:
	bash ./scripts/real-zendesk.sh
	bash ./scripts/present-zendesk.sh technical

# Credential-free ZIP construction and source/secret inspection; runs in CI.
zendesk-package:
	bash ./scripts/package-zendesk-app.sh offline

# Official ZCLI server-side validation/package. Zendesk authentication is required.
zendesk-zcli-package:
	bash ./scripts/package-zendesk-app.sh zcli

# Final installed-app gate: machine-verify Talon evidence and record the four
# browser-only observations explicitly as operator-confirmed facts.
verify-zendesk-installed:
	bash ./scripts/verify-zendesk-installed.sh

# Explicit opt-in installation of GitHub's official Copilot CLI.
copilot-install:
	bash ./scripts/install-copilot-cli.sh

real-copilot:
	bash ./scripts/real-copilot.sh

present-copilot:
	bash ./scripts/present-copilot.sh buyer

present-copilot-tech:
	bash ./scripts/present-copilot.sh technical

present-copilot-all:
	bash ./scripts/present-copilot.sh all

demo-copilot-buyer:
	COPILOT_DEMO_OUTPUT=quiet bash ./scripts/real-copilot.sh
	bash ./scripts/present-copilot.sh buyer

demo-copilot-tech:
	bash ./scripts/real-copilot.sh
	bash ./scripts/present-copilot.sh technical

# Import, execute, export, clean-import, and execute again against the mock
# allow-then-budget-deny contract in pinned n8n 2.30.4.
n8n-validate:
	bash ./scripts/n8n-workflow.sh validate

# Real imported workflow through Talon + Anthropic. The wrapper resolves the
# exact CLI used by the running stack even in a fresh shell with a shorter PATH.
real-n8n:
	bash ./scripts/with-talon.sh bash ./scripts/n8n-workflow.sh real

present-n8n:
	bash ./scripts/with-talon.sh bash ./scripts/present-n8n.sh buyer

present-n8n-tech:
	bash ./scripts/with-talon.sh bash ./scripts/present-n8n.sh technical

present-n8n-all:
	bash ./scripts/with-talon.sh bash ./scripts/present-n8n.sh all

demo-n8n-buyer:
	N8N_DEMO_OUTPUT=quiet bash ./scripts/with-talon.sh bash ./scripts/n8n-workflow.sh real
	bash ./scripts/with-talon.sh bash ./scripts/present-n8n.sh buyer

demo-n8n-tech:
	bash ./scripts/with-talon.sh bash ./scripts/n8n-workflow.sh real
	bash ./scripts/with-talon.sh bash ./scripts/present-n8n.sh technical

real-status:
	bash ./scripts/real-status.sh

real-stop:
	bash ./scripts/real-stack.sh stop

ci: validate-local
	git diff --check

clean:
	rm -rf bin .state

env:
	./scripts/generate-env.sh

bootstrap-config:
	./scripts/bootstrap-talon-config.sh

preflight:
	./scripts/preflight.sh
