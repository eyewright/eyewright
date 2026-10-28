//! eyewright Rust core slice: `gate` and `ask` (typed path).
//!
//! Server (`serve`), MCP, the generative engine and the supervisor are not
//! ported yet. See PORT.md for the slice plan.

mod config;
mod decide;
mod engine;
mod gate;
mod generative;
mod server;

use std::collections::HashMap;

use config::Cfg;

const DEFAULT_TIMEOUT_S: f64 = 120.0;

fn load_cfg(path: &str) -> Result<Cfg, String> {
    let text = std::fs::read_to_string(path).map_err(|e| format!("{path}: {e}"))?;
    serde_json::from_str(&text).map_err(|e| format!("{path}: {e}"))
}

fn print_json(value: &serde_json::Value) {
    println!("{}", serde_json::to_string_pretty(value).unwrap_or_default());
}

fn run() -> i32 {
    let argv: Vec<String> = std::env::args().skip(1).collect();
    if argv.iter().any(|a| a == "--version") {
        println!("eyewright {}", env!("CARGO_PKG_VERSION"));
        return 0;
    }
    let Some(cmd) = argv.first() else {
        eprintln!("usage: eyewright <gate|ask> ...");
        return 2;
    };

    let mut flags: HashMap<String, String> = HashMap::new();
    let mut i = 1;
    while i < argv.len() {
        if let Some(key) = argv[i].strip_prefix("--") {
            let value = argv.get(i + 1).cloned().unwrap_or_default();
            flags.insert(key.to_string(), value);
            i += 2;
        } else {
            i += 1;
        }
    }

    let config_path = flags
        .get("config")
        .cloned()
        .unwrap_or_else(|| "examples/gate.json".into());
    let cfg = match load_cfg(&config_path) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("eyewright: {e}");
            return 1;
        }
    };
    let state = flags.get("state").cloned().unwrap_or_default();
    let question = flags.get("question").cloned().unwrap_or_default();

    let choices = match flags.get("choices") {
        Some(raw) => match serde_json::from_str(raw) {
            Ok(v) => Some(v),
            Err(e) => {
                eprintln!("eyewright: --choices: {e}");
                return 2;
            }
        },
        None => None,
    };
    let levels = match flags.get("levels") {
        Some(raw) => match serde_json::from_str(raw) {
            Ok(v) => Some(v),
            Err(e) => {
                eprintln!("eyewright: --levels: {e}");
                return 2;
            }
        },
        None => None,
    };

    let result = match cmd.as_str() {
        "gate" => gate::decide_gate(&cfg, &state, &question).map(|(p, trace)| {
            serde_json::json!({
                "p_done": gate::round4(p),
                "decision": trace.get("decision").cloned().unwrap_or(serde_json::Value::Null),
                "trace": trace,
            })
        }),
        "ask" => {
            let engine = flags.get("engine").map(String::as_str).filter(|e| *e != "typed");
            decide::ask(&cfg, &state, &question, choices, levels, engine)
        }
        "serve" => {
            if flags.contains_key("cert") || flags.contains_key("key") {
                eprintln!("eyewright: TLS is not ported yet (slice 3b)");
                return 2;
            }
            let host = flags
                .get("host")
                .cloned()
                .unwrap_or_else(|| "127.0.0.1".into());
            let port = flags
                .get("port")
                .and_then(|p| p.parse().ok())
                .unwrap_or(8090);
            let token = flags
                .get("token")
                .cloned()
                .or_else(|| std::env::var("EYEWRIGHT_TOKEN").ok());
            let max_body = flags
                .get("max-body")
                .and_then(|p| p.parse().ok())
                .unwrap_or(1_000_000);
            return server::serve(&cfg, &host, port, token, max_body);
        }
        other => {
            eprintln!("eyewright: unknown command {other:?}");
            return 2;
        }
    };

    match result {
        Ok(value) => {
            print_json(&value);
            0
        }
        Err(e) => {
            eprintln!("eyewright: {e}");
            1
        }
    }
}

fn main() {
    std::process::exit(run());
}
