"""
Step 2: Numeric Normalization Service
Repairs OCR digit misrecognitions (l->1, O->0, etc.), filters out non-amount
tokens (like percentages), strips formatting, and maps to clean numeric values.
"""

import re
import logging
from typing import List, Union, Optional
from app.models.schemas import Step2Output

logger = logging.getLogger(__name__)

# Common OCR confusion character map for digit positions
OCR_DIGIT_REPLACEMENTS = {
    'l': '1',
    'L': '1',
    'I': '1',
    'i': '1',
    '|': '1',
    '!': '1',
    'O': '0',
    'o': '0',
    'D': '0',
    'S': '5',
    's': '5',
    'B': '8',
    'Z': '2',
    'z': '2',
}


def clean_and_repair_token(token: str) -> Optional[Union[int, float]]:
    """
    Attempt to repair an OCR-distorted token into a valid numeric amount.
    Returns int, float, or None if the token is not a valid financial amount.
    """
    token_str = token.strip()
    
    # Exclude percentage tokens (e.g., 10%, 18%) - they are rates, not bill values
    if token_str.endswith("%") or "%" in token_str:
        return None
        
    # Remove currency symbols or unwanted punctuation attached to the number
    token_str = re.sub(r'^[^\w\d]+|[^\w\d]+$', '', token_str)
    
    # If the token contains thousands separator commas, e.g. 1,200 or 11,200
    # Clean standard commas
    cleaned_chars = []
    has_digit = False
    
    for idx, ch in enumerate(token_str):
        if ch.isdigit():
            cleaned_chars.append(ch)
            has_digit = True
        elif ch == ',':
            # Ignore thousand separators
            continue
        elif ch == '.':
            cleaned_chars.append('.')
        elif ch in OCR_DIGIT_REPLACEMENTS:
            # Check if this character is part of a digit sequence
            cleaned_chars.append(OCR_DIGIT_REPLACEMENTS[ch])
            has_digit = True
        else:
            # Non-digit, non-repairable character
            return None
            
    repaired_str = "".join(cleaned_chars)
    if not has_digit or not repaired_str:
        return None

    # Parse into int or float
    try:
        # Check decimal point occurrences
        if repaired_str.count('.') == 1:
            val = float(repaired_str)
            # If it's a whole number like 1200.0 or 1200.00, return as int
            if val.is_integer():
                return int(val)
            return round(val, 2)
        elif repaired_str.count('.') > 1:
            # Multiple dots might be European thousand separators or OCR noise
            # e.g. 1.200.00 -> 1200.00 or 1.200 -> 1200
            parts = repaired_str.split('.')
            if len(parts[-1]) == 2:
                # Last part is cents/paise
                integer_part = "".join(parts[:-1])
                val = float(f"{integer_part}.{parts[-1]}")
                return round(val, 2)
            else:
                # All dots are thousand separators
                integer_part = "".join(parts)
                return int(integer_part)
        else:
            return int(repaired_str)
    except ValueError:
        return None


def process_step2(raw_tokens: List[str], base_confidence: float = 0.82) -> Step2Output:
    """
    Execute Step 2: Normalization.
    Takes raw tokens, repairs OCR errors, filters out percentages, and maps to numeric list.
    """
    normalized: List[Union[int, float]] = []
    corrections_made = 0
    valid_amount_count = 0

    for token in raw_tokens:
        repaired = clean_and_repair_token(token)
        if repaired is not None:
            # Check if token required OCR letter repairs
            if any(ch in OCR_DIGIT_REPLACEMENTS for ch in token if not ch.isdigit()):
                corrections_made += 1
            normalized.append(repaired)
            valid_amount_count += 1

    # Calculate normalization confidence
    if not normalized:
        conf = 0.50
    else:
        # If tokens were already clean numbers, confidence is higher
        conf = base_confidence
        if corrections_made > 0:
            # Slight adjustment for noisy corrections
            conf = max(0.70, round(conf - (corrections_made * 0.02), 2))
        else:
            conf = min(0.95, round(conf + 0.04, 2))

    return Step2Output(
        normalized_amounts=normalized,
        normalization_confidence=round(conf, 2)
    )
