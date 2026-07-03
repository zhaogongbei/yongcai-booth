"""
Beauty schemas - canonical location for BeautyParams.
Delegates to the canonical definition in services/beauty_service.py.
"""

from app.services.beauty_service import BeautyParams, FaceBox

__all__ = ["BeautyParams", "FaceBox"]
