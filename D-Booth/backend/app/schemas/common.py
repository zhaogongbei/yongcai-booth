from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Unified paginated response model"""

    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(
        cls, items: List[T], total: int, page: int, page_size: int
    ) -> "PaginatedResponse[T]":
        """Create paginated response"""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


class APIResponse(BaseModel, Generic[T]):
    """Unified API response model"""

    success: bool = True
    data: T = None
    message: str = None
    request_id: str = None

    @classmethod
    def success_response(
        cls, data: T = None, message: str = None, request_id: str = None
    ) -> "APIResponse[T]":
        """Create success response"""
        return cls(success=True, data=data, message=message, request_id=request_id)

    @classmethod
    def error_response(cls, message: str, request_id: str = None) -> "APIResponse":
        """Create error response"""
        return cls(success=False, message=message, request_id=request_id)
