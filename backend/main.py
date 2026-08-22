from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Routers ────────────────────────────────────────────────────────────────
from app.routes import auth, evaluations, payments
from app.routes.evaluation import router as evaluation_router
from app.routes.ocr import router as ocr_router

# ── DB ─────────────────────────────────────────────────────────────────────
from app.database import connect_db, disconnect_db

app = FastAPI(
    title="AI Answer Sheet Evaluation API",
    description=(
        "Evaluation system with FAIR scoring + OCR + Payments integration"
    ),
    version="2.0.0",
)

# ── CORS ───────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "*"  # optional (remove in production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

# Old + New evaluation support
app.include_router(evaluations.router, prefix="/api/evaluations", tags=["Evaluations"])
app.include_router(evaluation_router)

# OCR (new)
app.include_router(ocr_router)

# Payments (old)
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])


# ── Lifecycle ──────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await connect_db()


@app.on_event("shutdown")
async def shutdown():
    await disconnect_db()


# ── Routes ─────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "message": "AI Answer Sheet Evaluation API (Merged V1 + V2)",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}