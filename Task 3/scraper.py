"""
Cosmetic Packaging Price Scraper
=================================

Target: Alibaba Showroom (https://www.alibaba.com/showroom/<term>.html)

Why Alibaba?
  - Primary global marketplace for cosmetic suppliers and packaging.
  - robots.txt explicitly allows /showroom/ paths.
  - Consistent layout and high-quality data.

Anti-block measures implemented:
  1. Random User-Agent rotation
  2. Random delays between requests
  3. playwright_stealth — masks headless fingerprints
  4. Proxy rotation — cycles through a pool on each context
  5. Rate-limit / 429 backoff — exponential retry with jitter
  6. Request header randomization — Accept-Language, Referer, Accept, etc.
  7. Cookie persistence — saves/loads cookies per session to disk

Run modes:
  uv run "Task 3/scraper.py"             -> single scrape run, then exit
  uv run "Task 3/scraper.py" --schedule  -> run now + repeat daily at 08:00 UTC
"""

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
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL    = "https://www.alibaba.com"
SEARCH_URL  = BASE_URL + "/showroom/{term}.html"
ROBOTS_URL  = BASE_URL + "/robots.txt"

COOKIE_FILE = Path("cookies.json")   # persisted cookie store

# ── User-Agents ──────────────────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

# ── Accept-Language pool (randomized per request) ────────────────────────────
ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.8,zh-CN;q=0.5",
    "en-CA,en;q=0.9,fr-CA;q=0.8",
    "en-AU,en;q=0.9",
]

# Free public proxies are unreliable — for production use a paid provider:
#   Bright Data:   http://zproxy.lum-superproxy.io:22225
#   Oxylabs:       http://pr.oxylabs.io:7777
#   Smartproxy:    http://gate.smartproxy.com:7000
#
PROXIES: list = [
    "http://mzupfxqu:1t8zi1rs2cij@31.59.20.176:6754",
    "http://mzupfxqu:1t8zi1rs2cij@198.23.239.134:6540",
    "http://mzupfxqu:1t8zi1rs2cij@31.56.127.193:7684"
    # "http://user:pass@proxy2.example.com:8080",
]

# ── Rate-limit / backoff settings ────────────────────────────────────────────
MAX_RETRIES    = 4      # max attempts per URL before giving up
BACKOFF_BASE   = 2.0    # seconds — doubles each retry (exponential)
BACKOFF_JITTER = 1.5    # random extra seconds added to each wait

# ── Search terms ─────────────────────────────────────────────────────────────
SEARCH_TERMS = [
    "glass dropper bottle 30ml",
    "aluminium cosmetic jar",
    "cosmetic pump bottle 100ml",
    "lip balm tube packaging",
]

# ─────────────────────────────────────────────────────────────────────────────
# Robots.txt compliance
# ─────────────────────────────────────────────────────────────────────────────

def check_robots_allowed(url: str) -> bool:
    rp = RobotFileParser()
    rp.set_url(ROBOTS_URL)
    try:
        rp.read()
        return rp.can_fetch("*", url)
    except Exception:
        return True  # default to allowed if robots.txt unreachable

# ─────────────────────────────────────────────────────────────────────────────
# Cookie persistence
# ─────────────────────────────────────────────────────────────────────────────

def save_cookies(context) -> None:
    """Persist browser cookies to disk for reuse across sessions."""
    try:
        cookies = context.cookies()
        COOKIE_FILE.write_text(json.dumps(cookies, indent=2))
        print(f"  [cookies] Saved {len(cookies)} cookies -> {COOKIE_FILE}")
    except Exception as e:
        print(f"  [cookies] Save failed: {e}")


def load_cookies(context) -> None:
    """Restore previously saved cookies into the current browser context."""
    if not COOKIE_FILE.exists():
        return
    try:
        cookies = json.loads(COOKIE_FILE.read_text())
        if cookies:
            context.add_cookies(cookies)
            print(f"  [cookies] Loaded {len(cookies)} cookies from {COOKIE_FILE}")
    except Exception as e:
        print(f"  [cookies] Load failed: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Randomized extra headers
# ─────────────────────────────────────────────────────────────────────────────

def random_headers(referrer: str = BASE_URL) -> dict:
    """
    Build a realistic HTTP header set.
    Accept-Language and Referer are randomized so every session looks
    like a slightly different real browser.
    """
    return {
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": referrer,
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

# ─────────────────────────────────────────────────────────────────────────────
# Proxy helpers
# ─────────────────────────────────────────────────────────────────────────────

def pick_proxy():
    """Return a random proxy dict for Playwright, or None if pool is empty."""
    if not PROXIES:
        return None
    proxy_url = random.choice(PROXIES)
    # Parse  http://user:pass@host:port  into Playwright proxy dict
    proxy = {"server": proxy_url}
    if "@" in proxy_url:
        creds, server = proxy_url.rsplit("@", 1)
        scheme    = creds.split("://")[0]
        user_pass = creds.split("://")[1]
        user, password = user_pass.split(":", 1)
        proxy = {
            "server":   f"{scheme}://{server}",
            "username": user,
            "password": password,
        }
    return proxy

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def extract_price(text: str) -> float:
    if not text:
        return 0.0
    matches = re.findall(r"\d+\.?\d*", text.replace(",", ""))
    if matches:
        try:
            return float(matches[0])
        except Exception:
            return 0.0
    return 0.0

def safe_text(locator, timeout: int = 2000) -> str:
    try:
        return locator.first.inner_text(timeout=timeout).strip()
    except Exception:
        return ""

def safe_attr(locator, attr: str, timeout: int = 2000) -> str:
    try:
        return (locator.first.get_attribute(attr, timeout=timeout) or "").strip()
    except Exception:
        return ""

# ─────────────────────────────────────────────────────────────────────────────
# Rate-limit aware page.goto with exponential backoff
# ─────────────────────────────────────────────────────────────────────────────

def goto_with_backoff(page, url: str, max_retries: int = MAX_RETRIES) -> bool:
    """
    Navigate to `url` with automatic retry + exponential backoff.
    Handles HTTP 429 (Too Many Requests) and transient network errors.
    Returns True on success, False if all retries exhausted.
    """
    for attempt in range(1, max_retries + 1):
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=60_000)

            # Playwright returns None for same-page navigations; treat as OK
            status = response.status if response else 200

            if status == 429:
                wait = BACKOFF_BASE ** attempt + random.uniform(0, BACKOFF_JITTER)
                print(f"  [429] Rate-limited. Retry {attempt}/{max_retries} in {wait:.1f}s ...")
                time.sleep(wait)
                continue

            if status in (403, 503):
                wait = BACKOFF_BASE ** attempt + random.uniform(0, BACKOFF_JITTER)
                print(f"  [{status}] Blocked/unavailable. Retry {attempt}/{max_retries} in {wait:.1f}s ...")
                time.sleep(wait)
                continue

            return True  # success

        except PWTimeout:
            wait = BACKOFF_BASE ** attempt + random.uniform(0, BACKOFF_JITTER)
            print(f"  [timeout] Attempt {attempt}/{max_retries}. Retrying in {wait:.1f}s ...")
            time.sleep(wait)

        except Exception as e:
            print(f"  [error] {e}. Attempt {attempt}/{max_retries}.")
            time.sleep(BACKOFF_BASE ** attempt)

    print(f"  [fail] All {max_retries} retries exhausted for {url}")
    return False

# ─────────────────────────────────────────────────────────────────────────────
# Scraper logic
# ─────────────────────────────────────────────────────────────────────────────

def scrape_alibaba_showroom(page, db, term: str, max_items: int = 5) -> int:
    formatted_term = term.strip().replace(" ", "-").lower()
    url = SEARCH_URL.format(term=formatted_term)

    if not check_robots_allowed(url):
        print(f"  [robots.txt] BLOCKED: {url}")
        return 0

    print(f"\n  [Alibaba Showroom] {url}")

    # Navigate with backoff; bail out if all retries fail
    if not goto_with_backoff(page, url):
        return 0

    # Try common Alibaba showroom card selectors
    card_selector = None
    for sel in [
        ".search-card-e",
        "div[data-content='productItem']",
        ".gallery-card-item",
        ".J-offer-wrapper",
    ]:
        try:
            page.wait_for_selector(sel, timeout=10_000)
            card_selector = sel
            break
        except Exception:
            continue

    if not card_selector:
        print("    No product cards found.")
        return 0

    time.sleep(random.uniform(1, 3))
    cards = page.locator(card_selector).all()
    print(f"    Found {len(cards)} items, processing top {max_items}...")

    count = 0
    for card in cards[:max_items]:
        try:
            title_sel = card.locator(
                ".search-card-e-title, .title-link, a[href*='/product-detail/']"
            ).first
            name = safe_text(title_sel)
            href = safe_attr(title_sel, "href")

            if not name or not href:
                continue
            if href.startswith("//"):
                href = "https:" + href
            href = href.split("?")[0]

            price_text = safe_text(
                card.locator(
                    ".search-card-e-price-main, .price, .search-card-e-price-single"
                )
            )
            price_val = extract_price(price_text)

            supplier = safe_text(
                card.locator(
                    ".search-card-e-company, .company-name, .supplier-name"
                )
            )

            print(f"    -> {name[:40]:<40} | ${price_val:>8.2f} | {supplier[:25]}")

            previous = (
                db.query(PriceComparison)
                .filter(PriceComparison.url == href)
                .order_by(PriceComparison.date_scraped.desc())
                .first()
            )
            if previous:
                if price_val > 0 and round(previous.price, 2) != round(price_val, 2):
                    diff = price_val - previous.price
                    print(
                        f"      PRICE CHANGE: ${previous.price:.2f} -> "
                        f"${price_val:.2f} ({diff:+.2f})"
                    )
                else:
                    print(f"      Price stable @ ${price_val:.2f}")
            else:
                print("      New item tracked.")

            db.add(
                PriceComparison(
                    search_term=term,
                    product_name=name,
                    seller=supplier,
                    price=price_val,
                    url=href,
                    date_scraped=now_utc(),
                )
            )
            count += 1
        except Exception:
            continue

    return count

# ─────────────────────────────────────────────────────────────────────────────
# Main run
# ─────────────────────────────────────────────────────────────────────────────

def run_scrape(search_terms: list) -> None:
    print(f"\n{'='*70}")
    print(f"  Scrape Started: {now_utc().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'='*70}")

    init_db()
    db = SessionLocal()

    ua      = random.choice(USER_AGENTS)
    proxy   = pick_proxy()
    headers = random_headers()

    with sync_playwright() as p:
        launch_kwargs = {"headless": True}

        # ── Proxy rotation ────────────────────────────────────────────────
        if proxy:
            launch_kwargs["proxy"] = proxy
            print(f"  [proxy] Using -> {proxy['server']}")
        else:
            print("  [proxy] No proxy configured — direct connection.")

        browser = p.chromium.launch(**launch_kwargs)

        context = browser.new_context(
            user_agent=ua,
            viewport={"width": 1920, "height": 1080},
            # ── Randomized headers injected at context level ──────────────
            extra_http_headers=headers,
            # Realistic locale/timezone to match Accept-Language header
            locale="en-US",
            timezone_id="America/New_York",
            permissions=[],
        )

        # ── Cookie persistence — load saved cookies ───────────────────────
        load_cookies(context)

        page = context.new_page()

        # ── Stealth fingerprint masking ───────────────────────────────────
        if STEALTH_AVAILABLE:
            stealth_sync(page)

        total = 0
        for term in search_terms:
            saved = scrape_alibaba_showroom(page, db, term)
            total += saved
            db.commit()
            time.sleep(random.uniform(2, 5))

        # ── Cookie persistence — save cookies for next session ────────────
        save_cookies(context)

        db.close()
        browser.close()

    print(f"\n{'='*70}")
    print(f"  Total records saved : {total}")
    print(f"  Finished            : {now_utc().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'='*70}\n")

# ─────────────────────────────────────────────────────────────────────────────
# Scheduler
# ─────────────────────────────────────────────────────────────────────────────

def start_scheduler(search_terms: list) -> None:
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
    except ImportError:
        print("APScheduler missing. Run: uv add apscheduler")
        return

    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        func=run_scrape,
        trigger="cron",
        hour=8, minute=0,
        args=[search_terms],
        id="daily_scrape",
        replace_existing=True,
    )
    print("Scheduler active. Running first scrape now...")
    run_scrape(search_terms)
    print("Next run at 08:00 UTC. Ctrl+C to stop.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass

# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", action="store_true",
                        help="Run now then repeat daily at 08:00 UTC")
    args = parser.parse_args()

    if args.schedule:
        start_scheduler(SEARCH_TERMS)
    else:
        run_scrape(SEARCH_TERMS)