import uuid
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_team_member, get_current_active_user, get_db
from app.core.logging import logger
from app.models.models import Event, PhotoSession, Signature, User
from app.schemas.signature import SignatureResponse
from app.services.storage_service import r2_storage

router = APIRouter(prefix="/signatures", tags=["signatures"])


async def _ensure_session_exists(db: AsyncSession, session_id: UUID) -> None:
    result = await db.execute(select(PhotoSession.id).where(PhotoSession.id == session_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


async def _ensure_session_access(db: AsyncSession, session_id: UUID, current_user: User) -> None:
    result = await db.execute(
        select(Event.team_id)
        .join(PhotoSession, PhotoSession.event_id == Event.id)
        .where(PhotoSession.id == session_id)
    )
    team_id = result.scalar_one_or_none()
    if team_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    await check_team_member(team_id, current_user, db)


@router.post("", response_model=SignatureResponse)
async def upload_signature(
    session_id: UUID, signature_file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
):
    """上传签名PNG并关联到会话"""
    try:
        # 验证文件类型
        if not signature_file.content_type == "image/png":
            raise HTTPException(status_code=400, detail="仅支持PNG格式的签名")

        await _ensure_session_exists(db, session_id)

        # 读取文件内容
        file_content = await signature_file.read()

        # 上传到R2存储
        file_url = await r2_storage.upload_file(
            file_data=file_content,
            filename=f"signature_{session_id}.png",
            content_type="image/png",
            folder="uploads/signatures",
        )

        # 创建签名记录
        signature = Signature(id=uuid.uuid4(), session_id=session_id, signature_url=file_url)

        db.add(signature)
        await db.commit()
        await db.refresh(signature)

        return signature

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传签名失败: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"上传签名失败: {str(e)}")


@router.get("/session/{session_id}", response_model=List[SignatureResponse])
async def get_session_signatures(
    session_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定会话的所有签名"""
    await _ensure_session_access(db, session_id, current_user)
    result = await db.execute(
        select(
            Signature.id,
            Signature.session_id,
            Signature.signature_url,
            Signature.created_at,
            Signature.updated_at,
        ).where(Signature.session_id == session_id)
    )
    return [
        SignatureResponse(
            id=row.id,
            session_id=row.session_id,
            signature_url=row.signature_url,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in result
    ]


@router.delete("/{signature_id}", status_code=204)
async def delete_signature(
    signature_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """删除指定签名"""
    result = await db.execute(
        select(Signature.signature_url, Event.team_id)
        .select_from(Signature)
        .join(PhotoSession, Signature.session_id == PhotoSession.id)
        .join(Event, PhotoSession.event_id == Event.id)
        .where(Signature.id == signature_id)
    )
    signature = result.one_or_none()
    if not signature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="签名不存在")

    await check_team_member(signature.team_id, current_user, db)

    try:
        # 删除R2中的文件
        await r2_storage.delete_file(signature.signature_url)

        # 删除数据库记录
        await db.execute(delete(Signature).where(Signature.id == signature_id))
        await db.commit()

    except Exception as e:
        logger.error(f"删除签名失败: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除签名失败: {str(e)}")
