import os

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not os.getenv("TELEGRAM_LIVE_TESTS"),
    reason="Set TELEGRAM_LIVE_TESTS=1 to run real Telegram integration tests",
)
def test_placeholder_for_live_telegram():
    pytest.skip("Provide a dedicated live account before enabling this suite")
