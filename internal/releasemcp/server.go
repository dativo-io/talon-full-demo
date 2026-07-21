package releasemcp

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type Config struct {
	ReceiptPath string
}

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type callParams struct {
	Name      string         `json:"name"`
	Arguments map[string]any `json:"arguments"`
}

type server struct {
	receiptPath string
	mu          sync.Mutex
}

func New(cfg Config) (http.Handler, error) {
	if cfg.ReceiptPath == "" {
		return nil, errors.New("receipt path is required")
	}
	dir := filepath.Dir(cfg.ReceiptPath)
	if dir != "." {
		if err := os.MkdirAll(dir, 0o700); err != nil {
			return nil, fmt.Errorf("creating receipt directory: %w", err)
		}
	}
	file, err := os.OpenFile(cfg.ReceiptPath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
	if err != nil {
		return nil, fmt.Errorf("opening receipt file: %w", err)
	}
	if err := file.Close(); err != nil {
		return nil, fmt.Errorf("closing receipt file: %w", err)
	}

	s := &server{receiptPath: cfg.ReceiptPath}
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"status":"ok","service":"synthetic-release-mcp"}`))
	})
	mux.HandleFunc("/mcp", s.handle)
	return mux, nil
}

func (s *server) writeReceipt(name string, args map[string]any) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	file, err := os.OpenFile(s.receiptPath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
	if err != nil {
		return err
	}
	defer file.Close()
	return json.NewEncoder(file).Encode(map[string]any{
		"time":      time.Now().UTC().Format(time.RFC3339Nano),
		"tool":      name,
		"arguments": args,
		"synthetic": true,
	})
}

func reply(w http.ResponseWriter, id json.RawMessage, result any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	_ = json.NewEncoder(w).Encode(map[string]any{"jsonrpc": "2.0", "id": normalizedID(id), "result": result})
}

func rpcError(w http.ResponseWriter, id json.RawMessage, code int, message string) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	_ = json.NewEncoder(w).Encode(map[string]any{
		"jsonrpc": "2.0",
		"id":      normalizedID(id),
		"error":   map[string]any{"code": code, "message": message},
	})
}

func normalizedID(id json.RawMessage) any {
	if len(id) == 0 {
		return nil
	}
	return id
}

func (s *server) handle(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20))
	decoder.DisallowUnknownFields()
	var request rpcRequest
	if err := decoder.Decode(&request); err != nil {
		rpcError(w, nil, -32700, "parse error")
		return
	}
	var extra any
	if err := decoder.Decode(&extra); !errors.Is(err, io.EOF) {
		rpcError(w, request.ID, -32700, "parse error")
		return
	}
	if request.JSONRPC != "2.0" || request.Method == "" {
		rpcError(w, request.ID, -32600, "invalid request")
		return
	}

	switch request.Method {
	case "initialize":
		reply(w, request.ID, map[string]any{
			"protocolVersion": "2025-03-26",
			"capabilities":    map[string]any{"tools": map[string]any{"listChanged": false}},
			"serverInfo":      map[string]string{"name": "talon-demo-release", "version": "0.1.0"},
		})
	case "notifications/initialized":
		w.WriteHeader(http.StatusAccepted)
	case "tools/list":
		tools := make([]map[string]any, 0, 3)
		for _, name := range []string{"release_status", "release_prepare", "release_publish"} {
			tools = append(tools, map[string]any{
				"name":        name,
				"description": "Safe synthetic release operation for the Talon full demo; it cannot publish externally",
				// run_nonce MUST be advertised and required: the demo correlates
				// upstream receipts to the current run by this nonce
				// (scripts/assert-release-blocked.sh), and a conforming MCP
				// client sends only declared properties. Talon's proxy forwards
				// each tool object verbatim (filtering by name only), so this is
				// the schema the real client sees. additionalProperties:false is
				// kept so the client sends exactly {version?, run_nonce}.
				"inputSchema": map[string]any{
					"type": "object",
					"properties": map[string]any{
						"version":   map[string]any{"type": "string"},
						"run_nonce": map[string]any{"type": "string", "minLength": 1, "description": "Per-run correlation nonce from scripts/preflight.sh (.state/run-nonce)"},
					},
					"required":             []string{"run_nonce"},
					"additionalProperties": false,
				},
			})
		}
		reply(w, request.ID, map[string]any{"tools": tools})
	case "tools/call":
		var params callParams
		if err := json.Unmarshal(request.Params, &params); err != nil {
			rpcError(w, request.ID, -32602, "invalid params")
			return
		}
		switch params.Name {
		case "release_status", "release_prepare", "release_publish":
		default:
			rpcError(w, request.ID, -32602, "unknown tool")
			return
		}
		// Enforce the advertised schema server-side: run_nonce is required and
		// must be a non-empty string. Without this the receipt could carry no
		// nonce (or a non-string one) and the run-correlation proof would be
		// vacuous. Applies to all tools so the schema and validation match.
		if nonce, ok := params.Arguments["run_nonce"].(string); !ok || nonce == "" {
			rpcError(w, request.ID, -32602, "run_nonce is required and must be a non-empty string")
			return
		}
		if err := s.writeReceipt(params.Name, params.Arguments); err != nil {
			rpcError(w, request.ID, -32603, "receipt write failed")
			return
		}
		reply(w, request.ID, map[string]any{
			"content": []map[string]any{{"type": "text", "text": fmt.Sprintf("Synthetic %s completed; no external release action exists", params.Name)}},
			"isError": false,
		})
	default:
		rpcError(w, request.ID, -32601, "method not found")
	}
}
