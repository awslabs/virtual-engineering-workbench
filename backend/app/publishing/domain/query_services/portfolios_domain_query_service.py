from app.publishing.domain.ports import portfolios_query_service


class PortfoliosDomainQueryService:
    def __init__(self, portfolio_qry_srv: portfolios_query_service.PortfoliosQueryService):
        self._portfolio_qry_srv = portfolio_qry_srv

    def get_portfolios_by_tech_and_stage(self, technology_id: str, portfolio_stage: str):
        return self._portfolio_qry_srv.get_portfolios_by_tech_and_stage(
            technology_id=technology_id, portfolio_stage=portfolio_stage
        )
