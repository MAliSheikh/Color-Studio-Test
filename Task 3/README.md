# Task 3: Price Comparison Scraper

This is a Python scraper built using **Playwright** and **SQLAlchemy** to collect pricing data for cosmetic raw materials and packaging.

## Design Choices & Target Website
- **Target:** The scraper targets **Alibaba Showroom** results (`www.alibaba.com/showroom/`).
- **Why Alibaba?** Alibaba is the primary global marketplace for cosmetic "suppliers" and "raw materials", making it the most relevant candidate for this business use case.
- **Robots.txt Compliance:** While many marketplaces disallow general search queries, Alibaba's `robots.txt` explicitly has `Allow: /showroom/`. By targeting the showroom directory, the scraper remains fully compliant with the site's scraping policy.
- **Stealth Mode:** Uses `playwright-stealth` and a custom user-agent to ensure natural browsing behavior.
- **Database:** Uses **SQLAlchemy**. It relies on your environment variables (`DATABASE_URL`) to connect. It handles both SQLite and PostgreSQL automatically.
- **Idempotency & Change Detection:** The scraper searches for products. Before saving, it checks the database for the exact URL. If the price has changed since the last scrape, it logs a `🚨 PRICE CHANGE DETECTED` alert.

## How to Run

1. **Install Dependencies and Browsers**
   Ensure you install the Python requirements and the Playwright Chromium binaries:
   ```bash
   uv sync
   uv run playwright install chromium
   ```

2. **Execute the Scraper**
   Run the scraper directly:
   ```bash
   uv run python "Task 3/scraper.py"
   ```

## How to Schedule (Cron / APScheduler)

To run this scraper daily to monitor price fluctuations automatically:

### Option A: Using `cron` (Linux/Mac)
Open your crontab using `crontab -e` and add the following line to run the scraper every day at 2:00 AM:
```bash
0 2 * * * cd /path/to/project/Task\ 3 && uv run python scraper.py >> scraper.log 2>&1
```

### Option B: Using Python `APScheduler`
You can create a standalone scheduling script if you prefer an all-Python approach. `APScheduler` is included in the requirements.
```python
from apscheduler.schedulers.blocking import BlockingScheduler
from scraper import scrape_ebay

def job():
    print("Running scheduled scrape...")
    scrape_ebay(["glass dropper bottle 30ml", "aluminium cosmetic jar"])

scheduler = BlockingScheduler()
# Run job every day at 8:00 AM
scheduler.add_job(job, 'cron', hour=8)
scheduler.start()
```
