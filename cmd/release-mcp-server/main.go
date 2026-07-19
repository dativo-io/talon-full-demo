package main

import (
	"log"
	"net/http"
	"os"

	"github.com/dativo-io/talon-full-demo/internal/releasemcp"
)

func main() {
	bind := os.Getenv("RELEASE_MCP_BIND")
	if bind == "" {
		bind = "127.0.0.1:8090"
	}
	receipts := os.Getenv("RELEASE_MCP_RECEIPTS")
	if receipts == "" {
		receipts = ".state/release-mcp-receipts.jsonl"
	}

	handler, err := releasemcp.New(releasemcp.Config{ReceiptPath: receipts})
	if err != nil {
		log.Fatal(err)
	}
	log.Printf("synthetic release MCP server listening on http://%s", bind)
	log.Fatal(http.ListenAndServe(bind, handler))
}
