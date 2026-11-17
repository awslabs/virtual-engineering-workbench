use clap::{CommandFactory, FromArgMatches};
use vew::bootstrap::{self, resolve_identity};
use vew::cli::app::{AuthCommands, Cli, CliTokenType, Commands};
use vew::cli::args::normalize_args;
use vew::cli::output::render;
use vew::configuration::domain::commands::ResolveProfile;
use vew::configuration::ports::inbound::ConfigurationService;
use vew::identity::domain::commands::{GetAccessToken, GetToken, Login, Logout};
use vew::identity::domain::model::TokenType;
use vew::identity::ports::inbound::IdentityService;
use vew::vew_api::domain::commands::{ExecuteCommand, InitAllCaches, ListEnabledContexts};
use vew::vew_api::domain::model::{BoundedContext, ExecuteResult};
use vew::vew_api::ports::inbound::VewApiService;

fn main() -> anyhow::Result<()> {
    let raw_args = normalize_args(std::env::args().collect());
    let cli = Cli::from_arg_matches(
        &Cli::command()
            .after_help(vew::cli::help::build_root_help(None))
            .get_matches_from(raw_args),
    )?;
    vew::shared::verbose::set_verbose(cli.verbose);
    let deps = bootstrap::bootstrap()?;

    let output: Option<String> = match cli.command {
        None => {
            let enabled = deps
                .config_svc
                .resolve_profile(ResolveProfile {
                    profile_name: cli.profile.clone(),
                })
                .ok()
                .and_then(|profile| {
                    deps.vew_api_svc
                        .list_enabled_contexts(ListEnabledContexts {
                            profile_name: profile.name.as_str().to_string(),
                        })
                        .ok()
                });

            Cli::command()
                .after_help(vew::cli::help::build_root_help(enabled.as_ref()))
                .print_help()?;
            println!();
            return Ok(());
        }
        Some(Commands::Init) => {
            let (profile, profile_id, provider) = resolve_identity(&deps, cli.profile)?;
            let token = deps.identity_svc.get_access_token(GetAccessToken {
                profile_id,
                provider,
            })?;

            let result = deps.vew_api_svc.init_all_caches(InitAllCaches {
                api_endpoint: profile.api_endpoint.clone(),
                access_token: token,
                profile_name: profile.name.as_str().to_string(),
            })?;

            Some(render(&result))
        }
        Some(Commands::Auth {
            action: AuthCommands::Login { no_browser },
        }) => {
            let (_, profile_id, provider) = resolve_identity(&deps, cli.profile)?;
            let result = deps.identity_svc.login(Login {
                profile_id,
                provider,
                no_browser,
            })?;
            Some(render(&result))
        }
        Some(Commands::Auth {
            action: AuthCommands::Logout,
        }) => {
            let (_, profile_id, provider) = resolve_identity(&deps, cli.profile)?;
            let result = deps.identity_svc.logout(Logout {
                profile_id,
                provider,
            })?;
            Some(render(&result))
        }
        Some(Commands::Auth {
            action: AuthCommands::Token { r#type },
        }) => {
            let (_, profile_id, provider) = resolve_identity(&deps, cli.profile)?;
            let token_type = match r#type {
                CliTokenType::Access => TokenType::Access,
                CliTokenType::Id => TokenType::Id,
            };
            let token = deps.identity_svc.get_token(GetToken {
                profile_id,
                provider,
                token_type,
            })?;
            print!("{token}");
            None
        }
        Some(Commands::External(args)) => {
            let bc = BoundedContext::parse(&args[0])?;
            let operation = args.get(1).cloned();
            let raw_args = if args.len() > 2 {
                args[2..].to_vec()
            } else {
                vec![]
            };

            let (profile, profile_id, provider) = resolve_identity(&deps, cli.profile)?;
            let token = deps.identity_svc.get_access_token(GetAccessToken {
                profile_id,
                provider,
            })?;

            let result = deps.vew_api_svc.execute(ExecuteCommand {
                bounded_context: bc,
                operation,
                raw_args,
                api_endpoint: profile.api_endpoint.clone(),
                access_token: token,
                refresh_cache: cli.refresh_cache,
                profile_name: profile.name.as_str().to_string(),
            })?;

            match result {
                ExecuteResult::Help(text) => {
                    println!("{text}");
                    None
                }
                ExecuteResult::Response(inv) => Some(render(&inv)),
            }
        }
    };

    if let Some(output) = output {
        println!("{output}");
    }

    Ok(())
}
