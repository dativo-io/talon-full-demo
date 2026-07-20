package zendesk

import (
	"bytes"
	"context"
	"crypto/subtle"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"time"
)

var (
	ticketIDPattern = regexp.MustCompile(`^[0-9]{1,18}$`)
	providerPattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`)
)

const (
	defaultProvider = "local-llama"
	defaultModel    = "llama3.2:1b"
)

type TicketRequest struct {
	TicketID  string `json:"ticket_id"`
	Subject   string `json:"subject"`
	Requester struct {
		Name  string `json:"name"`
		Email string `json:"email"`
	} `json:"requester"`
	Message string `json:"message"`
}

type Config struct {
	AdapterToken string
	Gateway      string
	CustomerKey  string
	Provider     string
	Model        string
	HTTPClient   *http.Client
}

type adapter struct {
	token       string
	gateway     string
	customerKey string
	provider    string
	model       string
	client      *http.Client
}

type openAIRequest struct {
	Model     string              `json:"model"`
	MaxTokens int                 `json:"max_tokens"`
	Messages  []map[string]string `json:"messages"`
}

type openAIResponse struct {
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	} `json:"choices"`
}

func New(cfg Config) (http.Handler, error) {
	if cfg.AdapterToken == "" || cfg.CustomerKey == "" || cfg.Gateway == "" {
		return nil, errors.New("adapter token, Talon gateway, and customer-support key are required")
	}
	gatewayURL, err := url.Parse(cfg.Gateway)
	if err != nil || gatewayURL.Host == "" || (gatewayURL.Scheme != "http" && gatewayURL.Scheme != "https") {
		return nil, errors.New("Talon gateway must be an absolute http or https URL")
	}
	if cfg.Provider == "" {
		cfg.Provider = defaultProvider
	}
	if cfg.Model == "" {
		cfg.Model = defaultModel
	}
	if !providerPattern.MatchString(cfg.Provider) {
		return nil, errors.New("provider must be a safe Talon route segment")
	}
	if strings.TrimSpace(cfg.Model) == "" || len(cfg.Model) > 200 {
		return nil, errors.New("model is required and must be at most 200 characters")
	}
	if cfg.HTTPClient == nil {
		cfg.HTTPClient = &http.Client{Timeout: 65 * time.Second}
	}

	a := &adapter{
		token:       cfg.AdapterToken,
		gateway:     strings.TrimRight(cfg.Gateway, "/"),
		customerKey: cfg.CustomerKey,
		provider:    cfg.Provider,
		model:       cfg.Model,
		client:      cfg.HTTPClient,
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/health", a.health)
	mux.HandleFunc("/v1/zendesk/draft", a.draft)
	return mux, nil
}

func bearerOK(header, expected string) bool {
	const prefix = "Bearer "
	if !strings.HasPrefix(header, prefix) {
		return false
	}
	got := strings.TrimSpace(strings.TrimPrefix(header, prefix))
	if len(got) != len(expected) {
		return false
	}
	return subtle.ConstantTimeCompare([]byte(got), []byte(expected)) == 1
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

// adapterError is the safe machine contract the browser receives on failure:
// a stable code and a retryable hint, never the upstream body. The UI can use
// `code` to decide retry vs escalate vs contact-the-integration-owner while
// still showing the operator a safe generic message.
type adapterError struct {
	Code      string `json:"code"`
	Error     string `json:"error"`
	Retryable bool   `json:"retryable"`
	SessionID string `json:"session_id,omitempty"`
}

func writeError(w http.ResponseWriter, status int, code, message string, retryable bool, sessionID string) {
	writeJSON(w, status, adapterError{Code: code, Error: message, Retryable: retryable, SessionID: sessionID})
}

func (a *adapter) health(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (a *adapter) draft(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if !bearerOK(r.Header.Get("Authorization"), a.token) {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
		return
	}

	r.Body = http.MaxBytesReader(w, r.Body, 64<<10)
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	var input TicketRequest
	if err := decoder.Decode(&input); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid request"})
		return
	}
	var extra any
	if err := decoder.Decode(&extra); !errors.Is(err, io.EOF) {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid request"})
		return
	}
	if !ticketIDPattern.MatchString(input.TicketID) || strings.TrimSpace(input.Message) == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "ticket_id and message are required"})
		return
	}
	if len(input.Subject) > 500 || len(input.Requester.Name) > 200 || len(input.Requester.Email) > 320 || len(input.Message) > 20000 {
		writeJSON(w, http.StatusRequestEntityTooLarge, map[string]string{"error": "request too large"})
		return
	}

	sessionID := "zendesk-ticket-" + input.TicketID
	prompt := fmt.Sprintf(
		`Synthetic Zendesk ticket %s
Subject: %s
Requester: %s
Email: %s
Latest requester message:
%s`,
		input.TicketID,
		input.Subject,
		input.Requester.Name,
		input.Requester.Email,
		input.Message,
	)
	requestBody := openAIRequest{
		Model:     a.model,
		MaxTokens: 220,
		Messages: []map[string]string{
			{"role": "system", "content": "Draft a concise support reply. All data is synthetic. Do not include a signature block."},
			{"role": "user", "content": prompt},
		},
	}
	raw, err := json.Marshal(requestBody)
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "adapter error"})
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 60*time.Second)
	defer cancel()
	endpoint := fmt.Sprintf("%s/v1/proxy/%s/v1/chat/completions", a.gateway, a.provider)
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(raw))
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "adapter error"})
		return
	}
	request.Header.Set("Authorization", "Bearer "+a.customerKey)
	request.Header.Set("X-Talon-Session-ID", sessionID)
	request.Header.Set("X-Talon-Client", "zendesk-support-full-demo")
	request.Header.Set("Content-Type", "application/json")

	response, err := a.client.Do(request)
	if err != nil {
		writeError(w, http.StatusBadGateway, "service_unavailable", "Talon gateway unavailable", true, sessionID)
		return
	}
	defer response.Body.Close()
	limited := io.LimitReader(response.Body, (2<<20)+1)
	body, err := io.ReadAll(limited)
	if err != nil || len(body) > 2<<20 {
		writeError(w, http.StatusBadGateway, "service_unavailable", "invalid Talon response", true, sessionID)
		return
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		log.Printf("Talon denied or failed Zendesk session=%s status=%d", sessionID, response.StatusCode)
		// Return a small safe machine contract (code + retryable) so the UI can
		// decide retry vs escalate vs contact-the-integration-owner, WITHOUT ever
		// forwarding the upstream body. Only a genuine policy/budget denial
		// (Talon's 403) may claim "policy"; a 401/429/other-4xx must not, or the
		// adapter would report "policy worked" when the integration is actually
		// misconfigured or throttled. Talon's contract (internal/gateway/gateway.go):
		//   401 Invalid or missing agent key, 403 policy/budget/agent-disabled
		//   deny, 429 Rate limit exceeded.
		switch {
		case response.StatusCode == http.StatusForbidden:
			// The one status that is a Talon policy/budget decision.
			writeError(w, http.StatusForbidden, "policy_denied", "request denied by Talon policy", false, sessionID)
		case response.StatusCode == http.StatusUnauthorized:
			// The adapter's own Talon agent key is wrong or missing: an
			// integration configuration failure, not a policy outcome.
			writeError(w, http.StatusBadGateway, "integration_misconfigured", "governed draft unavailable", false, sessionID)
		case response.StatusCode == http.StatusTooManyRequests:
			// Keep 429 distinguishable so throttling is not mistaken for a denial.
			writeError(w, http.StatusTooManyRequests, "rate_limited", "rate limited by Talon", true, sessionID)
		default:
			// Any other non-2xx (other 4xx, 5xx, malformed route): an
			// availability/integration failure that makes no policy claim.
			writeError(w, http.StatusBadGateway, "service_unavailable", "governed draft unavailable", true, sessionID)
		}
		return
	}

	var output openAIResponse
	if err := json.Unmarshal(body, &output); err != nil || len(output.Choices) == 0 || strings.TrimSpace(output.Choices[0].Message.Content) == "" {
		writeError(w, http.StatusBadGateway, "service_unavailable", "Talon returned no draft", true, sessionID)
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{
		"draft":      output.Choices[0].Message.Content,
		"session_id": sessionID,
	})
}
