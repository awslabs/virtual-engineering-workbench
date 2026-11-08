//! Filesystem helpers shared by adapters that persist secrets and caches.
//!
//! Provides atomic writes (tmp-file + rename) and best-effort restrictive
//! permissions on Unix. On non-Unix platforms permission calls are no-ops —
//! user-profile directory ACLs are relied on for confidentiality.

use std::io;
use std::path::Path;

/// Ensures `dir` exists and applies mode 0o700 on Unix.
pub fn ensure_private_dir(dir: &Path) -> io::Result<()> {
    std::fs::create_dir_all(dir)?;
    set_mode(dir, 0o700)
}

/// Atomically writes `bytes` to `target`. The parent directory must already
/// exist. Uses a sibling `.tmp` file + `rename` to avoid torn writes, and
/// sets mode 0o600 on Unix before renaming.
pub fn atomic_write_private(target: &Path, bytes: &[u8]) -> io::Result<()> {
    let tmp = tmp_path(target);
    std::fs::write(&tmp, bytes)?;
    set_mode(&tmp, 0o600)?;
    std::fs::rename(&tmp, target)
}

/// Emits a warning to stderr if `path` is readable by group/other on Unix.
pub fn warn_if_world_readable(path: &Path) {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        if let Ok(meta) = std::fs::metadata(path) {
            let mode = meta.permissions().mode() & 0o777;
            if mode != 0o600 {
                eprintln!(
                    "warning: token file {:?} has permissions {:o}, expected 600",
                    path, mode
                );
            }
        }
    }
    #[cfg(not(unix))]
    let _ = path;
}

fn tmp_path(target: &Path) -> std::path::PathBuf {
    let mut tmp = target.as_os_str().to_owned();
    tmp.push(".tmp");
    tmp.into()
}

#[cfg(unix)]
fn set_mode(path: &Path, mode: u32) -> io::Result<()> {
    use std::os::unix::fs::PermissionsExt;
    std::fs::set_permissions(path, std::fs::Permissions::from_mode(mode))
}

#[cfg(not(unix))]
fn set_mode(_path: &Path, _mode: u32) -> io::Result<()> {
    Ok(())
}
