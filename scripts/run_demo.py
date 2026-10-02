"""
Interactive Terminal Demo for Problem Statement 4:
AI-Powered Amount Detection in Medical Documents.
Demonstrates all 4 pipeline steps, noisy input handling, and guardrails.
"""

import os
import sys
import json

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.services import (
    process_step1,
    process_step2,
    classify_amounts,
    build_final_output,
    execute_pipeline_from_text,
    execute_pipeline_from_image,
)
from app.models.schemas import Step1Output, GuardrailExit


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step_num: int, name: str, data: dict):
    print(f"\n--- [Step {step_num}: {name}] ---")
    print(json.dumps(data, indent=2))


def demo_text_clean():
    print_header("DEMO 1: Clean Typed Bill (Problem Statement Sample)")
    input_text = "Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%"
    print(f"Input (text): {input_text}")

    # Step 1
    s1 = process_step1(input_text)
    print_step(1, "OCR / Text Extraction", s1.model_dump())

    # Step 2
    s2 = process_step2(s1.raw_tokens)
    print_step(2, "Numeric Normalization", s2.model_dump())

    # Step 3
    s3 = classify_amounts(s2.normalized_amounts, input_text)
    print_step(3, "Classification by Context", s3.model_dump())

    # Step 4
    s4 = build_final_output(s3, s1.currency_hint, input_text)
    print_step(4, "Final Structured Output with Provenance", s4.model_dump())


def demo_text_noisy():
    print_header("DEMO 2: Noisy OCR Text (Problem Statement Sample)")
    input_text = "T0tal: Rs l200 | Pald: 1000 | Due: 200"
    print(f"Input (noisy OCR text): {input_text}")

    # Step 1
    s1 = process_step1(input_text)
    print_step(1, "OCR / Text Extraction", s1.model_dump())

    # Step 2
    s2 = process_step2(s1.raw_tokens)
    print_step(2, "Numeric Normalization (Repairs l200 -> 1200)", s2.model_dump())

    # Step 3
    s3 = classify_amounts(s2.normalized_amounts, input_text)
    print_step(3, "Classification by Context (Repairs T0tal, Pald)", s3.model_dump())

    # Step 4
    s4 = build_final_output(s3, s1.currency_hint, input_text)
    print_step(4, "Final Structured Output with Provenance", s4.model_dump())


def demo_image_ocr():
    print_header("DEMO 3: Image OCR Ingestion")
    img_path = os.path.join(PROJECT_ROOT, "app", "samples", "sample_noisy.png")
    if not os.path.exists(img_path):
        print(f"Image not found at {img_path}. Skipping.")
        return

    print(f"Reading image file: {img_path}")
    with open(img_path, "rb") as f:
        img_bytes = f.read()

    result = execute_pipeline_from_image(img_bytes, include_details=True)
    if hasattr(result, "guardrail_triggered") and result.guardrail_triggered:
        print_step(0, "Guardrail Triggered", result.guardrail_details.model_dump())
    else:
        print(f"OCR Extracted Text: {result.ocr_raw_text}")
        print_step(1, "OCR Token Extraction", result.step1.model_dump())
        print_step(2, "Numeric Normalization", result.step2.model_dump())
        print_step(3, "Context Classification", result.step3.model_dump())
        print_step(4, "Final Output with Provenance", result.step4.model_dump())


def demo_guardrail():
    print_header("DEMO 4: Guardrail Exit Condition (Non-Financial Document)")
    input_text = "Clinical note: Patient has seasonal cold and headache. Prescribed rest."
    print(f"Input (Noisy/No amounts): {input_text}")

    result = execute_pipeline_from_text(input_text)
    print_step(0, "Guardrail Exit JSON", result.model_dump())


if __name__ == "__main__":
    demo_text_clean()
    demo_text_noisy()
    demo_image_ocr()
    demo_guardrail()
    print("\n[SUCCESS] All demo scenarios completed successfully.")
