package main

import (
	"log"
	"net/http"
	"net/url"
	"os"

	"github.com/dativo-io/talon-full-demo/internal/sessionproxy"
)

func mustEnv(name string) string {
	value := os.Getenv(name)
	if value == "" {
		log.Fatalf("%s is required", name)
	}
	return value
}

func main() {
	target, err := url.Parse(mustEnv("TALON_GATEWAY"))
	if err != nil {
		log.Fatalf("invalid TALON_GATEWAY: %v", err)
	}

	bind := os.Getenv("COPILOT_SHIM_BIND")
	if bind == "" {
		bind = "127.0.0.1:8079"
	}

	handler, err := sessionproxy.New(sessionproxy.Config{
		Target:    target,
		SessionID: mustEnv("TALON_COPILOT_SESSION_ID"),
		ClientID:  "github-copilot-cli-full-demo",
	})
	if err != nil {
		log.Fatal(err)
	}

	log.Printf("Copilot session shim listening on http://%s", bind)
	log.Fatal(http.ListenAndServe(bind, handler))
}
