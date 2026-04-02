"""Modelo de datos para información del partner."""

from dataclasses import dataclass


@dataclass
class PartnerData:
    """Datos del partner/socio de negocio y cliente final.

    Atributos:
        partner_name: Nombre del partner o socio de negocio.
        partner_email: Correo electrónico del partner.
        region: Región o país de procedencia.
        end_customer: Nombre del cliente final.
    """

    partner_name: str = ""
    partner_email: str = ""
    region: str = ""
    end_customer: str = ""
