# Task 3: AI-Powered Price Comparison Scraper

An intelligent price comparison scraper built with **Playwright** + **Groq AI (Llama 3.3 70B)**. Instead of brittle CSS selectors, this scraper uses an LLM to intelligently extract product data from raw HTML.

## Architecture

```
scraper.py          →  Browser automation, anti-detection, navigation
ai_scraper.py       →  AI-powered data extraction (separate module)
models.py / database.py  →  SQLAlchemy ORM + DB connection
```

### How the AI Scraper Works

1. **Playwright** navigates to Amazon/eBay with full anti-detection (proxies, stealth, UA rotation)
2. **scraper.py** grabs the complete page HTML via `page.content()`
3. **ai_scraper.py** receives the HTML and:
   - **Cleans it** — strips `<script>`, `<style>`, `<nav>`, `<footer>`, comments
   - **Keyword-filters** — scans for search term matches, extracts only ±2000 chars around each match (saves ~95% tokens)
   - **Sends to Groq LLM** — with a structured extraction prompt
   - **Parses JSON response** — validates and returns clean product data
4. Results are saved to the database with **price-change detection**

### Why AI Instead of CSS Selectors?

| CSS Selectors | AI Extraction |
|---|---|
| Break on every layout change | Self-adapting — LLM understands HTML |
| 40+ selectors to maintain | Zero selector maintenance |
| Site-specific, not portable | Works across ANY e-commerce site |
| Misses dynamically loaded content | Reads complete page source |

## Anti-Blocking Measures

1. **Rotating Residential Proxies** — 3-proxy pool, different proxy per site
2. **User-Agent Rotation** — Chrome, Firefox, Safari pools
3. **playwright_stealth** — masks headless browser fingerprints
4. **Rate Limiting** — 4-8 second random delays between page loads
5. **Exponential Backoff** — automatic retry on 429/403/503
6. **Cookie Persistence** — saves/loads session cookies to disk
7. **Viewport Randomization** — different screen sizes per session
8. **Timezone + Locale Rotation** — varies identity per context
9. **Human-like Scrolling** — smooth scroll to trigger lazy-loaded content
10. **Randomized Headers** — Accept-Language, Referer, Cache-Control

## How to Run

```bash
# Install dependencies + browser
uv sync
uv run playwright install chromium

# Single run
uv run "Task 3/scraper.py"

# Custom terms
uv run "Task 3/scraper.py" --terms "glass dropper bottle 30ml" --max-items 3

# Daily schedule (runs immediately + 08:00 UTC daily)
uv run "Task 3/scraper.py" --schedule
```

## Token Efficiency

The keyword-filtering step is critical for cost control:
- Raw HTML page: **~200,000+ characters**
- After cleaning: **~80,000 characters**
- After keyword filter: **~5,000-15,000 characters** (95%+ reduction)
- This means each extraction costs fractions of a cent on Groq
