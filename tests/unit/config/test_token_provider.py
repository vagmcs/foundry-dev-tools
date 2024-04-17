from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest import mock

import requests_mock

from foundry_dev_tools.config.config_types import FoundryOAuthGrantType, Token
from foundry_dev_tools.config.token_provider import (
    CachedTokenProvider,
)
from tests.unit.mocks import TEST_HOST, FoundryMockContext, MockOAuthTokenProvider

if TYPE_CHECKING:
    from typing import Generator


def generate_tokens_with_expiry(expiries: list[int]) -> Generator[tuple[Token, float], None, None]:
    for i in range(len(expiries)):
        yield (str(i), time.time() + (expiries[i] or 0 if expiries and len(expiries) > i else 0))


@mock.patch(
    "foundry_dev_tools.config.token_provider.CachedTokenProvider._request_token",
    side_effect=generate_tokens_with_expiry([0, 5, 1000, 0]),
)
def test_cached_token_provider(foundry_client_id, foundry_client_secret):
    ctp = CachedTokenProvider(TEST_HOST)
    assert ctp.token == str(0)
    assert ctp.token == str(1)
    # expiry of 5 seconds, but clock_skew is 10 seconds, token should be requested
    assert ctp.token == str(2)
    # expiry of 1000 seconds, token shouldn't be requested
    assert ctp.token == str(2)
    # now invalidate cache and get the next token
    ctp.invalidate_cache()
    assert ctp.token == str(3)


def test_foundry_client_credentials_provider(foundry_token, foundry_client_id, foundry_client_secret):
    ctx = FoundryMockContext(
        token_provider=MockOAuthTokenProvider(
            client_id=foundry_client_id,
            client_secret=foundry_client_secret,
            grant_type=FoundryOAuthGrantType.client_credentials,
        ),
    )
    with requests_mock.Mocker() as m:
        m.post(
            f"{ctx.token_provider.host.url}/multipass/api/oauth2/token",
            json={"access_token": foundry_token, "expires_in": 0},
        )
        assert ctx.token == foundry_token