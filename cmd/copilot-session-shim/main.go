package main

import (
	"context"
	"errors"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/dativo-io/talon-full-demo/internal/sessionproxy"
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
	target, err := url.Parse(mustEnv("TALON_GATEWAY"))
	if err != nil || target.Scheme == "" || target.Host == "" {
		log.Fatalf("invalid TALON_GATEWAY")
	}

	bind := os.Getenv("COPILOT_SHIM_BIND")
	if bind == "" {
		bind = "127.0.0.1:8079"
	}
	requireLoopbackBind(bind)

	handler, err := sessionproxy.New(sessionproxy.Config{
		Target:    target,
		SessionID: mustEnv("TALON_COPILOT_SESSION_ID"),
		ClientID:  "github-copilot-cli-full-demo",
	})
	if err != nil {
		log.Fatal(err)
	}

	server := &http.Server{
		Addr:              bind,
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
		IdleTimeout:       90 * time.Second,
		MaxHeaderBytes:    32 << 10,
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := server.Shutdown(shutdownCtx); err != nil {
			log.Printf("Copilot session shim shutdown: %v", err)
		}
	}()

	log.Printf("Copilot session shim listening on http://%s", bind)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
}
