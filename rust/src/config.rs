//! Config shapes. Unknown keys are ignored, matching Python's `.get()` style.

use serde::Deserialize;
use serde_json::Value;

#[derive(Deserialize, Default, Clone)]
pub struct GenerativeCfg {
    pub model: Option<String>,
    pub options: Option<Value>,
    pub format: Option<String>,
    pub think: Option<bool>,
    pub timeout_s: Option<f64>,
}

#[derive(Deserialize, Default, Clone)]
pub struct Entry {
    pub name: Option<String>,
    #[serde(rename = "type")]
    pub kind: Option<String>,
    pub url: Option<String>,
    pub model: Option<String>,
    pub key_file: Option<String>,
    pub key_env: Option<String>,
    pub zdr: Option<bool>,
    pub allow_remote: Option<bool>,
    pub timeout_s: Option<f64>,
}

impl Entry {
    pub fn label(&self) -> String {
        self.name
            .clone()
            .or_else(|| self.model.clone())
            .or_else(|| self.kind.clone())
            .unwrap_or_else(|| "consult".into())
    }
}

#[derive(Deserialize, Default, Clone)]
pub struct Cfg {
    pub primary: Option<Entry>,
    #[serde(default)]
    pub consults: Vec<Entry>,
    pub accept_threshold: Option<f64>,
    pub consult_threshold: Option<f64>,
    pub high_confidence: Option<f64>,
    pub match_delta: Option<f64>,
    pub attempts: Option<i64>,
    pub retries: Option<i64>,
    pub retry_backoff_s: Option<f64>,
    pub timeout_s: Option<f64>,
    pub on_primary_unavailable: Option<String>,
    pub generative: Option<GenerativeCfg>,
}

impl Cfg {
    pub fn accept(&self) -> f64 {
        self.accept_threshold.unwrap_or(0.75)
    }
    pub fn consult(&self) -> f64 {
        self.consult_threshold.unwrap_or(0.55)
    }
    pub fn high(&self) -> f64 {
        self.high_confidence.unwrap_or(0.9)
    }
    pub fn delta(&self) -> f64 {
        self.match_delta.unwrap_or(0.05)
    }
    pub fn timeout(&self) -> f64 {
        self.timeout_s.unwrap_or(crate::DEFAULT_TIMEOUT_S)
    }
    pub fn backoff(&self) -> f64 {
        self.retry_backoff_s.unwrap_or(1.0)
    }
    /// `attempts` is total; `retries` is the legacy alias for attempts beyond
    /// the first (attempts = retries + 1).
    pub fn attempts(&self) -> i64 {
        if let Some(a) = self.attempts {
            a.max(1)
        } else if let Some(r) = self.retries {
            (r + 1).max(1)
        } else {
            1
        }
    }
    pub fn policy(&self) -> String {
        self.on_primary_unavailable
            .clone()
            .unwrap_or_else(|| "fallback".into())
            .to_lowercase()
    }
}
