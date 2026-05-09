# Color Studio Test

## How to Run the Project

### 1. Install Dependencies

First, install `uv` if you don't already have it:

```bash
pip install uv
```

Then install all project dependencies:

```bash
uv sync
```

All libraries will install automatically.

---

## Task 1A — Database Schema Design

Check the `Task 1/task_1a_schema_design/` folder.
The schema is in `schema.sql`.

---

## Task 1B — Vector Knowledge Base

Check the `Task 1/task_1b_vector_knowledge_base/` folder.

**To run:**
```bash
uv run "Task 1/task_1b_vector_knowledge_base/knowledge_base.py"
```

### Example Questions

#### 🔹 Packaging Queries
- What packaging options are available for skincare products?
- Which packaging is used for lipsticks?
- Do you offer airless pump packaging?
- What packaging do you recommend for serums?

#### 🔹 MOQ (Minimum Order Quantity) Queries
- What is the minimum order quantity for makeup products?
- How many units are required for lip gloss production?
- MOQ for skincare glass jars?

#### 🔹 Lead Time Queries
- How long does production take for fragrance bottles?

#### 🔹 Formulation Capability Queries
- Do you support vegan skincare formulations?

#### 🔹 Mixed / Complex Queries
- What packaging and MOQ do you offer for skincare serums?
- What is the MOQ for fragrance lipsticks?

---

## Task 2 — AI Customer Intake Agent (Bilingual)

The solution for Task 2 is located in the `Task 2/` folder.
This is a FastAPI application that simulates an AI customer intake agent capable of automatically qualifying leads through a simulated WhatsApp/Instagram channel in English and Urdu.

**To run the server:**
```bash
uv run uvicorn "Task 2.main:app" --reload
```

Then go to: http://127.0.0.1:8000/docs

*(Make sure to run this from the root directory so it can access the `.env` and `Task 1` vector database!)*

Please see the internal `Task 2/README.md` for a full explanation of the design choices (SQLite state management, Prompts, Vector DB integration) and `curl` examples to test the English and Urdu flows.

---

## Task 3 — AI-Powered Price Comparison Scraper

The solution for Task 3 is located in the `Task 3/` folder.
This is an **AI-powered** price comparison scraper built with **Playwright** + **Groq AI (Llama 3.3 70B)**. It scrapes **Amazon** and **eBay** for cosmetic raw materials/packaging. Instead of brittle CSS selectors, it uses an LLM to intelligently extract product data from raw HTML — with keyword-based filtering to save 95%+ tokens.

**Key features:**
- Separate AI scraper module (`ai_scraper.py`) for intelligent data extraction
- Rotating residential proxies, UA rotation, rate limiting, and 10+ anti-blocking measures
- Price-change detection with historical tracking

**To run the scraper:**
```bash
uv run playwright install chromium

# Run once:
uv run "Task 3/scraper.py"

# Custom search terms:
uv run "Task 3/scraper.py" --terms "glass dropper bottle 30ml" --max-items 3

# Run on daily schedule (APScheduler, fires immediately + 08:00 UTC daily):
uv run "Task 3/scraper.py" --schedule
```

Please see the internal `Task 3/README.md` for the full architecture explanation, anti-blocking measures, and token efficiency strategy.

---

## Task 4 — Shopify Product Review App

The solution for Task 4 is located in the `Task 4/` folder.
This is a FastAPI application that provides a Shopify embedded app for collecting and displaying product reviews, with AI-generated summaries powered by the Groq API. It includes a merchant admin dashboard, a storefront widget (Theme App Extension / App Block), and a REST API.

**To run the server:**
```bash
uv run uvicorn "Task 4.app.main:app" --reload --port 8000
```

Then go to: http://localhost:8000/

Interactive API docs available at: http://localhost:8000/docs

Please see the internal `Task 4/README.md` for full installation instructions (including Shopify Partner setup, ngrok tunneling, and App Block configuration).
