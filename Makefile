SHELL := /usr/bin/env bash

.PHONY: all build test vet fmt fmt-check shell-check validate-local integration-local ci clean env bootstrap-config preflight

all: test

build:
	mkdir -p bin
	go build -o bin/copilot-session-shim ./cmd/copilot-session-shim
	go build -o bin/zendesk-adapter ./cmd/zendesk-adapter
	go build -o bin/release-mcp-server ./cmd/release-mcp-server

test:
	go test ./...
	node --test integrations/zendesk-app/test/*.test.cjs

vet:
	go vet ./...

fmt:
	gofmt -w cmd internal

fmt-check:
	@files="$$(find cmd internal -name '*.go' -type f -print)"; \
	unformatted="$$(gofmt -l $$files)"; \
	if [[ -n "$$unformatted" ]]; then echo "Go files need gofmt:" >&2; echo "$$unformatted" >&2; exit 1; fi

shell-check:
	bash -n scripts/*.sh

validate-local: fmt-check vet build test shell-check
	./scripts/validate-local.sh

integration-local: build
	./scripts/test-integration-local.sh

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
