# copiousbags.com Monitor

Automated website monitor using Python + Selenium. Runs on a configurable interval, checks the homepage, add-to-cart flow, and checkout page, then sends email alerts on failure and a daily summary report.

---

## What it checks

| Check | Description |
|---|---|
| **Site load** | Homepage loads with a valid title |
| **Add to cart** | Opens a product page and clicks Add to Cart |
| **Checkout** | Navigates to checkout and verifies all form elements are present |

Screenshots are saved for every step and attached to failure emails.

---

## Requirements

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- A Mailgun (or any SMTP) account for email notifications

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/youruser/copiousbags-monitor.git
cd copiousbags-monitor
```

**2. Create your `.env` file**
```bash
cp .env-example .env
```
Edit `.env` with your SMTP credentials and preferred schedule.

**3. Build and start**
```bash
make build
make up
```

---

## Configuration

All configuration is done via the `.env` file:

| Variable | Description | Default |
|---|---|---|
| `CHECK_INTERVAL_MINUTES` | How often to run checks | `5` |
| `DAILY_REPORT_TIME` | Time to send daily report (EST, HH:MM) | `09:15` |
| `EMAIL_ENABLED` | Enable/disable email notifications | `true` |
| `SMTP_HOST` | SMTP server hostname | — |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USER` | SMTP username | — |
| `SMTP_PASS` | SMTP password | — |
| `SMTP_FROM` | Sender email address | — |
| `SMTP_TO` | Recipient email address | — |

---

## Makefile commands

```bash
make build      # Build the Docker image
make up         # Start all services in the background
make down       # Stop all services
make logs       # Stream monitor logs live
make check      # Build + start + tail logs
make clean      # Stop containers and delete screenshots
make image      # Build and tag for the registry
make push       # Build, tag and push to registry
make release    # Alias for push
make run        # Pull and run from the registry
```

---

## Running from Docker Hub (no local build)

**1. Create a shared network**
```bash
docker network create monitor-net
```

**2. Start Selenium**
```bash
# Apple Silicon (M1/M2)
docker run -d --name selenium \
  --network monitor-net \
  --shm-size=2g \
  seleniarm/standalone-chromium:latest

# Intel / Linux
docker run -d --name selenium \
  --network monitor-net \
  --shm-size=2g \
  selenium/standalone-chrome:latest
```

**3. Start the monitor**
```bash
docker run -d --name copiousbags-monitor \
  --network monitor-net \
  --env-file .env \
  -v $(pwd)/screenshots:/screenshots \
  docker.io/youruser/copiousbags-monitor:latest
```

---

## Email notifications

| Event | Email sent |
|---|---|
| Any check fails | Immediately — subject: `[Monitor] FAILED: <checks>` with screenshots attached |
| Daily report (at `DAILY_REPORT_TIME`) | Summary of last 24h runs with homepage + checkout screenshots |

Set `EMAIL_ENABLED=false` in `.env` to disable all emails.

---

## Screenshots

Screenshots are saved to `./screenshots/` on the host machine:

| File | Description |
|---|---|
| `01_homepage.png` | Full-page homepage |
| `02_shop.png` | Full-page product page |
| `03_before_add_to_cart.png` | Product page before clicking Add to Cart |
| `04_after_add_to_cart.png` | After clicking Add to Cart |
| `05_checkout_page.png` | Checkout page |
| `06_checkout_elements.png` | Checkout with element verification |
| `report_homepage.png` | Fresh homepage snapshot taken at daily report time |
| `error_state.png` | Captured when an unexpected error occurs |

---

## Project structure

```
.
├── monitor.py          # Main monitoring script
├── Dockerfile          # Monitor container image
├── docker-compose.yml  # Compose config (monitor + Selenium)
├── requirements.txt    # Python dependencies
├── Makefile            # Convenience commands
├── .env                # Your local config (never commit this)
└── .env-example        # Config template
```
