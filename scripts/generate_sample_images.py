"""
Generate realistic sample bill images (clean, noisy, and no-amounts) for testing.
"""

import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "samples")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_clean_bill():
    """Generates a clean typed medical receipt."""
    img = Image.new("RGB", (650, 220), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    lines = [
        "METRO CARE CLINIC & PHARMACY",
        "Invoice No: MC-2025-9981",
        "--------------------------------------------------",
        "Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%",
        "--------------------------------------------------",
        "Thank you for choosing Metro Care."
    ]

    y = 20
    for line in lines:
        draw.text((25, y), line, fill=(20, 20, 20))
        y += 28

    out_path = os.path.join(OUTPUT_DIR, "sample_clean.png")
    img.save(out_path)
    print(f"Generated clean bill: {out_path}")


def create_noisy_bill():
    """Generates a noisy, slightly degraded receipt with OCR challenge characters."""
    img = Image.new("RGB", (650, 220), color=(245, 245, 240))
    draw = ImageDraw.Draw(img)

    # Add background noise / paper texture
    np_img = np.array(img)
    noise = np.random.normal(0, 10, np_img.shape).astype(np.int16)
    noisy_img = np.clip(np_img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(noisy_img)
    draw = ImageDraw.Draw(img)

    lines = [
        "CITY HEALTH HOSPITAL RECEIPT",
        "-----------------------------------------",
        "T0tal: Rs l200 | Pald: 1000 | Due: 200",
        "-----------------------------------------",
        "Cashier: Counter 3"
    ]

    y = 25
    for line in lines:
        draw.text((30, y), line, fill=(35, 35, 40))
        y += 32

    # Draw faint crease / scan line across receipt
    draw.line([(0, 110), (650, 115)], fill=(210, 210, 210), width=2)

    out_path = os.path.join(OUTPUT_DIR, "sample_noisy.png")
    img.save(out_path)
    print(f"Generated noisy bill: {out_path}")


def create_empty_guardrail_note():
    """Generates a doctor's note with no amounts to test guardrails."""
    img = Image.new("RGB", (650, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    lines = [
        "CLINICAL CONSULTATION NOTES",
        "Patient: John Doe (Age: 34)",
        "Diagnosis: Viral fever, seasonal allergies",
        "Rx: Paracetamol 500mg SOS, Cetirizine 10mg OD",
        "Follow up in 5 days if fever persists."
    ]

    y = 25
    for line in lines:
        draw.text((25, y), line, fill=(30, 30, 30))
        y += 30

    out_path = os.path.join(OUTPUT_DIR, "sample_empty.png")
    img.save(out_path)
    print(f"Generated empty guardrail note: {out_path}")


if __name__ == "__main__":
    create_clean_bill()
    create_noisy_bill()
    create_empty_guardrail_note()
    print("All sample images created successfully.")
