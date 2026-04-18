import os
import time
import sys
import logging
import glob
import smtplib
from collections import deque
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ_EST = ZoneInfo("America/New_York")
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

TARGET_URL   = "https://www.copiousbags.com"
PRODUCT_URL  = "https://www.copiousbags.com/product/3x5-luxefrost-stand-up-bag-matte-frosted/"
CHECKOUT_URL = "https://www.copiousbags.com/shop/checkout/"
SELENIUM_URL = "http://selenium:4444/wd/hub"
WAIT_TIMEOUT = 20
SCREENSHOTS_DIR = "/screenshots"

INTERVAL_SECONDS     = int(os.getenv("CHECK_INTERVAL_MINUTES", "5")) * 60
DAILY_REPORT_TIME    = os.getenv("DAILY_REPORT_TIME", "09:15")  # HH:MM

CHECKOUT_ELEMENTS = [
    ("Billing first name", By.ID, "billing_first_name"),
    ("Billing last name",  By.ID, "billing_last_name"),
    ("Billing address",    By.ID, "billing_address_1"),
    ("Billing city",       By.ID, "billing_city"),
    ("Billing postcode",   By.ID, "billing_postcode"),
    ("Billing phone",      By.ID, "billing_phone"),
    ("Billing email",      By.ID, "billing_email"),
    ("Order review",       By.ID, "order_review"),
    ("Place order button", By.ID, "place_order"),
]

# Rolling 24-hour history: each entry is {"time": datetime, "results": dict, "passed": bool}
history: deque = deque()


def _prune_history():
    cutoff = datetime.now() - timedelta(hours=24)
    while history and history[0]["time"] < cutoff:
        history.popleft()


def _smtp_connection():
    return {
        "host":      os.environ["SMTP_HOST"],
        "port":      int(os.environ["SMTP_PORT"]),
        "user":      os.environ["SMTP_USER"],
        "password":  os.environ["SMTP_PASS"],
        "from_addr": os.environ["SMTP_FROM"],
        "to_addr":   os.environ["SMTP_TO"],
    }


def _send(subject, body, html=None, attach_screenshots=False, extra_images=None):
    if os.getenv("EMAIL_ENABLED", "false").lower() != "true":
        return
    cfg = _smtp_connection()
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = cfg["from_addr"]
    msg["To"]      = cfg["to_addr"]
    if html:
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(body, "plain"))
        alt.attach(MIMEText(html, "html"))
        msg.attach(alt)
    else:
        msg.attach(MIMEText(body, "plain"))

    paths = []
    if attach_screenshots:
        paths += sorted(glob.glob(os.path.join(SCREENSHOTS_DIR, "*.png")))
    if extra_images:
        paths += extra_images

    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            img = MIMEImage(f.read(), _subtype="png")
            img.add_header("Content-Disposition", "attachment", filename=os.path.basename(path))
            msg.attach(img)
    if paths:
        log.info("Attaching %d screenshot(s)", len(paths))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["from_addr"], cfg["to_addr"], msg.as_string())
        log.info("Email sent — subject: %s", subject)
    except Exception as exc:
        log.error("Failed to send email: %s", exc)


def send_failure_email(results):
    failed  = [c for c, p in results.items() if not p]
    lines   = [f"  {c:<15} {'PASS' if p else 'FAIL'}" for c, p in results.items()]
    summary = "\n".join(lines)
    _send(
        subject=f"[Monitor] copiousbags.com — FAILED: {', '.join(failed)}",
        body=f"One or more checks failed for {TARGET_URL}\n\n{summary}\n\nSee attached screenshots.\n",
        attach_screenshots=True,
    )


def take_homepage_screenshot():
    driver = None
    try:
        driver = make_driver()
        wait = WebDriverWait(driver, WAIT_TIMEOUT)
        driver.get(TARGET_URL)
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        path = full_page_screenshot(driver, "report_homepage")
        return path
    except Exception as exc:
        log.error("Failed to take homepage screenshot: %s", exc)
        return None
    finally:
        if driver:
            driver.quit()


def send_daily_report():
    _prune_history()
    total  = len(history)
    passed = sum(1 for e in history if e["passed"])
    failed = total - passed
    now_str = datetime.now(TZ_EST).strftime("%Y-%m-%d %H:%M EST")
    status_color = "#2e7d32" if failed == 0 else "#c62828"
    status_label = "All checks passed" if failed == 0 else f"{failed} run(s) failed"

    # Plain text fallback
    plain_lines = [
        f"Daily Report — {TARGET_URL}",
        f"Period : last 24 hours (up to {now_str})",
        f"Runs   : {total}",
        f"Passed : {passed}",
        f"Failed : {failed}",
        "",
    ]
    if failed:
        plain_lines.append("Failed runs:")
        for entry in history:
            if not entry["passed"]:
                checks = ", ".join(c for c, p in entry["results"].items() if not p)
                plain_lines.append(f"  {entry['time'].strftime('%Y-%m-%d %H:%M')}  —  {checks}")
    else:
        plain_lines.append("All runs passed — site is healthy.")

    # Failed runs rows for HTML
    failed_rows = ""
    if failed:
        for entry in history:
            if not entry["passed"]:
                checks = ", ".join(c for c, p in entry["results"].items() if not p)
                ts = entry["time"].strftime("%Y-%m-%d %H:%M")
                failed_rows += f"<tr><td style='padding:4px 8px;color:#555'>{ts}</td><td style='padding:4px 8px;color:#c62828'>{checks}</td></tr>"
        failed_section = f"""
        <h3 style="margin-top:24px;color:#c62828">Failed Runs</h3>
        <table style="border-collapse:collapse;font-family:monospace;font-size:13px">
          <tr style="background:#fce4e4">
            <th style="padding:4px 8px;text-align:left">Time</th>
            <th style="padding:4px 8px;text-align:left">Failed checks</th>
          </tr>
          {failed_rows}
        </table>"""
    else:
        failed_section = "<p style='color:#2e7d32'>&#10003; All runs passed — site is healthy.</p>"

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
      <div style="background:#cc0000;padding:16px 24px;border-radius:6px 6px 0 0">
        <h2 style="color:#fff;margin:0">copiousbags.com — Daily Report</h2>
        <p style="color:#ffcccc;margin:4px 0 0">Last 24 hours &nbsp;·&nbsp; up to {now_str}</p>
      </div>
      <div style="background:#f9f9f9;padding:24px;border:1px solid #ddd;border-top:none;border-radius:0 0 6px 6px">

        <div style="display:flex;gap:16px;margin-bottom:24px">
          <div style="flex:1;background:#fff;border:1px solid #ddd;border-radius:6px;padding:16px;text-align:center">
            <div style="font-size:32px;font-weight:bold;color:#333">{total}</div>
            <div style="color:#777;font-size:13px">Runs</div>
          </div>
          <div style="flex:1;background:#fff;border:1px solid #ddd;border-radius:6px;padding:16px;text-align:center">
            <div style="font-size:32px;font-weight:bold;color:#2e7d32">{passed}</div>
            <div style="color:#777;font-size:13px">Passed</div>
          </div>
          <div style="flex:1;background:#fff;border:1px solid #ddd;border-radius:6px;padding:16px;text-align:center">
            <div style="font-size:32px;font-weight:bold;color:#c62828">{failed}</div>
            <div style="color:#777;font-size:13px">Failed</div>
          </div>
        </div>

        <div style="background:{status_color};color:#fff;padding:10px 16px;border-radius:4px;font-weight:bold">
          {status_label}
        </div>

        {failed_section}
      </div>
    </div>
    """

    homepage = take_homepage_screenshot()
    report_images = [
        p for p in [
            homepage,
            os.path.join(SCREENSHOTS_DIR, "04_after_add_to_cart.png"),
            os.path.join(SCREENSHOTS_DIR, "06_checkout_elements.png"),
        ]
        if p and os.path.exists(p)
    ]
    _send(
        subject=f"[Monitor] copiousbags.com — Daily Report ({passed}/{total} passed)",
        body="\n".join(plain_lines) + "\n",
        html=html,
        extra_images=report_images,
    )


def make_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Remote(command_executor=SELENIUM_URL, options=options)


def save_screenshot(driver, name):
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    path = os.path.join(SCREENSHOTS_DIR, f"{name}.png")
    driver.save_screenshot(path)
    log.info("Screenshot saved: %s", path)


def full_page_screenshot(driver, name):
    """Scroll the page to trigger lazy-load, then capture the full height."""
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//img[@src and string-length(@src)>0]"))
        )
    except TimeoutException:
        pass
    total_height = driver.execute_script("return document.body.scrollHeight")
    driver.set_window_size(1920, total_height)
    time.sleep(1)
    path = os.path.join(SCREENSHOTS_DIR, f"{name}.png")
    driver.save_screenshot(path)
    driver.set_window_size(1920, 1080)  # restore for subsequent checks
    log.info("Full-page screenshot saved: %s (%dpx)", path, total_height)
    return path


def check_site_loads(driver):
    log.info("Checking site load: %s", TARGET_URL)
    driver.get(TARGET_URL)
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    title = driver.title
    if not title:
        raise AssertionError("Page loaded but title is empty")
    log.info("Site loaded OK — title: %s", title)
    full_page_screenshot(driver, "01_homepage")
    return True


def check_add_to_cart(driver):
    log.info("Opening product: %s", PRODUCT_URL)
    wait = WebDriverWait(driver, WAIT_TIMEOUT)
    driver.get(PRODUCT_URL)
    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    full_page_screenshot(driver, "02_shop")

    try:
        btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, (
                    "//button["
                    "@name='add-to-cart' or "
                    "contains(@class,'single_add_to_cart_button') or "
                    "contains(@class,'add-to-cart') or "
                    "contains(@class,'AddToCart') or "
                    "contains(@id,'add-to-cart') or "
                    "contains(translate(normalize-space(.),'ADDTOCART','addtocart'),'add to cart')"
                    "]"
                ))
            )
        )
        log.info("Add to Cart button found — text: %r", btn.text)
    except TimeoutException:
        save_screenshot(driver, "02b_no_add_to_cart")
        raise AssertionError("Add to Cart button not found on product page")

    save_screenshot(driver, "03_before_add_to_cart")
    btn.click()
    log.info("Clicked Add to Cart")

    try:
        wait.until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".woocommerce-message, .added_to_cart, .cart-contents")),
                EC.url_contains("/cart"),
            )
        )
        log.info("Add to Cart confirmed")
    except TimeoutException:
        log.info("No explicit confirmation — continuing anyway")

    save_screenshot(driver, "04_after_add_to_cart")
    return True


def check_checkout(driver):
    log.info("Navigating to checkout: %s", CHECKOUT_URL)
    wait = WebDriverWait(driver, WAIT_TIMEOUT)
    driver.get(CHECKOUT_URL)
    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

    try:
        wait.until(EC.presence_of_element_located((By.ID, "order_review")))
    except TimeoutException:
        save_screenshot(driver, "05_checkout_load_fail")
        raise AssertionError("Checkout page did not load the order review section")

    save_screenshot(driver, "05_checkout_page")

    missing = []
    for label, by, selector in CHECKOUT_ELEMENTS:
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((by, selector)))
            log.info("  [FOUND]   %s", label)
        except TimeoutException:
            log.warning("  [MISSING] %s", label)
            missing.append(label)

    save_screenshot(driver, "06_checkout_elements")

    if missing:
        raise AssertionError(f"Checkout missing elements: {', '.join(missing)}")

    log.info("All checkout elements present")
    return True


def run_checks():
    results = {"site_load": False, "add_to_cart": False, "checkout": False}
    driver = None
    try:
        driver = make_driver()
        results["site_load"]   = check_site_loads(driver)
        results["add_to_cart"] = check_add_to_cart(driver)
        results["checkout"]    = check_checkout(driver)
    except (TimeoutException, WebDriverException, AssertionError) as exc:
        log.error("Check failed: %s", exc)
        if driver:
            save_screenshot(driver, "error_state")
    finally:
        if driver:
            driver.quit()

    log.info("--- Results ---")
    for check, passed in results.items():
        log.info("  %-15s %s", check, "PASS" if passed else "FAIL")

    all_passed = all(results.values())

    history.append({"time": datetime.now(), "results": results, "passed": all_passed})
    _prune_history()

    if not all_passed:
        send_failure_email(results)

    return all_passed


def _daily_report_due(last_report_date):
    now_est = datetime.now(TZ_EST)
    report_h, report_m = map(int, DAILY_REPORT_TIME.split(":"))
    scheduled_today = now_est.replace(hour=report_h, minute=report_m, second=0, microsecond=0)
    log.debug("Daily report check — now EST: %s, scheduled: %s, last sent: %s",
              now_est.strftime("%H:%M"), DAILY_REPORT_TIME, last_report_date)
    return now_est >= scheduled_today and last_report_date != now_est.date()


if __name__ == "__main__":
    time.sleep(3)
    run_number = 1
    last_report_date = None

    while True:
        log.info("=== Run #%d ===", run_number)
        run_checks()

        if _daily_report_due(last_report_date):
            log.info("Sending daily report")
            send_daily_report()
            last_report_date = datetime.now().date()

        log.info("Next check in %d seconds...", INTERVAL_SECONDS)
        time.sleep(INTERVAL_SECONDS)
        run_number += 1
