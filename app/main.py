"""
FastAPI Main Application
AI-Powered Amount Detection in Medical Documents
Strictly conforms to Problem Statement 4 specifications.
"""

import os
from typing import Union, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.schemas import (
    TextProcessRequest,
    Step1Request,
    Step2Request,
    Step3Request,
    Step1Output,
    GuardrailExit,
    Step2Output,
    Step3Output,
    Step4Output,
    PipelineStepDetails,
)
from app.services import (
    process_step1,
    process_step2,
    classify_amounts,
    build_final_output,
    execute_pipeline_from_text,
    execute_pipeline_from_image,
    extract_text_from_image_bytes,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-ready REST API for extracting financial amounts from medical bills and receipts.",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration for easy local testing & ngrok integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder for interactive testing UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

samples_dir = os.path.join(os.path.dirname(__file__), "samples")
if os.path.exists(samples_dir):
    app.mount("/samples", StaticFiles(directory=samples_dir), name="samples")


@app.get("/", response_class=HTMLResponse, tags=["UI Playground"])
async def serve_home():
    """Serve the interactive Web UI playground."""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>AI Medical Amount Detector API is running. Access <a href='/docs'>Swagger Docs</a></h1>")


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }


# ==========================================
# Individual Step Endpoints
# ==========================================

@app.post(
    f"{settings.API_PREFIX}/step1-extract",
    response_model=Union[Step1Output, GuardrailExit],
    tags=["Pipeline Steps"]
)
async def api_step1_extract(req: Step1Request):
    """
    Step 1: Extract raw numeric tokens and infer currency hint.
    Exits with guardrail if document has no amounts or is too noisy.
    """
    return process_step1(req.text)


@app.post(
    f"{settings.API_PREFIX}/step2-normalize",
    response_model=Step2Output,
    tags=["Pipeline Steps"]
)
async def api_step2_normalize(req: Step2Request):
    """
    Step 2: Fix OCR digit errors (e.g. l200->1200), strip percentages, and map to numbers.
    """
    return process_step2(req.raw_tokens)


@app.post(
    f"{settings.API_PREFIX}/step3-classify",
    response_model=Step3Output,
    tags=["Pipeline Steps"]
)
async def api_step3_classify(req: Step3Request):
    """
    Step 3: Classify amounts by surrounding text context into total_bill, paid, due, etc.
    """
    return classify_amounts(req.normalized_amounts, req.context_text)


# ==========================================
# Full End-to-End Pipeline Endpoints
# ==========================================

@app.post(
    f"{settings.API_PREFIX}/process-text",
    response_model=Union[Step4Output, GuardrailExit],
    tags=["End-to-End Pipeline"]
)
async def process_text_endpoint(req: TextProcessRequest):
    """
    Execute full pipeline from raw text.
    Returns Step 4 structured JSON with currency, amounts, and provenance.
    """
    return execute_pipeline_from_text(req.text, include_details=False)


@app.post(
    f"{settings.API_PREFIX}/process-image",
    response_model=Union[Step4Output, GuardrailExit],
    tags=["End-to-End Pipeline"]
)
async def process_image_endpoint(file: UploadFile = File(...)):
    """
    Execute full pipeline from an uploaded image (bill / receipt).
    Performs OCR, token extraction, digit repair, context classification, and provenance.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a valid image (PNG, JPG, JPEG, TIFF, etc.)"
        )
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image file is empty."
        )
    return execute_pipeline_from_image(content, include_details=False)


@app.post(
    f"{settings.API_PREFIX}/pipeline/steps-text",
    response_model=Union[PipelineStepDetails, GuardrailExit],
    tags=["Diagnostic / Intermediate Pipeline Steps"]
)
async def pipeline_steps_text(req: TextProcessRequest):
    """
    Execute full pipeline from text and return intermediate results of ALL 4 steps.
    """
    return execute_pipeline_from_text(req.text, include_details=True)


@app.post(
    f"{settings.API_PREFIX}/pipeline/steps-image",
    response_model=Union[PipelineStepDetails, GuardrailExit],
    tags=["Diagnostic / Intermediate Pipeline Steps"]
)
async def pipeline_steps_image(file: UploadFile = File(...)):
    """
    Execute full pipeline from image and return intermediate results of ALL 4 steps.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be an image."
        )
    content = await file.read()
    return execute_pipeline_from_image(content, include_details=True)
