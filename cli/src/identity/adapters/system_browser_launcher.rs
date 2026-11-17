use crate::identity::domain::error::IdentityError;
use crate::identity::ports::outbound::BrowserLauncher;

pub struct SystemBrowserLauncher;

impl Default for SystemBrowserLauncher {
    fn default() -> Self {
        Self::new()
    }
}

impl SystemBrowserLauncher {
    pub fn new() -> Self {
        Self
    }
}

impl BrowserLauncher for SystemBrowserLauncher {
    fn open(&self, url: &str) -> Result<(), IdentityError> {
        open::that(url).map_err(|e| IdentityError::BrowserError(e.to_string()))
    }
}
