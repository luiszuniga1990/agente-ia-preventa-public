"""Generador de PDF y CSV para estimaciones de costos.

Genera documentos PDF con reportlab y CSV con el módulo estándar,
incluyendo datos del partner, desglose de costos, supuestos y disclaimer.
Soporta 4 idiomas: es, en, pt, de.
"""

import csv
import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.models.estimation import Estimation

# Etiquetas multiidioma
_LABELS: dict[str, dict[str, str]] = {
    "es": {
        "title": "Estimación de Costos AWS",
        "partner": "Partner",
        "email": "Correo",
        "region": "Región",
        "end_customer": "Cliente Final",
        "date": "Fecha",
        "pricing_date": "Precios actualizados al",
        "service": "Servicio",
        "monthly_cost": "Costo Mensual",
        "annual_cost": "Costo Anual",
        "breakdown": "Desglose de Costos",
        "component": "Componente",
        "unit_price": "Precio Unitario",
        "quantity": "Cantidad",
        "cost": "Costo/Mes",
        "assumptions": "Supuestos",
        "disclaimer": "AVISO: Los costos son aproximados y están sujetos a cambios según los precios vigentes del proveedor.",
        "external_estimations": "Estimaciones Externas",
        "consolidated_total": "Total Consolidado",
        "total_monthly": "Costo Mensual Total",
        "total_annual": "Costo Anual Total",
        "service_name": "Servicio",
        "provider": "Proveedor",
        "notes": "Notas",
    },
    "en": {
        "title": "AWS Cost Estimation",
        "partner": "Partner",
        "email": "Email",
        "region": "Region",
        "end_customer": "End Customer",
        "date": "Date",
        "pricing_date": "Pricing updated on",
        "service": "Service",
        "monthly_cost": "Monthly Cost",
        "annual_cost": "Annual Cost",
        "breakdown": "Cost Breakdown",
        "component": "Component",
        "unit_price": "Unit Price",
        "quantity": "Quantity",
        "cost": "Cost/Month",
        "assumptions": "Assumptions",
        "disclaimer": "NOTICE: Costs are approximate and subject to change based on current provider pricing.",
        "external_estimations": "External Estimations",
        "consolidated_total": "Consolidated Total",
        "total_monthly": "Total Monthly Cost",
        "total_annual": "Total Annual Cost",
        "service_name": "Service",
        "provider": "Provider",
        "notes": "Notes",
    },
    "pt": {
        "title": "Estimativa de Custos AWS",
        "partner": "Parceiro",
        "email": "E-mail",
        "region": "Região",
        "end_customer": "Cliente Final",
        "date": "Data",
        "pricing_date": "Preços atualizados em",
        "service": "Serviço",
        "monthly_cost": "Custo Mensal",
        "annual_cost": "Custo Anual",
        "breakdown": "Detalhamento de Custos",
        "component": "Componente",
        "unit_price": "Preço Unitário",
        "quantity": "Quantidade",
        "cost": "Custo/Mês",
        "assumptions": "Premissas",
        "disclaimer": "AVISO: Os custos são aproximados e estão sujeitos a alterações conforme os preços vigentes do provedor.",
        "external_estimations": "Estimativas Externas",
        "consolidated_total": "Total Consolidado",
        "total_monthly": "Custo Mensal Total",
        "total_annual": "Custo Anual Total",
        "service_name": "Serviço",
        "provider": "Provedor",
        "notes": "Notas",
    },
    "de": {
        "title": "AWS Kostenschätzung",
        "partner": "Partner",
        "email": "E-Mail",
        "region": "Region",
        "end_customer": "Endkunde",
        "date": "Datum",
        "pricing_date": "Preise aktualisiert am",
        "service": "Dienst",
        "monthly_cost": "Monatliche Kosten",
        "annual_cost": "Jährliche Kosten",
        "breakdown": "Kostenaufschlüsselung",
        "component": "Komponente",
        "unit_price": "Stückpreis",
        "quantity": "Menge",
        "cost": "Kosten/Monat",
        "assumptions": "Annahmen",
        "disclaimer": "HINWEIS: Die Kosten sind Näherungswerte und können sich je nach aktuellen Anbieterpreisen ändern.",
        "external_estimations": "Externe Schätzungen",
        "consolidated_total": "Konsolidierte Gesamtsumme",
        "total_monthly": "Monatliche Gesamtkosten",
        "total_annual": "Jährliche Gesamtkosten",
        "service_name": "Dienst",
        "provider": "Anbieter",
        "notes": "Anmerkungen",
    },
}


def _get_labels(language: str) -> dict[str, str]:
    """Obtener etiquetas para el idioma dado, con fallback a español."""
    return _LABELS.get(language, _LABELS["es"])


def generate_pdf(estimation: Estimation, language: str = "es") -> bytes:
    """Generar PDF con los datos de la estimación.

    Incluye: datos del partner, tabla de costos con desglose, supuestos,
    fecha de pricing, disclaimer. Si hay consolidación, incluye sección
    de estimaciones externas y total consolidado.

    Args:
        estimation: Objeto Estimation con todos los datos.
        language: Código ISO del idioma (es/en/pt/de).

    Returns:
        Contenido del PDF como bytes.
    """
    labels = _get_labels(language)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Title"], fontSize=18, spaceAfter=12
    )
    heading_style = ParagraphStyle(
        "CustomHeading", parent=styles["Heading2"], fontSize=13, spaceAfter=6
    )
    normal_style = styles["Normal"]

    elements: list[Any] = []

    # Título
    elements.append(Paragraph(labels["title"], title_style))
    elements.append(Spacer(1, 12))

    # Datos del partner
    partner = estimation.partner_data
    partner_info = [
        f"<b>{labels['partner']}:</b> {partner.partner_name}",
        f"<b>{labels['email']}:</b> {partner.partner_email}",
        f"<b>{labels['region']}:</b> {partner.region}",
        f"<b>{labels['end_customer']}:</b> {partner.end_customer}",
        f"<b>{labels['date']}:</b> {estimation.created_at}",
        f"<b>{labels['pricing_date']}:</b> {estimation.pricing_date}",
    ]
    for line in partner_info:
        elements.append(Paragraph(line, normal_style))
    elements.append(Spacer(1, 12))

    # Servicio y costos
    elements.append(Paragraph(f"{labels['service']}: {estimation.service}", heading_style))
    elements.append(
        Paragraph(
            f"{labels['monthly_cost']}: ${estimation.monthly_cost:,.2f} | "
            f"{labels['annual_cost']}: ${estimation.annual_cost:,.2f}",
            normal_style,
        )
    )
    elements.append(Spacer(1, 12))

    # Tabla de desglose
    if estimation.breakdown:
        elements.append(Paragraph(labels["breakdown"], heading_style))
        table_data = [
            [labels["component"], labels["unit_price"], labels["quantity"], labels["cost"]]
        ]
        for item in estimation.breakdown:
            table_data.append([
                str(item.get("component", "")),
                f"${float(item.get('unit_price', 0)):,.2f}",
                str(item.get("quantity", "")),
                f"${float(item.get('monthly_cost', 0)):,.2f}",
            ])

        table = Table(table_data, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#232F3E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

    # Supuestos
    if estimation.assumptions:
        elements.append(Paragraph(labels["assumptions"], heading_style))
        for assumption in estimation.assumptions:
            elements.append(Paragraph(f"• {assumption}", normal_style))
        elements.append(Spacer(1, 12))

    # Estimaciones externas (consolidación)
    if estimation.is_consolidated and estimation.external_estimations:
        elements.append(Paragraph(labels["external_estimations"], heading_style))
        ext_services = estimation.external_estimations.get("external_services", [])
        for ext in ext_services:
            svc_name = ext.get("service_name", "N/A")
            provider = ext.get("provider", "N/A")
            m_cost = float(ext.get("monthly_cost", 0))
            a_cost = float(ext.get("annual_cost", 0))
            elements.append(
                Paragraph(
                    f"<b>{svc_name}</b> ({provider}): "
                    f"${m_cost:,.2f}/mes | ${a_cost:,.2f}/año",
                    normal_style,
                )
            )
        elements.append(Spacer(1, 12))

        # Total consolidado
        elements.append(Paragraph(labels["consolidated_total"], heading_style))
        total_monthly = estimation.monthly_cost + sum(
            float(e.get("monthly_cost", 0)) for e in ext_services
        )
        total_annual = estimation.annual_cost + sum(
            float(e.get("annual_cost", 0)) for e in ext_services
        )
        elements.append(
            Paragraph(
                f"{labels['total_monthly']}: ${total_monthly:,.2f} | "
                f"{labels['total_annual']}: ${total_annual:,.2f}",
                normal_style,
            )
        )
        elements.append(Spacer(1, 12))

    # Disclaimer
    disclaimer_style = ParagraphStyle(
        "Disclaimer", parent=normal_style, fontSize=8, textColor=colors.grey
    )
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(labels["disclaimer"], disclaimer_style))

    doc.build(elements)
    return buffer.getvalue()


def generate_csv(estimation: Estimation) -> str:
    """Generar CSV con el desglose de costos de la estimación.

    Args:
        estimation: Objeto Estimation con los datos.

    Returns:
        Contenido CSV como cadena de texto.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Encabezados
    writer.writerow(["Component", "Unit Price", "Quantity", "Monthly Cost"])

    # Filas de desglose
    for item in estimation.breakdown:
        writer.writerow([
            item.get("component", ""),
            item.get("unit_price", 0),
            item.get("quantity", 0),
            item.get("monthly_cost", 0),
        ])

    # Fila de totales
    writer.writerow([])
    writer.writerow(["Total Monthly Cost", "", "", estimation.monthly_cost])
    writer.writerow(["Total Annual Cost", "", "", estimation.annual_cost])

    # Estimaciones externas si hay consolidación
    if estimation.is_consolidated and estimation.external_estimations:
        writer.writerow([])
        writer.writerow(["External Estimations"])
        writer.writerow(["Service", "Provider", "Monthly Cost", "Annual Cost"])
        for ext in estimation.external_estimations.get("external_services", []):
            writer.writerow([
                ext.get("service_name", ""),
                ext.get("provider", ""),
                ext.get("monthly_cost", 0),
                ext.get("annual_cost", 0),
            ])

    return output.getvalue()
