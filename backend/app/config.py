import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── MongoDB ─────────────────────────────────────────────
    MONGODB_URL: str = "mongodb+srv://aayushchalke1501_db_user:Aayush2005@aieval.zmnuh7g.mongodb.net/?appName=AiEval"
    DATABASE_NAME: str = "answersheet_eval"

    # ── JWT ─────────────────────────────────────────────────
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ── Razorpay ────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = "rzp_test_1a4JvinKUs2blA"
    RAZORPAY_KEY_SECRET: str = "Xfnuzq63VzhCibfFXFfycWhV"

    # ── NVIDIA OCR ──────────────────────────────────────────
    NVIDIA_API_KEY: str = "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"

    # ── Email ───────────────────────────────────────────────
    SENDER_EMAIL: str = "nitesh.t.mulam2004@gmail.com"
    APP_PASSWORD: str = "gxdd zdyh gfym mlcq"

    # ── File handling ───────────────────────────────────────
    OUTPUT_DIR: str = "extracted_pdfs"
    POPPLER_PATH: str = "C:\poppler\poppler-25.12.0\Library\bin"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure output folder exists
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)