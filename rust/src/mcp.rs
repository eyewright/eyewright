//! `mcp` - stdio MCP server, ported from `eyewright/mcp_server.py`.
//!
//! Two tools: eyewright_gate and eyewright_ask. Newline-delimited JSON-RPC.
//! Hand-rolled on purpose: four methods and one transport, no async runtime.

use std::io::{BufRead, Write};

use serde_json::{json, Value};

use crate::config::Cfg;
use crate::decide::ask;
use crate::gate::{decide_gate, round4};

const GATE_DESC: &str = "Gate a claim against the eyewright committee.\n\n        Returns p_done, the policy decision (accept / consensus-* / review-*),\n        and the full consult trace.\n        ";
const ASK_DESC: &str = "Ask eyewright a typed decision.\n\n        With `choices` (option -> description) it picks an option; without, it is a\n        yes/no judgment. `engine`: None/typed (decision models), \"generative\" (local\n        LLM adjudicator, uncalibrated), or \"auto\" (typed, fall back to generative).\n        Returns answer, confidence, and the trace.\n        ";

fn tools() -> Value {
    json!([
        {
            "name": "eyewright_gate",
            "description": GATE_DESC,
            "inputSchema": {
                "properties": {
                    "state": {"title": "State", "type": "string"},
                    "question": {"title": "Question", "type": "string"}
                },
                "required": ["state", "question"],
                "type": "object",
                "title": "eyewright_gateArguments"
            }
        },
        {
            "name": "eyewright_ask",
            "description": ASK_DESC,
            "inputSchema": {
                "properties": {
                    "state": {"title": "State", "type": "string"},
                    "question": {"title": "Question", "type": "string"},
                    "choices": {
                        "anyOf": [
                            {"additionalProperties": true, "type": "object"},
                            {"type": "null"}
                        ],
                        "default": null,
                        "title": "Choices"
                    },
                    "engine": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                        "default": null,
                        "title": "Engine"
                    }
                },
                "required": ["state", "question"],
                "type": "object",
                "title": "eyewright_askArguments"
            }
        }
    ])
}

fn text_result(text: String, is_error: bool) -> Value {
    json!({
        "content": [{"text": text, "type": "text"}],
        "isError": is_error,
    })
}

fn pretty(value: &Value) -> String {
    serde_json::to_string_pretty(value).unwrap_or_default()
}

fn call_tool(cfg: &Cfg, params: &Value) -> Value {
    let name = params.get("name").and_then(|v| v.as_str()).unwrap_or("");
    let args = params.get("arguments").cloned().unwrap_or_else(|| json!({}));
    let state = args.get("state").and_then(|v| v.as_str()).unwrap_or("");
    let question = args.get("question").and_then(|v| v.as_str()).unwrap_or("");

    match name {
        "eyewright_gate" => match decide_gate(cfg, state, question) {
            Ok((p, trace)) => text_result(
                pretty(&json!({
                    "p_done": round4(p),
                    "decision": trace.get("decision").cloned().unwrap_or(Value::Null),
                    "trace": trace,
                })),
                false,
            ),
            Err(e) => text_result(
                format!("Error executing tool eyewright_gate: {e}"),
                true,
            ),
        },
        "eyewright_ask" => {
            let choices = args.get("choices").cloned().filter(|v| !v.is_null());
            let engine = args.get("engine").and_then(|v| v.as_str());
            match ask(cfg, state, question, choices, None, engine) {
                Ok(out) => text_result(pretty(&out), false),
                Err(e) => text_result(format!("Error executing tool eyewright_ask: {e}"), true),
            }
        }
        other => text_result(format!("Unknown tool: {other}"), true),
    }
}

fn handle(cfg: &Cfg, msg: &Value) -> Option<Value> {
    let id = msg.get("id")?.clone();
    let method = msg.get("method").and_then(|m| m.as_str()).unwrap_or("");
    let params = msg.get("params").cloned().unwrap_or_else(|| json!({}));

    let response = match method {
        "initialize" => json!({
            "jsonrpc": "2.0",
            "id": id,
            "result": {
                "capabilities": {
                    "prompts": {"listChanged": false},
                    "resources": {"listChanged": false, "subscribe": false},
                    "tools": {"listChanged": false}
                },
                "protocolVersion": params
                    .get("protocolVersion")
                    .and_then(|v| v.as_str())
                    .unwrap_or("2025-06-18"),
                "serverInfo": {"name": "eyewright", "version": ""}
            }
        }),
        "ping" => json!({"jsonrpc": "2.0", "id": id, "result": {}}),
        "tools/list" => json!({"jsonrpc": "2.0", "id": id, "result": {"tools": tools()}}),
        "tools/call" => json!({"jsonrpc": "2.0", "id": id, "result": call_tool(cfg, &params)}),
        other => json!({
            "jsonrpc": "2.0",
            "id": id,
            "error": {"code": -32601, "message": "Method not found", "data": other}
        }),
    };
    Some(response)
}

pub fn run(cfg: &Cfg) -> i32 {
    let stdin = std::io::stdin();
    let mut stdout = std::io::stdout();
    for line in stdin.lock().lines() {
        let Ok(line) = line else { break };
        if line.trim().is_empty() {
            continue;
        }
        let Ok(msg) = serde_json::from_str::<Value>(&line) else {
            let _ = writeln!(
                stdout,
                "{}",
                json!({"jsonrpc": "2.0", "id": null, "error": {"code": -32700, "message": "Parse error"}})
            );
            let _ = stdout.flush();
            continue;
        };
        if let Some(response) = handle(cfg, &msg) {
            let _ = writeln!(stdout, "{response}");
            let _ = stdout.flush();
        }
    }
    0
}
