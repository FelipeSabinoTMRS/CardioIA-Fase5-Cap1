"""Testes locais do schema; não fazem chamadas à API."""

import pytest
from pydantic import ValidationError

from extracao_clinica import ExtracaoClinica, SinaisVitais


def test_schema_aceita_campos_ausentes() -> None:
    resultado = ExtracaoClinica(
        sintomas=["tontura"],
        sinais_vitais=SinaisVitais(),
    )
    assert resultado.sinais_vitais.pressao_arterial is None
    assert resultado.medicamentos == []


def test_schema_remove_duplicados_e_vazios() -> None:
    resultado = ExtracaoClinica(sintomas=["Tontura", "tontura", "  "])
    assert resultado.sintomas == ["Tontura"]


def test_schema_rejeita_campo_inventado() -> None:
    with pytest.raises(ValidationError):
        ExtracaoClinica.model_validate({"diagnostico": "hipertensão"})

