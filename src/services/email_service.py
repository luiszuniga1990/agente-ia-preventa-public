"""Servicio de envío de estimaciones por correo electrónico vía SES.

Construye un mensaje MIME multipart con texto plano y PDF adjunto,
y lo envía usando Amazon SES send_raw_email.
"""

import logging
import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.models.estimation import Estimation

logger = logging.getLogger(__name__)

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "noreply@preventa.example.com")


def send_estimation_email(
    ses_client,
    estimation: Estimation,
    recipient_email: str,
    pdf_bytes: bytes,
    language: str = "es",
) -> dict:
    """Enviar estimación por correo electrónico vía SES.

    Construye cuerpo en texto plano con datos del partner, desglose,
    estimaciones externas (si consolidada) y disclaimer.
    Adjunta el PDF de la estimación.

    Args:
        ses_client: Cliente boto3 de SES.
        estimation: Objeto Estimation completo.
        recipient_email: Correo del destinatario.
        pdf_bytes: Contenido del PDF como bytes.
        language: Código ISO del idioma (es/en/pt/de).

    Returns:
        Diccionario con message_id y status.
    """
    try:
        # Construir cuerpo de texto plano
        body_text = _build_plain_text_body(estimation, language)

        # Construir mensaje MIME multipart
        msg = MIMEMultipart("mixed")
        msg["Subject"] = _get_subject(estimation, language)
        msg["From"] = SENDER_EMAIL
        msg["To"] = recipient_email

        # Parte de texto plano
        text_part = MIMEText(body_text, "plain", "utf-8")
        msg.attach(text_part)

        # Parte de PDF adjunto
        pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_filename = f"estimacion_{estimation.estimation_id}.pdf"
        pdf_part.add_header(
            "Content-Disposition", "attachment", filename=pdf_filename
        )
        msg.attach(pdf_part)

        # Enviar vía SES
        response = ses_client.send_raw_email(
            Source=SENDER_EMAIL,
            Destinations=[recipient_email],
            RawMessage={"Data": msg.as_string()},
        )

        message_id = response.get("MessageId", "")
        return {"message_id": message_id, "status": "sent"}

    except Exception as exc:
        logger.exception("Error enviando email: %s", exc)
        return {"message_id": "", "status": "failed", "error": str(exc)}


def _get_subject(estimation: Estimation, language: str) -> str:
    """Obtener asunto del correo según idioma."""
    subjects = {
        "es": f"Estimación de Costos AWS - {estimation.service}",
        "en": f"AWS Cost Estimation - {estimation.service}",
        "pt": f"Estimativa de Custos AWS - {estimation.service}",
        "de": f"AWS Kostenschätzung - {estimation.service}",
    }
    return subjects.get(language, subjects["es"])


def _build_plain_text_body(estimation: Estimation, language: str) -> str:
    """Construir cuerpo del correo en texto plano.

    Sigue el formato definido en el diseño técnico.

    Args:
        estimation: Objeto Estimation completo.
        language: Código ISO del idioma.

    Returns:
        Cuerpo del correo como texto plano.
    """
    partner = estimation.partner_data
    lines: list[str] = []

    lines.append("=== ESTIMACIÓN DE COSTOS AWS ===")
    lines.append("")
    lines.append(f"Partner: {partner.partner_name}")
    lines.append(f"Correo: {partner.partner_email}")
    lines.append(f"Región: {partner.region}")
    lines.append(f"Cliente Final: {partner.end_customer}")
    lines.append(f"Fecha: {estimation.created_at}")
    lines.append(f"Precios actualizados al: {estimation.pricing_date}")
    lines.append("")

    # Estimación del servicio
    lines.append(f"--- ESTIMACIÓN: {estimation.service} ---")
    lines.append(f"Costo Mensual: ${estimation.monthly_cost:,.2f}")
    lines.append(f"Costo Anual: ${estimation.annual_cost:,.2f}")
    lines.append("")

    # Desglose
    lines.append("Desglose:")
    for item in estimation.breakdown:
        component = item.get("component", "")
        cost = float(item.get("monthly_cost", 0))
        quantity = item.get("quantity", "")
        unit_price = float(item.get("unit_price", 0))
        lines.append(
            f"  - {component}: ${cost:,.2f}/mes ({quantity} x ${unit_price:,.2f})"
        )
    lines.append("")

    # Supuestos
    lines.append("Supuestos:")
    for assumption in estimation.assumptions:
        lines.append(f"  - {assumption}")
    lines.append("")

    # Estimaciones externas (si hay consolidación)
    if estimation.is_consolidated and estimation.external_estimations:
        ext_services = estimation.external_estimations.get("external_services", [])
        if ext_services:
            lines.append("--- ESTIMACIONES EXTERNAS ---")
            for ext in ext_services:
                svc_name = ext.get("service_name", "N/A")
                m_cost = float(ext.get("monthly_cost", 0))
                lines.append(f"  - {svc_name}: ${m_cost:,.2f}/mes")
            lines.append("")

            # Total consolidado
            total_monthly = estimation.monthly_cost + sum(
                float(e.get("monthly_cost", 0)) for e in ext_services
            )
            total_annual = estimation.annual_cost + sum(
                float(e.get("annual_cost", 0)) for e in ext_services
            )
            lines.append("--- TOTAL CONSOLIDADO ---")
            lines.append(f"Costo Mensual Total: ${total_monthly:,.2f}")
            lines.append(f"Costo Anual Total: ${total_annual:,.2f}")
            lines.append("")

    # Disclaimer
    lines.append(
        "AVISO: Los costos son aproximados y están sujetos a cambios"
    )
    lines.append("según los precios vigentes del proveedor.")

    return "\n".join(lines)
