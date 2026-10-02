"""
Test Step 3: Classification by Context
Verifies categorization into total_bill, paid, due, and handling of OCR typos like T0tal, Pald.
"""

from app.services.context_classifier import classify_amounts
from app.models.schemas import Step3Output


def test_step3_assignment_sample():
    """
    Context: Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%
    Normalized amounts: [1200, 1000, 200]
    Expected:
      amounts:
        - total_bill: 1200
        - paid: 1000
        - due: 200
    """
    context = "Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%"
    normalized = [1200, 1000, 200]
    
    result = classify_amounts(normalized, context)
    assert isinstance(result, Step3Output)
    assert len(result.amounts) == 3
    
    amount_dict = {item.type: item.value for item in result.amounts}
    assert amount_dict.get("total_bill") == 1200
    assert amount_dict.get("paid") == 1000
    assert amount_dict.get("due") == 200
    assert result.confidence >= 0.70


def test_step3_noisy_ocr_context():
    """
    Context with OCR typos: T0tal: Rs l200 | Pald: 1000 | Due: 200
    """
    context = "T0tal: Rs l200 | Pald: 1000 | Due: 200"
    normalized = [1200, 1000, 200]
    
    result = classify_amounts(normalized, context)
    amount_dict = {item.type: item.value for item in result.amounts}
    
    assert amount_dict.get("total_bill") == 1200
    assert amount_dict.get("paid") == 1000
    assert amount_dict.get("due") == 200
