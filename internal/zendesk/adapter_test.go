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

func denialTestHandler(t *testing.T, talonStatus int, talonBody string) http.Handler {
	t.Helper()
	talon := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(talonStatus)
		_, _ = w.Write([]byte(talonBody))
	}))
	t.Cleanup(talon.Close)
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
	return handler
}

func doDraft(t *testing.T, handler http.Handler) (*http.Response, map[string]string) {
	t.Helper()
	server := httptest.NewServer(handler)
	t.Cleanup(server.Close)
	payload := `{"ticket_id":"7","subject":"s","requester":{"name":"n","email":"e@example.com"},"message":"m"}`
	req, _ := http.NewRequest(http.MethodPost, server.URL+"/v1/zendesk/draft", strings.NewReader(payload))
	req.Header.Set("Authorization", "Bearer adapter-secret")
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { resp.Body.Close() })
	var body map[string]string
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		t.Fatal(err)
	}
	return resp, body
}

func TestDraftSurfacesTalonPolicyDenialAs403WithoutLeakingUpstreamBody(t *testing.T) {
	upstream := `{"error":{"message":"denied: session_budget_exceeded: cap reached","type":"session_budget_exceeded","code":"session_budget_exceeded"}}`
	resp, body := doDraft(t, denialTestHandler(t, http.StatusForbidden, upstream))
	if resp.StatusCode != http.StatusForbidden {
		t.Fatalf("Talon 403 must surface as 403, got %d", resp.StatusCode)
	}
	if body["error"] != "request denied by Talon policy" || body["session_id"] != "zendesk-ticket-7" {
		t.Fatalf("unexpected denial body: %v", body)
	}
	for _, v := range body {
		if strings.Contains(v, "session_budget_exceeded") {
			t.Fatalf("upstream error body leaked to the client: %v", body)
		}
	}
}

func TestDraftSurfacesTalonOutageAs502DistinctFromDenial(t *testing.T) {
	resp, body := doDraft(t, denialTestHandler(t, http.StatusBadGateway, `{"error":"upstream provider unreachable"}`))
	if resp.StatusCode != http.StatusBadGateway {
		t.Fatalf("Talon 5xx must surface as 502, got %d", resp.StatusCode)
	}
	if body["error"] != "governed draft unavailable" {
		t.Fatalf("unexpected outage body: %v", body)
	}
}

// A Talon 401 means the adapter's own agent key is wrong or missing: an
// integration misconfiguration. It must NOT be reported as a policy denial,
// or the operator would conclude "policy worked" when nothing was governed.
func TestDraftTreatsTalon401AsIntegrationFailureNotPolicy(t *testing.T) {
	resp, body := doDraft(t, denialTestHandler(t, http.StatusUnauthorized, `{"error":"Invalid or missing agent key"}`))
	if resp.StatusCode != http.StatusBadGateway {
		t.Fatalf("Talon 401 must surface as 502, got %d", resp.StatusCode)
	}
	if strings.Contains(body["error"], "policy") == false || strings.Contains(body["error"], "not a policy denial") == false {
		t.Fatalf("401 must be marked as an integration failure, not a policy denial: %v", body)
	}
	if body["error"] == "request denied by Talon policy" {
		t.Fatalf("401 must not claim a policy denial: %v", body)
	}
}

// A Talon 429 must stay distinguishable so throttling is not mistaken for a
// denial or an outage.
func TestDraftKeepsTalon429Distinguishable(t *testing.T) {
	resp, body := doDraft(t, denialTestHandler(t, http.StatusTooManyRequests, `{"error":"Rate limit exceeded"}`))
	if resp.StatusCode != http.StatusTooManyRequests {
		t.Fatalf("Talon 429 must surface as 429, got %d", resp.StatusCode)
	}
	if body["error"] != "rate limited by Talon" {
		t.Fatalf("unexpected 429 body: %v", body)
	}
}

// An unexpected 4xx (e.g. 404 wrong route) must fail generically and make no
// policy claim.
func TestDraftDoesNotClaimPolicyForUnexpected4xx(t *testing.T) {
	resp, body := doDraft(t, denialTestHandler(t, http.StatusNotFound, `{"error":"no such route"}`))
	if resp.StatusCode != http.StatusBadGateway {
		t.Fatalf("unexpected 4xx must surface as 502, got %d", resp.StatusCode)
	}
	if body["error"] != "governed draft unavailable" {
		t.Fatalf("unexpected 4xx must not claim a policy denial: %v", body)
	}
}
