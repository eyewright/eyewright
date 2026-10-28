//! Eyes: HTTP calls, credential loading, and the config-trust guards.

use std::path::{Path, PathBuf};
use std::time::Duration;

use serde_json::{json, Value};

use crate::config::Entry;

const LOOPBACK: [&str; 3] = ["127.0.0.1", "::1", "localhost"];
const OPENROUTER: [&str; 2] = ["openrouter.ai", "www.openrouter.ai"];
const SENSITIVE_DIRS: [&str; 6] = [
    "/.ssh/",
    "/.aws/",
    "/.gnupg/",
    "/.config/gcloud/",
    "/.azure/",
    "/.kube/",
];
const SENSITIVE_NAMES: [&str; 10] = [
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "id_dsa",
    "credentials",
    ".netrc",
    ".npmrc",
    ".pypirc",
    ".env",
    ".git-credentials",
];

pub fn host_of(url: &str) -> String {
    let rest = url.split("://").nth(1).unwrap_or(url);
    let authority = rest.split('/').next().unwrap_or("");
    let host = authority.rsplit('@').next().unwrap_or(authority);
    if let Some(v6) = host.strip_prefix('[') {
        return v6.split(']').next().unwrap_or("").to_lowercase();
    }
    host.split(':').next().unwrap_or("").to_lowercase()
}

fn require_loopback(url: &str, allow_remote: bool) -> Result<(), String> {
    let host = host_of(url);
    if !allow_remote && !LOOPBACK.contains(&host.as_str()) {
        return Err(format!(
            "refusing to send state to non-loopback host '{host}'; set \"allow_remote\": true on the entry to opt in"
        ));
    }
    Ok(())
}

fn home() -> String {
    std::env::var("USERPROFILE")
        .or_else(|_| std::env::var("HOME"))
        .unwrap_or_default()
}

fn expand_vars(input: &str) -> String {
    let mut out = String::new();
    let mut chars = input.chars().peekable();
    while let Some(c) = chars.next() {
        if c == '%' {
            let mut name = String::new();
            while let Some(&n) = chars.peek() {
                chars.next();
                if n == '%' {
                    break;
                }
                name.push(n);
            }
            out.push_str(&std::env::var(&name).unwrap_or_default());
        } else if c == '$' {
            let mut name = String::new();
            while let Some(&n) = chars.peek() {
                if n.is_alphanumeric() || n == '_' {
                    name.push(n);
                    chars.next();
                } else {
                    break;
                }
            }
            out.push_str(&std::env::var(&name).unwrap_or_default());
        } else {
            out.push(c);
        }
    }
    out
}

fn is_sensitive(path: &Path) -> bool {
    let absolute = std::path::absolute(path).unwrap_or_else(|_| path.to_path_buf());
    let s = absolute.to_string_lossy().to_lowercase().replace('\\', "/");
    if SENSITIVE_DIRS.iter().any(|m| s.contains(m)) {
        return true;
    }
    let name = path
        .file_name()
        .map(|n| n.to_string_lossy().to_lowercase())
        .unwrap_or_default();
    SENSITIVE_NAMES.contains(&name.as_str())
}

/// Read an API key file. `~` and `%VAR%` / `$VAR` are expanded.
pub fn load_key(path: Option<&str>) -> Result<String, String> {
    let Some(path) = path.filter(|p| !p.is_empty()) else {
        return Ok(String::new());
    };
    let expanded = expand_vars(path);
    let expanded = if let Some(rest) = expanded.strip_prefix("~/").or_else(|| expanded.strip_prefix("~\\")) {
        format!("{}/{}", home(), rest)
    } else if expanded == "~" {
        home()
    } else {
        expanded
    };
    let mut p = PathBuf::from(expanded);
    if !p.is_absolute() {
        p = std::env::current_dir().unwrap_or_default().join(p);
    }
    if is_sensitive(&p) {
        return Err(format!(
            "refusing to read a sensitive credential file as an API key: {}",
            p.display()
        ));
    }
    if p.exists() {
        Ok(std::fs::read_to_string(&p)
            .map_err(|e| e.to_string())?
            .trim()
            .to_string())
    } else {
        Ok(String::new())
    }
}

pub fn post_json(url: &str, payload: &Value, timeout: f64, bearer: Option<&str>) -> Result<Value, String> {
    let agent = ureq::AgentBuilder::new()
        .timeout_connect(Duration::from_secs_f64(timeout))
        .timeout_read(Duration::from_secs_f64(timeout))
        .timeout_write(Duration::from_secs_f64(timeout))
        .build();
    let mut req = agent.post(url).set("Content-Type", "application/json");
    if let Some(key) = bearer.filter(|k| !k.is_empty()) {
        req = req.set("Authorization", &format!("Bearer {key}"));
    }
    let body = serde_json::to_string(payload).map_err(|e| e.to_string())?;
    match req.send_string(&body) {
        Ok(resp) => resp.into_json::<Value>().map_err(|e| e.to_string()),
        Err(ureq::Error::Status(code, _)) => Err(format!("HTTP Error {code}")),
        Err(e) => Err(e.to_string()),
    }
}

pub fn systemone_http(
    entry: &Entry,
    state: &str,
    question: &str,
    timeout: f64,
) -> Result<f64, String> {
    let url = entry.url.clone().unwrap_or_default();
    require_loopback(&url, entry.allow_remote.unwrap_or(false))?;
    let key = load_key(entry.key_file.as_deref())?;
    let mut payload = json!({
        "state": state,
        "questions": {"done": {"type": "noul", "instructions": question}},
    });
    if let Some(model) = entry.model.as_deref().filter(|m| !m.is_empty()) {
        payload["model"] = json!(model);
    }
    let resp = post_json(&url, &payload, timeout, Some(&key))?;
    resp["answers"]["done"]["noul"]
        .as_f64()
        .ok_or_else(|| "missing answers.done.noul".to_string())
}

pub fn systemone_ollama(entry: &Entry, state: &str, question: &str, timeout: f64) -> Result<f64, String> {
    let payload = json!({
        "model": entry.model.clone().unwrap_or_default(),
        "state": state,
        "questions": {"done": {"type": "noul", "instructions": question}},
    });
    let resp = post_json("http://localhost:11434/v1/systemone", &payload, timeout, None)?;
    resp["answers"]["done"]["noul"]
        .as_f64()
        .ok_or_else(|| "missing answers.done.noul".to_string())
}

pub fn openrouter_decisions(
    entry: &Entry,
    state: &str,
    question: &str,
    timeout: f64,
) -> Result<f64, String> {
    let url = entry
        .url
        .clone()
        .unwrap_or_else(|| "https://openrouter.ai/api/alpha/decisions".into());
    let host = host_of(&url);
    if !entry.allow_remote.unwrap_or(false) && !OPENROUTER.contains(&host.as_str()) {
        return Err(format!(
            "refusing to send state to non-OpenRouter host '{host}'; set \"allow_remote\": true on the entry to opt in"
        ));
    }
    let mut payload = json!({
        "model": entry.model.clone().unwrap_or_default(),
        "state": state,
        "questions": {"done": {"type": "noul", "instructions": question}},
    });
    if entry.zdr.unwrap_or(false) {
        payload["provider"] = json!({"zdr": true});
    }
    let key_env = entry.key_env.clone().unwrap_or_else(|| "OPENROUTER_API_KEY".into());
    let key = std::env::var(key_env).unwrap_or_default();
    let resp = post_json(&url, &payload, timeout, Some(&key))?;
    resp["answers"]["done"]["noul"]
        .as_f64()
        .ok_or_else(|| "missing answers.done.noul".to_string())
}

/// One systemone call for a typed question (`ask`, choice/score paths).
pub fn call_engine(entry: &Entry, state: &str, questions: &Value, timeout: f64) -> Result<Value, String> {
    match entry.kind.as_deref() {
        Some("systemone-http") => {
            let url = entry.url.clone().unwrap_or_default();
            require_loopback(&url, entry.allow_remote.unwrap_or(false))?;
            let mut payload = json!({"state": state, "questions": questions});
            if let Some(model) = entry.model.as_deref().filter(|m| !m.is_empty()) {
                payload["model"] = json!(model);
            }
            let key = load_key(entry.key_file.as_deref())?;
            post_json(&url, &payload, timeout, Some(&key))
        }
        Some("systemone-ollama") => {
            let payload = json!({
                "model": entry.model.clone().unwrap_or_default(),
                "state": state,
                "questions": questions,
            });
            post_json("http://localhost:11434/v1/systemone", &payload, timeout, None)
        }
        other => Err(format!("unknown engine type {other:?}")),
    }
}
