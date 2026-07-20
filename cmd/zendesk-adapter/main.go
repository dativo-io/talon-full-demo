package main

import (
	"context"
	"errors"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
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

func requireLoopbackBind(bind string) {
	host, _, err := net.SplitHostPort(bind)
	if err != nil {
		log.Fatalf("invalid bind address")
	}
	ip := net.ParseIP(host)
	if host != "localhost" && (ip == nil || !ip.IsLoopback()) {
		log.Fatalf("bind address must be loopback")
	}
}

func main() {
	bind := os.Getenv("ZENDESK_ADAPTER_BIND")
	if bind == "" {
		bind = "127.0.0.1:8443"
	}
	requireLoopbackBind(bind)

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

	server := &http.Server{
		Addr:              bind,
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      70 * time.Second,
		IdleTimeout:       60 * time.Second,
		MaxHeaderBytes:    16 << 10,
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := server.Shutdown(shutdownCtx); err != nil {
			log.Printf("Zendesk adapter shutdown: %v", err)
		}
	}()

	log.Printf("Zendesk adapter listening on http://%s; TLS must terminate at the external tunnel", bind)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
}
