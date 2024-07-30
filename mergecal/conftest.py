from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from mergecal.users.models import User
from mergecal.users.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir) -> None:
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture()
def user(db) -> User:
    return UserFactory()


@pytest.fixture(scope="session", autouse=True)
def patch_customer_get_or_create():
    with patch(
        "djstripe.models.Customer.get_or_create",
        return_value=(MagicMock(), True),
    ) as mock_method:
        yield mock_method
