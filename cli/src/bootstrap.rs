use std::time::Duration;

use crate::configuration::adapters::file_config_reader::FileConfigReader;
use crate::configuration::domain::model::Profile;
use crate::configuration::domain::service::ConfigurationServiceImpl;
use crate::identity::adapters::file_token_store::FileTokenStore;
use crate::identity::adapters::http_oidc_client::HttpOidcClient;
use crate::identity::adapters::jwt_token_validator::JwtTokenValidator;
use crate::identity::adapters::system_browser_launcher::SystemBrowserLauncher;
use crate::identity::adapters::system_crypto_provider::SystemCryptoProvider;
use crate::identity::adapters::tcp_callback_server::TcpCallbackServer;
use crate::identity::domain::error::IdentityError;
use crate::identity::domain::model::OidcProvider;
use crate::identity::domain::service::IdentityServiceImpl;
use crate::identity::ports::outbound::OidcDiscovery;
use crate::vew_api::adapters::file_catalog_cache::FileCatalogCache;
use crate::vew_api::adapters::file_enabled_contexts_store::FileEnabledContextsStore;
use crate::vew_api::adapters::http_api_invoker::HttpApiInvoker;
use crate::vew_api::adapters::http_spec_fetcher::HttpSpecFetcher;
use crate::vew_api::domain::service::VewApiServiceImpl;

pub type AppConfigService = ConfigurationServiceImpl<FileConfigReader>;
pub type AppIdentityService = IdentityServiceImpl<
    HttpOidcClient,
    FileTokenStore,
    JwtTokenValidator,
    TcpCallbackServer,
    SystemCryptoProvider,
    SystemBrowserLauncher,
>;
pub type AppVewApiService =
    VewApiServiceImpl<HttpSpecFetcher, FileCatalogCache, HttpApiInvoker, FileEnabledContextsStore>;

pub struct Dependencies {
    pub config_svc: AppConfigService,
    pub identity_svc: AppIdentityService,
    pub discovery: HttpOidcDiscoveryAdapter,
    pub vew_api_svc: AppVewApiService,
}

// Thin wrapper so we don't expose the adapter type before it exists in mod.rs
pub use crate::identity::adapters::http_oidc_discovery::HttpOidcDiscovery as HttpOidcDiscoveryAdapter;

pub fn bootstrap() -> anyhow::Result<Dependencies> {
    let config_reader = FileConfigReader::new(FileConfigReader::default_path()?);
    let config_svc = ConfigurationServiceImpl::new(config_reader);

    let identity_svc = IdentityServiceImpl::new(
        HttpOidcClient::new(),
        FileTokenStore::new(FileTokenStore::default_dir()?),
        JwtTokenValidator::new(),
        TcpCallbackServer::new(Duration::from_secs(120)),
        SystemCryptoProvider::new(),
        SystemBrowserLauncher::new(),
    );

    let discovery = HttpOidcDiscoveryAdapter::new();

    let vew_api_svc = VewApiServiceImpl::new(
        HttpSpecFetcher::new(),
        FileCatalogCache::new(FileCatalogCache::default_dir()?),
        HttpApiInvoker::new(),
        FileEnabledContextsStore::new(FileEnabledContextsStore::default_dir()?),
    );

    Ok(Dependencies {
        config_svc,
        identity_svc,
        discovery,
        vew_api_svc,
    })
}

pub fn to_identity_context(
    profile: &Profile,
    discovery: &impl OidcDiscovery,
) -> Result<(String, OidcProvider), IdentityError> {
    let mut provider = discovery.resolve(&profile.issuer_url, &profile.oidc_client_id)?;
    if let Some(ref scopes) = profile.scopes {
        provider.scopes = scopes.clone();
    }
    Ok((profile.name.as_str().to_string(), provider))
}

/// Resolves the active profile and the OIDC provider for it in one step.
/// Used by every CLI arm that needs authentication.
pub fn resolve_identity(
    deps: &Dependencies,
    profile_name: Option<String>,
) -> anyhow::Result<(Profile, String, OidcProvider)> {
    use crate::configuration::domain::commands::ResolveProfile;
    use crate::configuration::ports::inbound::ConfigurationService;

    let profile = deps
        .config_svc
        .resolve_profile(ResolveProfile { profile_name })?;
    let (pid, provider) = to_identity_context(&profile, &deps.discovery)?;
    Ok((profile, pid, provider))
}
