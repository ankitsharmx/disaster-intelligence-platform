from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get_by_id(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        result = await db.execute(select(self.model).filter(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, db: AsyncSession, limit: int = 100, offset: int = 0) -> List[ModelType]:
        result = await db.execute(select(self.model).limit(limit).offset(offset))
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj_in: ModelType) -> ModelType:
        db.add(obj_in)
        await db.flush()
        await db.refresh(obj_in)
        return obj_in
