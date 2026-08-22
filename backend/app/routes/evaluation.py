"""
routes/evaluation.py
FastAPI routes for answer-sheet evaluation (PDF upload, OCR, grading, email).
"""

import os
import json
import shutil
import tempfile
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.models import UserInDB as User
from app.auth import get_current_user
from app.config import settings
from app.evaluation_engine import MultiSubjectEvaluator

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_evaluator() -> MultiSubjectEvaluator:
    return MultiSubjectEvaluator(
        nvidia_api_key=settings.NVIDIA_API_KEY,
        sender_email=settings.SENDER_EMAIL,
        app_password=settings.APP_PASSWORD,
        output_dir=settings.OUTPUT_DIR,
        use_ocr=True,
    )


def _save_upload(upload: UploadFile, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, upload.filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    return path


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SubjectIn(BaseModel):
    name: str


class EvaluationResponse(BaseModel):
    subject: str
    results: list
    results_file: Optional[str] = None


class EmailRequest(BaseModel):
    results: list
    detailed_feedback: dict
    consolidated_file: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/evaluate-subject",
    summary="Evaluate one subject: upload master PDF + student PDFs",
)
async def evaluate_subject(
    background_tasks: BackgroundTasks,
    subject_name: str = Form(..., description="Subject name, e.g. 'Software Engineering'"),
    master_pdf:   UploadFile = File(..., description="Master answer-key PDF"),
    student_pdfs: List[UploadFile] = File(..., description="One or more student answer PDFs"),
    send_email:   bool = Form(False, description="Send result emails after evaluation"),
    current_user: User = Depends(get_current_user),
):
    """
    1. Saves uploaded PDFs temporarily.
    2. Extracts text (PyPDF2 → NVIDIA NIM OCR fallback).
    3. Parses Q&A with regex.
    4. Runs FAIR scoring (semantic 60 % + keyword 25 % + structure 10 % + length 5 %).
    5. Returns per-student results JSON and saves an Excel file.
    6. Optionally sends result emails in the background.
    """
    tmp_dir = tempfile.mkdtemp(prefix="eval_")
    try:
        master_path = _save_upload(master_pdf, tmp_dir)
        student_paths = [_save_upload(f, tmp_dir) for f in student_pdfs]

        evaluator = _get_evaluator()
        logs: list[str] = []
        results = evaluator.evaluate_subject(
            subject_name=subject_name,
            master_pdf_path=master_path,
            student_pdf_paths=student_paths,
            log_fn=lambda msg: logs.append(msg),
        )

        results_file = evaluator.save_subject_results(subject_name, results)

        # Strip internal keys before returning
        clean_results = [{k: v for k, v in r.items() if not k.startswith("_")} for r in results]

        response = {
            "subject": subject_name,
            "students_evaluated": len(results),
            "results_file": results_file,
            "results": clean_results,
            "logs": logs[-30:],  # Last 30 log lines
        }

        if send_email and results:
            feedback = {f"{r['Roll No']}_{r['Name']}": r.get("_feedback", {}) for r in results}
            background_tasks.add_task(
                evaluator.send_emails, results, feedback, results_file
            )
            response["email_status"] = "queued"

        return JSONResponse(content=response)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp uploads (keep output Excel)
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass


@router.post(
    "/evaluate-multi-subject",
    summary="Evaluate multiple subjects in one request",
)
async def evaluate_multi_subject(
    background_tasks: BackgroundTasks,
    subject_names:  List[str]          = Form(...),
    master_pdfs:    List[UploadFile]   = File(...),
    student_pdfs:   List[List[UploadFile]] = File(...),   # nested list not natively supported; see note
    send_email:     bool               = Form(False),
    current_user:   User               = Depends(get_current_user),
):
    """
    Evaluate multiple subjects at once.

    **Note:** Because HTML multipart cannot represent nested file lists,
    call `/evaluate-subject` once per subject OR use the JSON batch
    helper `/evaluate-batch` below.
    """
    raise HTTPException(
        status_code=501,
        detail="Use /evaluate-subject once per subject, or see /evaluate-batch.",
    )


@router.post(
    "/evaluate-batch",
    summary="Submit multiple subjects as separate form parts (recommended)",
)
async def evaluate_batch(
    background_tasks: BackgroundTasks,
    # Each subject is prefixed: subject_name_0, master_0, students_0
    # We receive raw form and parse manually
    subject_name_0: Optional[str]          = Form(None),
    master_0:       Optional[UploadFile]   = File(None),
    students_0:     Optional[List[UploadFile]] = File(None),
    subject_name_1: Optional[str]          = Form(None),
    master_1:       Optional[UploadFile]   = File(None),
    students_1:     Optional[List[UploadFile]] = File(None),
    subject_name_2: Optional[str]          = Form(None),
    master_2:       Optional[UploadFile]   = File(None),
    students_2:     Optional[List[UploadFile]] = File(None),
    send_email:     bool = Form(False),
    current_user:   User = Depends(get_current_user),
):
    """
    Evaluate up to 3 subjects in one batch request.

    Returns consolidated results with per-subject Excel sheets.
    Supports up to 3 subject slots (0, 1, 2).  Call /evaluate-subject
    for more subjects.
    """
    subjects_raw = [
        (subject_name_0, master_0, students_0),
        (subject_name_1, master_1, students_1),
        (subject_name_2, master_2, students_2),
    ]
    active = [(sn, m, st) for sn, m, st in subjects_raw
              if sn and m and st]

    if not active:
        raise HTTPException(status_code=422, detail="At least one subject with master and student PDFs is required.")

    tmp_dir = tempfile.mkdtemp(prefix="batch_eval_")
    try:
        evaluator = _get_evaluator()
        all_results: list = []
        subject_names: list[str] = []
        all_feedback: dict = {}
        logs: list[str] = []
        consolidated_file = None

        for sn, master_file, student_files in active:
            master_path = _save_upload(master_file, tmp_dir)
            student_paths = [_save_upload(f, tmp_dir) for f in student_files]

            results = evaluator.evaluate_subject(
                subject_name=sn,
                master_pdf_path=master_path,
                student_pdf_paths=student_paths,
                log_fn=lambda msg: logs.append(msg),
            )

            evaluator.save_subject_results(sn, results)
            all_results.extend(results)
            subject_names.append(sn)

            for r in results:
                key = f"{r['Roll No']}_{r['Name']}"
                if key not in all_feedback:
                    all_feedback[key] = {}
                all_feedback[key][sn] = r.get("_feedback", {})

        if all_results:
            consolidated_file = evaluator.save_consolidated_results(all_results, subject_names)
            evaluator.save_detailed_feedback(all_feedback)

        clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in all_results]

        response = {
            "subjects_evaluated": subject_names,
            "total_students": len({r["Roll No"] for r in all_results}),
            "consolidated_file": consolidated_file,
            "results": clean,
            "logs": logs[-50:],
        }

        if send_email and all_results:
            background_tasks.add_task(
                evaluator.send_emails, all_results, all_feedback, consolidated_file
            )
            response["email_status"] = "queued"

        return JSONResponse(content=response)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass


@router.post("/send-emails", summary="Send result emails to students")
async def send_result_emails(
    payload: EmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """
    Send result emails to students using pre-computed results JSON.
    Use this if you already have evaluation results and want to (re-)send emails.
    """
    background_tasks.add_task(
        _get_evaluator().send_emails,
        payload.results,
        payload.detailed_feedback,
        payload.consolidated_file,
    )
    return {"status": "Email dispatch queued", "recipients": len({r["Roll No"] for r in payload.results})}


@router.post("/test-email", summary="Test SMTP connection")
async def test_email(current_user: User = Depends(get_current_user)):
    evaluator = _get_evaluator()
    ok, msg = evaluator.email_sender.test_connection()
    if not ok:
        raise HTTPException(status_code=503, detail=msg)
    return {"status": "ok", "message": msg}


@router.get("/download/{filename}", summary="Download a result file")
async def download_file(
    filename: str,
    current_user: User = Depends(get_current_user),
):
    path = os.path.join(settings.OUTPUT_DIR, filename)
    if not os.path.exists(path) or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename)


@router.get("/list-results", summary="List all result files in output directory")
async def list_results(current_user: User = Depends(get_current_user)):
    out = settings.OUTPUT_DIR
    if not os.path.isdir(out):
        return {"files": []}
    files = sorted(os.listdir(out), reverse=True)
    return {
        "output_dir": out,
        "files": [
            {"name": f, "size_kb": round(os.path.getsize(os.path.join(out, f)) / 1024, 1)}
            for f in files if os.path.isfile(os.path.join(out, f))
        ],
    }
