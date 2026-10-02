"""
Pipeline Orchestration Service
Chains Step 1 (OCR/Extraction) -> Step 2 (Normalization) -> Step 3 (Classification) -> Step 4 (Final Output).
Enforces guardrails and supports both text and image input formats.
"""

import logging
from typing import Union, Optional, Tuple
from app.models.schemas import (
    Step1Output,
    GuardrailExit,
    Step2Output,
    Step3Output,
    Step4Output,
    PipelineStepDetails,
)
from app.services.ocr_service import extract_text_from_image_bytes
from app.services.token_extractor import process_step1
from app.services.digit_normalizer import process_step2
from app.services.context_classifier import classify_amounts
from app.services.provenance_tracker import build_final_output
from app.services.ai_validator import validate_arithmetic_balance, validate_with_gemini

logger = logging.getLogger(__name__)


def execute_pipeline_from_text(
    text: str,
    include_details: bool = False
) -> Union[Step4Output, GuardrailExit, PipelineStepDetails]:
    """
    Execute full pipeline starting from raw or typed text.
    """
    # Step 1: Token Extraction
    step1_res = process_step1(text)
    if isinstance(step1_res, GuardrailExit):
        if include_details:
            return PipelineStepDetails(
                input_text=text,
                guardrail_triggered=True,
                guardrail_details=step1_res
            )
        return step1_res

    # Step 2: Normalization
    step2_res = process_step2(step1_res.raw_tokens)
    
    # If no valid normalized amounts survived Step 2
    if not step2_res.normalized_amounts:
        exit_guard = GuardrailExit(status="no_amounts_found", reason="document too noisy")
        if include_details:
            return PipelineStepDetails(
                input_text=text,
                step1=step1_res,
                step2=step2_res,
                guardrail_triggered=True,
                guardrail_details=exit_guard
            )
        return exit_guard

    # Step 3: Context Classification
    step3_res = classify_amounts(step2_res.normalized_amounts, text)

    # AI & Arithmetic Validation
    val_report = validate_arithmetic_balance(step3_res)

    # Step 4: Final Output
    currency = step1_res.currency_hint or "INR"
    step4_res = build_final_output(step3_res, currency, text)

    if include_details:
        ai_notes = list(val_report.notes)
        # Optional Gemini AI check
        gemini_notes = validate_with_gemini(text, step4_res)
        ai_notes.extend(gemini_notes)

        return PipelineStepDetails(
            input_text=text,
            step1=step1_res,
            step2=step2_res,
            step3=step3_res,
            step4=step4_res,
            guardrail_triggered=False,
            ai_validation_notes=ai_notes
        )

    return step4_res


def execute_pipeline_from_image(
    image_bytes: bytes,
    include_details: bool = False
) -> Union[Step4Output, GuardrailExit, PipelineStepDetails]:
    """
    Execute full pipeline starting from an image (scanned bill / receipt).
    Runs OCR first, then chains steps 1 to 4.
    """
    ocr_result = extract_text_from_image_bytes(image_bytes)
    
    if not ocr_result.raw_text.strip():
        exit_guard = GuardrailExit(status="no_amounts_found", reason="document too noisy")
        if include_details:
            return PipelineStepDetails(
                input_text="",
                ocr_raw_text="",
                guardrail_triggered=True,
                guardrail_details=exit_guard
            )
        return exit_guard

    # Step 1: Token extraction with OCR confidence
    step1_res = process_step1(ocr_result.raw_text, ocr_conf=ocr_result.confidence)
    if isinstance(step1_res, GuardrailExit):
        if include_details:
            return PipelineStepDetails(
                input_text=ocr_result.raw_text,
                ocr_raw_text=ocr_result.raw_text,
                guardrail_triggered=True,
                guardrail_details=step1_res
            )
        return step1_res

    # Step 2: Normalization (repairs OCR digit errors)
    step2_res = process_step2(step1_res.raw_tokens)
    if not step2_res.normalized_amounts:
        exit_guard = GuardrailExit(status="no_amounts_found", reason="document too noisy")
        if include_details:
            return PipelineStepDetails(
                input_text=ocr_result.raw_text,
                ocr_raw_text=ocr_result.raw_text,
                step1=step1_res,
                step2=step2_res,
                guardrail_triggered=True,
                guardrail_details=exit_guard
            )
        return exit_guard

    # Step 3: Context Classification
    step3_res = classify_amounts(step2_res.normalized_amounts, ocr_result.raw_text)

    # Validation
    val_report = validate_arithmetic_balance(step3_res)

    # Step 4: Final Output
    currency = step1_res.currency_hint or "INR"
    step4_res = build_final_output(step3_res, currency, ocr_result.raw_text)

    if include_details:
        ai_notes = list(val_report.notes)
        gemini_notes = validate_with_gemini(ocr_result.raw_text, step4_res)
        ai_notes.extend(gemini_notes)

        return PipelineStepDetails(
            input_text=ocr_result.raw_text,
            ocr_raw_text=ocr_result.raw_text,
            step1=step1_res,
            step2=step2_res,
            step3=step3_res,
            step4=step4_res,
            guardrail_triggered=False,
            ai_validation_notes=ai_notes
        )

    return step4_res
