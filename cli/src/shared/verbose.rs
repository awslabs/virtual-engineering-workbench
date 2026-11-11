use std::sync::atomic::{AtomicBool, Ordering};

static VERBOSE: AtomicBool = AtomicBool::new(false);

pub fn set_verbose(enabled: bool) {
    VERBOSE.store(enabled, Ordering::Relaxed);
}

pub fn is_verbose() -> bool {
    VERBOSE.load(Ordering::Relaxed)
}

/// In-memory capture of `debug_log!` output, so tests can assert on what is
/// logged — in particular that no token, state value or provider-supplied text
/// reaches the log.
///
/// `debug_log!` writes to stderr, which a test cannot read back, so without this
/// the "no secret is logged" property is unassertable and regressions are
/// invisible. Compiled only under `cfg(test)` or the `log-capture` feature, so a
/// release binary has no log buffer at all. The adapter tests live in
/// `cli/tests/`, which does not get `cfg(test)` for this crate, hence the
/// feature: run them with `cargo test --features log-capture`.
#[cfg(any(test, feature = "log-capture"))]
pub mod capture {
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::sync::{Mutex, OnceLock};

    static ENABLED: AtomicBool = AtomicBool::new(false);
    static LINES: OnceLock<Mutex<Vec<String>>> = OnceLock::new();

    fn lines() -> &'static Mutex<Vec<String>> {
        LINES.get_or_init(|| Mutex::new(Vec::new()))
    }

    pub fn is_enabled() -> bool {
        ENABLED.load(Ordering::Relaxed)
    }

    pub fn record(line: String) {
        if let Ok(mut buf) = lines().lock() {
            buf.push(line);
        }
    }

    /// Start capturing. Idempotent, and deliberately takes no lock: the buffer
    /// is append-only and shared by every test in the binary, so a test asserts
    /// that its OWN unique marker is absent rather than that the buffer is
    /// empty. That makes concurrent tests safe without serialising them, and
    /// without holding a guard across an await.
    pub fn enable() {
        ENABLED.store(true, Ordering::Relaxed);
    }

    /// Everything captured so far, joined.
    pub fn joined() -> String {
        lines().lock().map(|buf| buf.join("\n")).unwrap_or_default()
    }
}

#[macro_export]
macro_rules! debug_log {
    ($($arg:tt)*) => {{
        #[cfg(any(test, feature = "log-capture"))]
        if $crate::shared::verbose::capture::is_enabled() {
            $crate::shared::verbose::capture::record(format!($($arg)*));
        }
        if $crate::shared::verbose::is_verbose() {
            eprintln!("[DEBUG] {}", format!($($arg)*));
        }
    }};
}
