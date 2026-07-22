SHELL := /usr/bin/env bash

.PHONY: all check-go build test vet fmt fmt-check shell-check validate-local integration-local ci clean env bootstrap-config preflight live-check real-prepare real-start real-smoke real-copilot real-status real-stop

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

real-smoke:
	bash ./scripts/real-stack.sh smoke

real-copilot:
	bash ./scripts/real-demo.sh copilot

real-status:
	bash ./scripts/real-demo.sh status

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
