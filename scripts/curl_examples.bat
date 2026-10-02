@echo off
REM Sample cURL commands for Windows Command Prompt / PowerShell

set BASE_URL=http://127.0.0.1:8000

echo ==========================================================
echo 1. Health Check
echo ==========================================================
curl -X GET "%BASE_URL%/health"
echo.
echo.

echo ==========================================================
echo 2. Step 1 - OCR / Token Extraction
echo ==========================================================
curl -X POST "%BASE_URL%/api/v1/step1-extract" -H "Content-Type: application/json" -d "{\"text\": \"Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%%\"}"
echo.
echo.

echo ==========================================================
echo 3. Step 2 - Numeric Normalization (OCR Repair)
echo ==========================================================
curl -X POST "%BASE_URL%/api/v1/step2-normalize" -H "Content-Type: application/json" -d "{\"raw_tokens\": [\"l200\", \"1OOO\", \"200\", \"10%%\"]}"
echo.
echo.

echo ==========================================================
echo 4. Step 3 - Classification by Context
echo ==========================================================
curl -X POST "%BASE_URL%/api/v1/step3-classify" -H "Content-Type: application/json" -d "{\"normalized_amounts\": [1200, 1000, 200], \"context_text\": \"Total: INR 1200 | Paid: 1000 | Due: 200\"}"
echo.
echo.

echo ==========================================================
echo 5. Step 4 - Full Pipeline (Text Input)
echo ==========================================================
curl -X POST "%BASE_URL%/api/v1/process-text" -H "Content-Type: application/json" -d "{\"text\": \"Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%%\"}"
echo.
echo.

echo ==========================================================
echo 6. Step 4 - Full Pipeline with Noisy OCR Input
echo ==========================================================
curl -X POST "%BASE_URL%/api/v1/process-text" -H "Content-Type: application/json" -d "{\"text\": \"T0tal: Rs l200 | Pald: 1000 | Due: 200\"}"
echo.
echo.

echo ==========================================================
echo 7. Guardrail Test (No Amounts / Noisy Doc)
echo ==========================================================
curl -X POST "%BASE_URL%/api/v1/process-text" -H "Content-Type: application/json" -d "{\"text\": \"Clinical note: Patient has mild viral fever. Advised bed rest and hydration.\"}"
echo.
echo.

pause
