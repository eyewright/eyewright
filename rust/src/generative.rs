//! Generative adjudicator, ported from `eyewright/generative.py`.
//!
//! The model is asked with a strict JSON contract. Its confidence is its own
//! estimate, so the result is always `calibrated: false`.

use serde_json::{json, Map, Value};

use crate::config::Cfg;
use crate::engine::post_json;

const YES: [&str; 5] = ["yes", "y", "true", "t", "1"];
const NO: [&str; 5] = ["no", "n", "false", "f", "0"];

fn ollama_url() -> String {
    // Deviation: the Python build hardcodes localhost:11434. The env var exists
    // so the parity harness can point both sides at a stub; unset means the
    // production URL.
    std::env::var("EYEWRIGHT_OLLAMA_URL")
        .unwrap_or_else(|_| "http://localhost:11434".into())
        .trim_end_matches('/')
        .to_string()
}

pub fn extract_json(text: &str) -> Option<Value> {
    let start = text.find('{')?;
    let slice = &text[start..];
    if let Ok(value) = serde_json::from_str::<Value>(slice) {
        return Some(value);
    }
    // Tolerant fallback: first balanced brace block, exactly like the Python.
    let mut depth = 0i32;
    for (i, ch) in slice.char_indices() {
        match ch {
            '{' => depth += 1,
            '}' => {
                depth -= 1;
                if depth == 0 {
                    return serde_json::from_str(&slice[..=i]).ok();
                }
            }
            _ => {}
        }
    }
    None
}

pub fn normalize_noul(answer: &Value) -> (Value, bool) {
    if let Some(b) = answer.as_bool() {
        return (json!(if b { "yes" } else { "no" }), true);
    }
    if let Some(n) = answer.as_f64() {
        if n == 1.0 {
            return (json!("yes"), true);
        }
        if n == 0.0 {
            return (json!("no"), true);
        }
    }
    if let Some(s) = answer.as_str() {
        let a = s.trim().to_lowercase();
        if YES.contains(&a.as_str()) {
            return (json!("yes"), true);
        }
        if NO.contains(&a.as_str()) {
            return (json!("no"), true);
        }
    }
    (answer.clone(), false)
}

pub fn prompt(state: &str, question: &str, choices: Option<&Value>, levels: Option<&Value>) -> String {
    let (opts, answer_rule) = if let Some(Value::Object(map)) = choices {
        let lines: Vec<String> = map
            .iter()
            .map(|(k, v)| format!("- {k}: {}", v.as_str().unwrap_or_default()))
            .collect();
        let keys: Vec<&str> = map.keys().map(String::as_str).collect();
        (
            lines.join("\n"),
            format!("exactly one of these option keys: {}", keys.join(", ")),
        )
    } else if let Some(Value::Array(items)) = levels {
        let lines: Vec<String> = items
            .iter()
            .enumerate()
            .map(|(i, v)| format!("- {i}: {}", v.as_str().unwrap_or_default()))
            .collect();
        (lines.join("\n"), "the 0-based index of the best level".to_string())
    } else {
        ("(none)".to_string(), "\"yes\" or \"no\"".to_string())
    };
    format!(
        "You are a decision engine. Answer with a single JSON object and nothing else:\n\
         {{\"answer\": <answer>, \"confidence\": <0.0-1.0>, \"reason\": \"<one short sentence>\"}}\n\n\
         Rules: \"answer\" must be {answer_rule}. \"confidence\" is your estimated\n\
         probability that the answer is correct. Base the answer only on the state.\n\n\
         STATE:\n{state}\n\nQUESTION:\n{question}\n\nOPTIONS:\n{opts}"
    )
}

fn ollama_chat(
    model: &str,
    prompt: &str,
    options: Option<&Value>,
    fmt: &str,
    think: Option<bool>,
    timeout: f64,
) -> Result<String, String> {
    let mut payload = json!({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": false,
        "format": fmt,
        "options": {"temperature": 0},
    });
    if let Some(Value::Object(extra)) = options {
        for (k, v) in extra {
            payload["options"][k] = v.clone();
        }
    }
    if let Some(t) = think {
        payload["think"] = json!(t);
    }
    let resp = post_json(&format!("{}/api/chat", ollama_url()), &payload, timeout, None)?;
    Ok(resp["message"]["content"].as_str().unwrap_or_default().to_string())
}

pub fn ask_generative(
    cfg: &Cfg,
    state: &str,
    question: &str,
    choices: Option<&Value>,
    levels: Option<&Value>,
    kind: &str,
) -> Result<Value, String> {
    let g = cfg
        .generative
        .as_ref()
        .ok_or_else(|| "config has no 'generative' block".to_string())?;
    let model = g.model.clone().unwrap_or_else(|| "gemma4:12b".into());
    let timeout = g.timeout_s.unwrap_or_else(|| cfg.timeout());
    let content = ollama_chat(
        &model,
        &prompt(state, question, choices, levels),
        g.options.as_ref(),
        g.format.as_deref().unwrap_or("json"),
        g.think,
        timeout,
    )?;

    let obj = extract_json(&content).unwrap_or_else(|| json!({}));
    let mut answer = obj.get("answer").cloned().unwrap_or(Value::Null);
    let mut normalized = Value::Null;

    if kind == "noul" {
        let (value, ok) = normalize_noul(&answer);
        answer = value;
        normalized = json!(ok);
    }
    if kind == "choice" {
        let text_opt = answer.as_str().map(str::to_string);
        if let (Some(text), Some(Value::Object(map))) = (text_opt, choices) {
            let lower = text.trim().to_lowercase();
            let exact = map.keys().find(|k| k.to_lowercase() == lower).cloned();
            let matched = exact.or_else(|| {
                map.keys()
                    .find(|k| lower.contains(&k.to_lowercase()))
                    .cloned()
            });
            answer = matched.map(|k| json!(k)).unwrap_or(Value::Null);
        }
    }
    if kind == "score" {
        let coerced = match &answer {
            Value::Bool(b) => Some(json!(if *b { 1 } else { 0 })),
            Value::Number(n) => n.as_i64().map(|v| json!(v)),
            Value::String(s) => s.trim().parse::<i64>().ok().map(|v| json!(v)),
            _ => None,
        };
        if let Some(v) = coerced {
            answer = v;
        }
    }

    let confidence = obj
        .get("confidence")
        .and_then(|c| {
            c.as_f64()
                .or_else(|| c.as_str().and_then(|s| s.trim().parse::<f64>().ok()))
        })
        .map(crate::gate::round4);

    let mut out = Map::new();
    out.insert("kind".into(), json!(kind));
    out.insert("answer".into(), answer);
    out.insert("confidence".into(), confidence.map(Value::from).unwrap_or(Value::Null));
    out.insert("reason".into(), obj.get("reason").cloned().unwrap_or(Value::Null));
    out.insert("model".into(), json!(model));
    out.insert("calibrated".into(), json!(false));
    out.insert("engine".into(), json!("generative"));
    out.insert("raw".into(), json!(content.chars().take(600).collect::<String>()));
    if kind == "noul" {
        out.insert("normalized".into(), normalized);
    }
    Ok(Value::Object(out))
}
