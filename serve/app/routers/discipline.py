from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.database import get_db
from ..deps import get_current_user
from ..models.user import UserInDB
from ..schemas.discipline import DisciplineResponse
from ..services.discipline import recalculate_discipline_stat


router = APIRouter(prefix="/discipline", tags=["自律统计"])


@router.get(
    "/me",
    response_model=DisciplineResponse,
    summary="获取当前用户自律排名统计",
)
async def get_my_discipline(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> DisciplineResponse:
    return await recalculate_discipline_stat(db, current_user.id or "")
