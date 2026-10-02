import os

class Settings:
    PROJECT_NAME: str = "AI-Powered Medical Document Amount Detector"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    
    # Gemini API key (optional for enhanced AI chaining and validation)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Guardrail thresholds
    MIN_TOKEN_CONFIDENCE: float = 0.40
    NOISY_DOCUMENT_RATIO: float = 0.85
    
    # Default currency fallback
    DEFAULT_CURRENCY: str = "INR"

settings = Settings()
