"""
FastAPI entry point for NASDAQ Hierarchical Multi-Agent System.

Endpoints:
  GET  /health         — Health check
  POST /cron/analyze   — Cloud Scheduler daily trigger
  POST /slack/events   — /nasdaqscan slash command → Slack + Email output
"""

import asyncio
import hashlib
import hmac
import logging
import time
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import JSONResponse

from .config import settings

# ── Logging ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("nasdaq-mas")

app = FastAPI(title="NASDAQ Multi-Agent System", version="0.1.0")


# ═══════════════════════════════════════════════════════════
#  Health Check
# ═══════════════════════════════════════════════════════════
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "nasdaq-multi-agent", "version": "0.1.0"}


# ═══════════════════════════════════════════════════════════
#  Cron Trigger (Cloud Scheduler)
# ═══════════════════════════════════════════════════════════
@app.post("/cron/analyze")
async def cron_analyze(request: Request, background_tasks: BackgroundTasks):
    """Triggered by Cloud Scheduler. Runs full analysis and posts to Slack."""
    # Verify cron secret
    if not _verify_cron_secret(request):
        return JSONResponse(status_code=403, content={"error": "Forbidden"})

    logger.info("⏰ Cron trigger received — starting full analysis")
    background_tasks.add_task(_run_and_deliver, channel_id=settings.SLACK_CHANNEL_ID)
    return {"status": "analysis_started", "delivery": "slack"}


# ═══════════════════════════════════════════════════════════
#  Slack Slash Command (/nasdaqscan)
# ═══════════════════════════════════════════════════════════
@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """Handle /nasdaqscan slash command from Slack."""
    # Verify Slack signature
    if not await _verify_slack_signature(request):
        return JSONResponse(status_code=401, content={"error": "Invalid signature"})

    form = await request.form()
    channel_id = form.get("channel_id", settings.SLACK_CHANNEL_ID)
    user_id = form.get("user_id", "unknown")
    logger.info(f"💬 Slack command from user {user_id} in channel {channel_id}")

    # Acknowledge within 3 seconds (Slack timeout rule)
    background_tasks.add_task(
        _run_and_deliver,
        channel_id=channel_id,
        send_email=True,  # Slash commands also trigger email
    )
    return {
        "response_type": "ephemeral",
        "text": "🔄 Running NASDAQ multi-agent analysis... results in ~60s ⏳",
    }


# ═══════════════════════════════════════════════════════════
#  Background Task: Run Analysis & Deliver
# ═══════════════════════════════════════════════════════════
async def _run_and_deliver(
    channel_id: str,
    send_email: bool = False,
):
    """Run the full hierarchical analysis pipeline and deliver results."""
    try:
        # Import here to avoid circular imports and speed up cold start
        from .orchestrator import HierarchicalOrchestrator

        orchestrator = HierarchicalOrchestrator()
        result = await orchestrator.run_full_analysis()

        # Format output
        from .formatter import format_slack_blocks, format_slack_message, format_email

        slack_blocks = format_slack_blocks(result)
        slack_fallback = format_slack_message(result)  # Plain text fallback

        # Send to Slack with Block Kit
        from slack_sdk import WebClient

        slack_client = WebClient(token=settings.SLACK_BOT_TOKEN)
        slack_client.chat_postMessage(
            channel=channel_id,
            text=slack_fallback,   # Fallback for notifications
            blocks=slack_blocks,   # Rich Block Kit layout
        )
        logger.info(f"📤 Slack Block Kit message sent to {channel_id}")

        # Send email — isolated so failures don't kill Slack delivery
        try:
            if settings.EMAIL_SENDER and settings.EMAIL_RECIPIENT and settings.EMAIL_APP_PASSWORD:
                email_body = format_email(result)
                _send_email(
                    subject="📊 NASDAQ Multi-Agent Analysis",
                    body=email_body,
                )
                logger.info(f"📧 Email sent to {settings.EMAIL_RECIPIENT}")
            else:
                logger.warning("📧 Email skipped — missing EMAIL_SENDER, EMAIL_RECIPIENT, or EMAIL_APP_PASSWORD")
        except Exception as email_err:
            logger.error(f"📧 Email delivery failed (Slack was sent OK): {email_err}")

    except Exception as e:
        logger.error(f"❌ Analysis pipeline failed: {e}", exc_info=True)
        try:
            from slack_sdk import WebClient

            slack_client = WebClient(token=settings.SLACK_BOT_TOKEN)
            slack_client.chat_postMessage(
                channel=channel_id,
                text=f"❌ NASDAQ analysis failed:\n```{str(e)[:500]}```",
            )
        except Exception:
            logger.error("Failed to send error message to Slack")


# ═══════════════════════════════════════════════════════════
#  Email Delivery
# ═══════════════════════════════════════════════════════════
def _send_email(subject: str, body: str):
    """Send email via Gmail SMTP with App Password."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_SENDER
    msg["To"] = settings.EMAIL_RECIPIENT
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(settings.EMAIL_SENDER, settings.EMAIL_APP_PASSWORD)
        server.sendmail(settings.EMAIL_SENDER, settings.EMAIL_RECIPIENT, msg.as_string())


# ═══════════════════════════════════════════════════════════
#  Security Helpers
# ═══════════════════════════════════════════════════════════
async def _verify_slack_signature(request: Request) -> bool:
    """HMAC-SHA256 verification of Slack requests."""
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not timestamp or not signature:
        return False
    if abs(time.time() - int(timestamp)) > 300:
        return False

    body = await request.body()
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    my_sig = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(my_sig, signature)


def _verify_cron_secret(request: Request) -> bool:
    """Verify X-Cron-Secret header for Cloud Scheduler."""
    incoming = request.headers.get("X-Cron-Secret", "")
    expected = settings.CRON_SECRET
    if not expected:
        logger.warning("⚠️ CRON_SECRET not configured — skipping auth")
        return True
    return hmac.compare_digest(incoming, expected)
