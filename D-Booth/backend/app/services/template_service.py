import copy
from io import BytesIO
from typing import Any, Dict, List, Optional
from uuid import UUID

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Template
from app.repositories.template_repository import TemplateRepository
from app.schemas.template import TemplateCreate, TemplateUpdate
from app.services.base_service import BaseService, BusinessRuleError, ValidationError


class TemplateService(BaseService[Template, TemplateCreate, TemplateUpdate]):
    """
    Service for template business logic.

    Manages photo booth templates with layer-based design system,
    validation, preview generation, and duplication.
    """

    def __init__(self, db: AsyncSession):
        repository = TemplateRepository(db)
        super().__init__(repository, db)

    # ── Validation Hooks ──────────────────────────────────────

    async def validate_create(self, obj_in: TemplateCreate) -> None:
        """Validate template creation business rules."""
        if obj_in.layers and not self.validate_template(obj_in.layers):
            raise ValidationError("Invalid template structure")

    async def validate_update(self, existing: Template, obj_in: TemplateUpdate) -> None:
        """Validate template update business rules."""
        update_dict = obj_in.model_dump(exclude_unset=True)
        if "layers" in update_dict and update_dict["layers"]:
            if not self.validate_template(update_dict["layers"]):
                raise ValidationError("Invalid template structure")

    # ── Business Logic Methods ────────────────────────────────

    async def get_template(self, template_id: UUID) -> Optional[Template]:
        """Get template by ID (alias for route compatibility)."""
        return await self.get(template_id)

    async def get_templates(
        self,
        team_id: Optional[UUID] = None,
        is_public: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Template]:
        """Get templates with optional filters.

        Combines team templates and public templates based on filters.
        """
        if team_id and is_public:
            # Return both team + public templates
            team_templates = await self.repository.get_by_team(team_id, skip, limit)
            public_templates = await self.repository.get_public_templates(skip, limit)
            # Merge and dedupe
            seen = set()
            result = []
            for t in team_templates + public_templates:
                if t.id not in seen:
                    seen.add(t.id)
                    result.append(t)
            return result[:limit]
        elif team_id:
            return await self.repository.get_by_team(team_id, skip, limit)
        elif is_public:
            return await self.repository.get_public_templates(skip, limit)
        else:
            return await self.repository.get_multi(skip, limit)

    async def get_team_templates(
        self, team_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Template]:
        """Get all templates for a team"""
        return await self.repository.get_by_team(team_id, skip, limit)

    async def get_public_templates(self, skip: int = 0, limit: int = 100) -> List[Template]:
        """Get all public templates."""
        return await self.repository.get_public_templates(skip, limit)

    async def create_template(self, template_in: TemplateCreate) -> Template:
        """Create a new template (alias for route compatibility)."""
        return await self.create(template_in)

    async def update_template(
        self, template_id: UUID, template_in: TemplateUpdate
    ) -> Optional[Template]:
        """Update template (alias for route compatibility)."""
        return await self.update(template_id, template_in)

    async def delete_template(self, template_id: UUID) -> bool:
        """Delete a template (alias for route compatibility)."""
        return await self.delete(template_id)

    def validate_template(self, template_data: Dict[str, Any]) -> bool:
        """Validate template JSON structure"""
        try:
            required_fields = [
                "name",
                "paperSize",
                "resolution",
                "orientation",
                "background",
                "elements",
            ]
            for field in required_fields:
                if field not in template_data:
                    return False

            # Validate paper size
            if (
                not isinstance(template_data["paperSize"], dict)
                or "width" not in template_data["paperSize"]
                or "height" not in template_data["paperSize"]
            ):
                return False

            # Validate elements
            if not isinstance(template_data["elements"], list):
                return False

            has_visible_photo_frame = False
            for elem in template_data["elements"]:
                elem_required = [
                    "id",
                    "type",
                    "x",
                    "y",
                    "width",
                    "height",
                    "rotation",
                    "opacity",
                    "zIndex",
                    "locked",
                    "visible",
                    "props",
                ]
                for f in elem_required:
                    if f not in elem:
                        return False

                # Validate element type
                allowed_types = {
                    "photo",
                    "text",
                    "shape",
                    "image",
                    "qr_code",
                    "date",
                    "datetime",
                    "filename",
                    "survey_answer",
                    "session_number",
                    "signature",
                }
                if elem["type"] not in allowed_types:
                    return False

                if elem["type"] == "photo":
                    props = elem.get("props")
                    if not isinstance(props, dict):
                        return False
                    photo_number = props.get("photoNumber")
                    if not isinstance(photo_number, int) or not 1 <= photo_number <= 4:
                        return False
                    if elem.get("visible") is not False:
                        has_visible_photo_frame = True

            return has_visible_photo_frame
        except Exception:
            return False

    async def generate_preview(
        self, template_id: UUID, sample_photos: List[BytesIO] = None
    ) -> bytes:
        """Generate template preview image using sample photos"""
        template = await self.get_template(template_id)
        if not template:
            raise ValueError("Template not found")

        # If layers data is empty, return placeholder
        if (
            not template.layers
            or not isinstance(template.layers, dict)
            or "elements" not in template.layers
        ):
            # Generate placeholder image
            img = Image.new("RGB", (400, 600), color="white")
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except Exception:
                font = ImageFont.load_default()

            draw.text((200, 300), template.name, fill="gray", font=font, anchor="mm")
            buf = BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()

        # Simple preview render
        try:
            # Get canvas size (4x6 inches @ 300DPI = 1200x1800, render smaller for preview)
            scale = 0.2
            canvas_width = int(1200 * scale)
            canvas_height = int(1800 * scale)
            img = Image.new(
                "RGB",
                (canvas_width, canvas_height),
                color=template.layers.get("background", {}).get("value", "#ffffff"),
            )
            draw = ImageDraw.Draw(img)

            # Render elements
            elements = template.layers.get("elements", [])
            for elem in elements:
                x = int(elem.get("x", 0) * scale)
                y = int(elem.get("y", 0) * scale)
                width = int(elem.get("width", 100) * scale)
                height = int(elem.get("height", 100) * scale)
                elem_type = elem.get("type", "text")

                if elem_type == "photo":
                    # Draw photo placeholder
                    draw.rectangle(
                        [x, y, x + width, y + height], fill="#f0f0f0", outline="#cccccc", width=2
                    )
                    try:
                        font = ImageFont.truetype("arial.ttf", int(12 * scale * 10))
                    except Exception:
                        font = ImageFont.load_default()
                    draw.text(
                        (x + width // 2, y + height // 2),
                        "PHOTO",
                        fill="#999999",
                        font=font,
                        anchor="mm",
                    )
                elif elem_type == "text":
                    # Draw text
                    content = elem.get("props", {}).get("content", "Text")
                    try:
                        font = ImageFont.truetype("arial.ttf", int(14 * scale * 10))
                    except Exception:
                        font = ImageFont.load_default()
                    color = elem.get("props", {}).get("color", "#000000")
                    draw.text(
                        (x + width // 2, y + height // 2),
                        content,
                        fill=color,
                        font=font,
                        anchor="mm",
                    )
                else:
                    # Draw generic element
                    draw.rectangle([x, y, x + width, y + height], fill="#e0e0e0", outline="#cccccc")

            buf = BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception as e:
            # Fallback to placeholder
            img = Image.new("RGB", (400, 600), color="white")
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except Exception:
                font = ImageFont.load_default()
            draw.text((200, 300), "Preview", fill="gray", font=font, anchor="mm")
            buf = BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()

    async def duplicate_template(self, template_id: UUID, new_name: str = None) -> Template:
        """Duplicate a template"""
        original = await self.get_template(template_id)
        if not original:
            raise ValueError("Template not found")

        # Create new template data
        template_data = {
            "team_id": original.team_id,
            "name": new_name or f"{original.name} (副本)",
            "description": original.description,
            "size": original.size,
            "canvas_width": original.canvas_width,
            "canvas_height": original.canvas_height,
            "layers": copy.deepcopy(original.layers),
            "is_public": original.is_public,
        }

        template_in = TemplateCreate(**template_data)
        return await self.create_template(template_in)
