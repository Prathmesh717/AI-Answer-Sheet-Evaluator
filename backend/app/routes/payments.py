import hmac
import hashlib
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional
import razorpay

from app.auth import get_current_user
from app.database import get_db
from app.config import settings

router = APIRouter()

# ── Razorpay client ───────────────────────────────────────────────────────────
rz_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

# Plan config (must match frontend plans.js)
PLAN_CONFIG = {
    "silver": {"name": "Silver", "amount": 29900,  "display": "₹299"},   # in paise
    "gold":   {"name": "Gold",   "amount": 69900,  "display": "₹699"},
}


# ── Request / Response schemas ────────────────────────────────────────────────
class CreateOrderRequest(BaseModel):
    plan_id: str   # "silver" or "gold"

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan_id: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/create-order")
async def create_order(
    body: CreateOrderRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Step 1: Create a Razorpay order.
    Frontend receives the order_id and opens the Razorpay checkout modal.
    """
    plan = PLAN_CONFIG.get(body.plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {body.plan_id}")

    try:
        order = rz_client.order.create({
            "amount":   plan["amount"],
            "currency": "INR",
            "receipt":  f"rcpt_{body.plan_id}_{int(datetime.utcnow().timestamp())}",
            "notes": {
                "plan_id":    body.plan_id,
                "teacher_id": str(current_user["_id"]),
                "email":      current_user["email"],
            },
        })
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Razorpay order creation failed: {str(e)}")

    return {
        "order_id":   order["id"],
        "amount":     plan["amount"],
        "currency":   "INR",
        "plan_id":    body.plan_id,
        "plan_name":  plan["name"],
        "key_id":     settings.RAZORPAY_KEY_ID,  # sent to frontend for checkout
    }


@router.post("/verify")
async def verify_payment(
    body: VerifyPaymentRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Step 2: Verify Razorpay signature (HMAC-SHA256).
    If valid → save payment record in MongoDB → return success + plan info.
    """
    # ── Signature verification ────────────────────────────────────────────────
    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        f"{body.razorpay_order_id}|{body.razorpay_payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, body.razorpay_signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment verification failed — invalid signature",
        )

    plan = PLAN_CONFIG.get(body.plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan")

    # ── Save payment to MongoDB ───────────────────────────────────────────────
    db = get_db()

    payment_doc = {
        "teacher_id":            current_user["_id"],
        "teacher_email":         current_user["email"],
        "teacher_name":          current_user["name"],
        "razorpay_order_id":     body.razorpay_order_id,
        "razorpay_payment_id":   body.razorpay_payment_id,
        "razorpay_signature":    body.razorpay_signature,
        "plan_id":               body.plan_id,
        "plan_name":             plan["name"],
        "amount":                plan["amount"],       # paise
        "amount_display":        plan["display"],      # "₹299"
        "currency":              "INR",
        "status":                "success",
        "paid_at":               datetime.utcnow(),
    }

    result = await db.payments.insert_one(payment_doc)

    return {
        "success":     True,
        "payment_id":  body.razorpay_payment_id,
        "order_id":    body.razorpay_order_id,
        "plan_id":     body.plan_id,
        "plan_name":   plan["name"],
        "amount":      plan["amount"],
        "amount_display": plan["display"],
        "db_id":       str(result.inserted_id),
        "message":     f"{plan['name']} plan activated successfully!",
    }

@router.get("/status")
async def subscription_status(current_user: dict = Depends(get_current_user)):
    """
    Return the logged-in user's current active plan, based on their most
    recent successful payment in MongoDB. This is the source of truth —
    the frontend should not decide subscription status from localStorage alone.
    """
    db = get_db()
    doc = await db.payments.find_one(
        {"teacher_id": current_user["_id"], "status": "success"},
        sort=[("paid_at", -1)],
    )

    if not doc:
        return {"planId": None, "planName": None, "activatedAt": None}

    return {
        "planId":      doc["plan_id"],
        "planName":    doc["plan_name"],
        # ms epoch, to match Date.now() used on the frontend
        "activatedAt": int(doc["paid_at"].timestamp() * 1000),
    }


@router.get("/history")
async def payment_history(current_user: dict = Depends(get_current_user)):
    """Get all payments made by the logged-in teacher."""
    db = get_db()
    cursor = db.payments.find(
        {"teacher_id": current_user["_id"]},
        {"razorpay_signature": 0}   # don't expose signature
    ).sort("paid_at", -1)

    records = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        doc["teacher_id"] = str(doc["teacher_id"])
        records.append(doc)

    return records
