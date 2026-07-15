from pydantic import BaseModel

from conditioner.shared.constants import BEARER_TOKEN_SCHEME


class TokenResponse(BaseModel):
    """Bearer token issued after successful OAuth."""

    access_token: str
    token_type: str = BEARER_TOKEN_SCHEME.lower()
