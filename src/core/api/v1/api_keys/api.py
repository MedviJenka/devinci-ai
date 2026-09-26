from core.settings import Config
from core.useful.log import Logger
from core.useful.auth import get_current_user_id
from fastapi import APIRouter, Depends, HTTPException
from core.database.api_keys.client import ApiKeyNotFoundError, ApiKeys
from core.database.api_keys.schemas import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeySummary

log = Logger(name='api-keys-service')

router = APIRouter(prefix=f'/api/{Config.API_VERSION}/api-keys')
api_keys = ApiKeys()


@router.get('/')
async def list_api_keys_route(user_id: str = Depends(get_current_user_id)) -> list[ApiKeySummary]:
    return api_keys.list(user_id)


@router.post('/', status_code=201)
async def create_api_key_route(
    req: ApiKeyCreateRequest, user_id: str = Depends(get_current_user_id),
) -> ApiKeyCreateResponse:
    return api_keys.create(user_id, req.name)


@router.delete('/{key_id}', status_code=204)
async def revoke_api_key_route(key_id: str, user_id: str = Depends(get_current_user_id)) -> None:
    try:
        api_keys.revoke(user_id, key_id)
    except ApiKeyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f'api key "{exc}" not found') from exc
