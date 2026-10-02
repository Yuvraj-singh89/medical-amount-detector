"""
Test Step 1: OCR / Text Extraction
Verifies extraction of raw numeric and percentage tokens, currency hint detection,
and confidence score calculation.
"""

from app.services.token_extractor import process_step1, extract_raw_tokens, detect_currency
from app.models.schemas import Step1Output, GuardrailExit


def test_step1_typed_text_sample():
    """
    Test standard sample input from assignment:
    Input: Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%
    Expected: raw_tokens includes 1200, 1000, 200, 10%, currency_hint: INR
    """
    sample_text = "Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%"
    result = process_step1(sample_text)
    
    assert isinstance(result, Step1Output)
    assert "1200" in result.raw_tokens
    assert "1000" in result.raw_tokens
    assert "200" in result.raw_tokens
    assert "10%" in result.raw_tokens
    assert result.currency_hint == "INR"
    assert 0.0 <= result.confidence <= 1.0


def test_step1_noisy_ocr_sample():
    """
    Test noisy OCR sample from assignment:
    Input: T0tal: Rs l200 | Pald: 1000 | Due: 200
    """
    sample_text = "T0tal: Rs l200 | Pald: 1000 | Due: 200"
    result = process_step1(sample_text)
    
    assert isinstance(result, Step1Output)
    assert len(result.raw_tokens) >= 3
    assert result.currency_hint == "INR"
    assert result.confidence > 0.5


def test_detect_currency():
    assert detect_currency("Total: ₹ 1500") == "INR"
    assert detect_currency("Net Amount: Rs 2000") == "INR"
    assert detect_currency("Bill: $ 500") == "USD"
    assert detect_currency("Total: 500 EUR") == "EUR"
