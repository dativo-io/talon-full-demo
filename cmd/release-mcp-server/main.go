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

	"github.com/dativo-io/talon-full-demo/internal/releasemcp"
)

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
	bind := os.Getenv("RELEASE_MCP_BIND")
	if bind == "" {
		bind = "127.0.0.1:8090"
	}
	requireLoopbackBind(bind)
	receipts := os.Getenv("RELEASE_MCP_RECEIPTS")
	if receipts == "" {
		receipts = ".state/release-mcp-receipts.jsonl"
	}

	handler, err := releasemcp.New(releasemcp.Config{ReceiptPath: receipts})
	if err != nil {
		log.Fatal(err)
	}
	server := &http.Server{
		Addr:              bind,
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
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
			log.Printf("release MCP server shutdown: %v", err)
		}
	}()

	log.Printf("synthetic release MCP server listening on http://%s", bind)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
}
