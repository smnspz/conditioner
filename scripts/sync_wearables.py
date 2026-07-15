"""Refresh Google credentials and ingest real wearable metrics for a user.

There's no HTTP endpoint for this yet (task: background Google Health sync).
This is the ad hoc equivalent, calling the same ports/adapters a real sync
use case would.

Usage:
    poetry run python scripts/sync_wearables.py <user_id> [days_back]
"""

import asyncio
import sys
from datetime import UTC, date, datetime, timedelta

from conditioner.core.adapters.google.oauth_client import GoogleOAuthClient
from conditioner.core.adapters.persistence.sqlite.credentials_repository import (
    SqliteCredentialsRepository,
)
from conditioner.core.adapters.persistence.sqlite.metrics_repository import (
    SqliteMetricsRepository,
)
from conditioner.core.adapters.wearables.google_health.client import GoogleHealthClient
from conditioner.core.domain.auth.credentials import GoogleCredentials
from conditioner.core.services.auth.token_cipher import TokenCipher
from conditioner.shared.config import get_settings


async def run(user_id: str, days_back: int) -> None:
    settings = get_settings()
    cipher = TokenCipher(settings.token_encryption_key)
    credentials_repository = SqliteCredentialsRepository(settings.database_path, cipher)
    metrics_repository = SqliteMetricsRepository(settings.database_path)
    oauth_provider = GoogleOAuthClient(
        client_secrets_path=settings.google_client_secrets_path,
        redirect_uri=settings.google_redirect_uri,
    )

    credentials = await credentials_repository.get_by_user_id(user_id)
    if credentials is None:
        print(f"No stored Google credentials for user {user_id}")
        sys.exit(1)

    if credentials.expires_at <= datetime.now(UTC):
        print("Access token expired, refreshing...")
        tokens = await oauth_provider.refresh_access_token(credentials.refresh_token)
        credentials = GoogleCredentials(
            user_id=user_id,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token or credentials.refresh_token,
            expires_at=datetime.now(UTC) + timedelta(seconds=tokens.expires_in_seconds),
            scopes=tokens.scope.split() if tokens.scope else credentials.scopes,
        )
        await credentials_repository.save(credentials)
        print("Refreshed and saved new access token")

    end = date.today()
    start = end - timedelta(days=days_back)
    metrics = await GoogleHealthClient().fetch(user_id, credentials, start, end)

    for daily in metrics:
        await metrics_repository.save(daily)

    with_data = [m for m in metrics if m.hrv_rmssd or m.sleep_duration_hours or m.training_load]
    print(f"Synced {len(metrics)} days ({start} to {end}), {len(with_data)} had actual data")
    for m in with_data:
        print(
            f"  {m.date}: hrv={m.hrv_rmssd} rhr={m.resting_heart_rate} "
            f"sleep={m.sleep_duration_hours}h eff={m.sleep_efficiency_pct}% steps={m.steps}"
        )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 28))
