"""Curva climatica per il calcolo deterministico della temperatura di mandata.

Unifica la compensazione climatica in un unico componente di dominio puro,
eliminando le doppie compensazioni concorrenti tra stanze e generatori.
Supporta parametri dedicati per emettitore:
  - Radiatori (esponente 1.3, T_min 35°C, T_max 70°C)
  - Pavimento radiante (esponente 1.1, T_min 25°C, T_max 40°C)
  - Ventilconvettori (esponente 1.0, T_min 42°C, T_max 55°C)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

EMITTER_RADIATOR = "radiator"
EMITTER_UNDERFLOOR = "underfloor"
EMITTER_FANCOIL = "fancoil"

EMITTER_PRESETS: dict[str, dict[str, float]] = {
    EMITTER_RADIATOR: {
        "t_min": 35.0,
        "t_max": 70.0,
        "exponent": 1.3,
        "default_curve": 1.2,
    },
    EMITTER_UNDERFLOOR: {
        "t_min": 25.0,
        "t_max": 40.0,
        "exponent": 1.1,
        "default_curve": 0.6,
    },
    EMITTER_FANCOIL: {
        "t_min": 42.0,
        "t_max": 55.0,
        "exponent": 1.0,
        "default_curve": 1.0,
    },
}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


@dataclass(frozen=True)
class FlowCurve:
    """Modello matematico puro per la curva climatica."""

    t_min: float = 35.0          # mandata minima
    t_max: float = 75.0          # mandata alla temperatura esterna di progetto
    t_room_ref: float = 20.0     # temperatura ambiente di riferimento
    t_out_design: float = -5.0   # esterna di progetto della zona climatica
    exponent: float = 1.3        # ~1.3 radiatori, ~1.1 pavimento, ~1.0 fancoil
    curve_multiplier: float = 1.0  # Moltiplicatore pendenza (slider weather_curve)

    def __post_init__(self) -> None:
        if self.t_min >= self.t_max:
            raise ValueError("t_min deve essere < t_max")
        if self.t_out_design >= self.t_room_ref:
            raise ValueError("t_out_design deve essere < t_room_ref")
        if self.exponent <= 0:
            raise ValueError("exponent deve essere > 0")

    def ceiling(self, t_out: float | None) -> float:
        """Mandata massima ammessa con questa temperatura esterna."""
        if t_out is None or self.curve_multiplier <= 0.0:
            # Sonda assente o curva disabilitata: tetto fisso tradizionale
            return self.t_max

        dt = self.t_room_ref - t_out
        if dt <= 0:
            return self.t_min

        base_ratio = dt / (self.t_room_ref - self.t_out_design)
        ratio = base_ratio * self.curve_multiplier
        flow = self.t_room_ref + (self.t_max - self.t_room_ref) * (ratio ** (1.0 / self.exponent))
        return _clamp(flow, self.t_min, self.t_max)

    def flow_for_demand(self, demand_pct: float, t_out: float | None) -> float:
        """Mandata richiesta: t_min a domanda 0, tetto climatico a domanda 100."""
        d = _clamp(demand_pct, 0.0, 100.0) / 100.0
        top = self.ceiling(t_out)
        return round(self.t_min + d * (top - self.t_min), 1)


def create_flow_curve_for_emitter(
    emitter_type: str = EMITTER_RADIATOR,
    t_min: float | None = None,
    t_max: float | None = None,
    curve_multiplier: float = 1.0,
    has_mixing_valve: bool = False,
    is_mixed_underfloor: bool = False,
    t_out_design: float = -5.0,
) -> FlowCurve:
    """Factory helper per costruire una FlowCurve calibrata sull'emettitore."""
    preset = EMITTER_PRESETS.get(emitter_type, EMITTER_PRESETS[EMITTER_RADIATOR])
    eff_min = t_min if t_min is not None else preset["t_min"]
    eff_max = t_max if t_max is not None else preset["t_max"]
    eff_exp = preset["exponent"]

    # Se l'emettitore è a bassa temperatura (es. pavimento radiante),
    # clampiamo t_max al tetto fisico dell'emettitore (40°C), a meno che
    # non ci sia una valvola miscelatrice dedicata a valle dell'impianto centrale.
    if emitter_type == EMITTER_UNDERFLOOR and not has_mixing_valve:
        eff_max = min(eff_max, preset["t_max"])
        eff_min = min(eff_min, eff_max - 5.0)

    # Se l'impianto è misto con pavimento e senza valvola miscelatrice,
    # la mandata centrale non può mai superare i 40°C del pavimento!
    if is_mixed_underfloor and not has_mixing_valve:
        eff_max = min(eff_max, 40.0)

    # Assicura validità dei limiti
    if eff_min >= eff_max:
        eff_min = eff_max - 5.0

    return FlowCurve(
        t_min=eff_min,
        t_max=eff_max,
        exponent=eff_exp,
        curve_multiplier=max(0.0, curve_multiplier),
        t_out_design=t_out_design,
    )
