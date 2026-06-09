"""Transactional email helpers powered by SendGrid.

Sends are dispatched on a background thread so the API request that triggered
them doesn't block on SendGrid latency. If SendGrid fails for any reason, the
failure is logged but does not propagate to the caller (emails are
fire-and-forget notifications, not part of the core transactional flow).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)

BRAND_ACCENT = "#FF3B30"
BRAND_BG = "#0A0A0A"


def _enabled() -> bool:
    return bool(os.environ.get("SENDGRID_API_KEY") and os.environ.get("SENDER_EMAIL"))


def _send_sync(to: str, subject: str, html: str, plain: str) -> None:
    if not _enabled():
        logger.warning("SendGrid not configured (SENDGRID_API_KEY / SENDER_EMAIL missing). Skipping email to %s", to)
        return
    try:
        message = Mail(
            from_email=os.environ["SENDER_EMAIL"],
            to_emails=to,
            subject=subject,
            html_content=html,
            plain_text_content=plain,
        )
        client = SendGridAPIClient(os.environ["SENDGRID_API_KEY"])
        response = client.send(message)
        if response.status_code >= 300:
            logger.error("SendGrid non-2xx for %s: status=%s body=%s", to, response.status_code, response.body)
        else:
            logger.info("SendGrid sent to %s (status=%s)", to, response.status_code)
    except Exception as exc:  # noqa: BLE001 - we never want to crash the caller
        logger.exception("SendGrid send to %s failed: %s", to, exc)


async def send_email_async(to: str, subject: str, html: str, plain: str) -> None:
    """Dispatch the SendGrid call on a worker thread so we don't block the event loop."""
    if not to:
        return
    await asyncio.to_thread(_send_sync, to, subject, html, plain)


def _wrap_html(title: str, intro: str, cta_url: Optional[str], cta_label: Optional[str], extra_html: str = "") -> str:
    cta_block = ""
    if cta_url and cta_label:
        cta_block = f"""
        <div style="margin: 32px 0;">
          <a href="{cta_url}"
             style="background:{BRAND_ACCENT};color:#ffffff;text-decoration:none;
                    font-family:Arial,sans-serif;font-weight:bold;letter-spacing:0.05em;
                    padding:14px 28px;display:inline-block;">
            {cta_label}
          </a>
        </div>
        """

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#141414;font-family:Arial,sans-serif;color:#fff;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#141414;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0" style="background:{BRAND_BG};border:1px solid #262626;">
        <tr><td style="padding:32px;">
          <p style="margin:0 0 24px 0;font-size:14px;letter-spacing:0.25em;color:{BRAND_ACCENT};font-weight:bold;">GAME ON MOFOS!</p>
          <h1 style="margin:0 0 16px 0;font-size:28px;line-height:1.15;color:#ffffff;font-weight:900;">{title}</h1>
          <p style="margin:0 0 16px 0;font-size:15px;line-height:1.6;color:#A3A3A3;">{intro}</p>
          {extra_html}
          {cta_block}
          <hr style="border:none;border-top:1px solid #262626;margin:32px 0;" />
          <p style="margin:0;font-size:12px;color:#777;line-height:1.5;">
            You're receiving this because you have a Gomofos account. Stake. Compete. Dominate.<br/>
            <a href="https://gomofos.com" style="color:{BRAND_ACCENT};text-decoration:none;">gomofos.com</a>
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ---------- Public senders ----------

async def send_match_invite(*, to_email: str, opponent_username: str, challenger_username: str,
                            game_name: str, stake_amount: float, tournament_id: str,
                            app_url: str, decline_token: Optional[str] = None) -> None:
    if not to_email:
        return
    title = f"{challenger_username} just challenged you on Gomofos"
    intro = (f"You've been invited to a 1v1 match in <strong style='color:#fff'>{game_name}</strong> "
             f"for <strong style='color:#fff'>{stake_amount:.0f} CR</strong>. "
             "Accept and prove you're the better Mofo — or decline and both stakes get refunded automatically.")
    extra = f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;background:#141414;border:1px solid #262626;">
      <tr><td style="padding:16px;">
        <p style="margin:0;font-size:11px;letter-spacing:0.2em;color:#A3A3A3;font-weight:bold;">CHALLENGER</p>
        <p style="margin:4px 0 12px 0;font-size:18px;color:#fff;font-weight:bold;">{challenger_username}</p>
        <p style="margin:0;font-size:11px;letter-spacing:0.2em;color:#A3A3A3;font-weight:bold;">GAME</p>
        <p style="margin:4px 0 12px 0;font-size:18px;color:#fff;font-weight:bold;">{game_name}</p>
        <p style="margin:0;font-size:11px;letter-spacing:0.2em;color:#A3A3A3;font-weight:bold;">STAKE</p>
        <p style="margin:4px 0 0 0;font-size:22px;color:{BRAND_ACCENT};font-weight:900;">{stake_amount:.0f} CR</p>
      </td></tr>
    </table>
    """
    base = app_url.rstrip("/")
    accept_url = f"{base}/tournament/{tournament_id}"
    decline_url = f"{base}/api/challenges/decline?token={decline_token}" if decline_token else None

    # Build dual-button CTA block manually so we can include BOTH accept + decline
    decline_button_html = ""
    if decline_url:
        decline_button_html = f"""
        <a href="{decline_url}"
           style="background:transparent;color:#A3A3A3;text-decoration:none;border:1px solid #3F3F3F;
                  font-family:Arial,sans-serif;font-weight:bold;letter-spacing:0.05em;
                  padding:13px 28px;display:inline-block;margin-left:8px;">
          DECLINE &amp; REFUND
        </a>
        """
    extra += f"""
    <div style="margin: 32px 0;">
      <a href="{accept_url}"
         style="background:{BRAND_ACCENT};color:#ffffff;text-decoration:none;
                font-family:Arial,sans-serif;font-weight:bold;letter-spacing:0.05em;
                padding:14px 28px;display:inline-block;">
        ACCEPT CHALLENGE
      </a>
      {decline_button_html}
    </div>
    <p style="margin:0;font-size:12px;color:#777;line-height:1.5;">
      Declining refunds {stake_amount:.0f} CR to the challenger's wallet immediately. You haven't paid anything yet. This decline link is valid for 7 days.
    </p>
    """
    # Use the inner template without the auto CTA (we built our own dual-button block above)
    html = _wrap_html(title, intro, None, None, extra)
    plain_parts = [
        f"Hey {opponent_username},",
        "",
        f"{challenger_username} challenged you to a 1v1 match in {game_name} for {stake_amount:.0f} CR on Gomofos.",
        "",
        f"Accept: {accept_url}",
    ]
    if decline_url:
        plain_parts.append(f"Decline & refund: {decline_url}")
    plain_parts.append("")
    plain_parts.append("Game on, Mofo.\n— Gomofos")
    plain = "\n".join(plain_parts)
    await send_email_async(to_email, title, html, plain)


async def send_dispute_alert(*, to_email: str, opponent_username: str, opener_username: str,
                             game_name: str, stake_amount: float, tournament_id: str,
                             app_url: str) -> None:
    if not to_email:
        return
    title = f"Dispute opened on your {game_name} match"
    intro = (f"{opener_username} reported a different winner for your recent match. "
             "Upload screenshot evidence within 48 hours or the dispute may resolve against you.")
    extra = f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;background:#141414;border:1px solid #262626;">
      <tr><td style="padding:16px;">
        <p style="margin:0;font-size:11px;letter-spacing:0.2em;color:#A3A3A3;font-weight:bold;">GAME</p>
        <p style="margin:4px 0 12px 0;font-size:18px;color:#fff;font-weight:bold;">{game_name}</p>
        <p style="margin:0;font-size:11px;letter-spacing:0.2em;color:#A3A3A3;font-weight:bold;">POT AT STAKE</p>
        <p style="margin:4px 0 12px 0;font-size:22px;color:{BRAND_ACCENT};font-weight:900;">{stake_amount:.0f} CR</p>
        <p style="margin:0;font-size:11px;letter-spacing:0.2em;color:#A3A3A3;font-weight:bold;">DISPUTE OPENED BY</p>
        <p style="margin:4px 0 0 0;font-size:16px;color:#fff;font-weight:bold;">{opener_username}</p>
      </td></tr>
    </table>
    <p style="margin:16px 0 0 0;font-size:13px;color:#A3A3A3;line-height:1.6;">
      Tip: in-match latency &gt; 200ms weighs against the high-latency player when admins review evidence.
    </p>
    """
    cta_url = f"{app_url.rstrip('/')}/tournament/{tournament_id}"
    html = _wrap_html(title, intro, cta_url, "REVIEW THE DISPUTE", extra)
    plain = (
        f"Hey {opponent_username},\n\n"
        f"{opener_username} opened a dispute on your match in {game_name} ({stake_amount:.0f} CR).\n\n"
        "Upload screenshot evidence here within 48 hours: "
        f"{cta_url}\n\n— Gomofos"
    )
    await send_email_async(to_email, title, html, plain)


async def send_dispute_admin_alert(*, admin_email: str, dispute_type: str,
                                   opener_username: str, opener_email: str,
                                   opponent_username: str, opponent_email: str,
                                   game_name: str, platform: str,
                                   stake_amount: float, dispute_id: str,
                                   review_url: Optional[str] = None,
                                   extra_context: Optional[str] = None) -> None:
    """Notify the admin/escalation inbox (e.g. david@gomofos.com) when a dispute is opened."""
    if not admin_email:
        return
    title = f"[GOMOFOS DISPUTE] {dispute_type} — {opener_username} vs {opponent_username}"
    intro = (f"A dispute has just been opened and needs admin review. "
             f"<strong style='color:#fff'>{opener_username}</strong> ({opener_email or 'no email'}) "
             f"is disputing a {dispute_type.lower()} against "
             f"<strong style='color:#fff'>{opponent_username}</strong> ({opponent_email or 'no email'}).")
    extra_block = ""
    if extra_context:
        extra_block = f"<p style=\"margin:16px 0 0 0;font-size:13px;color:#A3A3A3;\">{extra_context}</p>"
    platform_suffix = f" — {platform}" if platform else ""
    extra = f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;background:#141414;border:1px solid #262626;">
      <tr><td style="padding:16px;">
        <p style="margin:0;font-size:11px;letter-spacing:0.2em;color:#A3A3A3;font-weight:bold;">DISPUTE TYPE</p>
        <p style="margin:4px 0 12px 0;font-size:16px;color:#fff;font-weight:bold;">{dispute_type}</p>
        <p style="margin:0;font-size:11px;letter-spacing:0.2em;color:#A3A3A3;font-weight:bold;">GAME</p>
        <p style="margin:4px 0 12px 0;font-size:16px;color:#fff;font-weight:bold;">{game_name}{platform_suffix}</p>
        <p style="margin:0;font-size:11px;letter-spacing:0.2em;color:#A3A3A3;font-weight:bold;">POT AT STAKE</p>
        <p style="margin:4px 0 12px 0;font-size:22px;color:{BRAND_ACCENT};font-weight:900;">{stake_amount:.0f} CR</p>
        <p style="margin:0;font-size:11px;letter-spacing:0.2em;color:#A3A3A3;font-weight:bold;">REFERENCE ID</p>
        <p style="margin:4px 0 0 0;font-family:monospace;font-size:13px;color:#A3A3A3;">{dispute_id}</p>
      </td></tr>
    </table>
    {extra_block}
    """
    cta_label = "REVIEW IN DASHBOARD" if review_url else None
    html = _wrap_html(title, intro, review_url, cta_label, extra)
    plain = (
        "GOMOFOS DISPUTE ESCALATION\n"
        "==========================\n\n"
        f"Type:      {dispute_type}\n"
        f"Game:      {game_name}{platform_suffix}\n"
        f"Stake:     {stake_amount:.0f} CR\n"
        f"Ref ID:    {dispute_id}\n\n"
        f"Opener:    {opener_username} <{opener_email or 'no email'}>\n"
        f"Opponent:  {opponent_username} <{opponent_email or 'no email'}>\n\n"
    )
    if extra_context:
        plain += f"Context: {extra_context}\n\n"
    if review_url:
        plain += f"Review: {review_url}\n\n"
    plain += "— Gomofos Dispute Auto-Forwarder"
    await send_email_async(admin_email, title, html, plain)

