//! The three-eye gate policy, ported from `eyewright/gate.py`.

use std::collections::HashSet;
use std::thread::sleep;
use std::time::Duration;

use serde_json::{json, Map, Value};

use crate::config::{Cfg, Entry};
use crate::engine::{openrouter_decisions, systemone_http, systemone_ollama};

pub fn round4(x: f64) -> f64 {
    (x * 10_000.0).round() / 10_000.0
}

pub fn truncate(s: &str, n: usize) -> String {
    s.chars().take(n).collect()
}

fn ask_entry(entry: &Entry, state: &str, question: &str, timeout: f64) -> Result<f64, String> {
    let entry_timeout = entry.timeout_s.unwrap_or(timeout);
    match entry.kind.as_deref() {
        Some("systemone-http") => systemone_http(entry, state, question, entry_timeout),
        Some("systemone-ollama") => systemone_ollama(entry, state, question, entry_timeout),
        Some("openrouter-decisions") => openrouter_decisions(entry, state, question, entry_timeout),
        _ => Err("unknown consult type".into()),
    }
}

fn ask_retry(entry: &Entry, cfg: &Cfg, state: &str, question: &str) -> Result<f64, String> {
    let attempts = cfg.attempts();
    let mut last = String::new();
    for i in 0..attempts {
        match ask_entry(entry, state, question, cfg.timeout()) {
            Ok(p) => return Ok(p),
            Err(e) => {
                last = e;
                if i + 1 < attempts {
                    sleep(Duration::from_secs_f64(cfg.backoff() * 2f64.powi(i as i32)));
                }
            }
        }
    }
    Err(last)
}

/// Returns `(p_done, trace)`. Err only for `on_primary_unavailable = "error"`.
pub fn decide_gate(cfg: &Cfg, state: &str, question: &str) -> Result<(f64, Value), String> {
    let (accept, consult, high, delta) = (cfg.accept(), cfg.consult(), cfg.high(), cfg.delta());
    let policy = cfg.policy();
    let mut trace = Map::new();
    trace.insert("consults".into(), json!({}));
    trace.insert("policy".into(), json!(policy));

    let primary = cfg.primary.clone().unwrap_or_default();
    let mut p1: Option<f64> = match ask_retry(&primary, cfg, state, question) {
        Ok(p) => Some(p),
        Err(e) => {
            trace.insert("primary_error".into(), json!(truncate(&e, 140)));
            None
        }
    };

    if p1.is_none() {
        match policy.as_str() {
            "error" => {
                trace.insert("decision".into(), json!("error-primary"));
                let msg = trace
                    .get("primary_error")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();
                return Err(format!("primary unavailable: {msg}"));
            }
            "review" => {
                trace.insert("decision".into(), json!("review-primary-unavailable"));
                return Ok((0.0, Value::Object(trace)));
            }
            _ => {
                if let Some(first) = cfg.consults.first() {
                    match ask_retry(first, cfg, state, question) {
                        Ok(p) => {
                            p1 = Some(p);
                            trace.insert("primary_source".into(), json!(first.label()));
                        }
                        Err(e) => {
                            trace.insert("primary_error2".into(), json!(truncate(&e, 140)));
                        }
                    }
                }
            }
        }
    }

    let Some(p1) = p1 else {
        trace.insert("decision".into(), json!("none"));
        return Ok((0.0, Value::Object(trace)));
    };
    trace.insert("primary".into(), json!(round4(p1)));

    if p1 >= accept {
        trace.insert("decision".into(), json!("accept"));
        return Ok((p1, Value::Object(trace)));
    }
    if p1 < consult {
        trace.insert("decision".into(), json!("review-low"));
        return Ok((p1, Value::Object(trace)));
    }

    let mut consults = Map::new();
    let mut ps: Vec<(String, f64)> = Vec::new();
    let primary_source = trace.get("primary_source").and_then(|v| v.as_str()).map(str::to_string);
    for c in &cfg.consults {
        let name = c.label();
        if primary_source.as_deref() == Some(name.as_str()) {
            continue;
        }
        match ask_entry(c, state, question, cfg.timeout()) {
            Ok(p) => {
                consults.insert(name.clone(), json!(round4(p)));
                ps.push((name, p));
            }
            Err(e) => {
                consults.insert(format!("{name}_error"), json!(truncate(&e, 80)));
                consults.insert(name, Value::Null);
            }
        }
    }
    trace.insert("consults".into(), Value::Object(consults));

    let confident: Vec<&(String, f64)> = ps
        .iter()
        .filter(|(_, p)| p.max(1.0 - p) >= high)
        .collect();
    if confident.len() >= 2 {
        let directions: HashSet<bool> = confident.iter().map(|(_, p)| *p >= 0.5).collect();
        if directions.len() == 1 {
            let avg = confident.iter().map(|(_, p)| *p).sum::<f64>() / confident.len() as f64;
            trace.insert(
                "decision".into(),
                json!(if avg >= 0.5 { "consensus-accept" } else { "consensus-reject" }),
            );
            return Ok((avg, Value::Object(trace)));
        }
        trace.insert("decision".into(), json!("review-conflict"));
        return Ok((p1, Value::Object(trace)));
    }
    if confident.len() == 1 {
        let cn = confident[0].0.clone();
        let close = ps
            .iter()
            .filter(|(n, _)| *n != cn)
            .any(|(_, p)| (p - p1).abs() <= delta);
        trace.insert(
            "decision".into(),
            json!(if close { "review-conflict" } else { "review-weak" }),
        );
        return Ok((p1, Value::Object(trace)));
    }
    trace.insert("decision".into(), json!("review-no-signal"));
    Ok((p1, Value::Object(trace)))
}
