from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app.models import EvaluationCreate, EvaluationResponse, EvaluationSummary
from app.auth import get_current_user
from app.database import get_db

router = APIRouter()


def serialize_evaluation(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    doc["teacher_id"] = str(doc["teacher_id"])
    return doc


@router.post("/", response_model=EvaluationResponse, status_code=status.HTTP_201_CREATED)
async def save_evaluation(
    evaluation: EvaluationCreate,
    current_user: dict = Depends(get_current_user),
):
    """Save an evaluation result to MongoDB after running the AI grader."""
    db = get_db()

    doc = evaluation.dict()
    doc["teacher_id"] = current_user["_id"]
    doc["evaluated_at"] = datetime.utcnow()

    result = await db.evaluations.insert_one(doc)
    doc["_id"] = result.inserted_id

    return serialize_evaluation(doc)


@router.get("/", response_model=List[EvaluationSummary])
async def list_evaluations(
    subject: Optional[str] = Query(None, description="Filter by subject name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    """List all evaluations for the logged-in teacher."""
    db = get_db()

    query = {"teacher_id": current_user["_id"]}
    if subject:
        query["subject_name"] = {"$regex": subject, "$options": "i"}

    cursor = db.evaluations.find(
        query,
        {
            "subject_name": 1, "student_name": 1, "student_roll_no": 1,
            "total_marks": 1, "max_marks": 1, "percentage": 1,
            "grade": 1, "evaluated_at": 1,
        }
    ).sort("evaluated_at", -1).skip(skip).limit(limit)

    results = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        results.append(doc)

    return results


@router.get("/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    """Get summary statistics for the dashboard."""
    db = get_db()
    teacher_id = current_user["_id"]

    total = await db.evaluations.count_documents({"teacher_id": teacher_id})

    pipeline = [
        {"$match": {"teacher_id": teacher_id}},
        {"$group": {
            "_id": None,
            "avg_percentage": {"$avg": "$percentage"},
            "highest": {"$max": "$percentage"},
            "lowest": {"$min": "$percentage"},
        }}
    ]
    agg = await db.evaluations.aggregate(pipeline).to_list(1)
    stats = agg[0] if agg else {"avg_percentage": 0, "highest": 0, "lowest": 0}
    stats.pop("_id", None)

    # Grade distribution
    grade_pipeline = [
        {"$match": {"teacher_id": teacher_id}},
        {"$group": {"_id": "$grade", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    grades = await db.evaluations.aggregate(grade_pipeline).to_list(20)
    grade_dist = {g["_id"]: g["count"] for g in grades}

    # Subject breakdown
    subject_pipeline = [
        {"$match": {"teacher_id": teacher_id}},
        {"$group": {
            "_id": "$subject_name",
            "count": {"$sum": 1},
            "avg_pct": {"$avg": "$percentage"},
        }},
        {"$sort": {"count": -1}},
    ]
    subjects = await db.evaluations.aggregate(subject_pipeline).to_list(20)

    return {
        "total_evaluations": total,
        **stats,
        "grade_distribution": grade_dist,
        "subjects": subjects,
    }


@router.get("/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(
    evaluation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get full details of a single evaluation."""
    db = get_db()

    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID")

    doc = await db.evaluations.find_one({
        "_id": ObjectId(evaluation_id),
        "teacher_id": current_user["_id"],
    })

    if not doc:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    return serialize_evaluation(doc)


@router.delete("/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evaluation(
    evaluation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete an evaluation (only by the teacher who created it)."""
    db = get_db()

    if not ObjectId.is_valid(evaluation_id):
        raise HTTPException(status_code=400, detail="Invalid evaluation ID")

    result = await db.evaluations.delete_one({
        "_id": ObjectId(evaluation_id),
        "teacher_id": current_user["_id"],
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Evaluation not found")
