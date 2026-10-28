//! `ask` - one typed decision (noul / choice / score), ported from `decide.py`.

use serde_json::{json, Map, Value};

use crate::config::Cfg;
use crate::engine::call_engine;
use crate::gate::{decide_gate, round4, truncate};
use crate::generative::ask_generative;

const NO_SIGNAL: [&str; 3] = ["none", "review-primary-unavailable", "error-primary"];

fn kind_of(choices: &Option<Value>, levels: &Option<Value>) -> &'static str {
    if choices.is_some() {
        "choice"
    } else if levels.is_some() {
        "score"
    } else {
        "noul"
    }
}

fn argmax(probs: &Map<String, Value>) -> Option<String> {
    probs
        .iter()
        .filter_map(|(k, v)| v.as_f64().map(|n| (k.clone(), n)))
        .max_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal))
        .map(|(k, _)| k)
}

fn with_fallback(mut value: Value, typed_error: Option<&str>) -> Value {
    if let Some(obj) = value.as_object_mut() {
        obj.insert("fallback".into(), json!("typed->generative"));
        if let Some(err) = typed_error {
            obj.insert("typed_error".into(), json!(truncate(err, 140)));
        }
    }
    value
}

pub fn ask(
    cfg: &Cfg,
    state: &str,
    question: &str,
    choices: Option<Value>,
    levels: Option<Value>,
    engine: Option<&str>,
) -> Result<Value, String> {
    let kind = kind_of(&choices, &levels);
    let wants_auto = engine == Some("auto") && cfg.generative.is_some();

    if engine == Some("generative") {
        return ask_generative(cfg, state, question, choices.as_ref(), levels.as_ref(), kind);
    }

    let questions = match kind {
        "choice" => json!({"q": {
            "type": "choice",
            "instructions": question,
            "criteria": choices.clone().unwrap_or(Value::Null),
        }}),
        "score" => json!({"q": {
            "type": "score",
            "instructions": question,
            "criteria": levels.clone().unwrap_or(Value::Null),
        }}),
        _ => json!({"q": {"type": "noul", "instructions": question}}),
    };

    if kind == "noul" {
        return match decide_gate(cfg, state, question) {
            Ok((p, trace)) => {
                let decision = trace.get("decision").and_then(|v| v.as_str()).unwrap_or("");
                if wants_auto && NO_SIGNAL.contains(&decision) {
                    let fb = ask_generative(cfg, state, question, choices.as_ref(), levels.as_ref(), kind)?;
                    return Ok(with_fallback(fb, None));
                }
                Ok(json!({
                    "kind": "noul",
                    "answer": if p >= 0.5 { "yes" } else { "no" },
                    "confidence": round4(p.max(1.0 - p)),
                    "p_true": round4(p),
                    "trace": trace,
                }))
            }
            Err(e) => {
                if wants_auto {
                    let fb = ask_generative(cfg, state, question, choices.as_ref(), levels.as_ref(), kind)?;
                    return Ok(with_fallback(fb, Some(&e)));
                }
                Err(e)
            }
        };
    }

    let entry = cfg
        .primary
        .clone()
        .ok_or_else(|| "config has no primary engine".to_string())?;
    let resp = match call_engine(&entry, state, &questions, cfg.timeout()) {
        Ok(r) => r,
        Err(e) => {
            if wants_auto {
                let fb = ask_generative(cfg, state, question, choices.as_ref(), levels.as_ref(), kind)?;
                return Ok(with_fallback(fb, None));
            }
            return Ok(json!({"kind": kind, "answer": null, "confidence": null, "error": e}));
        }
    };

    let ans = resp
        .get("answers")
        .and_then(|a| a.get("q"))
        .cloned()
        .unwrap_or_else(|| json!({}));
    let probs = ans
        .get("probabilities")
        .and_then(|p| p.as_object())
        .cloned()
        .unwrap_or_default();

    let answer = if kind == "choice" {
        match ans.get("choice") {
            Some(Value::String(s)) if !s.is_empty() => Some(json!(s)),
            Some(Value::Null) | None => argmax(&probs).map(|k| json!(k)),
            Some(other) => Some(other.clone()),
        }
    } else {
        ans.get("score").cloned().filter(|v| !v.is_null())
    };

    let confidence = match ans.get("confidence").and_then(|c| c.as_f64()) {
        Some(c) => Some(round4(c)),
        // Python: a choice answer absent from `probabilities` gets 0.0, not None.
        None => answer
            .as_ref()
            .map(|a| {
                a.as_str()
                    .and_then(|k| probs.get(k))
                    .and_then(|v| v.as_f64())
                    .unwrap_or(0.0)
            })
            .map(round4),
    };

    if wants_auto && answer.is_none() {
        let fb = ask_generative(cfg, state, question, choices.as_ref(), levels.as_ref(), kind)?;
        return Ok(with_fallback(fb, None));
    }

    let rounded_probs: Map<String, Value> = probs
        .iter()
        .filter_map(|(k, v)| v.as_f64().map(|n| (k.clone(), json!(round4(n)))))
        .collect();

    Ok(json!({
        "kind": kind,
        "answer": answer,
        "confidence": confidence,
        "probabilities": Value::Object(rounded_probs),
        "model": resp.get("model").cloned().unwrap_or(Value::Null),
        "trace": {"engine": entry.label()},
    }))
}
