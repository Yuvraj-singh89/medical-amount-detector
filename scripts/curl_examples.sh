#!/usr/bin/env bash
# Sample cURL commands for Plum Problem Statement 4: AI Medical Amount Detector API

BASE_URL="http://127.0.0.1:8000"

echo "=========================================================="
echo "1. Health Check"
echo "=========================================================="
curl -s -X GET "${BASE_URL}/health" | jq .
echo -e "\n"

echo "=========================================================="
echo "2. Step 1 - OCR / Token Extraction"
echo "=========================================================="
curl -s -X POST "${BASE_URL}/api/v1/step1-extract" \
  -H "Content-Type: application/json" \
  -d '{"text": "Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%"}' | jq .
echo -e "\n"

echo "=========================================================="
echo "3. Step 2 - Numeric Normalization (OCR Repair)"
echo "=========================================================="
curl -s -X POST "${BASE_URL}/api/v1/step2-normalize" \
  -H "Content-Type: application/json" \
  -d '{"raw_tokens": ["l200", "1OOO", "200", "10%"]}' | jq .
echo -e "\n"

echo "=========================================================="
echo "4. Step 3 - Classification by Context"
echo "=========================================================="
curl -s -X POST "${BASE_URL}/api/v1/step3-classify" \
  -H "Content-Type: application/json" \
  -d '{
    "normalized_amounts": [1200, 1000, 200],
    "context_text": "Total: INR 1200 | Paid: 1000 | Due: 200"
  }' | jq .
echo -e "\n"

echo "=========================================================="
echo "5. Step 4 - Full Pipeline (Text Input)"
echo "=========================================================="
curl -s -X POST "${BASE_URL}/api/v1/process-text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%"}' | jq .
echo -e "\n"

echo "=========================================================="
echo "6. Step 4 - Full Pipeline with Noisy OCR Input"
echo "=========================================================="
curl -s -X POST "${BASE_URL}/api/v1/process-text" \
  -H "Content-Type: application/json" \
  -d '{"text": "T0tal: Rs l200 | Pald: 1000 | Due: 200"}' | jq .
echo -e "\n"

echo "=========================================================="
echo "7. Image Upload Pipeline (OCR + Normalization + Classification)"
echo "=========================================================="
curl -s -X POST "${BASE_URL}/api/v1/process-image" \
  -F "file=@app/samples/sample_clean.png" | jq .
echo -e "\n"

echo "=========================================================="
echo "8. Guardrail Exit Condition (No Amounts / Noisy Document)"
echo "=========================================================="
curl -s -X POST "${BASE_URL}/api/v1/process-text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Doctor prescription: Take Paracetamol twice a day after meals."}' | jq .
echo -e "\n"
