package zendesk

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestDraftUsesConfiguredTalonIdentityRouteModelAndStableSession(t *testing.T) {
	var gotAuth, gotSession, gotClient, gotPath, gotModel string
	talon := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotAuth = r.Header.Get("Authorization")
		gotSession = r.Header.Get("X-Talon-Session-ID")
		gotClient = r.Header.Get("X-Talon-Client")
		gotPath = r.URL.Path
		var input map[string]any
		if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
			t.Fatal(err)
		}
		gotModel, _ = input["model"].(string)
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"choices":[{"message":{"content":"Synthetic governed reply"}}]}`))
	}))
	defer talon.Close()

	handler, err := New(Config{
		AdapterToken: "adapter-secret",
		Gateway:      talon.URL,
		CustomerKey:  "customer-key",
		Provider:     "local-llama",
		Model:        "llama3.2:1b",
	})
	if err != nil {
		t.Fatal(err)
	}
	server := httptest.NewServer(handler)
	defer server.Close()

	payload := `{"ticket_id":"1042","subject":"Refund","requester":{"name":"Demo Customer","email":"demo@example.com"},"message":"Synthetic IBAN DE89370400440532013000"}`
	req, _ := http.NewRequest(http.MethodPost, server.URL+"/v1/zendesk/draft", strings.NewReader(payload))
	req.Header.Set("Authorization", "Bearer adapter-secret")
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()

	var body map[string]string
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		t.Fatal(err)
	}
	if resp.StatusCode != http.StatusOK || body["session_id"] != "zendesk-ticket-1042" {
		t.Fatalf("unexpected response: status=%d body=%v", resp.StatusCode, body)
	}
	if len(body) != 2 || body["draft"] == "" {
		t.Fatalf("adapter response must contain only draft and session_id: %v", body)
	}
	if gotAuth != "Bearer customer-key" || gotSession != "zendesk-ticket-1042" {
		t.Fatalf("wrong Talon identity: auth=%q session=%q", gotAuth, gotSession)
	}
	if gotClient != "zendesk-support-full-demo" {
		t.Fatalf("wrong Talon client attribution: %q", gotClient)
	}
	if gotPath != "/v1/proxy/local-llama/v1/chat/completions" || gotModel != "llama3.2:1b" {
		t.Fatalf("wrong Talon route/model: path=%q model=%q", gotPath, gotModel)
	}
}

func TestDraftRejectsBadAdapterToken(t *testing.T) {
	handler, _ := New(Config{AdapterToken: "expected", Gateway: "http://127.0.0.1:1", CustomerKey: "key"})
	request := httptest.NewRequest(http.MethodPost, "/v1/zendesk/draft", strings.NewReader(`{}`))
	request.Header.Set("Authorization", "Bearer wrong")
	recorder := httptest.NewRecorder()
	handler.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", recorder.Code)
	}
}

func TestDraftRejectsInvalidProviderRouteSegment(t *testing.T) {
	_, err := New(Config{AdapterToken: "expected", Gateway: "http://127.0.0.1:1", CustomerKey: "key", Provider: "../openai"})
	if err == nil {
		t.Fatal("expected invalid provider to fail")
	}
}

func TestDraftRejectsTrailingJSON(t *testing.T) {
	handler, _ := New(Config{AdapterToken: "expected", Gateway: "http://127.0.0.1:1", CustomerKey: "key"})
	request := httptest.NewRequest(http.MethodPost, "/v1/zendesk/draft", strings.NewReader(`{"ticket_id":"1","message":"x"}{}`))
	request.Header.Set("Authorization", "Bearer expected")
	recorder := httptest.NewRecorder()
	handler.ServeHTTP(recorder, request)
	if recorder.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", recorder.Code)
	}
}
