package sessionproxy

import (
	"errors"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"time"
)

type Config struct {
	Target    *url.URL
	SessionID string
	ClientID  string
}

func New(cfg Config) (http.Handler, error) {
	if cfg.Target == nil || cfg.Target.Scheme == "" || cfg.Target.Host == "" {
		return nil, errors.New("target URL is required")
	}
	if cfg.Target.Scheme != "http" && cfg.Target.Scheme != "https" {
		return nil, errors.New("target URL scheme must be http or https")
	}
	if strings.TrimSpace(cfg.SessionID) == "" {
		return nil, errors.New("session ID is required")
	}
	if cfg.ClientID == "" {
		cfg.ClientID = "talon-full-demo"
	}

	proxy := httputil.NewSingleHostReverseProxy(cfg.Target)
	transport := http.DefaultTransport.(*http.Transport).Clone()
	transport.DialContext = (&net.Dialer{Timeout: 10 * time.Second, KeepAlive: 30 * time.Second}).DialContext
	transport.TLSHandshakeTimeout = 10 * time.Second
	transport.ResponseHeaderTimeout = 90 * time.Second
	transport.ExpectContinueTimeout = time.Second
	transport.MaxIdleConns = 32
	transport.MaxIdleConnsPerHost = 16
	transport.IdleConnTimeout = 90 * time.Second
	proxy.Transport = transport
	baseDirector := proxy.Director
	proxy.Director = func(req *http.Request) {
		baseDirector(req)
		req.Header.Set("X-Talon-Session-ID", cfg.SessionID)
		req.Header.Set("X-Talon-Client", cfg.ClientID)
	}
	proxy.ErrorHandler = func(w http.ResponseWriter, _ *http.Request, err error) {
		log.Printf("session proxy error: %v", err)
		http.Error(w, "Talon gateway unavailable", http.StatusBadGateway)
	}
	return proxy, nil
}
