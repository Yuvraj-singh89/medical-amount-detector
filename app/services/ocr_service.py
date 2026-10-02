"""
OCR Service for Image Ingestion and Text Extraction.
Uses RapidOCR (ONNX runtime) with image pre-processing for handling noisy,
crumpled, or low-contrast medical documents and receipts.
"""

import io
import re
import logging
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)

# Lazy initialization of RapidOCR engine
_ocr_engine = None


def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
            logger.info("RapidOCR engine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize RapidOCR: {e}")
            _ocr_engine = None
    return _ocr_engine


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Enhance noisy, crumpled, or low-contrast medical document images.
    - Converts to Grayscale
    - Increases contrast
    - Applies slight sharpening
    """
    try:
        # Convert to RGB first if needed
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Increase contrast to highlight faint receipt ink
        enhancer = ImageEnhance.Contrast(image)
        enhanced = enhancer.enhance(1.8)
        
        # Boost sharpness to clarify broken digits
        sharpener = ImageEnhance.Sharpness(enhanced)
        sharpened = sharpener.enhance(1.5)
        
        return sharpened
    except Exception as e:
        logger.warning(f"Image preprocessing failed, falling back to original: {e}")
        return image


class OCRResult:
    def __init__(self, raw_text: str, lines: List[str], confidence: float, line_boxes: List[Dict[str, Any]]):
        self.raw_text = raw_text
        self.lines = lines
        self.confidence = confidence
        self.line_boxes = line_boxes


def extract_text_from_image_bytes(image_bytes: bytes) -> OCRResult:
    """
    Run OCR on image bytes and return aggregated text, lines, and confidence.
    """
    image = Image.open(io.BytesIO(image_bytes))
    return extract_text_from_pil(image)


def extract_text_from_pil(image: Image.Image) -> OCRResult:
    """
    Run OCR on PIL Image object.
    """
    engine = get_ocr_engine()
    if engine is None:
        raise RuntimeError("OCR engine is not available.")

    # Apply enhancement
    processed_img = preprocess_image(image)
    img_np = np.array(processed_img)

    try:
        ocr_res, _ = engine(img_np)
    except Exception as e:
        logger.error(f"OCR execution error: {e}")
        ocr_res = None

    if not ocr_res:
        # Try once without preprocessing if preprocessing was too harsh
        try:
            raw_np = np.array(image.convert("RGB"))
            ocr_res, _ = engine(raw_np)
        except Exception:
            ocr_res = None

    if not ocr_res:
        return OCRResult(raw_text="", lines=[], confidence=0.0, line_boxes=[])

    lines: List[str] = []
    confidences: List[float] = []
    line_boxes: List[Dict[str, Any]] = []

    for item in ocr_res:
        box, text, conf = item
        clean_text = str(text).strip()
        if clean_text:
            lines.append(clean_text)
            confidences.append(float(conf))
            line_boxes.append({
                "box": box,
                "text": clean_text,
                "confidence": float(conf)
            })

    raw_text = " | ".join(lines)
    avg_conf = float(np.mean(confidences)) if confidences else 0.0

    return OCRResult(
        raw_text=raw_text,
        lines=lines,
        confidence=round(avg_conf, 2),
        line_boxes=line_boxes
    )
