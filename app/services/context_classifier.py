"""
Step 3: Classification by Context Service
Labels amounts based on surrounding contextual text in medical documents,
such as 'Total', 'Paid', 'Due', 'Discount', with fuzzy matching for OCR typos.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional, Union
from app.models.schemas import Step3Output, ClassifiedAmount

logger = logging.getLogger(__name__)

# Category definitions with keywords and OCR typo variations
CATEGORY_KEYWORDS = {
    "total_bill": [
        "total", "t0tal", "totai", "totl", "bill total", "grand total",
        "gross total", "net payable", "final amount", "invoice total",
        "bill amount", "total bill", "total charges", "total amount",
        "net amount"
    ],
    "paid": [
        "paid", "pald", "p@id", "advance", "received", "payment",
        "deposit", "amount paid", "paid amount", "cash paid",
        "card paid", "online paid", "paid:"
    ],
    "due": [
        "due", "dve", "balance", "balance due", "amount due",
        "remaining", "pending", "outstanding", "due amount",
        "to pay", "payable"
    ],
    "discount": [
        "discount", "discnt", "less", "concession", "rebate", "waiver"
    ],
    "tax": [
        "tax", "gst", "cgst", "sgst", "vat"
    ],
    "subtotal": [
        "subtotal", "sub-total", "sub total"
    ]
}


def compute_levenshtein(s1: str, s2: str) -> int:
    """Compute simple Levenshtein edit distance."""
    if len(s1) < len(s2):
        return compute_levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def match_keyword_fuzzy(word: str, candidate_words: List[str], max_dist: int = 1) -> bool:
    """Check if word matches any candidate keyword with small edit distance."""
    w = word.lower().strip(" :|-#.,")
    if not w:
        return False
    for cw in candidate_words:
        if w == cw:
            return True
        if len(w) >= 3 and len(cw) >= 3 and abs(len(w) - len(cw)) <= max_dist:
            if compute_levenshtein(w, cw) <= max_dist:
                return True
    return False


def extract_context_window(text: str, amount_str: str, search_start_idx: int = 0) -> Tuple[str, int, int]:
    """
    Find the occurrence of an amount or its raw equivalent in text and extract
    the preceding and succeeding context snippet.
    """
    # Regex to find this number in text (handling commas, OCR letters)
    escaped_num = re.escape(amount_str)
    # Also allow for 'l' instead of '1' if number starts with 1
    if amount_str.startswith("1"):
        pattern_str = r"(?i)(?:\b|[^\d])([1lI\|]" + re.escape(amount_str[1:]) + r"(?:\.00)?)(?:\b|[^\d])"
    else:
        pattern_str = r"(?i)(?:\b|[^\d])(" + escaped_num + r"(?:\.00)?)(?:\b|[^\d])"

    m = re.search(pattern_str, text[search_start_idx:])
    if not m:
        # Fallback to direct substring search
        idx = text.find(amount_str, search_start_idx)
        if idx == -1:
            return "", -1, -1
        start = max(0, idx - 30)
        end = min(len(text), idx + len(amount_str) + 10)
        return text[start:end], idx, idx + len(amount_str)

    actual_start = search_start_idx + m.start(1)
    actual_end = search_start_idx + m.end(1)
    window_start = max(0, actual_start - 35)
    window_end = min(len(text), actual_end + 15)
    return text[window_start:window_end], actual_start, actual_end


def classify_from_context_snippet(snippet: str) -> Tuple[str, float]:
    """
    Analyze text snippet surrounding an amount to determine its type.
    """
    snippet_lower = snippet.lower()
    tokens = re.split(r'[\s:|\-,]+', snippet_lower)

    # Check for direct phrase matches first
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in snippet_lower:
                return cat, 0.85

    # Check fuzzy word matches for OCR typos
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for token in tokens:
            if match_keyword_fuzzy(token, keywords, max_dist=1):
                return cat, 0.78

    return "other", 0.50


def classify_amounts(
    normalized_amounts: List[Union[int, float]],
    context_text: str
) -> Step3Output:
    """
    Execute Step 3: Classification by Context.
    Uses surrounding text to label amounts into types (total_bill, paid, due, etc.).
    """
    classified: List[ClassifiedAmount] = []
    used_categories = set()
    current_search_idx = 0
    scores = []

    for val in normalized_amounts:
        val_str = str(val)
        snippet, start_idx, end_idx = extract_context_window(context_text, val_str, current_search_idx)
        if end_idx != -1:
            current_search_idx = end_idx

        category, conf = classify_from_context_snippet(snippet)
        
        # If ambiguous and we already have 3 amounts (likely Total, Paid, Due),
        # infer logical slots if unassigned
        if category == "other" or (category in used_categories and len(normalized_amounts) <= 3):
            # Check positional or value heuristics
            if "total_bill" not in used_categories and val == max(normalized_amounts):
                category = "total_bill"
                conf = 0.75
            elif "paid" not in used_categories:
                category = "paid"
                conf = 0.70
            elif "due" not in used_categories:
                category = "due"
                conf = 0.70

        used_categories.add(category)
        classified.append(ClassifiedAmount(type=category, value=val))
        scores.append(conf)

    # Verify mathematical balance: total_bill = paid + due
    # If balance holds, boost confidence
    amount_dict = {item.type: item.value for item in classified}
    if "total_bill" in amount_dict and "paid" in amount_dict and "due" in amount_dict:
        if amount_dict["total_bill"] == amount_dict["paid"] + amount_dict["due"]:
            scores = [min(0.95, s + 0.10) for s in scores]

    avg_confidence = round(sum(scores) / len(scores), 2) if scores else 0.80

    return Step3Output(
        amounts=classified,
        confidence=avg_confidence
    )
