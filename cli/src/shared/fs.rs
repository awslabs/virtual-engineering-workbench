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
/// exist. Uses a sibling `.tmp` file + `rename` to avoid torn writes.
///
/// The temporary file is created with mode 0o600 rather than created at the
/// umask default and chmod'd afterwards: the token file is written through here,
/// and between those two steps the secret was readable by anyone matching the
/// umask. A stale `.tmp` from an interrupted run is removed first, so a
/// leftover file created with looser permissions (or a symlink planted at that
/// path) is never written through.
pub fn atomic_write_private(target: &Path, bytes: &[u8]) -> io::Result<()> {
    let tmp = tmp_path(target);
    match std::fs::remove_file(&tmp) {
        Ok(()) => {}
        Err(e) if e.kind() == io::ErrorKind::NotFound => {}
        Err(e) => return Err(e),
    }
    write_private_new(&tmp, bytes)?;
    std::fs::rename(&tmp, target)
}

#[cfg(unix)]
fn write_private_new(path: &Path, bytes: &[u8]) -> io::Result<()> {
    use std::io::Write;
    use std::os::unix::fs::OpenOptionsExt;

    // create_new fails if the path already exists, which also refuses to follow
    // a symlink planted there.
    let mut file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(path)?;
    file.write_all(bytes)?;
    file.sync_all()
}

#[cfg(not(unix))]
fn write_private_new(path: &Path, bytes: &[u8]) -> io::Result<()> {
    use std::io::Write;
    let mut file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?;
    file.write_all(bytes)?;
    file.sync_all()
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
