"""
evaluation_saver.py
───────────────────
Drop this next to s10.py.
After the AI grader scores a student, call save_evaluation_to_api()
to persist the result in MongoDB via the FastAPI backend.

Usage in s10.py:
    from evaluation_saver import save_evaluation_to_api
    save_evaluation_to_api(token, subject_name, student_result, master_answers)
"""

import requests
from typing import Optional

API_BASE = "http://localhost:8000/api"


def login(email: str, password: str) -> Optional[str]:
    """
    Log in as a teacher and return the JWT access token.
    Call this once at app startup and store the token.
    """
    resp = requests.post(
        f"{API_BASE}/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json()["access_token"]
    print(f"⚠️  API login failed: {resp.json().get('detail')}")
    return None


def save_evaluation_to_api(
    token: str,
    subject_name: str,
    student_result: dict,
    question_results: list,
) -> Optional[dict]:
    """
    Save a completed evaluation to MongoDB via FastAPI.

    Parameters
    ----------
    token           : JWT from login()
    subject_name    : e.g. "Software Engineering"
    student_result  : dict with keys: name, roll_no, email,
                      total_marks, max_marks, percentage, grade
    question_results: list of dicts, each with keys:
                      question_key, student_answer, master_answer,
                      marks_awarded, max_marks, percentage,
                      semantic_score, keyword_score, feedback (optional)
    """
    payload = {
        "subject_name": subject_name,
        "student_name": student_result.get("name", "Unknown"),
        "student_roll_no": str(student_result.get("roll_no", "")),
        "student_email": student_result.get("email", ""),
        "total_marks": float(student_result.get("total_marks", 0)),
        "max_marks": float(student_result.get("max_marks", 0)),
        "percentage": float(student_result.get("percentage", 0)),
        "grade": student_result.get("grade", "F"),
        "question_results": question_results,
        "metadata": {},
    }

    resp = requests.post(
        f"{API_BASE}/evaluations/",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )

    if resp.status_code == 201:
        print(f"✅ Saved evaluation for {payload['student_name']} to database")
        return resp.json()
    else:
        print(f"⚠️  Failed to save evaluation: {resp.json().get('detail')}")
        return None
