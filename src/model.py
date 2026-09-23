import math
from typing import Optional, Dict
from pydantic import BaseModel, Field


class ResistProperties(BaseModel):
    name: str = Field(default="Standard Photoresist")
    viscosity_mPa_s: float = Field(description="Dynamische Viskosität in mPa·s (cP)")
    solid_content_fraction: float = Field(description="Feststoffgehalt als Anteil (0.0 bis 1.0)", ge=0.0, le=1.0)
    k_factor: float = Field(default=5000.0, description="Empirischer K-Faktor des Lackes")
    alpha_exponent: float = Field(default=0.5, description="Empirischer Exponent alpha (meist 0.45 - 0.55)")


# Voreingestellte Beispiellacke
PRESET_RESISTS: Dict[str, ResistProperties] = {
    "SU-8 2002": ResistProperties(
        name="SU-8 2002",
        viscosity_mPa_s=7.5,
        solid_content_fraction=0.29,
        k_factor=12000.0,
        alpha_exponent=0.5
    ),
    "AZ 1512": ResistProperties(
        name="AZ 1512",
        viscosity_mPa_s=18.0,
        solid_content_fraction=0.20,
        k_factor=7500.0,
        alpha_exponent=0.5
    ),
    "PMMA A4": ResistProperties(
        name="PMMA A4",
        viscosity_mPa_s=15.0,
        solid_content_fraction=0.04,
        k_factor=1300.0,
        alpha_exponent=0.5
    )
}


class SpinCoatingCalculator:
    """Berechnet Schichtdicken und Spin-Geschwindigkeiten für Lackbeschichtungen."""

    @staticmethod
    def calculate_thickness(rpm: float, resist: ResistProperties) -> float:
        """
        Berechnet die erwartete Schichtdicke in Nanometern (nm)
        basierend auf der Drehzahl (rpm) und den Lackeigenschaften.
        """
        if rpm <= 0:
            raise ValueError("Drehzahl (rpm) muss größer als 0 sein.")
        
        # Empirisches Potenzgesetz: h = K / (rpm ^ alpha)
        thickness_nm = resist.k_factor / (rpm ** resist.alpha_exponent)
        return round(thickness_nm, 2)

    @staticmethod
    def calculate_required_rpm(target_thickness_nm: float, resist: ResistProperties) -> float:
        """
        Berechnet die erforderliche Spin-Geschwindigkeit (rpm) 
        für eine gewünschte Schichtdicke in Nanometern (nm).
        """
        if target_thickness_nm <= 0:
            raise ValueError("Ziel-Schichtdicke muss größer als 0 nm sein.")
        
        # Umkehrfunktion: rpm = (K / h) ^ (1 / alpha)
        required_rpm = (resist.k_factor / target_thickness_nm) ** (1.0 / resist.alpha_exponent)
        return round(required_rpm, 1)