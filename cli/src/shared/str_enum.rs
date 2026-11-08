/// Defines an enum whose variants each map to a fixed `&'static str`.
///
/// Generates:
/// - the enum itself, with the attributes applied to it
/// - `as_str(&self) -> &'static str`
/// - `all() -> &'static [Self]`
/// - `try_from_str(&str) -> Option<Self>`
///
/// Example:
/// ```ignore
/// str_enum! {
///     #[derive(Debug, Clone, PartialEq, Eq)]
///     pub enum Color {
///         Red => "red",
///         Blue => "blue",
///     }
/// }
/// ```
#[macro_export]
macro_rules! str_enum {
    (
        $(#[$meta:meta])*
        $vis:vis enum $name:ident {
            $( $variant:ident => $str:literal ),* $(,)?
        }
    ) => {
        $(#[$meta])*
        $vis enum $name {
            $( $variant ),*
        }

        impl $name {
            pub fn as_str(&self) -> &'static str {
                match self {
                    $( Self::$variant => $str ),*
                }
            }

            pub fn all() -> &'static [Self] {
                &[ $( Self::$variant ),* ]
            }

            pub fn try_from_str(s: &str) -> Option<Self> {
                match s {
                    $( $str => Some(Self::$variant), )*
                    _ => None,
                }
            }
        }
    };
}
