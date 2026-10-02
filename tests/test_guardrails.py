"""
Test Guardrails and Error Handling
Verifies proper exit conditions for noisy documents, documents without amounts,
and edge cases.
"""

from app.services.token_extractor import process_step1
from app.services.pipeline import execute_pipeline_from_text, execute_pipeline_from_image
from app.models.schemas import GuardrailExit


def test_guardrail_empty_text():
    result = process_step1("")
    assert isinstance(result, GuardrailExit)
    assert result.status == "no_amounts_found"
    assert result.reason == "document too noisy"


def test_guardrail_pure_noise():
    result = process_step1("!@#$%^&*()_+~`|}{[]:;?><,./")
    assert isinstance(result, GuardrailExit)
    assert result.status == "no_amounts_found"
    assert result.reason == "document too noisy"


def test_guardrail_prescription_without_amounts():
    clinical_note = "Patient has mild viral fever. Advised bed rest and hydration. No billing records."
    result = execute_pipeline_from_text(clinical_note)
    assert isinstance(result, GuardrailExit)
    assert result.status == "no_amounts_found"
    assert result.reason == "document too noisy"
