from unittest import mock

import pytest

from app.packaging.domain.ports.image_query_service import ImageQueryService
from app.packaging.domain.ports.marketplace_agreement_service import MarketplaceAgreementService
from app.packaging.domain.ports.marketplace_ami_service import MarketplaceAmiService
from app.packaging.domain.ports.marketplace_license_service import MarketplaceLicenseService


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
def mock_image_query_service():
    return mock.create_autospec(spec=ImageQueryService)
