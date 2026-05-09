"""
ai_summary.py — Generate a one-sentence AI summary of all reviews for a product.

Uses the Groq API (llama-3.3-70b-versatile) with the existing GROQ_API_KEY.
Falls back gracefully if the API is unavailable.
"""

import os
import logging
from groq import Groq
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

logger = logging.getLogger(__name__)

_client: Groq | None = None


def _get_client() -> Groq | None:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY not set — AI summaries disabled.")
            return None
        _client = Groq(api_key=api_key)
    return _client


def generate_review_summary(reviews: list[dict]) -> str | None:
    """
    Given a list of review dicts (each with 'rating', 'review_text', 'customer_name'),
    return a one-sentence AI summary suitable for display on a product page.

    Returns None if the API is unavailable or no reviews exist.
    """
    if not reviews:
        return None

    client = _get_client()
    if client is None:
        return None

    # Build a compact review digest for the prompt
    digest_lines = []
    for r in reviews:
        stars = "★" * r["rating"] + "☆" * (5 - r["rating"])
        digest_lines.append(f'- {stars} "{r["review_text"]}" — {r["customer_name"]}')

    digest = "\n".join(digest_lines)
    avg_rating = sum(r["rating"] for r in reviews) / len(reviews)

    prompt = (
        f"You are a helpful assistant summarising customer product reviews for an e-commerce store.\n\n"
        f"Product reviews ({len(reviews)} total, average rating {avg_rating:.1f}/5):\n"
        f"{digest}\n\n"
        f"Write EXACTLY one concise sentence (max 25 words) summarising the overall customer sentiment. "
        f"Be specific about what customers praise or criticise. Do not start with 'Customers' every time."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.4,
        )
        summary = response.choices[0].message.content.strip()
        # Strip surrounding quotes if the model added them
        summary = summary.strip('"').strip("'")
        return summary
    except Exception as exc:
        logger.error("Groq API error: %s", exc)
        return None
