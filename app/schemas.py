from pydantic import BaseModel, Field
from typing import List, Optional

class MenuItem(BaseModel):
    category: str
    name: str
    price: Optional[int] = Field(None, description="Price in CZK")
    allergens: List[str] = Field(default_factory=list, description="List of allergen codes")
    weight: Optional[str] = Field(None, description="Weight/portion size with unit")

class MenuData(BaseModel):
    restaurant_name: str = Field(default="Unknown Restaurant", description="Name of the restaurant")
    date: str = Field(description="Date in YYYY-MM-DD format")
    day_of_week: str = Field(description="Day of week in Czech (always today's weekday in Prague timezone)")
    menu_items: List[MenuItem]
    daily_menu: bool = Field(default=True, description="Whether this is a daily menu")
    source_url: str

class SummarizeRequest(BaseModel):
    url: str

class SummarizeResponse(BaseModel):
    cached: bool
    data: MenuData
