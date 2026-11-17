use crate::vew_api::domain::model::{BoundedContext, EnabledContexts};

/// Builds root help listing bounded contexts.
/// When `enabled` is Some, shows only those BCs (filtered against current enum).
/// When None, shows all BCs with a hint to run `vew init`.
pub fn build_root_help(enabled: Option<&EnabledContexts>) -> String {
    let mut out = String::from("VEW CLI — Virtual Engineering Workbench\n\n");
    out.push_str("Available bounded contexts:\n\n");

    let format_bc = |bc: &BoundedContext| {
        let summary = enabled
            .and_then(|ec| ec.contexts.iter().find(|c| c.name == bc.as_str()))
            .and_then(|c| c.summary.as_deref());
        match summary {
            Some(s) => format!("  {:<26} {}\n", bc.as_str(), s),
            None => format!("  {}\n", bc.as_str()),
        }
    };

    match enabled {
        Some(ec) => {
            for bc in BoundedContext::all() {
                if ec.contexts.iter().any(|c| c.name == bc.as_str()) {
                    out.push_str(&format_bc(bc));
                }
            }
        }
        None => {
            for bc in BoundedContext::all() {
                out.push_str(&format_bc(bc));
            }
            out.push_str(
                "\nTip: Run 'vew init' to discover which bounded contexts are available for your profile\n",
            );
        }
    }

    out.push_str("\nRun `vew <bounded-context>` to list all available operations.\n");
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::vew_api::domain::model::{BoundedContextInfo, EnabledContexts};

    #[test]
    fn test_build_root_help_lists_all_bounded_contexts() {
        // Act
        let help = build_root_help(None);

        // Assert
        for bc in BoundedContext::all() {
            assert!(help.contains(bc.as_str()), "missing BC: {}", bc.as_str());
        }
        assert!(help.contains("Run `vew <bounded-context>`"));
    }

    #[test]
    fn test_build_root_help_with_no_enabled_shows_all_and_hint() {
        // Act
        let help = build_root_help(None);

        // Assert
        assert_eq!(
            BoundedContext::all()
                .iter()
                .filter(|bc| help.contains(bc.as_str()))
                .count(),
            BoundedContext::all().len()
        );
        assert!(help.contains("vew init"));
    }

    #[test]
    fn test_build_root_help_with_enabled_shows_only_enabled() {
        // Arrange
        let enabled = EnabledContexts {
            profile_name: "dev".into(),
            contexts: vec![
                BoundedContextInfo {
                    name: "pipelines".into(),
                    summary: None,
                },
                BoundedContextInfo {
                    name: "projects".into(),
                    summary: None,
                },
                BoundedContextInfo {
                    name: "packaging".into(),
                    summary: None,
                },
            ],
        };

        // Act
        let help = build_root_help(Some(&enabled));

        // Assert
        assert!(help.contains("pipelines"));
        assert!(help.contains("projects"));
        assert!(help.contains("packaging"));
        assert!(!help.contains("authorization"));
        assert!(!help.contains("vew init"));
    }

    #[test]
    fn test_build_root_help_filters_unknown_bc_names() {
        // Arrange
        let enabled = EnabledContexts {
            profile_name: "dev".into(),
            contexts: vec![
                BoundedContextInfo {
                    name: "pipelines".into(),
                    summary: None,
                },
                BoundedContextInfo {
                    name: "nonexistent-future-bc".into(),
                    summary: None,
                },
            ],
        };

        // Act
        let help = build_root_help(Some(&enabled));

        // Assert
        assert!(help.contains("pipelines"));
        assert!(!help.contains("nonexistent-future-bc"));
    }
}
