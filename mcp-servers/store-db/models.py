from typing import Optional

from pydantic import BaseModel


class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    inventory: int
    price: float


class ProductCreate(ProductBase):
    pass


class Product(ProductBase):
    id: int

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    product_id: int
    quantity: int
    customer_identifier: str


class OrderCreate(OrderBase):
    pass


class Order(OrderBase):
    id: int

    class Config:
        from_attributes = True


class ProductOrderRequest(BaseModel):
    product_id: int
    quantity: int
    customer_identifier: str
