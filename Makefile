SHELL := /usr/bin/env bash

.PHONY: all check-go build test vet fmt fmt-check shell-check validate-local integration-local ci clean env bootstrap-config preflight live-check real-prepare real-start real-smoke real-support present-support present-support-tech present-support-all demo-support-buyer demo-support-tech real-zendesk present-zendesk present-zendesk-tech present-zendesk-all demo-zendesk-buyer demo-zendesk-tech copilot-install real-copilot present-copilot present-copilot-tech present-copilot-all demo-copilot-buyer demo-copilot-tech present-n8n present-n8n-tech present-n8n-all real-status real-stop

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
	./scripts/validate-local.sh

integration-local: build
	./scripts/test-integration-local.sh

# Executable proof against a REAL Talon server built from source (no mock):
# the MCP forbidden-tool scene, the signed-evidence chain, and the
# session-budget engine. Needs a dativo-io/talon checkout (TALON_REPO,
# default ../talon). Run before presenting.
live-check:
	./scripts/test-live-talon.sh

# Simplified real-case path. Only real-prepare needs a provider key:
#   export OPENAI_API_KEY='sk-...'
#   make real-prepare real-start real-smoke
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

# Real local Zendesk adapter path. This proves adapter -> Talon -> provider,
# while the installed private-app gate remains external and explicitly separate.
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

# Explicit opt-in installation of GitHub's official Copilot CLI. The real
# client path otherwise never downloads or installs third-party software.
copilot-install:
	bash ./scripts/install-copilot-cli.sh

real-copilot:
	bash ./scripts/real-copilot.sh

# Present the latest successful real-Copilot session without rerunning it.
# Both projections export and verify the same signed Talon evidence.
present-copilot:
	bash ./scripts/present-copilot.sh buyer

present-copilot-tech:
	bash ./scripts/present-copilot.sh technical

present-copilot-all:
	bash ./scripts/present-copilot.sh all

# One-command audience flows. Buyer mode retains the full Copilot transcript
# on disk while keeping the terminal concise; technical mode streams it.
demo-copilot-buyer:
	COPILOT_DEMO_OUTPUT=quiet bash ./scripts/real-copilot.sh
	bash ./scripts/present-copilot.sh buyer

demo-copilot-tech:
	bash ./scripts/real-copilot.sh
	bash ./scripts/present-copilot.sh technical

# n8n remains externally run in the pinned UI. These projections fail closed
# unless real output artifacts and matching session-budget evidence exist.
present-n8n:
	bash ./scripts/present-n8n.sh buyer

present-n8n-tech:
	bash ./scripts/present-n8n.sh technical

present-n8n-all:
	bash ./scripts/present-n8n.sh all

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
