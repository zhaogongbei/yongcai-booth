import uuid
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.models.models import Signature
from app.schemas.signature import SignatureCreate, SignatureResponse
from app.services.storage_service import r2_storage

router = APIRouter(prefix="/signatures", tags=["signatures"])


@router.post("", response_model=SignatureResponse)
async def upload_signature(
    session_id: UUID, signature_file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
):
    """上传签名PNG并关联到会话"""
    try:
        # 验证文件类型
        if not signature_file.content_type == "image/png":
            raise HTTPException(status_code=400, detail="仅支持PNG格式的签名")

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

    except Exception as e:
        logger.error(f"上传签名失败: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"上传签名失败: {str(e)}")


@router.get("/session/{session_id}", response_model=List[SignatureResponse])
async def get_session_signatures(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """获取指定会话的所有签名"""
    result = await db.execute(
        Signature.__table__.select().where(Signature.session_id == session_id)
    )
    signatures = result.all()
    return [SignatureResponse.from_orm(sig) for sig in signatures]


@router.delete("/{signature_id}", status_code=204)
async def delete_signature(signature_id: UUID, db: AsyncSession = Depends(get_db)):
    """删除指定签名"""
    result = await db.execute(Signature.__table__.select().where(Signature.id == signature_id))
    signature = result.first()

    if not signature:
        raise HTTPException(status_code=404, detail="签名不存在")

    try:
        # 删除R2中的文件
        await r2_storage.delete_file(signature.signature_url)

        # 删除数据库记录
        await db.execute(Signature.__table__.delete().where(Signature.id == signature_id))
        await db.commit()

    except Exception as e:
        logger.error(f"删除签名失败: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除签名失败: {str(e)}")
