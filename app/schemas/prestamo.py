from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class PrestamoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edad: int = Field(ge=18, le=75, description="Edad del solicitante en años")
    ingresos_mensuales: float = Field(gt=0, description="Ingresos mensuales")
    importe_prestamo: float = Field(gt=0, description="Importe solicitado")
    plazo_meses: int = Field(ge=6, le=84, description="Plazo en meses")
    antiguedad_laboral_anios: int = Field(
        ge=0, le=50, description="Años de antigüedad laboral (máximo edad - 16)"
    )
    impagos_previos: int = Field(ge=0, le=20, description="Número de impagos previos")

    @field_validator("antiguedad_laboral_anios")
    @classmethod
    def antiguedad_coherente_con_edad(cls, valor: int, info: ValidationInfo) -> int:
        edad = info.data.get("edad")
        if edad is not None and valor > edad - 16:
            raise ValueError(
                "antiguedad_laboral_anios no puede ser mayor que edad - 16"
            )
        return valor


class PrediccionSalida(BaseModel):
    probabilidad_impago: float = Field(ge=0, le=1)
    decision: Literal["aprobar", "revisar", "rechazar"]
