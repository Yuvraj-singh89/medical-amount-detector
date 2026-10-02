"""
Step 1: OCR / Token Extraction Service
Extracts raw numeric tokens, percentage tokens, and currency hints from text.
Includes guardrails for noisy or unparseable documents.
"""

import re
import logging
from typing import List, Optional, Tuple, Dict, Any, Union
from app.models.schemas import Step1Output, GuardrailExit

logger = logging.getLogger(__name__)

# Currency patterns mapping to standardized currency codes
CURRENCY_PATTERNS = [
    (r"(?i)\b(?:INR|RS\.?|RUPEES?)\b|₹|Rs\.?", "INR"),
    (r"(?i)\b(?:USD|DOLLARS?)\b|\$", "USD"),
    (r"(?i)\b(?:EUR|EUROS?)\b|€", "EUR"),
    (r"(?i)\b(?:GBP|POUNDS?)\b|£", "GBP"),
]

# Clinical / Non-financial patterns to exclude from bill amount extraction
# (e.g. 500mg, 10mg, Age: 34, 5 days)
CLINICAL_MEASUREMENT_PATTERN = re.compile(
    r"(?i)\b\d+(?:\.\d+)?\s*(?:mg|mcg|ml|gm|g|kg|lbs|tabs?|caps?|tablets?|capsules?|days?|hrs?|hours?|bpm|mmhg|cm|mm|od|bd|tds|sos)\b"
)
PATIENT_METADATA_PATTERN = re.compile(
    r"(?i)\b(?:age|dob|phone|mobile|tel|pin|rx)\s*[:\-]?\s*\d+\b"
)

# Financial keyword indicators
FINANCIAL_INDICATORS = [
    "total", "t0tal", "paid", "pald", "due", "dve", "bill", "receipt",
    "charge", "fee", "cost", "inr", "rs", "₹", "$", "balance",
    "discount", "invoice", "payment", "net", "gross", "payable"
]

# Regex to find candidate amount / numeric / percentage tokens:
# Matches:
# 1. Standard numbers and percentages: 1200, 1,200.50, 10%, 200.00
# 2. OCR-distorted numbers: l200, I200, 1OOO, 2O0 (common OCR digit errors)
RAW_TOKEN_PATTERN = re.compile(
    r"""
    (?<![a-zA-Z0-9])                 # Not preceded by word character
    (?:
        \d+(?:,\d+)*(?:\.\d+)?%?     # Standard numbers, decimals, percentages
        |
        [lI|][0-9OoSsBb]+(?:\.\d+)?   # e.g. l200, I1000 (OCR l/I -> 1)
        |
        [0-9]+[OoSsBb]+[0-9]*        # e.g. 1OOO, 2O0 (OCR O -> 0)
    )
    (?![a-zA-Z0-9%])                 # Not followed by word character (unless %)
    """,
    re.VERBOSE
)


def detect_currency(text: str) -> Optional[str]:
    """Detect currency hint from text context."""
    for pattern, code in CURRENCY_PATTERNS:
        if re.search(pattern, text):
            return code
    return None


def extract_raw_tokens(text: str) -> List[str]:
    """
    Extract raw numeric and percentage tokens from text, preserving order.
    Filters out clinical dosage/patient metrics like 500mg, 10mg, Age: 34,
    and cleanly separates fused OCR text boundaries (e.g. Rs1200 -> Rs 1200, :1000 -> : 1000).
    """
    # Clean up fused boundaries common in OCR output
    cleaned_boundaries = re.sub(r':([0-9lI])', r': \1', text)
    cleaned_boundaries = re.sub(r'(?i)(Rs\.?|INR|\$|₹|€|£)\s*([0-9lI][0-9OoSsBb]*)', r'\1 \2', cleaned_boundaries)
    cleaned_boundaries = re.sub(r'(\d+)([A-Za-z]+)', r'\1 \2', cleaned_boundaries)

    # Mask non-financial clinical numbers to avoid false extraction
    masked_text = cleaned_boundaries
    for m in CLINICAL_MEASUREMENT_PATTERN.finditer(cleaned_boundaries):
        masked_text = masked_text[:m.start()] + " " * (m.end() - m.start()) + masked_text[m.end():]
    for m in PATIENT_METADATA_PATTERN.finditer(cleaned_boundaries):
        masked_text = masked_text[:m.start()] + " " * (m.end() - m.start()) + masked_text[m.end():]

    tokens = []
    matches = RAW_TOKEN_PATTERN.finditer(masked_text)
    for m in matches:
        token = m.group(0).strip()
        # Filter out standalone punctuation or isolated noise
        if token and not token.isalpha():
            tokens.append(token)
            
    return tokens


def assess_document_noise(text: str, tokens: List[str]) -> bool:
    """
    Check if a document is too noisy or contains no meaningful financial info.
    Returns True if document should trigger the guardrail.
    """
    cleaned = text.strip()
    if not cleaned:
        return True
    
    # No numeric tokens at all
    if not tokens:
        return True

    # Must contain at least one financial indicator keyword or currency
    text_lower = cleaned.lower()
    has_financial_clue = any(kw in text_lower for kw in FINANCIAL_INDICATORS)
    if not has_financial_clue and not detect_currency(cleaned):
        return True
        
    # Check ratio of recognizable alphanumeric vs corrupt symbols
    total_chars = len(cleaned)
    alpha_num_count = sum(1 for c in cleaned if c.isalnum())
    if total_chars > 0 and (alpha_num_count / total_chars) < 0.25:
        return True
        
    return False


def calculate_token_confidence(tokens: List[str], currency_hint: Optional[str], ocr_conf: Optional[float] = None) -> float:
    """
    Compute confidence score for Step 1 extraction.
    Base score is influenced by token clarity, currency presence, and OCR confidence.
    """
    if not tokens:
        return 0.0

    score = 0.65
    
    # Currency presence provides strong signal of financial context
    if currency_hint:
        score += 0.10
        
    # High quality tokens (pure digits) boost confidence
    pure_digit_ratio = sum(1 for t in tokens if t.replace(",", "").replace(".", "").replace("%", "").isdigit()) / len(tokens)
    score += (pure_digit_ratio * 0.10)
    
    # Factor in OCR engine confidence if available
    if ocr_conf is not None and ocr_conf > 0:
        score = (score * 0.5) + (ocr_conf * 0.5)
        
    return round(min(max(score, 0.40), 0.95), 2)


def process_step1(text: str, ocr_conf: Optional[float] = None) -> Union[Step1Output, GuardrailExit]:
    """
    Execute Step 1: OCR / Text Extraction.
    Returns Step1Output or GuardrailExit if document is too noisy / has no amounts.
    """
    raw_tokens = extract_raw_tokens(text)
    
    # Check guardrail exit condition
    if assess_document_noise(text, raw_tokens):
        logger.warning(f"Guardrail triggered for text: '{text[:50]}...'")
        return GuardrailExit(status="no_amounts_found", reason="document too noisy")
    
    currency_hint = detect_currency(text) or "INR"
    confidence = calculate_token_confidence(raw_tokens, currency_hint, ocr_conf)
    
    return Step1Output(
        raw_tokens=raw_tokens,
        currency_hint=currency_hint,
        confidence=confidence
    )
