"""
Test Step 4: Final Output & Provenance
Verifies schema conformity, currency attribution, and exact provenance snippet formatting.
"""

from app.services.context_classifier import classify_amounts
from app.services.provenance_tracker import build_final_output
from app.models.schemas import Step4Output


def test_step4_assignment_sample():
    """
    Test Step 4 matching problem statement output:
    {
      "currency": "INR",
      "amounts": [
        {"type":"total_bill","value":1200,"source":"text: 'Total: INR 1200'"},
        {"type":"paid","value":1000,"source":"text: 'Paid: 1000'"},
        {"type":"due","value":200,"source":"text: 'Due: 200'"}
      ],
      "status":"ok"
    }
    """
    raw_text = "Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%"
    step3_res = classify_amounts([1200, 1000, 200], raw_text)
    
    result = build_final_output(step3_res, "INR", raw_text)
    assert isinstance(result, Step4Output)
    assert result.status == "ok"
    assert result.currency == "INR"
    assert len(result.amounts) == 3

    # Check provenance format
    sources = [item.source for item in result.amounts]
    for s in sources:
        assert s.startswith("text: '")
        assert s.endswith("'")

    # Values check
    vals = [item.value for item in result.amounts]
    assert 1200 in vals
    assert 1000 in vals
    assert 200 in vals
