import pytest
from app.fetch.utils import (
    normalize_price_human, 
    convert_weight_to_string, 
    extract_allergens,
    detect_weekday_from_text
)

class TestPriceNormalization:
    """Unit tests for price normalization function"""
    
    def test_czech_price_format(self):
        """Test Czech price format with comma and dash"""
        assert normalize_price_human("145,-") == 145
        assert normalize_price_human("95,-") == 95
    
    def test_price_with_currency(self):
        """Test price with currency symbols"""
        assert normalize_price_human("120 Kč") == 120
        assert normalize_price_human("85 CZK") == 85
    
    def test_decimal_prices(self):
        """Test prices with decimal places"""
        assert normalize_price_human("145.50") == 145
        assert normalize_price_human("99,90") == 99
    
    def test_plain_numbers(self):
        """Test plain number strings"""
        assert normalize_price_human("75") == 75
        assert normalize_price_human("250") == 250
    
    def test_invalid_inputs(self):
        """Test handling of invalid inputs"""
        assert normalize_price_human("") is None
        assert normalize_price_human("bez ceny") is None
        assert normalize_price_human(None) is None

class TestWeightConversion:
    """Unit tests for weight/volume conversion"""
    
    def test_kilogram_to_gram(self):
        """Test kg to g conversion"""
        assert convert_weight_to_string("0,5 kg") == "500g"
        assert convert_weight_to_string("1.2 kg") == "1200g"
    
    def test_liter_to_milliliter(self):
        """Test l to ml conversion"""
        assert convert_weight_to_string("0.33 l") == "330ml"
        assert convert_weight_to_string("1,5 litr") == "1500ml"
    
    def test_direct_units(self):
        """Test direct g/ml units"""
        assert convert_weight_to_string("150g") == "150g"
        assert convert_weight_to_string("500 ml") == "500ml"
    
    def test_portions(self):
        """Test portion/piece units"""
        assert convert_weight_to_string("2 ks") == "2 ks"
        assert convert_weight_to_string("1 porce") == "1 porce"
    
    def test_invalid_weight_input(self):
        """Test handling of invalid weight inputs"""
        assert convert_weight_to_string("") is None
        assert convert_weight_to_string("bez váhy") is None

class TestAllergenExtraction:
    """Unit tests for allergen code extraction"""
    
    def test_parentheses_format(self):
        """Test allergen codes in parentheses"""
        assert extract_allergens("Řízek (1,3,9)") == ["1", "3", "9"]
        assert extract_allergens("Polévka (7)") == ["7"]
    
    def test_brackets_format(self):
        """Test allergen codes in square brackets"""
        assert extract_allergens("Salát [2,4,6]") == ["2", "4", "6"]
    
    def test_allergen_label(self):
        """Test with 'alergeny:' label"""
        assert extract_allergens("alergeny: 1,3,9") == ["1", "3", "9"]
        assert extract_allergens("Alergény: 5, 8") == ["5", "8"]
    
    def test_no_allergens(self):
        """Test text without allergens"""
        assert extract_allergens("Čistý pokrm") == []
        assert extract_allergens("") == []
    
    def test_duplicate_removal(self):
        """Test removal of duplicate allergen codes"""
        assert extract_allergens("Test (1,3,1) alergeny: 3,9") == ["1", "3", "9"]

class TestWeekdayDetection:
    """Unit tests for Czech weekday detection"""
    
    def test_full_weekday_names(self):
        """Test detection of full Czech weekday names"""
        assert detect_weekday_from_text("Dnešní menu - středa") == "středa"
        assert detect_weekday_from_text("Pondělní speciálka") == "pondělí"
    
    def test_abbreviated_weekdays(self):
        """Test detection of abbreviated weekdays"""
        assert detect_weekday_from_text("Menu na st:") == "středa"
        assert detect_weekday_from_text("Pá - 25.10.") == "pátek"
    
    def test_case_insensitive(self):
        """Test case insensitive detection"""
        assert detect_weekday_from_text("STŘEDA MENU") == "středa"
        assert detect_weekday_from_text("pátek speciál") == "pátek"
    
    def test_fallback_to_current(self):
        """Test fallback to current weekday when none detected"""
        # Test that function returns a valid Czech weekday
        from app.fetch.utils import CZ_WEEKDAYS
        result = detect_weekday_from_text("Menu bez dne")
        assert result in CZ_WEEKDAYS
