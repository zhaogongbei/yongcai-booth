import os
import uuid
from uuid import UUID
from typing import List, Optional, Tuple
from PIL import Image
from io import BytesIO
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select
from app.models.models import Prop, PropCategory
from app.services.storage_service import r2_storage
from app.core.config import settings


class AppliedProp:
    def __init__(
        self,
        prop_id: str,
        x: float,
        y: float,
        scale: float = 1.0,
        rotation: float = 0.0,
        flip_h: bool = False,
        flip_v: bool = False,
        opacity: float = 1.0
    ):
        self.prop_id = prop_id
        self.x = max(0.0, min(1.0, x))  # 0-1比例
        self.y = max(0.0, min(1.0, y))  # 0-1比例
        self.scale = max(0.1, min(3.0, scale))  # 0.1-3.0倍
        self.rotation = max(0.0, min(360.0, rotation))  # 0-360度
        self.flip_h = flip_h
        self.flip_v = flip_v
        self.opacity = max(0.0, min(1.0, opacity))  # 0-1透明度


class PropsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_props(
        self,
        team_id: Optional[UUID] = None,
        category: Optional[PropCategory] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Prop], int]:
        """获取道具列表（团队私有 + 公共道具）"""
        query = select(Prop).where(
            or_(
                Prop.is_public == True,
                Prop.team_id == team_id
            )
        )

        if category:
            query = query.where(Prop.category == category)

        # 排序：默认道具在前，然后按创建时间
        query = query.order_by(Prop.is_default.desc(), Prop.created_at.desc())

        # 分页
        result = await self.db.execute(query.offset(skip).limit(limit))
        props = result.scalars().all()

        # 总数
        count_result = await self.db.execute(select(Prop).where(
            or_(
                Prop.is_public == True,
                Prop.team_id == team_id
            )
        ))
        total = len(count_result.scalars().all())

        return props, total

    async def upload_prop(
        self,
        team_id: str,
        file: UploadFile,
        name: str,
        category: PropCategory,
        tags: Optional[List[str]] = None
    ) -> Prop:
        """上传自定义道具PNG"""
        # 验证文件类型
        if not file.filename.lower().endswith('.png'):
            raise ValueError("Only PNG files are allowed")

        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        original_filename = f"props/{file_id}_original.png"
        thumbnail_filename = f"props/{file_id}_thumb.png"

        # 读取文件内容
        content = await file.read()

        # 处理图片生成缩略图
        with Image.open(BytesIO(content)) as img:
            # 确保是RGBA格式（支持透明）
            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            # 保存原图
            original_io = BytesIO()
            img.save(original_io, format='PNG')
            original_io.seek(0)

            # 生成缩略图（最大200x200）
            thumb_size = (200, 200)
            img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
            thumb_io = BytesIO()
            img.save(thumb_io, format='PNG')
            thumb_io.seek(0)

        # 上传到存储
        original_url = await r2_storage.upload_file(
            original_io.getvalue(),
            original_filename,
            content_type="image/png",
            folder="props"
        )
        thumbnail_url = await r2_storage.upload_file(
            thumb_io.getvalue(),
            thumbnail_filename,
            content_type="image/png",
            folder="props"
        )

        # 创建道具记录
        prop = Prop(
            team_id=team_id,
            name=name,
            category=category,
            image_url=original_url,
            thumbnail_url=thumbnail_url,
            is_public=False,
            is_default=False,
            tags=tags or []
        )

        self.db.add(prop)
        await self.db.commit()
        await self.db.refresh(prop)

        return prop

    async def delete_prop(self, prop_id: str) -> bool:
        """删除道具"""
        result = await self.db.execute(select(Prop).where(Prop.id == prop_id))
        prop = result.scalar_one_or_none()

        if not prop:
            return False

        # 不能删除默认公共道具
        if prop.is_default and prop.is_public:
            raise ValueError("Cannot delete default public props")

        await self.db.delete(prop)
        await self.db.commit()

        return True

    async def get_categories(self) -> List[dict]:
        """获取分类列表"""
        return [
            {"value": category.value, "name": category.name}
            for category in PropCategory
        ]

    async def apply_props(self, image_bytes: bytes, applied_props: List[AppliedProp]) -> bytes:
        """将道具应用到图片上"""
        # 打开基础图片
        with Image.open(BytesIO(image_bytes)) as base_img:
            # 确保基础图片是RGBA格式
            if base_img.mode != 'RGBA':
                base_img = base_img.convert('RGBA')

            base_width, base_height = base_img.size

            # 逐个应用道具
            for applied_prop in applied_props:
                # 获取道具图片
                result = await self.db.execute(select(Prop).where(Prop.id == applied_prop.prop_id))
                prop = result.scalar_one_or_none()

                if not prop:
                    continue

                # 下载道具图片
                prop_bytes = await r2_storage.download_file(prop.image_url)
                with Image.open(BytesIO(prop_bytes)) as prop_img:
                    # 确保道具图片是RGBA格式
                    if prop_img.mode != 'RGBA':
                        prop_img = prop_img.convert('RGBA')

                    # 计算缩放后的尺寸
                    prop_width, prop_height = prop_img.size
                    scaled_width = int(prop_width * applied_prop.scale)
                    scaled_height = int(prop_height * applied_prop.scale)

                    # 缩放
                    prop_img = prop_img.resize(
                        (scaled_width, scaled_height),
                        Image.Resampling.LANCZOS
                    )

                    # 翻转
                    if applied_prop.flip_h:
                        prop_img = prop_img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                    if applied_prop.flip_v:
                        prop_img = prop_img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

                    # 旋转（expand=True确保旋转后图片不会被裁剪）
                    if applied_prop.rotation != 0:
                        prop_img = prop_img.rotate(
                            applied_prop.rotation,
                            expand=True,
                            resample=Image.Resampling.BICUBIC
                        )

                    # 应用透明度
                    if applied_prop.opacity < 1.0:
                        alpha = prop_img.split()[3]
                        alpha = alpha.point(lambda p: p * applied_prop.opacity)
                        prop_img.putalpha(alpha)

                    # 计算位置（基于比例转换为像素坐标）
                    pos_x = int(applied_prop.x * base_width - prop_img.width / 2)
                    pos_y = int(applied_prop.y * base_height - prop_img.height / 2)

                    # 确保位置在图片范围内
                    pos_x = max(0, min(pos_x, base_width - prop_img.width))
                    pos_y = max(0, min(pos_y, base_height - prop_img.height))

                    # 叠加道具到基础图片
                    base_img.paste(prop_img, (pos_x, pos_y), prop_img)

            # 保存处理后的图片
            output_io = BytesIO()
            base_img.save(output_io, format='PNG')
            output_io.seek(0)

            return output_io.getvalue()