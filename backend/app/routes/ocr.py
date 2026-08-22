"""
routes/ocr.py
Standalone NVIDIA NIM OCR endpoint — convert scanned / handwritten PDFs to text.
"""

import os
import shutil
import tempfile
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.auth import get_current_user
from app.models import UserInDB as User
from app.config import settings
from app.evaluation_engine import PDFProcessor

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post("/extract-text", summary="Extract text from a PDF using NVIDIA NIM OCR")
async def extract_text(
    pdf_file:   UploadFile = File(..., description="PDF to process (scanned or digital)"),
    force_ocr:  bool       = Form(False, description="Force OCR even if PyPDF2 extracts text"),
    current_user: User = Depends(get_current_user),
):
    """
    Extracts text from the uploaded PDF.

    - If the PDF is digital (has embedded text), PyPDF2 is used first (fast).
    - If the PDF is scanned/handwritten, NVIDIA NIM llama-3.2-11b-vision is used for OCR.
    - Set `force_ocr=true` to always use the NVIDIA NIM vision model.
    """
    tmp_dir = tempfile.mkdtemp(prefix="ocr_")
    try:
        pdf_path = os.path.join(tmp_dir, pdf_file.filename)
        with open(pdf_path, "wb") as f:
            shutil.copyfileobj(pdf_file.file, f)

        processor = PDFProcessor(nvidia_api_key=settings.NVIDIA_API_KEY)
        logs: list[str] = []

        text = ""
        method = "none"

        if not force_ocr:
            text = processor.extract_pdf_text(pdf_path)
            if text and len(text.strip()) > 100:
                method = "pypdf2"

        if not text or force_ocr:
            text = processor.extract_text_with_ocr(pdf_path, log_fn=lambda m: logs.append(m))
            method = "nvidia_nim_ocr" if text else "failed"

        if not text:
            raise HTTPException(status_code=422, detail="Could not extract text from PDF.")

        return JSONResponse(content={
            "filename":    pdf_file.filename,
            "method_used": method,
            "char_count":  len(text),
            "text":        text,
            "logs":        logs[-20:],
        })

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post(
    "/extract-text-batch",
    summary="Extract text from multiple PDFs",
)
async def extract_text_batch(
    pdf_files:  list[UploadFile] = File(...),
    force_ocr:  bool             = Form(False),
    current_user: User           = Depends(get_current_user),
):
    """Batch OCR — returns a list of extraction results, one per PDF."""
    tmp_dir = tempfile.mkdtemp(prefix="ocr_batch_")
    processor = PDFProcessor(nvidia_api_key=settings.NVIDIA_API_KEY)
    results = []

    try:
        for upload in pdf_files:
            pdf_path = os.path.join(tmp_dir, upload.filename)
            with open(pdf_path, "wb") as f:
                shutil.copyfileobj(upload.file, f)

            logs: list[str] = []
            text, method = "", "none"

            if not force_ocr:
                text = processor.extract_pdf_text(pdf_path)
                if text and len(text.strip()) > 100:
                    method = "pypdf2"

            if not text or force_ocr:
                text = processor.extract_text_with_ocr(pdf_path, log_fn=lambda m: logs.append(m))
                method = "nvidia_nim_ocr" if text else "failed"

            results.append({
                "filename":    upload.filename,
                "method_used": method,
                "char_count":  len(text) if text else 0,
                "text":        text or "",
                "success":     bool(text),
            })

        return JSONResponse(content={"results": results, "total": len(results)})

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
