use clap::{Parser, Subcommand, ValueEnum};

#[derive(Parser)]
#[command(
    name = "vew",
    version,
    about = "VEW CLI",
    subcommand_required = false,
    disable_help_subcommand = true
)]
pub struct Cli {
    /// Profile name (overrides default_profile in config)
    #[arg(short, long, global = true, env = "VEW_PROFILE")]
    pub profile: Option<String>,

    /// Enable verbose debug output
    #[arg(short, long, global = true)]
    pub verbose: bool,

    /// Force re-fetch of the OpenAPI spec for the targeted bounded context
    #[arg(long, global = true)]
    pub refresh_cache: bool,

    #[command(subcommand)]
    pub command: Option<Commands>,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Authentication commands
    Auth {
        #[command(subcommand)]
        action: AuthCommands,
    },

    /// Fetch and cache API specs for all bounded contexts
    Init,

    /// Catch-all for dynamically resolved BC commands
    #[command(external_subcommand)]
    External(Vec<String>),
}

#[derive(Subcommand)]
pub enum AuthCommands {
    /// Authenticate via browser
    Login {
        /// Print the login URL to stdout instead of opening a browser
        #[arg(long, env = "VEW_NO_BROWSER")]
        no_browser: bool,
    },
    /// Remove stored tokens and revoke session
    Logout,
    /// Output a token for piping to other commands
    Token {
        /// Token type to output (access or id)
        #[arg(long, value_enum, default_value = "access")]
        r#type: CliTokenType,
    },
}

#[derive(Clone, ValueEnum)]
pub enum CliTokenType {
    Access,
    Id,
}

#[cfg(test)]
mod tests {
    use super::*;
    use clap::Parser;

    #[test]
    fn test_parse_no_subcommand_returns_none() {
        // Act
        let cli = Cli::parse_from(["vew"]);

        // Assert
        assert!(cli.command.is_none());
    }

    #[test]
    fn test_parse_auth_login() {
        let cli = Cli::parse_from(["vew", "auth", "login"]);
        assert!(matches!(
            cli.command,
            Some(Commands::Auth {
                action: AuthCommands::Login { no_browser: false }
            })
        ));
    }

    #[test]
    fn test_parse_auth_login_no_browser_flag() {
        // Act
        let cli = Cli::parse_from(["vew", "auth", "login", "--no-browser"]);

        // Assert
        assert!(matches!(
            cli.command,
            Some(Commands::Auth {
                action: AuthCommands::Login { no_browser: true }
            })
        ));
    }

    #[test]
    fn test_parse_auth_logout() {
        let cli = Cli::parse_from(["vew", "auth", "logout"]);
        assert!(matches!(
            cli.command,
            Some(Commands::Auth {
                action: AuthCommands::Logout
            })
        ));
    }

    #[test]
    fn test_parse_global_profile() {
        let cli = Cli::parse_from(["vew", "--profile", "dev", "auth", "login"]);
        assert_eq!(cli.profile, Some("dev".to_string()));
    }

    #[test]
    fn test_parse_external_subcommand() {
        let cli = Cli::parse_from(["vew", "publishing", "list-products"]);
        match cli.command {
            Some(Commands::External(args)) => {
                assert_eq!(args, vec!["publishing", "list-products"]);
            }
            _ => panic!("expected External"),
        }
    }

    #[test]
    fn test_parse_refresh_cache_flag() {
        // Act
        let cli = Cli::parse_from(["vew", "--refresh-cache", "pipelines"]);

        // Assert
        assert!(cli.refresh_cache);
        match cli.command {
            Some(Commands::External(args)) => {
                assert_eq!(args, vec!["pipelines"]);
            }
            _ => panic!("expected External"),
        }
    }

    #[test]
    fn test_parse_auth_token_default_access() {
        // Act
        let cli = Cli::parse_from(["vew", "auth", "token"]);

        // Assert
        match cli.command {
            Some(Commands::Auth {
                action: AuthCommands::Token { r#type },
            }) => assert!(matches!(r#type, CliTokenType::Access)),
            _ => panic!("expected Auth Token"),
        }
    }

    #[test]
    fn test_parse_auth_token_with_type_id() {
        // Act
        let cli = Cli::parse_from(["vew", "auth", "token", "--type", "id"]);

        // Assert
        match cli.command {
            Some(Commands::Auth {
                action: AuthCommands::Token { r#type },
            }) => assert!(matches!(r#type, CliTokenType::Id)),
            _ => panic!("expected Auth Token"),
        }
    }

    #[test]
    fn test_parse_init_subcommand() {
        // Act
        let cli = Cli::parse_from(["vew", "init"]);

        // Assert
        assert!(matches!(cli.command, Some(Commands::Init)));
    }

    #[test]
    fn test_parse_init_with_profile() {
        // Act
        let cli = Cli::parse_from(["vew", "--profile", "dev", "init"]);

        // Assert
        assert!(matches!(cli.command, Some(Commands::Init)));
        assert_eq!(cli.profile, Some("dev".to_string()));
    }
}
