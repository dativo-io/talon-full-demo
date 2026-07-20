package sessionproxy

import (
	"bufio"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
)

func TestProxyPreservesRequestPathQueryBodyAuthorizationAndStreaming(t *testing.T) {
	var gotPath, gotQuery, gotAuth, gotSession, gotClient, gotBody string
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		gotQuery = r.URL.RawQuery
		gotAuth = r.Header.Get("Authorization")
		gotSession = r.Header.Get("X-Talon-Session-ID")
		gotClient = r.Header.Get("X-Talon-Client")
		body, _ := io.ReadAll(r.Body)
		gotBody = string(body)
		w.Header().Set("Content-Type", "text/event-stream")
		flusher := w.(http.Flusher)
		_, _ = io.WriteString(w, "data: first\n\n")
		flusher.Flush()
		_, _ = io.WriteString(w, "data: second\n\n")
	}))
	defer upstream.Close()

	target, _ := url.Parse(upstream.URL)
	handler, err := New(Config{Target: target, SessionID: "copilot-demo", ClientID: "copilot"})
	if err != nil {
		t.Fatal(err)
	}
	proxy := httptest.NewServer(handler)
	defer proxy.Close()

	req, _ := http.NewRequest(http.MethodPost, proxy.URL+"/v1/proxy/openai/v1/chat/completions?stream=true", strings.NewReader(`{"model":"gpt-4o"}`))
	req.Header.Set("Authorization", "Bearer coding-key")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	scanner := bufio.NewScanner(resp.Body)
	var lines []string
	for scanner.Scan() {
		if scanner.Text() != "" {
			lines = append(lines, scanner.Text())
		}
	}
	if err := scanner.Err(); err != nil {
		t.Fatal(err)
	}

	if gotPath != "/v1/proxy/openai/v1/chat/completions" || gotQuery != "stream=true" {
		t.Fatalf("unexpected target: path=%q query=%q", gotPath, gotQuery)
	}
	if gotAuth != "Bearer coding-key" || gotSession != "copilot-demo" || gotClient != "copilot" {
		t.Fatalf("headers changed or missing: auth=%q session=%q client=%q", gotAuth, gotSession, gotClient)
	}
	if gotBody != `{"model":"gpt-4o"}` {
		t.Fatalf("body changed: %s", gotBody)
	}
	if strings.Join(lines, "|") != "data: first|data: second" {
		t.Fatalf("stream not preserved: %v", lines)
	}
}

func TestProxyRejectsUnsupportedTargetScheme(t *testing.T) {
	target, _ := url.Parse("file:///tmp/socket")
	if _, err := New(Config{Target: target, SessionID: "s"}); err == nil {
		t.Fatal("expected unsupported target scheme to fail")
	}
}
