from typing import List

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from saved_models.models import als_ann, lfm_ann, recommend_offline, userknn
from service.api.exceptions import ModelNotFoundError, UnauthorizedUserError, UserNotFoundError
from service.log import app_logger


class RecoResponse(BaseModel):
    user_id: int
    items: List[int]


router = APIRouter()
bearer = HTTPBearer()


@router.get(
    path="/health",
    tags=["Health"],
)
async def health() -> str:
    return "I am alive"


@router.get(
    path="/reco/{model_name}/{user_id}",
    tags=["Recommendations"],
    response_model=RecoResponse,
    responses={
        404: {
            "description": "Not found",
            "content": {"application/json": {"example": {"detail": "Model or user not found"}}},
        },
        401: {
            "description": "Not authorized",
            "content": {"application/json": {"example": {"detail": "Authorization failed"}}},
        },
    },
)
async def get_reco(
    request: Request, model_name: str, user_id: int, token: HTTPAuthorizationCredentials = Depends(bearer)
) -> RecoResponse:
    app_logger.info(f"Request for model: {model_name}, user_id: {user_id}")

    if request.app.state.token != token.credentials:
        raise UnauthorizedUserError()

    if user_id > 10**9:
        raise UserNotFoundError(error_message=f"User {user_id} not found")

    k_recs = request.app.state.k_recs

    if model_name == "some_model":
        reco = list(range(k_recs))
    elif userknn and model_name == "userknn":
        reco = userknn.recommend(user_id=user_id, N_recs=10)
    elif als_ann and model_name == "als_ann":
        reco = als_ann.recommend(user_id=user_id, N_recs=10)
    elif lfm_ann and model_name == "lfm_ann":
        reco = lfm_ann.recommend(user_id=user_id, N_recs=10)
    elif recommend_offline and model_name in ("dssm", "ae", "recvae", "ranker"):
        reco = recommend_offline(model_name=model_name, user_id=user_id)
    else:
        raise ModelNotFoundError(error_message=f"Model {model_name} not found")

    return RecoResponse(user_id=user_id, items=reco)


def add_views(app: FastAPI) -> None:
    app.include_router(router)
