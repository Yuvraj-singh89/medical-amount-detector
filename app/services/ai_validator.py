"""
AI Validation and Chaining Service.
Validates extraction integrity, checks arithmetic balance (total == paid + due),
and optionally queries Gemini API for multimodal or semantic cross-validation.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from app.models.schemas import Step1Output, Step2Output, Step3Output, Step4Output

logger = logging.getLogger(__name__)


class ValidationReport:
    def __init__(self, is_valid: bool, notes: List[str], confidence_adjustment: float = 0.0):
        self.is_valid = is_valid
        self.notes = notes
        self.confidence_adjustment = confidence_adjustment


def validate_arithmetic_balance(step3_output: Step3Output) -> ValidationReport:
    """
    Check if financial amounts are mathematically consistent:
    total_bill == paid + due
    """
    notes = []
    amounts_map = {item.type: item.value for item in step3_output.amounts}
    
    total = amounts_map.get("total_bill")
    paid = amounts_map.get("paid")
    due = amounts_map.get("due")
    
    if total is not None and paid is not None and due is not None:
        expected_total = paid + due
        if abs(total - expected_total) < 0.01:
            notes.append(f"Arithmetic validation PASSED: total_bill ({total}) == paid ({paid}) + due ({due})")
            return ValidationReport(is_valid=True, notes=notes, confidence_adjustment=+0.08)
        else:
            notes.append(
                f"Arithmetic discrepancy detected: total_bill ({total}) != paid ({paid}) + due ({due}). "
                f"Diff: {abs(total - expected_total)}"
            )
            return ValidationReport(is_valid=False, notes=notes, confidence_adjustment=-0.05)
            
    notes.append("Partial financial fields extracted; strict balance check skipped.")
    return ValidationReport(is_valid=True, notes=notes, confidence_adjustment=0.0)


def validate_with_gemini(
    raw_text: str,
    final_output: Step4Output,
    api_key: Optional[str] = None
) -> List[str]:
    """
    Optional Gemini AI audit:
    If GEMINI_API_KEY is configured, queries Gemini to verify extraction correctness,
    detect any missed discounts, and validate medical context.
    """
    notes = []
    key = api_key or os.getenv("GEMINI_API_KEY", "")
    if not key:
        return ["Gemini API key not configured; used deterministic rule validation."]
        
    try:
        from google import genai
        client = genai.Client(api_key=key)
        
        prompt = (
            f"You are a medical billing auditor AI. Audit this extraction:\n\n"
            f"Raw Text:\n{raw_text}\n\n"
            f"Extracted JSON:\n{final_output.model_dump_json()}\n\n"
            f"Briefly verify if all financial amounts (total, paid, due, discount) are correctly identified "
            f"without hallucination. Reply in 1-2 concise bullet points."
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        if response and response.text:
            notes.append(f"Gemini AI Audit: {response.text.strip()}")
        else:
            notes.append("Gemini AI validation returned empty response.")
    except Exception as e:
        logger.warning(f"Gemini AI validation skipped due to error: {e}")
        notes.append(f"Gemini AI validation skipped: {str(e)}")
        
    return notes
