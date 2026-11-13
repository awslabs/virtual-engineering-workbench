use base64::Engine;
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use rand::RngCore;
use rand::rngs::OsRng;
use sha2::{Digest, Sha256};

use crate::identity::domain::model::{Nonce, PkceChallenge, StateParam};
use crate::identity::ports::outbound::CryptoProvider;

pub struct SystemCryptoProvider;

impl Default for SystemCryptoProvider {
    fn default() -> Self {
        Self::new()
    }
}

impl SystemCryptoProvider {
    pub fn new() -> Self {
        Self
    }
}

impl CryptoProvider for SystemCryptoProvider {
    fn generate_pkce_challenge(&self) -> PkceChallenge {
        let mut bytes = [0u8; 96];
        OsRng.fill_bytes(&mut bytes);
        let verifier = URL_SAFE_NO_PAD.encode(bytes);
        let digest = Sha256::digest(verifier.as_bytes());
        let challenge = URL_SAFE_NO_PAD.encode(digest);
        PkceChallenge {
            verifier,
            challenge,
        }
    }

    fn generate_state(&self) -> StateParam {
        let mut bytes = [0u8; 32];
        OsRng.fill_bytes(&mut bytes);
        StateParam(URL_SAFE_NO_PAD.encode(bytes))
    }

    fn generate_nonce(&self) -> Nonce {
        let mut bytes = [0u8; 32];
        OsRng.fill_bytes(&mut bytes);
        Nonce(URL_SAFE_NO_PAD.encode(bytes))
    }
}
