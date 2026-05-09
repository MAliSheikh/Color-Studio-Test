"""
main.py — FastAPI application for the Shopify Product Review App.

Routes
------
GET  /                          Landing / install page
GET  /admin                     Merchant review dashboard (Shopify embedded)
GET  /widget                    Standalone storefront widget (loaded by App Block)
GET  /api/reviews               JSON: list reviews for a SKU + AI summary
POST /api/reviews               JSON: submit a new review
GET  /api/skus                  JSON: all SKUs that have reviews

Interactive API docs: http://localhost:8000/docs

Run locally
-----------
    uv run uvicorn "Task 4.app.main:app" --reload --port 8000
or from inside Task 4/app/:
    uvicorn main:app --reload --port 8000
"""

import logging
import os
import sys

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# ── Path bootstrap ────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from database import Base, engine, SessionLocal
from models import Review
from ai_summary import generate_review_summary

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

# ── Create tables ─────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)
logger.info("Database tables ensured ✓")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Shopify Product Reviews",
    description="Collect customer reviews, display them on the storefront, and generate AI summaries.",
    version="1.0.0",
)

# Allow all origins so the Liquid App Block (on a Shopify storefront domain)
# can call the API without CORS errors.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ReviewIn(BaseModel):
    product_sku: str = Field(..., min_length=1, description="Product SKU")
    customer_name: str = Field(..., min_length=1, description="Reviewer's name")
    rating: int = Field(..., ge=1, le=5, description="Star rating 1–5")
    review_text: str = Field(..., min_length=1, description="Review body")

    @field_validator("product_sku", "customer_name", "review_text", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class ReviewOut(BaseModel):
    id: str
    product_sku: str
    customer_name: str
    rating: int
    review_text: str
    created_at: str | None

    model_config = {"from_attributes": True}


class ReviewsResponse(BaseModel):
    sku: str
    total: int
    average_rating: float
    ai_summary: str | None
    reviews: list[ReviewOut]


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    """Landing page / Shopify OAuth install entry point."""
    return templates.TemplateResponse(request, "install.html")


@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin(request: Request, sku: str = ""):
    """Merchant review dashboard — embedded in Shopify Admin via App Page."""
    db = SessionLocal()
    try:
        skus = [
            row[0]
            for row in db.query(Review.product_sku)
            .distinct()
            .order_by(Review.product_sku)
            .all()
        ]
        selected_sku = sku or (skus[0] if skus else "")
        reviews: list[Review] = []
        summary: str | None = None

        if selected_sku:
            reviews = (
                db.query(Review)
                .filter(Review.product_sku == selected_sku)
                .order_by(Review.created_at.desc())
                .all()
            )
            summary = generate_review_summary([r.to_dict() for r in reviews])

        avg = (
            round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0.0
        )
        return templates.TemplateResponse(
            request,
            "admin.html",
            {
                "skus": skus,
                "selected_sku": selected_sku,
                "reviews": reviews,
                "ai_summary": summary,
                "total_reviews": len(reviews),
                "avg_rating": avg,
            },
        )
    finally:
        db.close()


@app.get("/widget", response_class=HTMLResponse, include_in_schema=False)
async def widget(request: Request, sku: str = ""):
    """Standalone widget page embedded by the Liquid App Block via iframe."""
    return templates.TemplateResponse(request, "widget.html", {"sku": sku})


# ── JSON API ──────────────────────────────────────────────────────────────────

@app.get(
    "/api/reviews",
    response_model=ReviewsResponse,
    summary="Get reviews for a product SKU",
    tags=["Reviews"],
)
async def get_reviews(
    sku: str = Query(..., description="Product SKU to retrieve reviews for"),
):
    """Return all reviews and an AI summary for the given product SKU."""
    db = SessionLocal()
    try:
        rows = (
            db.query(Review)
            .filter(Review.product_sku == sku.strip())
            .order_by(Review.created_at.desc())
            .all()
        )
        review_dicts = [r.to_dict() for r in rows]
        summary = generate_review_summary(review_dicts)
        avg = (
            round(sum(r["rating"] for r in review_dicts) / len(review_dicts), 1)
            if review_dicts
            else 0.0
        )
        return ReviewsResponse(
            sku=sku,
            total=len(review_dicts),
            average_rating=avg,
            ai_summary=summary,
            reviews=[ReviewOut(**d) for d in review_dicts],
        )
    finally:
        db.close()


@app.post(
    "/api/reviews",
    response_model=dict,
    status_code=201,
    summary="Submit a new review",
    tags=["Reviews"],
)
async def post_review(body: ReviewIn):
    """Submit a customer review. Returns the created review object."""
    db = SessionLocal()
    try:
        review = Review(
            product_sku=body.product_sku,
            customer_name=body.customer_name,
            rating=body.rating,
            review_text=body.review_text,
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        logger.info("New review saved: %s → %s ★%d", body.customer_name, body.product_sku, body.rating)
        return {"success": True, "review": review.to_dict()}
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error: %s", exc)
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        db.close()


@app.get(
    "/api/skus",
    response_model=dict,
    summary="List all SKUs with reviews",
    tags=["Reviews"],
)
async def get_skus():
    """Return all product SKUs that have at least one review."""
    db = SessionLocal()
    try:
        skus = [
            row[0]
            for row in db.query(Review.product_sku)
            .distinct()
            .order_by(Review.product_sku)
            .all()
        ]
        return {"skus": skus}
    finally:
        db.close()


# ── Dev entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
