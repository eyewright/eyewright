//! `serve` - the local HTTP surface, ported from `eyewright/server.py`.
//!
//! Endpoints: GET /health, /health/deep, / ; POST /v1/gate, /v1/ask.
//! Loopback-only by default; binding off-loopback requires a bearer token.
//! TLS is not ported yet (see PORT.md).

use std::io::Read;
use std::sync::Arc;
use std::thread;

use serde_json::{json, Value};
use tiny_http::{Header, Method, Request, Response, Server};

use crate::config::Cfg;
use crate::decide::ask;
use crate::gate::{decide_gate, round4};

const VERSION: &str = env!("CARGO_PKG_VERSION");
const LOOPBACK: [&str; 3] = ["127.0.0.1", "::1", "localhost"];

fn json_response(request: Request, code: u16, body: &Value) {
    let text = serde_json::to_string(body).unwrap_or_default();
    let header = Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap();
    let _ = request.respond(Response::from_string(text).with_status_code(code).with_header(header));
}

fn authorized(request: &Request, token: &Option<String>) -> bool {
    match token {
        None => true,
        Some(expected) => request
            .headers()
            .iter()
            .find(|h| h.field.equiv("Authorization"))
            .map(|h| h.value.as_str() == format!("Bearer {expected}"))
            .unwrap_or(false),
    }
}

fn content_length(request: &Request) -> Option<usize> {
    request
        .headers()
        .iter()
        .find(|h| h.field.equiv("Content-Length"))
        .and_then(|h| h.value.as_str().trim().parse::<usize>().ok())
}

fn dependency_checks(cfg: &Cfg) -> Vec<(String, String)> {
    let mut out = Vec::new();
    for entry in cfg.primary.iter().chain(cfg.consults.iter()) {
        let label = entry
            .name
            .clone()
            .or_else(|| entry.model.clone())
            .or_else(|| entry.kind.clone())
            .unwrap_or_else(|| "eye".into());
        match entry.kind.as_deref() {
            Some("systemone-http") => {
                if let Some(url) = &entry.url {
                    let root = url.split("/v1/").next().unwrap_or(url);
                    out.push((label, format!("{root}/health")));
                }
            }
            Some("systemone-ollama") => {
                out.push((format!("{label} (ollama)"), "http://localhost:11434/api/tags".into()))
            }
            Some("openrouter-decisions") => out.push((
                format!("{label} (openrouter)"),
                "https://openrouter.ai/api/v1/models".into(),
            )),
            _ => {}
        }
    }
    out
}

fn deep_health(cfg: &Cfg) -> Value {
    let mut deps = serde_json::Map::new();
    let mut ok = true;
    for (name, url) in dependency_checks(cfg) {
        let up = crate::engine::url_ok(&url, 3.0);
        ok = ok && up;
        deps.insert(name, json!({"url": url, "ok": up}));
    }
    json!({
        "status": if ok { "ok" } else { "degraded" },
        "service": "eyewright",
        "version": VERSION,
        "dependencies": Value::Object(deps),
    })
}

fn handle_get(request: Request, cfg: &Cfg, token: &Option<String>) {
    let path = request.url().to_string();
    let deep = path.contains("deep");
    if deep && !authorized(&request, token) {
        json_response(request, 401, &json!({"error": "unauthorized"}));
        return;
    }
    if path.starts_with("/health") {
        if deep {
            let body = deep_health(cfg);
            json_response(request, 200, &body);
        } else {
            json_response(
                request,
                200,
                &json!({"status": "ok", "service": "eyewright", "version": VERSION}),
            );
        }
    } else if path == "/" {
        json_response(
            request,
            200,
            &json!({"status": "ok", "service": "eyewright", "version": VERSION}),
        );
    } else {
        json_response(request, 404, &json!({"error": "not found"}));
    }
}

fn handle_post(mut request: Request, cfg: &Cfg, token: &Option<String>, max_body: usize) {
    let declared = match content_length(&request) {
        Some(n) => n,
        None => 0,
    };
    if !authorized(&request, token) {
        json_response(request, 401, &json!({"error": "unauthorized"}));
        return;
    }
    if declared > max_body {
        json_response(
            request,
            413,
            &json!({"error": format!("body too large (max {max_body} bytes)")}),
        );
        return;
    }
    let mut raw = String::new();
    let _ = request.as_reader().take(declared as u64).read_to_string(&mut raw);
    let body: Value = if raw.trim().is_empty() {
        json!({})
    } else {
        match serde_json::from_str(&raw) {
            Ok(v) => v,
            Err(_) => {
                json_response(request, 400, &json!({"error": "invalid json"}));
                return;
            }
        }
    };

    let path = request.url().to_string();
    let state = body.get("state").and_then(|v| v.as_str()).unwrap_or("");
    let question = body.get("question").and_then(|v| v.as_str()).unwrap_or("");
    if path == "/v1/gate" {
        match decide_gate(cfg, state, question) {
            Ok((p, trace)) => json_response(
                request,
                200,
                &json!({
                    "p_done": round4(p),
                    "decision": trace.get("decision").cloned().unwrap_or(Value::Null),
                    "trace": trace,
                }),
            ),
            Err(e) => {
                eprintln!("[eyewright] error handling {path}: {e}");
                json_response(request, 500, &json!({"error": "internal error"}));
            }
        }
    } else if path == "/v1/ask" {
        let choices = body.get("choices").cloned();
        let levels = body.get("levels").cloned();
        let engine = body.get("engine").and_then(|v| v.as_str());
        match ask(cfg, state, question, choices, levels, engine) {
            Ok(out) => json_response(request, 200, &out),
            Err(e) => {
                eprintln!("[eyewright] error handling {path}: {e}");
                json_response(request, 500, &json!({"error": "internal error"}));
            }
        }
    } else {
        json_response(request, 404, &json!({"error": "not found"}));
    }
}

pub fn serve(cfg: &Cfg, host: &str, port: u16, token: Option<String>, max_body: usize) -> i32 {
    if !LOOPBACK.contains(&host) && token.is_none() {
        eprintln!(
            "refusing to bind {host} without a bearer token; pass --token or set EYEWRIGHT_TOKEN"
        );
        return 1;
    }
    let addr = format!("{host}:{port}");
    let server = match Server::http(&addr) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("eyewright: cannot bind {addr}: {e}");
            return 1;
        }
    };
    let cfg = Arc::new(cfg.clone());
    let token = Arc::new(token);
    let note = if token.is_some() { "  (token required)" } else { "" };
    println!("eyewright serving on http://{addr}{note}  (gate: /v1/gate, ask: /v1/ask)");

    for request in server.incoming_requests() {
        let cfg = Arc::clone(&cfg);
        let token = Arc::clone(&token);
        // ponytail: thread per request; a small pool if this ever serves more
        // than one caller at a time.
        thread::spawn(move || match request.method() {
            Method::Get => handle_get(request, &cfg, &token),
            Method::Post => handle_post(request, &cfg, &token, max_body),
            _ => json_response(request, 404, &json!({"error": "not found"})),
        });
    }
    0
}
