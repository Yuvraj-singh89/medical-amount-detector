"""
Step 4: Final Output & Provenance Tracking Service
Pairs classified amounts with currency hints and precise provenance strings.
Conforms strictly to Expected Output schema:
{
  "currency": "INR",
  "amounts": [
    {"type":"total_bill","value":1200,"source":"text: 'Total: INR 1200'"},
    ...
  ],
  "status":"ok"
}
"""

import re
import logging
from typing import List, Union
from app.models.schemas import Step3Output, Step4Output, FinalAmountItem, ClassifiedAmount

logger = logging.getLogger(__name__)


def extract_provenance_snippet(full_text: str, amount_val: Union[int, float], category: str) -> str:
    """
    Extract the most accurate concise source snippet from the raw text for provenance.
    Example: 'Total: INR 1200' or 'Paid: 1000' or 'Due: 200'
    """
    # 1. If text is pipe-delimited or newline-delimited, check each section first
    sections = re.split(r'[|\n]+', full_text)
    val_str = str(amount_val)

    # Patterns to match the number or OCR equivalent
    if val_str.startswith("1"):
        num_pattern = re.compile(r"(?i)\b[1lI\|]" + re.escape(val_str[1:]) + r"(?:\.00)?\b")
    else:
        num_pattern = re.compile(r"(?i)\b" + re.escape(val_str) + r"(?:\.00)?\b")

    for sec in sections:
        clean_sec = sec.strip()
        if num_pattern.search(clean_sec):
            # Clean up excessive spaces
            clean_sec = re.sub(r'\s+', ' ', clean_sec)
            return f"text: '{clean_sec}'"

    # 2. If not separated by pipes or newlines, find matching window around number
    m = num_pattern.search(full_text)
    if m:
        start = max(0, m.start() - 15)
        end = min(len(full_text), m.end() + 5)
        # Find clean boundary
        snippet = full_text[start:end].strip()
        snippet = re.sub(r'^[^\w]+|[^\w\d]+$', '', snippet)
        return f"text: '{snippet}'"

    # Fallback to category + value
    return f"text: '{category.replace('_', ' ').title()}: {amount_val}'"


def build_final_output(
    step3_result: Step3Output,
    currency: str,
    raw_text: str
) -> Step4Output:
    """
    Execute Step 4: Final Output.
    Generates structured JSON with currency, labeled amounts, and provenance.
    """
    final_items: List[FinalAmountItem] = []

    for item in step3_result.amounts:
        source_str = extract_provenance_snippet(raw_text, item.value, item.type)
        final_items.append(FinalAmountItem(
            type=item.type,
            value=item.value,
            source=source_str
        ))

    return Step4Output(
        currency=currency,
        amounts=final_items,
        status="ok"
    )
