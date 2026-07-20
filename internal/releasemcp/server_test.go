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

	body := `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"release_prepare","arguments":{"version":"demo"}}}`
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
