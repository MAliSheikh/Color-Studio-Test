How to Run the Project
1. Install Dependencies
First Run: 
```bash
pip install uv
```
Before running the project, you need to install the required Python 
libraries. Run the following command in your terminal:

uv sync

All libraries will install automatically 

For Task 1 a

check task 1 folder which has sub filder task_1a_schema_design 
schema.sql file for task 1

for task 2 check task 1 folder which has sub filder 
task_1b_vector_knowledge_base

run this command on terminal
uv run "Task 1/task_1b_vector_knowledge_base/knowledge_base.py"

Example Questions
# 📌 Task 1B – Vector Knowledge Base Questions Log

## 🔹 Packaging Queries
- What packaging options are available for skincare products?
- Which packaging is used for lipsticks?
- Do you offer airless pump packaging?
- What packaging do you recommend for serums?

---

## 🔹 MOQ (Minimum Order Quantity) Queries
- What is the minimum order quantity for makeup products?
- How many units are required for lip gloss production?
- MOQ for skincare glass jars?

---

## 🔹 Lead Time Queries
- How long does production take for fragrance bottles?

---

## 🔹 Formulation Capability Queries
- Do you support vegan skincare formulations?

---

## 🔹 Mixed / Complex Queries
- What packaging and MOQ do you offer for skincare serums?
- What is the MOQ for fragrance lipsticks?

---

## 🔹 Task 2: AI Customer Intake Agent (Bilingual)
The solution for Task 2 (AI Intake Agent) is located in the `Task 2/` folder.
This is a FastAPI application that simulates an AI customer intake agent capable of automatically qualifying leads through a simulated WhatsApp/Instagram channel in English and Urdu.

**To run the server:**
```bash
uv run uvicorn "Task 2.main:app" --reload

and go to
http://127.0.0.1:8000/docs 


```
*(Make sure to run this from the root directory so it can access the `.env` and `Task 1` vector database!)*

Please see the internal `Task 2/README.md` for a full explanation of the design choices (SQLite state management, Prompts, Vector DB integration) and `curl` examples to test the English and Urdu flows.

---

## 🔹 Task 3: Price Comparison Scraper
The solution for Task 3 is located in the `Task 3/` folder.
This is a Python scraper built with Playwright and SQLAlchemy. It scrapes eBay search results for cosmetic raw materials and dynamically creates a PostgreSQL-ready database (defaults to SQLite locally for immediate testing).

**To run the scraper:**
```bash
uv run playwright install chromium
# Run once:
uv run "Task 3/scraper.py"

# Run on daily schedule (APScheduler, fires immediately + 08:00 UTC daily):
uv run "Task 3/scraper.py" --schedule
```

Please see the internal `Task 3/README.md` for a full explanation of the design choices, how the scraper bypasses basic bot protections, and how to schedule it using `cron` or `APScheduler`.