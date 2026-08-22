from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

# ── Helpers ──────────────────────────────────────────────────────────────────
class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)


# ── User Models ───────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserInDB(BaseModel):
    id: Optional[str] = None
    name: str
    email: str
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Token Models ──────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None


# ── Evaluation Models ─────────────────────────────────────────────────────────
class QuestionResult(BaseModel):
    question_key: str           # e.g. "1a", "2", "3b"
    student_answer: str
    master_answer: str
    marks_awarded: float
    max_marks: float
    percentage: float
    semantic_score: float
    keyword_score: float
    feedback: Optional[str] = None

class EvaluationCreate(BaseModel):
    subject_name: str
    student_name: str
    student_roll_no: str
    student_email: Optional[str] = None
    total_marks: float
    max_marks: float
    percentage: float
    grade: str
    question_results: List[QuestionResult] = []
    metadata: Optional[Dict[str, Any]] = {}

class EvaluationResponse(EvaluationCreate):
    id: str
    teacher_id: str
    evaluated_at: datetime

    class Config:
        from_attributes = True

class EvaluationSummary(BaseModel):
    id: str
    subject_name: str
    student_name: str
    student_roll_no: str
    total_marks: float
    max_marks: float
    percentage: float
    grade: str
    evaluated_at: datetime
