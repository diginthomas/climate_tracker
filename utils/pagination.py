from typing import Optional, Generic, TypeVar, List
from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


def get_pagination_params(page: Optional[int] = None, page_size: Optional[int] = None) -> tuple[int, int]:
    """
    Get pagination parameters with defaults and validation.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        
    Returns:
        Tuple of (skip, limit) for MongoDB queries
    """
    # Default values
    page = page if page is not None and page > 0 else 1
    page_size = page_size if page_size is not None and page_size > 0 else 20
    
    # Enforce maximum page size
    max_page_size = 100
    if page_size > max_page_size:
        page_size = max_page_size
    
    # Calculate skip
    skip = (page - 1) * page_size
    
    return skip, page_size


def create_paginated_response(
    items: List[T],
    total: int,
    page: int,
    page_size: int
) -> PaginatedResponse[T]:
    """
    Create a paginated response object.
    
    Args:
        items: List of items for current page
        total: Total number of items
        page: Current page number
        page_size: Items per page
        
    Returns:
        PaginatedResponse object
    """
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )


