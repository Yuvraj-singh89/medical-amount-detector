"""
Test Step 2: Normalization
Verifies OCR digit repairs, percentage filtration, and mapping to numbers.
"""

from app.services.digit_normalizer import process_step2, clean_and_repair_token
from app.models.schemas import Step2Output


def test_step2_assignment_sample():
    """
    Input: ["1200", "1000", "200", "10%"]
    Expected: normalized_amounts: [1200, 1000, 200]
    """
    raw_tokens = ["1200", "1000", "200", "10%"]
    result = process_step2(raw_tokens)
    
    assert isinstance(result, Step2Output)
    assert result.normalized_amounts == [1200, 1000, 200]
    assert 0.0 <= result.normalization_confidence <= 1.0


def test_step2_ocr_digit_repairs():
    """
    Test fixing OCR misread characters:
    - 'l200' -> 1200 (lowercase L to 1)
    - '1OOO' -> 1000 (letter O to 0)
    - '2O0'  -> 200  (letter O to 0)
    """
    raw_tokens = ["l200", "1OOO", "2O0"]
    result = process_step2(raw_tokens)
    
    assert result.normalized_amounts == [1200, 1000, 200]


def test_clean_and_repair_token():
    assert clean_and_repair_token("1200") == 1200
    assert clean_and_repair_token("1,200.00") == 1200
    assert clean_and_repair_token("1200.50") == 1200.5
    assert clean_and_repair_token("10%") is None  # Excluded
    assert clean_and_repair_token("l200") == 1200
    assert clean_and_repair_token("I000") == 1000
