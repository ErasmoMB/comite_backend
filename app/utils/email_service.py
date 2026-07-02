import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


def get_email_config():
    """Return SMTP config from env vars, or None if not configured."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT", "587")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_from = os.getenv("SMTP_FROM")

    if not all([smtp_host, smtp_user, smtp_pass, smtp_from]):
        return None

    return {
        "host": smtp_host,
        "port": int(smtp_port),
        "user": smtp_user,
        "password": smtp_pass,
        "from_email": smtp_from,
    }


def enviar_email(
    to_emails: List[str],
    subject: str,
    body: str,
    pdf_paths: Optional[List[str]] = None,
) -> bool:
    """
    Send an email with optional PDF attachments.
    Returns True if sent successfully, False otherwise.
    Falls back to logging if SMTP is not configured.
    """
    config = get_email_config()

    if not config:
        logger.info(
            f"[EMAIL] SMTP no configurado. Se simula envío a: {to_emails}\n"
            f"  Asunto: {subject}\n"
            f"  Cuerpo: {body[:200]}...\n"
            f"  Adjuntos: {pdf_paths or []}"
        )
        return True

    try:
        msg = MIMEMultipart()
        msg["From"] = config["from_email"]
        msg["To"] = ", ".join(to_emails)
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))

        if pdf_paths:
            for pdf_path in pdf_paths:
                path = Path(pdf_path)
                if not path.exists():
                    logger.warning(f"Archivo PDF no encontrado: {pdf_path}")
                    continue
                with open(path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f'attachment; filename="{path.name}"',
                    )
                    msg.attach(part)

        server = smtplib.SMTP(config["host"], config["port"])
        server.starttls()
        server.login(config["user"], config["password"])
        server.send_message(msg)
        server.quit()

        logger.info(f"Email enviado exitosamente a: {to_emails}")
        return True

    except Exception as e:
        logger.error(f"Error enviando email: {e}")
        return False
