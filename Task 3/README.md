# Task 3: AI-Powered Price Comparison Scraper

This project implements an AI‑enhanced price‑comparison scraper that uses Playwright for browser automation and Groq LLM (Llama 3.3 70B) for intelligent data extraction. It scrapes e‑commerce sites (e.g., Amazon, eBay) and extracts product information without relying on brittle CSS selectors.

## Architecture Overview

- **Browser Automation** – Playwright with anti‑detection measures (rotating residential proxies, UA rotation, stealth, random scrolling, viewport/randomization, etc.).
- **Persistence** – Extracted data is stored in a SQLite database with price‑change detection.
- **Scheduling** – Supports one‑off runs and a daily schedule via APScheduler.

The original README contained detailed Bash command blocks for installing Playwright and running the scraper. Those commands have been removed to keep this file concise.

For full installation steps, dependency setup, and exact run commands (including `uv run playwright install chromium` and the various `uv run "Task 3/scraper.py"` invocations), refer to the root `Readme.md`.
