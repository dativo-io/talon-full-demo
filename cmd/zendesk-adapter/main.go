package main

import (
	"log"
	"net/http"
	"os"
	"time"

	"github.com/dativo-io/talon-full-demo/internal/zendesk"
)

func mustEnv(name string) string {
	value := os.Getenv(name)
	if value == "" {
		log.Fatalf("%s is required", name)
	}
	return value
}

func main() {
	bind := os.Getenv("ZENDESK_ADAPTER_BIND")
	if bind == "" {
		bind = "127.0.0.1:8443"
	}

	handler, err := zendesk.New(zendesk.Config{
		AdapterToken: mustEnv("ZENDESK_ADAPTER_TOKEN"),
		Gateway:      mustEnv("TALON_GATEWAY"),
		CustomerKey:  mustEnv("TALON_CUSTOMER_SUPPORT_KEY"),
		Provider:     os.Getenv("TALON_CUSTOMER_SUPPORT_PROVIDER"),
		Model:        os.Getenv("TALON_CUSTOMER_SUPPORT_MODEL"),
		HTTPClient:   &http.Client{Timeout: 65 * time.Second},
	})
	if err != nil {
		log.Fatal(err)
	}

	log.Printf("Zendesk adapter listening on http://%s; TLS must terminate at the external tunnel", bind)
	log.Fatal(http.ListenAndServe(bind, handler))
}
