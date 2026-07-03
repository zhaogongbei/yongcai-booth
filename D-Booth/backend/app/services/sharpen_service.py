from io import BytesIO
from typing import Literal

from PIL import Image, ImageFilter

SharpenProfile = Literal["none", "low", "medium", "high"]


class SharpenService:
    """Service for applying sharpening to images for print optimization"""

    @staticmethod
    def apply_sharpen(image_bytes: bytes, profile: SharpenProfile = "medium") -> bytes:
        """
        Apply unsharp mask sharpening to an image

        Args:
            image_bytes: Original image bytes
            profile: Sharpening profile

        Returns:
            Bytes of the sharpened image
        """
        if profile == "none":
            return image_bytes

        # Define sharpening profiles
        profiles = {
            "low": ImageFilter.UnsharpMask(radius=1, percent=50, threshold=0),
            "medium": ImageFilter.UnsharpMask(radius=2, percent=100, threshold=2),
            "high": ImageFilter.UnsharpMask(radius=3, percent=150, threshold=3),
        }

        filter = profiles.get(profile, profiles["medium"])

        # Open and process image
        with Image.open(BytesIO(image_bytes)) as img:
            img = img.convert("RGB")

            # Apply sharpening
            sharpened = img.filter(filter)

            # Save to bytes
            output_bytes = BytesIO()
            sharpened.save(output_bytes, format="JPEG", quality=95, optimize=True)
            return output_bytes.getvalue()
