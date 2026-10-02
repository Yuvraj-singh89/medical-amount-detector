"""
Pydantic Schemas for AI-Powered Amount Detection in Medical Documents.
Conforms strictly to the problem statement JSON specifications.
"""

from typing import List, Optional, Union
from pydantic import BaseModel, Field


# ==========================================
# Input Models
# ==========================================

class TextProcessRequest(BaseModel):
    """Input payload for text-based amount detection."""
    text: str = Field(
        ...,
        description="Raw or OCR-extracted text from medical document",
        examples=["Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%"]
    )


class Step1Request(BaseModel):
    """Input payload specifically for Step 1 extraction."""
    text: str = Field(..., description="Text from bill/receipt")


class Step2Request(BaseModel):
    """Input payload specifically for Step 2 normalization."""
    raw_tokens: List[str] = Field(..., description="Raw tokens extracted from Step 1")


class Step3Request(BaseModel):
    """Input payload specifically for Step 3 context classification."""
    normalized_amounts: List[Union[int, float]] = Field(..., description="Normalized amounts from Step 2")
    context_text: str = Field(..., description="Context text to classify amounts against")


# ==========================================
# Step 1: OCR / Token Extraction Models
# ==========================================

class Step1Output(BaseModel):
    """Expected Output for Step 1 - OCR/Text Extraction."""
    raw_tokens: List[str] = Field(..., description="Extracted raw numeric and percentage tokens")
    currency_hint: Optional[str] = Field(None, description="Inferred currency code or symbol (e.g. INR, USD)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for token extraction")


class GuardrailExit(BaseModel):
    """Exit condition when no amounts or noise exceeds threshold."""
    status: str = Field("no_amounts_found", description="Status code indicating guardrail exit")
    reason: str = Field("document too noisy", description="Explanation of why processing stopped")


# ==========================================
# Step 2: Normalization Models
# ==========================================

class Step2Output(BaseModel):
    """Expected Output for Step 2 - Normalization."""
    normalized_amounts: List[Union[int, float]] = Field(..., description="Cleaned, parsed numeric amounts (excluding %)")
    normalization_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for normalization")


# ==========================================
# Step 3: Classification by Context Models
# ==========================================

class ClassifiedAmount(BaseModel):
    """Individual classified amount without provenance."""
    type: str = Field(..., description="Classification category (e.g. total_bill, paid, due, discount)")
    value: Union[int, float] = Field(..., description="Normalized numeric value")


class Step3Output(BaseModel):
    """Expected Output for Step 3 - Classification by Context."""
    amounts: List[ClassifiedAmount] = Field(..., description="List of amounts classified by context")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence score")


# ==========================================
# Step 4: Final Output Models
# ==========================================

class FinalAmountItem(BaseModel):
    """Classified amount with source provenance snippet."""
    type: str = Field(..., description="Classification category (e.g. total_bill, paid, due)")
    value: Union[int, float] = Field(..., description="Normalized numeric value")
    source: str = Field(..., description="Provenance text snippet where amount was found, e.g. text: 'Total: INR 1200'")


class Step4Output(BaseModel):
    """Expected Output for Step 4 - Final Structured Output."""
    currency: str = Field(..., description="Identified currency (e.g. INR, USD, EUR)")
    amounts: List[FinalAmountItem] = Field(..., description="Labeled amounts with provenance")
    status: str = Field("ok", description="Processing status")


# ==========================================
# Pipeline Intermediate / Debug Model
# ==========================================

class PipelineStepDetails(BaseModel):
    """All intermediate step outputs for transparent evaluation and UI tracing."""
    input_text: str
    ocr_raw_text: Optional[str] = None
    step1: Optional[Step1Output] = None
    step2: Optional[Step2Output] = None
    step3: Optional[Step3Output] = None
    step4: Optional[Step4Output] = None
    guardrail_triggered: bool = False
    guardrail_details: Optional[GuardrailExit] = None
    ai_validation_notes: Optional[List[str]] = None
