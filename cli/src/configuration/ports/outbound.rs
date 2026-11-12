use super::super::domain::error::ConfigError;
use super::super::domain::model::Config;

pub trait ConfigReader {
    fn read_config(&self) -> Result<Config, ConfigError>;
}
