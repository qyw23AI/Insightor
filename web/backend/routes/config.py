"""Config routes: per-user encrypted configuration."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.auth import get_current_user
from web.backend.database import get_db
from web.backend.encryption import decrypt, encrypt
from web.backend.models import User, UserConfig

router = APIRouter(prefix="/api/config", tags=["config"])

# Config keys that should be shown to the frontend
CONFIG_KEYS = [
    "GITHUB_TOKEN",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY",
    "ANTHROPIC_BASE_URL",
    "OPENAI_API_BASE",
    "DEEPSEEK_API_BASE",
    "INSIGHTOR_MODELS_PRIMARY",
    "INSIGHTOR_MODELS_WEAK",
    "INSIGHTOR_MODELS_REASONING",
    "INSIGHTOR_REVIEW_MIN_SEVERITY",
    "INSIGHTOR_REVIEW_MAX_FINDINGS",
]


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return value[:2] + "***" + value[-2:]
    return value[:4] + "***" + value[-4:]


class ConfigPutRequest(BaseModel):
    configs: dict[str, str]


@router.get("")
async def get_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    configs = result.scalars().all()
    return {c.key: decrypt(c.value) for c in configs}


@router.get("/masked")
async def get_config_masked(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    configs = result.scalars().all()
    return {c.key: _mask(decrypt(c.value)) for c in configs}


@router.put("")
async def put_config(
    req: ConfigPutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for key, value in req.configs.items():
        if not value:
            # Delete empty configs
            result = await db.execute(
                select(UserConfig).where(
                    UserConfig.user_id == current_user.id,
                    UserConfig.key == key,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                await db.delete(existing)
            continue

        encrypted = encrypt(value)
        result = await db.execute(
            select(UserConfig).where(
                UserConfig.user_id == current_user.id,
                UserConfig.key == key,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = encrypted
        else:
            db.add(UserConfig(user_id=current_user.id, key=key, value=encrypted))

    await db.commit()
    return {"ok": True}
