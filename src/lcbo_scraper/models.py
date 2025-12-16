"""Data models for LCBO product information."""

from pydantic import BaseModel


class Product(BaseModel):
    """Represents an LCBO product with scraped information."""

    product_number: str
    name: str | None = None
    url: str | None = None
    price: str | None = None
    details: dict[str, str] = {}
