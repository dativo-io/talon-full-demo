package releasemcp

import (
	"bufio"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestToolCallWritesSyntheticExecutionReceipt(t *testing.T) {
	receiptPath := filepath.Join(t.TempDir(), "receipts.jsonl")
	handler, err := New(Config{ReceiptPath: receiptPath})
	if err != nil {
		t.Fatal(err)
	}
	server := httptest.NewServer(handler)
	defer server.Close()

	body := `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"release_prepare","arguments":{"version":"demo","run_nonce":"abc123"}}}`
	response, err := http.Post(server.URL+"/mcp", "application/json", strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	_ = response.Body.Close()

	file, err := os.Open(receiptPath)
	if err != nil {
		t.Fatal(err)
	}
	defer file.Close()
	scanner := bufio.NewScanner(file)
	if !scanner.Scan() {
		t.Fatal("expected receipt")
	}
	var receipt map[string]any
	if err := json.Unmarshal(scanner.Bytes(), &receipt); err != nil {
		t.Fatal(err)
	}
	if receipt["tool"] != "release_prepare" || receipt["synthetic"] != true {
		t.Fatalf("unexpected receipt: %v", receipt)
	}
	args, _ := receipt["arguments"].(map[string]any)
	if args["run_nonce"] != "abc123" {
		t.Fatalf("receipt must carry the run_nonce: %v", receipt)
	}
}

// The advertised tool schema must declare run_nonce as required, or a
// conforming MCP client (which sends only declared properties) would omit it
// and the run-correlation proof would break. Talon's proxy forwards each tool
// object verbatim, so this is the schema the real client sees.
func TestToolsListAdvertisesRunNonceRequired(t *testing.T) {
	handler, err := New(Config{ReceiptPath: filepath.Join(t.TempDir(), "receipts.jsonl")})
	if err != nil {
		t.Fatal(err)
	}
	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/mcp", strings.NewReader(`{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}`))
	handler.ServeHTTP(recorder, request)

	var out struct {
		Result struct {
			Tools []struct {
				Name        string `json:"name"`
				InputSchema struct {
					Properties           map[string]any `json:"properties"`
					Required             []string       `json:"required"`
					AdditionalProperties bool           `json:"additionalProperties"`
				} `json:"inputSchema"`
			} `json:"tools"`
		} `json:"result"`
	}
	if err := json.Unmarshal(recorder.Body.Bytes(), &out); err != nil {
		t.Fatal(err)
	}
	if len(out.Result.Tools) != 3 {
		t.Fatalf("expected 3 advertised tools, got %d", len(out.Result.Tools))
	}
	for _, tool := range out.Result.Tools {
		if _, ok := tool.InputSchema.Properties["run_nonce"]; !ok {
			t.Fatalf("tool %s does not advertise run_nonce", tool.Name)
		}
		found := false
		for _, r := range tool.InputSchema.Required {
			if r == "run_nonce" {
				found = true
			}
		}
		if !found {
			t.Fatalf("tool %s does not mark run_nonce required", tool.Name)
		}
	}
}

func TestRejectsMissingOrMalformedRunNonce(t *testing.T) {
	for _, tc := range []struct {
		name string
		args string
	}{
		{"missing", `{"version":"demo"}`},
		{"empty", `{"version":"demo","run_nonce":""}`},
		{"non-string", `{"version":"demo","run_nonce":42}`},
	} {
		t.Run(tc.name, func(t *testing.T) {
			receiptPath := filepath.Join(t.TempDir(), "receipts.jsonl")
			handler, err := New(Config{ReceiptPath: receiptPath})
			if err != nil {
				t.Fatal(err)
			}
			recorder := httptest.NewRecorder()
			body := `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"release_status","arguments":` + tc.args + `}}`
			handler.ServeHTTP(recorder, httptest.NewRequest(http.MethodPost, "/mcp", strings.NewReader(body)))
			if !strings.Contains(recorder.Body.String(), `"code":-32602`) {
				t.Fatalf("expected -32602 for %s run_nonce: %s", tc.name, recorder.Body.String())
			}
			if info, _ := os.Stat(receiptPath); info != nil && info.Size() != 0 {
				t.Fatalf("a call with %s run_nonce must not write a receipt", tc.name)
			}
		})
	}
}

func TestRejectsInvalidJSONRPCVersionBeforeReceipt(t *testing.T) {
	receiptPath := filepath.Join(t.TempDir(), "receipts.jsonl")
	handler, err := New(Config{ReceiptPath: receiptPath})
	if err != nil {
		t.Fatal(err)
	}
	recorder := httptest.NewRecorder()
	request := httptest.NewRequest(http.MethodPost, "/mcp", strings.NewReader(`{"jsonrpc":"1.0","id":1,"method":"tools/call","params":{"name":"release_publish"}}`))
	handler.ServeHTTP(recorder, request)
	if !strings.Contains(recorder.Body.String(), `"code":-32600`) {
		t.Fatalf("expected invalid request response: %s", recorder.Body.String())
	}
	info, err := os.Stat(receiptPath)
	if err != nil {
		t.Fatal(err)
	}
	if info.Size() != 0 {
		t.Fatal("invalid JSON-RPC request must not write a receipt")
	}
}
