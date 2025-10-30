import pytest
from app.schemas import MenuData, MenuItem

class TestSchemaValidation:
    """Unit tests for Pydantic schema validation"""
    
    def test_valid_menu_item(self):
        """Test valid menu item creation"""
        item = MenuItem(
            category="polévka",
            name="Hovězí vývar",
            price=45,
            allergens=["1", "3"],
            weight="300ml"
        )
        assert item.category == "polévka"
        assert item.name == "Hovězí vývar"
        assert item.price == 45
        assert item.allergens == ["1", "3"]
        assert item.weight == "300ml"
    
    def test_menu_item_optional_fields(self):
        """Test menu item with optional fields as None"""
        item = MenuItem(
            category="hlavní chod",
            name="Řízek"
        )
        assert item.price is None
        assert item.allergens == []
        assert item.weight is None
    
    def test_valid_menu_data(self):
        """Test valid complete menu data"""
        menu_items = [
            MenuItem(
                category="polévka",
                name="Hovězí vývar",
                price=45,
                allergens=["1"],
                weight="300ml"
            ),
            MenuItem(
                category="hlavní chod", 
                name="Smažený řízek",
                price=185,
                allergens=["1", "3"],
                weight="200g"
            )
        ]
        
        menu = MenuData(
            restaurant_name="Restaurace Test",
            date="2025-10-27",
            day_of_week="neděle",
            menu_items=menu_items,
            daily_menu=True,
            source_url="https://example.com"
        )
        
        assert menu.restaurant_name == "Restaurace Test"
        assert menu.date == "2025-10-27"
        assert menu.day_of_week == "neděle"
        assert len(menu.menu_items) == 2
        assert menu.daily_menu is True
        assert menu.source_url == "https://example.com"
    
    def test_menu_data_serialization(self):
        """Test menu data can be serialized to dict"""
        item = MenuItem(category="polévka", name="Test", price=50)
        menu = MenuData(
            restaurant_name="Test",
            date="2025-10-27",
            day_of_week="neděle",
            menu_items=[item],
            source_url="https://test.com"
        )
        
        data_dict = menu.model_dump()
        assert isinstance(data_dict, dict)
        assert data_dict["restaurant_name"] == "Test"
        assert len(data_dict["menu_items"]) == 1
        assert data_dict["menu_items"][0]["category"] == "polévka"
