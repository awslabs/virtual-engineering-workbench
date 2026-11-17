use super::super::domain::commands::{ExecuteCommand, InitAllCaches, ListEnabledContexts};
use super::super::domain::error::VewApiError;
use super::super::domain::model::{BulkRefreshResult, EnabledContexts, ExecuteResult};

pub trait VewApiService {
    fn execute(&self, cmd: ExecuteCommand) -> Result<ExecuteResult, VewApiError>;
    fn init_all_caches(&self, cmd: InitAllCaches) -> Result<BulkRefreshResult, VewApiError>;
    fn list_enabled_contexts(
        &self,
        cmd: ListEnabledContexts,
    ) -> Result<EnabledContexts, VewApiError>;
}
