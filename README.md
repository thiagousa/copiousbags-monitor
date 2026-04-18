# Website Monitor

Automated website monitor using Python + Selenium. Monitors multiple sites on a configurable interval, checks critical user flows, sends email alerts on failure, and delivers a daily HTML summary report.

---

## Monitored Sites

| Site | Directory | Selenium Port |
|---|---|---|
| [copiousbags.com](https://www.copiousbags.com) | `copious/` | `4444` |
| [bloombirthstudio.com](https://bloombirthstudio.com) | `bloom/` | `4445` |

Both monitors run independently and can run simultaneously.

---

## What it checks

### copiousbags.com (`copious/`)
| Check | Description |
|---|---|
| **Site load** | Homepage loads with a valid title |
| **Add to cart** | Opens the 3x5 LuxeFrost product and clicks Add to Cart |
| **Checkout** | Navigates to `/shop/checkout/` and verifies all form elements and order review |

### bloombirthstudio.com (`bloom/`)
| Check | Description |
|---|---|
| **Site load** | Homepage loads with a valid title |
| **Add to cart** | Opens the Nora June template product and clicks Add to Cart |
| **Checkout** | Navigates to `/checkout` and verifies all form elements and order review |

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
git clone https://github.com/thiagousa/copiousbags-monitor.git
cd copiousbags-monitor
```

**2. Create `.env` files for each site**
```bash
cp copious/.env-example copious/.env
cp bloom/.env-example bloom/.env
```
Edit each `.env` with your SMTP credentials and preferred schedule.

**3. Start both monitors**
```bash
make up
```

---

## Configuration

Each site has its own `.env` file inside its directory:

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

Run all commands from the project root.

### copiousbags.com
```bash
make copious-build    # Build the image
make copious-up       # Start in the background
make copious-down     # Stop
make copious-logs     # Stream logs live
make copious-check    # Build + start + tail logs
make copious-clean    # Stop containers and delete screenshots
make copious-image    # Build and tag for the registry
make copious-push     # Build, tag and push to registry
make copious-release  # Alias for push
```

### bloombirthstudio.com
```bash
make bloom-build      # Build the image
make bloom-up         # Start in the background
make bloom-down       # Stop
make bloom-logs       # Stream logs live
make bloom-check      # Build + start + tail logs
make bloom-clean      # Stop containers and delete screenshots
make bloom-image      # Build and tag for the registry
make bloom-push       # Build, tag and push to registry
make bloom-release    # Alias for push
```

### Both sites
```bash
make up               # Start both monitors
make down             # Stop both monitors
make clean            # Stop both and delete all screenshots
```

---

## Email notifications

| Event | Email sent |
|---|---|
| Any check fails | Immediately — subject: `[Monitor] FAILED: <checks>` with screenshots attached |
| Daily report (at `DAILY_REPORT_TIME` EST) | HTML summary of last 24h: runs/passed/failed + 3 screenshots |

Daily report screenshots:
- Fresh full-page homepage
- `04_after_add_to_cart.png`
- `06_checkout_elements.png`

Set `EMAIL_ENABLED=false` in `.env` to disable all emails.

---

## Screenshots

Screenshots are saved to `<site>/screenshots/` on the host machine:

| File | Description |
|---|---|
| `01_homepage.png` | Full-page homepage |
| `02_product_page.png` | Full-page product page |
| `03_before_add_to_cart.png` | Product page before clicking Add to Cart |
| `04_after_add_to_cart.png` | After clicking Add to Cart |
| `05_checkout_page.png` | Checkout page |
| `06_checkout_elements.png` | Checkout with element verification |
| `report_homepage.png` | Fresh homepage snapshot taken at daily report time |
| `error_state.png` | Captured when an unexpected error occurs |

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
  --env-file copious/.env \
  -v $(pwd)/copious/screenshots:/screenshots \
  docker.io/thiagousa/copiousbags-monitor:latest

docker run -d --name bloombirthstudio-monitor \
  --network monitor-net \
  --env-file bloom/.env \
  -v $(pwd)/bloom/screenshots:/screenshots \
  docker.io/thiagousa/bloombirthstudio-monitor:latest
```

---

## Project structure

```
.
├── Makefile                  # Root commands for both sites
├── README.md
├── copious/                  # copiousbags.com monitor
│   ├── monitor.py
│   ├── Dockerfile
│   ├── docker-compose.yml    # Selenium on port 4444
│   ├── requirements.txt
│   ├── Makefile
│   ├── .env                  # Local config (never commit)
│   ├── .env-example
│   ├── .gitignore
│   └── screenshots/
└── bloom/                    # bloombirthstudio.com monitor
    ├── monitor.py
    ├── Dockerfile
    ├── docker-compose.yml    # Selenium on port 4445
    ├── requirements.txt
    ├── Makefile
    ├── .env                  # Local config (never commit)
    ├── .env-example
    ├── .gitignore
    └── screenshots/
```
