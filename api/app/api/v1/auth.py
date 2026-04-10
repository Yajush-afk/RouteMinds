from fastapi import APIRouter, Depends

from api.app.core.auth import TokenClaims, extract_token_permissions, require_auth
from api.app.schemas.auth import AuthSessionResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/me", response_model=AuthSessionResponse)
async def read_authenticated_session(
    claims: TokenClaims = Depends(require_auth),
) -> AuthSessionResponse:
    scope = claims.get("scope")

    return AuthSessionResponse(
        subject=str(claims.get("sub") or ""),
        scope=scope.split() if isinstance(scope, str) and scope else [],
        permissions=sorted(extract_token_permissions(claims)),
        claims=claims,
    )
