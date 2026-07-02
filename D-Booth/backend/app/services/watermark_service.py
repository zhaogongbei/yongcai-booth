from io import BytesIO
from PIL import Image, ImageOps
from typing import Literal, Optional
from pydantic import BaseModel, Field

PositionType = Literal[
    "top_left", "top_center", "top_right",
    "center",
    "bottom_left", "bottom_center", "bottom_right",
    "tile"
]


class WatermarkSettings(BaseModel):
    """Watermark configuration model"""
    enabled: bool = False
    watermark_url: Optional[str] = None
    position: PositionType = "bottom_right"
    opacity: float = Field(0.5, ge=0.0, le=1.0)
    scale: float = Field(0.2, ge=0.1, le=2.0)
    tile: bool = False


class WatermarkService:
    """Service for applying watermarks to images"""

    @staticmethod
    def apply_watermark(
        image_bytes: bytes,
        watermark_bytes: bytes,
        position: PositionType = "bottom_right",
        opacity: float = 0.5,
        scale: float = 0.2,
        tile: bool = False
    ) -> bytes:
        """
        Apply watermark to an image using alpha compositing

        Args:
            image_bytes: Original image bytes
            watermark_bytes: Watermark image bytes (PNG with alpha recommended)
            position: Watermark position
            opacity: Watermark opacity (0-1)
            scale: Watermark scale relative to image size (0.1-2.0)
            tile: Whether to tile the watermark across the entire image

        Returns:
            Bytes of the watermarked image
        """
        # Open original image
        with Image.open(BytesIO(image_bytes)) as img:
            img = img.convert("RGBA")
            img_width, img_height = img.size

            # Open and process watermark
            with Image.open(BytesIO(watermark_bytes)) as watermark:
                watermark = watermark.convert("RGBA")

                # Calculate watermark size
                max_dimension = min(img_width, img_height) * scale
                wm_width, wm_height = watermark.size
                wm_ratio = wm_width / wm_height

                if wm_width > wm_height:
                    new_wm_width = int(max_dimension)
                    new_wm_height = int(new_wm_width / wm_ratio)
                else:
                    new_wm_height = int(max_dimension)
                    new_wm_width = int(new_wm_height * wm_ratio)

                # Resize watermark
                watermark = watermark.resize((new_wm_width, new_wm_height), Image.Resampling.LANCZOS)

                # Apply opacity
                if opacity < 1.0:
                    alpha = watermark.split()[3]
                    alpha = alpha.point(lambda p: p * opacity)
                    watermark.putalpha(alpha)

                # Create output image
                output = Image.new("RGBA", img.size, (0, 0, 0, 0))
                output.paste(img, (0, 0))

                if tile or position == "tile":
                    # Tile mode: repeat watermark across entire image
                    for x in range(0, img_width, new_wm_width):
                        for y in range(0, img_height, new_wm_height):
                            output.paste(watermark, (x, y), mask=watermark)
                else:
                    # Calculate position coordinates
                    if position == "top_left":
                        x, y = 20, 20
                    elif position == "top_center":
                        x, y = (img_width - new_wm_width) // 2, 20
                    elif position == "top_right":
                        x, y = img_width - new_wm_width - 20, 20
                    elif position == "center":
                        x, y = (img_width - new_wm_width) // 2, (img_height - new_wm_height) // 2
                    elif position == "bottom_left":
                        x, y = 20, img_height - new_wm_height - 20
                    elif position == "bottom_center":
                        x, y = (img_width - new_wm_width) // 2, img_height - new_wm_height - 20
                    elif position == "bottom_right":
                        x, y = img_width - new_wm_width - 20, img_height - new_wm_height - 20
                    else:
                        # Default to bottom right
                        x, y = img_width - new_wm_width - 20, img_height - new_wm_height - 20

                    # Apply single watermark
                    output.paste(watermark, (x, y), mask=watermark)

                # Convert back to RGB for JPG output
                output = output.convert("RGB")

                # Save to bytes
                output_bytes = BytesIO()
                output.save(output_bytes, format="JPEG", quality=95, optimize=True)
                return output_bytes.getvalue()