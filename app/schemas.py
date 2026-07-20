from pydantic import BaseModel


class ProductRecommendation(BaseModel):
    id: int
    name: str
    price: float
    image: str
    category_id: int
    slug: str

    class Config:
        from_attributes = True
