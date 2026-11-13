from unittest import mock

import pytest

from app.packaging.domain.ports.image_query_service import ImageQueryService
from app.packaging.domain.ports.marketplace_agreement_service import MarketplaceAgreementService
from app.packaging.domain.ports.marketplace_ami_service import MarketplaceAmiService
from app.packaging.domain.ports.marketplace_license_service import MarketplaceLicenseService
from app.packaging.domain.ports.org_integration_service import OrgIntegrationService


@pytest.fixture()
def mock_marketplace_agreement_service():
    return mock.create_autospec(spec=MarketplaceAgreementService)


@pytest.fixture()
def mock_marketplace_ami_service():
    return mock.create_autospec(spec=MarketplaceAmiService)


@pytest.fixture()
def mock_marketplace_license_service():
    return mock.create_autospec(spec=MarketplaceLicenseService)


@pytest.fixture()
def mock_org_integration_service():
    svc = mock.create_autospec(spec=OrgIntegrationService)
    svc.is_license_manager_org_integration_active.return_value = True
    return svc


@pytest.fixture()
def mock_image_query_service():
    return mock.create_autospec(spec=ImageQueryService)
