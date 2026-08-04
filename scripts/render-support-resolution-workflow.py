#!/usr/bin/env python3
"""Render the support workflow with a blocking operator-approval continuation gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REMOVE = {
    "Build Resolution Packet",
    "Write Resolution Packet",
    "Build Resolution Status",
    "Write Resolution Status",
}


def code_node(node_id: str, name: str, position: list[int], js_code: str) -> dict[str, Any]:
    return {
        "parameters": {"mode": "runOnceForEachItem", "jsCode": js_code},
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": position,
    }


def http_node(
    node_id: str,
    name: str,
    position: list[int],
    method: str,
    url: str,
    *,
    json_body: str | None = None,
    timeout: int = 10_000,
) -> dict[str, Any]:
    parameters: dict[str, Any] = {
        "method": method,
        "url": url,
        "options": {
            "timeout": timeout,
            "response": {
                "response": {
                    "fullResponse": True,
                    "neverError": True,
                    "responseFormat": "json",
                }
            },
        },
    }
    if json_body is not None:
        parameters.update(
            {
                "sendHeaders": True,
                "specifyHeaders": "keypair",
                "headerParameters": {
                    "parameters": [{"name": "Content-Type", "value": "application/json"}]
                },
                "sendBody": True,
                "contentType": "json",
                "specifyBody": "json",
                "jsonBody": json_body,
            }
        )
    return {
        "parameters": parameters,
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.4,
        "position": position,
    }


def write_node(
    node_id: str,
    name: str,
    position: list[int],
    binary_property: str,
    path: str,
) -> dict[str, Any]:
    return {
        "parameters": {
            "operation": "write",
            "fileName": path,
            "dataPropertyName": binary_property,
            "options": {},
        },
        "id": node_id,
        "name": name,
        "type": "n8n-nodes-base.readWriteFile",
        "typeVersion": 1.1,
        "position": position,
    }


def edge(target: str) -> dict[str, Any]:
    return {"node": target, "type": "main", "index": 0}


def one(nodes: list[dict[str, Any]], name: str) -> dict[str, Any]:
    matches = [node for node in nodes if node.get("name") == name]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one node named {name!r}")
    return matches[0]


def js_single_quoted(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        .replace("'", "\\'")
    )
    return "'" + escaped + "'"


REQUIRE_REPLY_JS = r"""const source = $('Assemble Support Case').item.json;
const status = Number($json.statusCode || 0);
const text = $json.body?.choices?.[0]?.message?.content;
if (status !== 200 || typeof text !== 'string' || !text.trim()) {
  throw new Error(`Support reply draft failed: HTTP ${status} ${JSON.stringify($json.body)}`);
}
let body = text.trim().replace(/^Subject:.*(?:\r?\n)+/i, '');
body = body.replace(/^(?:Dear|Hi)\s+[^,\n]+,\s*/i, 'Hello,\n\n');
const closing = body.search(/\n(?:Best regards|Kind regards|Regards|Sincerely),?/i);
if (closing >= 0) body = body.slice(0, closing).trim();
if (!/^Hello,/i.test(body)) body = `Hello,\n\n${body}`;
if (/\[\[[^\]]+\]\]/.test(body)) throw new Error('Reply contains a redaction placeholder');
if (/anna\.kowalska@example\.test|PL61109010140000071219812874/i.test(body)) throw new Error('Reply contains a raw synthetic identifier');
if (/refund (?:has been|was|is) (?:issued|completed|processed)|money (?:has been|was) returned/i.test(body)) throw new Error('Reply incorrectly claims the refund was executed');
return { json: { ...source, reply_body: body, entry_requested_model: 'llama3.2:1b', fallback_target_model: 'gpt-4o-mini', provider_reported_model: String($json.body?.model || 'not-recorded') } };"""

REQUIRE_PENDING_JS = r"""const source = $('Require Refund Action Denial').item.json;
const status = Number($json.statusCode || 0);
const request = $json.body?.request;
if (![200, 201].includes(status) || $json.body?.status !== 'pending' || !request) {
  throw new Error(`Approval request failed: HTTP ${status} ${JSON.stringify($json.body)}`);
}
if (request.approval_id !== $env.TALON_SUPPORT_APPROVAL_ID || request.session_id !== $env.TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID || request.run_nonce !== $env.RELEASE_RUN_NONCE || request.ticket_id !== source.ticket_id || Number(request.amount_eur) !== source.refund_amount_eur || request.requested_action !== source.blocked_tool) {
  throw new Error('Approval request binding mismatch');
}
return { json: { ...source, approval_id: request.approval_id, approval_url: String($json.body.approval_url || '') } };"""

VALIDATE_DECISION_JS = r"""const source = $('Require Pending Approval').item.json;
const status = Number($json.statusCode || 0);
const receipt = $json.body;
if (status !== 200 || !receipt || !['approved', 'rejected'].includes(receipt.decision) || typeof receipt.signature !== 'string') {
  throw new Error(`Operator decision failed: HTTP ${status} ${JSON.stringify($json.body)}`);
}
if (receipt.approval_id !== source.approval_id || receipt.session_id !== $env.TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID || receipt.run_nonce !== $env.RELEASE_RUN_NONCE || receipt.ticket_id !== source.ticket_id || Number(receipt.amount_eur) !== source.refund_amount_eur || receipt.requested_action !== source.blocked_tool || receipt.refund_executed !== false) {
  throw new Error('Operator approval receipt binding mismatch');
}
return { json: { ...source, operator_decision: receipt.decision, operator_approval_receipt: receipt, human_approval_completed: true } };"""

APPROVED_JS = r"""const source = $json;
const createdAt = new Date().toISOString();
const receipt = source.operator_approval_receipt;
const finance = { approval_id: source.approval_id, session_id: receipt.session_id, run_nonce: receipt.run_nonce, ticket_id: source.ticket_id, amount_eur: source.refund_amount_eur, requested_action: source.blocked_tool, status: 'approved_for_finance_processing', refund_executed: false, approval_decided_at: receipt.decided_at, created_at: createdAt };
const status = { status: 'completed', result: 'governed_support_resolution', session_id: receipt.session_id, run_nonce: receipt.run_nonce, operational_id: 'customer-support', documents_read: source.document_count, ticket_id: source.ticket_id, refund_amount_eur: source.refund_amount_eur, reply_draft_created: true, blocked_tool: source.blocked_tool, denial_code: source.denial_code, denied_provider_cost_usd: 0, action_status: 'approved_for_finance_processing', operator_approval_required: true, human_approval_completed: true, operator_decision: 'approved', approval_id: source.approval_id, entry_requested_model: source.entry_requested_model, fallback_target_model: source.fallback_target_model, provider_reported_model: source.provider_reported_model, pii_expected: ['email', 'iban'], report_file: 'customer-support-resolution.md', approval_receipt_file: 'operator-approval-receipt.json', finance_handoff_file: 'finance-refund-request.json', refund_executed: false };
const markdown = `# Synthetic customer-support resolution\n\n> The reply is a draft. The EUR ${source.refund_amount_eur} refund was not executed. A demo operator approved only the synthetic finance handoff.\n\n## Ticket\n\n${source.ticket_id} — plausible duplicate Enterprise renewal charge.\n\n## Customer reply draft\n\n${source.reply_body}\n\nBest regards,\nACME Support Team\n\n## Action status\n\n- Requested AI action: ${source.blocked_tool}\n- AI result: blocked before provider dispatch\n- Provider cost for denied request: USD 0\n- Human decision: approved synthetic finance handoff\n- Refund executed: no\n`;
const binary = (value, mimeType, fileName) => ({ data: Buffer.from(typeof value === 'string' ? value : JSON.stringify(value, null, 2) + '\n', 'utf8').toString('base64'), mimeType, fileName });
return { json: status, binary: { approval: binary(receipt, 'application/json', 'operator-approval-receipt.json'), finance: binary(finance, 'application/json', 'finance-refund-request.json'), report: binary(markdown, 'text/markdown', 'customer-support-resolution.md'), status: binary(status, 'application/json', 'status.json') } };"""

REJECTED_JS = r"""const source = $json;
const receipt = source.operator_approval_receipt;
const status = { status: 'completed', result: 'governed_support_resolution_rejected', session_id: receipt.session_id, run_nonce: receipt.run_nonce, operational_id: 'customer-support', documents_read: source.document_count, ticket_id: source.ticket_id, refund_amount_eur: source.refund_amount_eur, reply_draft_created: true, blocked_tool: source.blocked_tool, denial_code: source.denial_code, denied_provider_cost_usd: 0, action_status: 'human_rejected', operator_approval_required: true, human_approval_completed: true, operator_decision: 'rejected', approval_id: source.approval_id, entry_requested_model: source.entry_requested_model, fallback_target_model: source.fallback_target_model, provider_reported_model: source.provider_reported_model, pii_expected: ['email', 'iban'], report_file: 'customer-support-resolution.md', approval_receipt_file: 'operator-approval-receipt.json', finance_handoff_file: null, refund_executed: false };
const markdown = `# Synthetic customer-support resolution\n\n> The reply is a draft. The EUR ${source.refund_amount_eur} refund was not executed. The demo operator rejected the synthetic finance handoff.\n\n## Ticket\n\n${source.ticket_id} — plausible duplicate Enterprise renewal charge.\n\n## Customer reply draft\n\n${source.reply_body}\n\nBest regards,\nACME Support Team\n\n## Action status\n\n- Requested AI action: ${source.blocked_tool}\n- AI result: blocked before provider dispatch\n- Provider cost for denied request: USD 0\n- Human decision: rejected\n- Finance handoff created: no\n- Refund executed: no\n`;
const binary = (value, mimeType, fileName) => ({ data: Buffer.from(typeof value === 'string' ? value : JSON.stringify(value, null, 2) + '\n', 'utf8').toString('base64'), mimeType, fileName });
return { json: status, binary: { approval: binary(receipt, 'application/json', 'operator-approval-receipt.json'), report: binary(markdown, 'text/markdown', 'customer-support-resolution.md'), status: binary(status, 'application/json', 'status.json') } };"""


def render(source: dict[str, Any]) -> dict[str, Any]:
    nodes = [node for node in source["nodes"] if node.get("name") not in REMOVE]

    prompt = (
        "Using only the synthetic ticket, account context, and refund policy below, "
        "write only the body of a concise customer reply. Start with exactly Hello,. "
        "Acknowledge the likely duplicate charge and say that the refund request requires "
        "human support and finance approval. Do not claim that money has already been returned. "
        "Do not include a subject line, customer name, agent name, signature, closing, company "
        "sign-off, personal identifiers, banking identifiers, or placeholder tokens. End before "
        "any closing or signature.\n\n"
    )
    draft = one(nodes, "Draft Reply Through Talon")
    draft["parameters"]["jsonBody"] = (
        "={{ "
        "{ model: 'llama3.2:1b', max_tokens: 350, messages: ["
        "{ role: 'user', content: "
        + js_single_quoted(prompt)
        + " + $json.case_package }"
        "] }"
        " }}"
    )

    one(nodes, "Require Reply Draft")["parameters"]["jsCode"] = REQUIRE_REPLY_JS

    nodes.extend(
        [
            http_node(
                "approval-create-0001",
                "Create Human Approval Request",
                [0, 120],
                "POST",
                "={{ $env.TALON_SUPPORT_APPROVAL_URL + '/requests' }}",
                json_body="={{ { approval_id: $env.TALON_SUPPORT_APPROVAL_ID, session_id: $env.TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID, run_nonce: $env.RELEASE_RUN_NONCE, ticket_id: $json.ticket_id, amount_eur: $json.refund_amount_eur, requested_action: $json.blocked_tool } }}",
            ),
            code_node("approval-pending-0001", "Require Pending Approval", [200, 120], REQUIRE_PENDING_JS),
            http_node(
                "approval-wait-0001",
                "Wait for Operator Decision",
                [400, 120],
                "GET",
                "={{ $env.TALON_SUPPORT_APPROVAL_URL + '/wait/' + $json.approval_id + '?timeout=1800' }}",
                timeout=1_900_000,
            ),
            code_node("approval-validate-0001", "Validate Operator Decision", [600, 120], VALIDATE_DECISION_JS),
            {
                "parameters": {
                    "conditions": {
                        "options": {
                            "caseSensitive": True,
                            "leftValue": "",
                            "typeValidation": "strict",
                            "version": 2,
                        },
                        "conditions": [
                            {
                                "id": "approval-decision-condition",
                                "leftValue": "={{ $json.operator_decision }}",
                                "rightValue": "approved",
                                "operator": {"type": "string", "operation": "equals"},
                            }
                        ],
                        "combinator": "and",
                    },
                    "options": {},
                },
                "id": "approval-if-0001",
                "name": "Operator Approved?",
                "type": "n8n-nodes-base.if",
                "typeVersion": 2.2,
                "position": [800, 120],
            },
            code_node("approval-build-approved", "Build Approved Artifacts", [1020, 20], APPROVED_JS),
            write_node("approval-write-receipt", "Write Approved Receipt", [1240, -60], "approval", "/demo/output/operator-approval-receipt.json"),
            write_node("approval-write-finance", "Write Finance Handoff", [1460, -60], "finance", "/demo/output/finance-refund-request.json"),
            write_node("approval-write-report", "Write Approved Resolution", [1680, -60], "report", "/demo/output/customer-support-resolution.md"),
            write_node("approval-write-status", "Write Approved Status", [1900, -60], "status", "/demo/output/status.json"),
            code_node("approval-build-rejected", "Build Rejected Artifacts", [1020, 260], REJECTED_JS),
            write_node("rejection-write-receipt", "Write Rejected Receipt", [1240, 260], "approval", "/demo/output/operator-approval-receipt.json"),
            write_node("rejection-write-report", "Write Rejected Resolution", [1460, 260], "report", "/demo/output/customer-support-resolution.md"),
            write_node("rejection-write-status", "Write Rejected Status", [1680, 260], "status", "/demo/output/status.json"),
        ]
    )

    connections = {key: value for key, value in source["connections"].items() if key not in REMOVE}
    for value in connections.values():
        for branch in value.get("main", []):
            branch[:] = [item for item in branch if item.get("node") not in REMOVE]

    connections.update(
        {
            "Require Refund Action Denial": {"main": [[edge("Create Human Approval Request")]]},
            "Create Human Approval Request": {"main": [[edge("Require Pending Approval")]]},
            "Require Pending Approval": {"main": [[edge("Wait for Operator Decision")]]},
            "Wait for Operator Decision": {"main": [[edge("Validate Operator Decision")]]},
            "Validate Operator Decision": {"main": [[edge("Operator Approved?")]]},
            "Operator Approved?": {
                "main": [[edge("Build Approved Artifacts")], [edge("Build Rejected Artifacts")]]
            },
            "Build Approved Artifacts": {"main": [[edge("Write Approved Receipt")]]},
            "Write Approved Receipt": {"main": [[edge("Write Finance Handoff")]]},
            "Write Finance Handoff": {"main": [[edge("Write Approved Resolution")]]},
            "Write Approved Resolution": {"main": [[edge("Write Approved Status")]]},
            "Build Rejected Artifacts": {"main": [[edge("Write Rejected Receipt")]]},
            "Write Rejected Receipt": {"main": [[edge("Write Rejected Resolution")]]},
            "Write Rejected Resolution": {"main": [[edge("Write Rejected Status")]]},
        }
    )

    rendered = dict(source)
    rendered["nodes"] = nodes
    rendered["connections"] = connections
    rendered["versionId"] = "operator-approval-gate-v1"
    return rendered


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(render(source), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
