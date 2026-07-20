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
		log.Fatalf("invalid TAL