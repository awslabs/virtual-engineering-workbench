/// Global flags that can appear anywhere in the command line.
/// These are relocated to before the subcommand so clap can parse them.
///
/// To add a new global flag, add it to the `Cli` struct (clap) AND to one of
/// the arrays below. That's it — no other changes needed.
const GLOBAL_BOOL_FLAGS: &[&[&str]] = &[&["--refresh-cache"], &["--verbose", "-v"]];

const GLOBAL_VALUE_FLAGS: &[&[&str]] = &[&["--profile", "-p"]];

/// Reorders CLI args so that global flags appearing after the subcommand
/// are moved to before it, where clap expects them.
///
/// Example:
///   `["vew", "pipelines", "--profile", "dev", "--refresh-cache", "get-items"]`
/// becomes:
///   `["vew", "--profile", "dev", "--refresh-cache", "pipelines", "get-items"]`
pub fn normalize_args(args: Vec<String>) -> Vec<String> {
    if args.len() <= 1 {
        return args;
    }

    let program = &args[0];

    // Find the subcommand position: first arg that doesn't start with '-'
    // and isn't a value for a preceding flag.
    let mut subcmd_pos = None;
    let mut i = 1;
    while i < args.len() {
        if is_value_flag(&args[i]) {
            i += 2; // skip flag + its value
            continue;
        }
        if args[i].starts_with('-') {
            i += 1; // skip bool flag
            continue;
        }
        subcmd_pos = Some(i);
        break;
    }

    let subcmd_pos = match subcmd_pos {
        Some(p) => p,
        None => return args, // no subcommand found, let clap handle it
    };

    // Everything from subcmd_pos onward: separate global flags from the rest
    let mut global_flags: Vec<String> = Vec::new();
    let mut remainder: Vec<String> = Vec::new();

    let mut j = subcmd_pos;
    while j < args.len() {
        if is_bool_flag(&args[j]) {
            global_flags.push(args[j].clone());
            j += 1;
        } else if is_value_flag(&args[j]) {
            global_flags.push(args[j].clone());
            if let Some(val) = args.get(j + 1) {
                // Only consume next arg as value if it doesn't look like a flag
                // and the current arg doesn't use = syntax
                if !args[j].contains('=') {
                    global_flags.push(val.clone());
                    j += 2;
                    continue;
                }
            }
            j += 1;
        } else if args[j].contains('=') && is_value_flag_prefix(&args[j]) {
            // Handle --profile=dev syntax
            global_flags.push(args[j].clone());
            j += 1;
        } else {
            remainder.push(args[j].clone());
            j += 1;
        }
    }

    // Reassemble: program + pre-subcmd flags + extracted globals + remainder
    let mut result = vec![program.clone()];
    result.extend_from_slice(&args[1..subcmd_pos]);
    result.extend(global_flags);
    result.extend(remainder);
    result
}

fn is_bool_flag(arg: &str) -> bool {
    GLOBAL_BOOL_FLAGS.iter().any(|names| names.contains(&arg))
}

fn is_value_flag(arg: &str) -> bool {
    GLOBAL_VALUE_FLAGS.iter().any(|names| names.contains(&arg))
}

fn is_value_flag_prefix(arg: &str) -> bool {
    GLOBAL_VALUE_FLAGS.iter().any(|names| {
        names
            .iter()
            .any(|name| arg.starts_with(&format!("{}=", name)))
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(s: &str) -> Vec<String> {
        s.split_whitespace().map(String::from).collect()
    }

    #[test]
    fn test_flags_before_subcommand_unchanged() {
        // Arrange & Act
        let result = normalize_args(args("vew --profile dev --verbose pipelines get-items"));

        // Assert
        assert_eq!(
            result,
            args("vew --profile dev --verbose pipelines get-items")
        );
    }

    #[test]
    fn test_flags_after_bc_moved_before_it() {
        // Act
        let result = normalize_args(args("vew pipelines --profile dev --refresh-cache"));

        // Assert
        assert_eq!(result, args("vew --profile dev --refresh-cache pipelines"));
    }

    #[test]
    fn test_flags_after_operation_moved_before_bc() {
        // Act
        let result = normalize_args(args(
            "vew pipelines get-items --profile dev --project-id abc",
        ));

        // Assert
        let result_str: Vec<&str> = result.iter().map(|s| s.as_str()).collect();
        let pipelines_pos = result_str.iter().position(|&s| s == "pipelines").unwrap();
        let profile_pos = result_str.iter().position(|&s| s == "--profile").unwrap();
        assert!(profile_pos < pipelines_pos);
        // Non-global flags stay after
        assert!(result_str.contains(&"--project-id"));
        assert!(result_str.contains(&"abc"));
    }

    #[test]
    fn test_mixed_positions() {
        // Act
        let result = normalize_args(args(
            "vew --verbose pipelines --refresh-cache get-items --project-id abc",
        ));

        // Assert
        let result_str: Vec<&str> = result.iter().map(|s| s.as_str()).collect();
        let pipelines_pos = result_str.iter().position(|&s| s == "pipelines").unwrap();
        let refresh_pos = result_str
            .iter()
            .position(|&s| s == "--refresh-cache")
            .unwrap();
        assert!(refresh_pos < pipelines_pos);
        // --verbose was already before, should stay
        assert!(result_str[1] == "--verbose");
        // operation args preserved
        assert!(result_str.contains(&"get-items"));
        assert!(result_str.contains(&"--project-id"));
    }

    #[test]
    fn test_no_subcommand() {
        // Act
        let result = normalize_args(args("vew --verbose --profile dev"));

        // Assert
        assert_eq!(result, args("vew --verbose --profile dev"));
    }

    #[test]
    fn test_auth_subcommand_unaffected() {
        // Act
        let result = normalize_args(args("vew --profile dev auth login"));

        // Assert
        assert_eq!(result, args("vew --profile dev auth login"));
    }

    #[test]
    fn test_short_verbose_after_bc() {
        // Act
        let result = normalize_args(args("vew pipelines -v"));

        // Assert
        assert_eq!(result, args("vew -v pipelines"));
    }
}
