# Website Monitor — Project Context

## Overview
Multi-site website monitor using Python + Selenium in Docker. Checks critical user flows on a configurable interval, sends immediate failure emails with screenshots, and delivers a daily HTML summary report.

## Repository
https://github.com/thiagousa/copiousbags-monitor

## Project Structure
```
monitor/
├── Makefile                  # Root commands for both sites
├── README.md
├── CLAUDE.md
├── copious/                  # copiousbags.com monitor
│   ├── monitor.py
│   ├── Dockerfile
│   ├── docker-compose.yml    # Selenium on port 4444
│   ├── requirements.txt
│   ├── Makefile
│   ├── .env                  # Never commit
│   ├── .env-example
│   └── .gitignore
└── bloom/                    # bloombirthstudio.com monitor
    ├── monitor.py
    ├── Dockerfile
    ├── docker-compose.yml    # Selenium on port 4445
    ├── requirements.txt
    ├── Makefile
    ├── .env                  # Never commit
    ├── .env-example
    └── .gitignore
```

## Monitored Sites

### copiousbags.com
- **URL:** https://www.copiousbags.com
- **Product under test:** https://www.copiousbags.com/product/3x5-luxefrost-stand-up-bag-matte-frosted/
- **Checkout URL:** https://www.copiousbags.com/shop/checkout/
- **Platform:** WooCommerce
- **Selenium port:** 4444

### bloombirthstudio.com
- **URL:** https://bloombirthstudio.com
- **Product under test:** https://bloombirthstudio.com/product/doula-website-template-nora-june
- **Checkout URL:** https://bloombirthstudio.com/checkout
- **Platform:** WooCommerce
- **Selenium port:** 4445

## Checks Per Site
1. **site_load** — Homepage loads with a valid title; full-page screenshot taken
2. **add_to_cart** — Opens the specific product URL, clicks Add to Cart, confirms WooCommerce response
3. **checkout** — Navigates to checkout, verifies all billing fields + order review + Place Order button

## Email Notifications
- **On failure:** Sent immediately with all screenshots attached
- **Daily report:** HTML email at `DAILY_REPORT_TIME` (EST) with run stats and 3 screenshots:
  - Fresh full-page homepage (taken at report time)
  - `04_after_add_to_cart.png`
  - `06_checkout_elements.png`
- Configured via `.env` in each site directory

## Environment Variables (per site `.env`)
| Variable | Description |
|---|---|
| `CHECK_INTERVAL_MINUTES` | How often to run checks |
| `DAILY_REPORT_TIME` | Daily report time in EST (HH:MM) |
| `EMAIL_ENABLED` | true/false |
| `SMTP_HOST` | SMTP server (Mailgun: smtp.mailgun.org) |
| `SMTP_PORT` | 587 |
| `SMTP_USER` | Mailgun postmaster address |
| `SMTP_PASS` | Mailgun SMTP password |
| `SMTP_FROM` | Sender address |
| `SMTP_TO` | thiago@thiagodsantos.com |

## Docker
- **ARM64 (Apple Silicon):** `seleniarm/standalone-chromium:latest`
- **Intel/Linux:** `selenium/standalone-chrome:latest`
- Both sites run simultaneously — different Selenium ports prevent conflicts
- Screenshots mounted to host via `./screenshots:/screenshots`

## Makefile Commands (from project root)
```bash
make copious-up / make bloom-up     # Start individual monitor
make copious-logs / make bloom-logs # Stream logs
make copious-check / make bloom-check # Build + start + tail
make copious-push / make bloom-push # Push image to Docker Hub
make up                             # Start both
make down                           # Stop both
make clean                          # Stop both + delete screenshots
```

## Docker Hub Images
- `docker.io/thiagousa/copiousbags-monitor`
- `docker.io/thiagousa/bloombirthstudio-monitor`

## Screenshots Reference
| File | Description |
|---|---|
| `01_homepage.png` | Full-page homepage |
| `02_product_page.png` / `02_shop.png` | Full-page product |
| `03_before_add_to_cart.png` | Before clicking Add to Cart |
| `04_after_add_to_cart.png` | After clicking Add to Cart |
| `05_checkout_page.png` | Checkout page |
| `06_checkout_elements.png` | Checkout with field verification |
| `report_homepage.png` | Fresh homepage at daily report time |
| `error_state.png` | Captured on unexpected errors |

## Key Implementation Notes
- `full_page_screenshot()` scrolls to bottom then top before capturing to trigger lazy-loaded images, resizes window to full page height, then restores to 1920x1080
- Daily report time comparison uses `America/New_York` timezone via `zoneinfo` — handles DST automatically
- 24-hour history stored in a `deque`, pruned on each run; resets if container restarts
- `.env` is never baked into the Docker image — injected at runtime via `--env-file`
