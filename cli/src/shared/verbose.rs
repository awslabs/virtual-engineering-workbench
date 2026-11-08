use std::sync::atomic::{AtomicBool, Ordering};

static VERBOSE: AtomicBool = AtomicBool::new(false);

pub fn set_verbose(enabled: bool) {
    VERBOSE.store(enabled, Ordering::Relaxed);
}

pub fn is_verbose() -> bool {
    VERBOSE.load(Ordering::Relaxed)
}

#[macro_export]
macro_rules! debug_log {
    ($($arg:tt)*) => {
        if $crate::shared::verbose::is_verbose() {
            eprintln!("[DEBUG] {}", format!($($arg)*));
        }
    };
}
