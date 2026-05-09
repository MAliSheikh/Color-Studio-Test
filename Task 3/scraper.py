import re
import time
import json
import argparse
import random
from pathlib import Path
from datetime import datetime, timezone
from urllib.robotparser import RobotFileParser

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

try:
    from playwright_stealth import stealth_sync
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    print("[warn] playwright_stealth not installed — running without stealth mode.")

from database import init_db, SessionLocal
from models import PriceComparison

# ─────────────────────────────────────────────────────────────────────────────
# Configuration (eBay Scraper)
# ─────────────────────────────────────────────────────────────────────────────
BASE_URL    = "https://www.ebay.com"
SEARCH_URL  = BASE_URL + "/sch/i.html?_nkw={term}"
ROBOTS_URL  = BASE_URL + "/robots.txt"

COOKIE_FILE = Path("cookies.json")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
]

# We are using direct connections instead of failing proxies, 
# but stealth mode + user-agent rotation helps bypass blocks.
MAX_RETRIES    = 3
BACKOFF_BASE   = 2.0
BACKOFF_JITTER = 1.0

SEARCH_TERMS = [
    "glass dropper bottle 30ml",
    "aluminium cosmetic jar",
    "cosmetic pump bottle 100ml",
    "lip balm tube packaging",
]

def check_robots_allowed(url: str) -> bool:
    rp = RobotFileParser()
    rp.set_url(ROBOTS_URL)
    try:
        rp.read()
        return rp.can_fetch("*", url)
    except Exception:
        return True

def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def safe_text(locator, timeout: int = 2000) -> str:
    try: return locator.first.inner_text(timeout=timeout).strip()
    except Exception: return ""

def safe_attr(locator, attr: str, timeout: int = 2000) -> str:
    try: return (locator.first.get_attribute(attr, timeout=timeout) or "").strip()
    except Exception: return ""

def extract_price(text: str) -> float:
    if not text: return 0.0
    matches = re.findall(r"\d+\.?\d*", text.replace(",", ""))
    return float(matches[0]) if matches else 0.0

def goto_with_backoff(page, url: str, max_retries: int = MAX_RETRIES) -> bool:
    for attempt in range(1, max_retries + 1):
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            status = response.status if response else 200
            if status in (429, 403, 503):
                time.sleep(BACKOFF_BASE ** attempt + random.uniform(0, BACKOFF_JITTER))
                continue
            return True
        except Exception:
            time.sleep(BACKOFF_BASE ** attempt + random.uniform(0, BACKOFF_JITTER))
    return False

def scrape_ebay(page, db, term: str, max_items: int = 5) -> int:
    formatted_term = term.strip().replace(" ", "+")
    url = SEARCH_URL.format(term=formatted_term)

    print(f"\n  [eBay] {url}")
    if not goto_with_backoff(page, url): return 0

    try:
        # eBay results are usually in .s-item or .s-card
        page.wait_for_selector(".s-card, .s-item", timeout=10_000)
    except Exception:
        print("    No product cards found. We might be blocked or CAPTCHA'd.")
        return 0

    time.sleep(random.uniform(1, 3))
    cards = page.locator(".s-card, .s-item").all()
    print(f"    Found {len(cards)} items, processing top {max_items}...")

    count = 0
    # eBay's first item is often a hidden banner or placeholder, start from 1
    for card in cards[1:max_items + 1]:
        try:
            name = safe_text(card.locator(".s-card__title, .s-item__title"))
            href = safe_attr(card.locator(".s-card__link, .s-item__link"), "href")
            
            if not name or not href or "Shop on eBay" in name: 
                continue
                
            href = href.split("?")[0]

            price_text = safe_text(card.locator(".s-card__price, .s-item__price"))
            price_val = extract_price(price_text)
            
            seller = safe_text(card.locator(".su-card-container__attributes__secondary, .s-item__seller-info-text"))

            print(f"    -> {name[:40]:<40} | ${price_val:>8.2f} | {seller[:20]}")
            
            # Check for price changes
            previous = db.query(PriceComparison).filter(PriceComparison.url == href).order_by(PriceComparison.date_scraped.desc()).first()
            if previous:
                if price_val > 0 and round(previous.price, 2) != round(price_val, 2):
                    diff = price_val - previous.price
                    print(f"      PRICE CHANGE: ${previous.price:.2f} -> ${price_val:.2f} ({diff:+.2f})")
                else: print(f"      Price stable @ ${price_val:.2f}")
            else: print("      New item tracked.")

            db.add(PriceComparison(
                search_term=term, 
                product_name=name, 
                seller=seller or "eBay Seller",
                price=price_val, 
                url=href, 
                date_scraped=now_utc()
            ))
            count += 1
        except Exception: continue
    return count

def run_scrape(search_terms: list) -> None:
    print(f"\n{'='*70}\n  Normal Scrape Started: {now_utc().strftime('%Y-%m-%d %H:%M:%S')} UTC\n{'='*70}")
    init_db()
    db = SessionLocal()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
            extra_http_headers={
                "Accept-Language": random.choice(ACCEPT_LANGUAGES),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        page = context.new_page()
        if STEALTH_AVAILABLE: stealth_sync(page)
        
        total = 0
        for term in search_terms:
            total += scrape_ebay(page, db, term)
            db.commit()
            time.sleep(random.uniform(2, 4))
            
        browser.close()
    db.close()
    print(f"\n{'='*70}\n  Total records saved : {total}\n  Finished            : {now_utc().strftime('%Y-%m-%d %H:%M:%S')} UTC\n{'='*70}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Normal Web Scraper (eBay)")
    parser.add_argument("--schedule", action="store_true")
    args = parser.parse_args()
    if args.schedule:
        from apscheduler.schedulers.blocking import BlockingScheduler
        scheduler = BlockingScheduler(timezone="UTC")
        scheduler.add_job(func=run_scrape, trigger="cron", hour=8, minute=0, args=[SEARCH_TERMS], id="daily")
        run_scrape(SEARCH_TERMS)
        scheduler.start()
    else:
        run_scrape(SEARCH_TERMS)