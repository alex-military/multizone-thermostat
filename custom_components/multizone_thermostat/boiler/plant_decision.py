"""Arbitraggio deterministico puro dei generatori (Gas vs Pompa di Calore).

Funzione pura a zero I/O e zero dipendenze da Home Assistant.
Garantisce il comportamento immutabile secondo le regole concordate:
  - Antigelo prioritario assoluto con fallback su qualsiasi generatore disponibile.
  - electric_priority con fallback a gas in caso di PDC guasta/indisponibile.
  - gas_priority pura (senza commutazioni solari non richieste).
  - combined: carico base a gas + boost PDC se delta_T >= 1.5°C o solar surplus.
"""
from __future__ import annotations

from dataclasses import dataclass

AUTO = "auto"
HYBRID = "hybrid"
COMBINED = "combined"
GAS_ONLY = "gas_only"
ELECTRIC_ONLY = "electric_only"
GAS_PRIORITY = "gas_priority"
ELECTRIC_PRIORITY = "electric_priority"

BOOST_DELTA = 1.5  # °C: scarto termico per attivare il boost in modalità combined


@dataclass(frozen=True)
class PlantInputs:
    """Parametri immutabili di ingresso per l'arbitraggio termico."""

    demand: float                 # 0.0 - 100.0 dall'aggregatore
    priority: str                 # Modalità priorità impostata
    gas_enabled: bool             # Caldaia a gas abilitata
    hp_enabled: bool              # Pompa di calore abilitata
    hp_available: bool = True     # Entità HP raggiungibile / senza guasto
    solar_surplus: bool = False   # Presenza di surplus fotovoltaico
    max_zone_delta: float = 0.0   # max(target - corrente) sulle zone primarie
    frost_emergency: bool = False # Flag emergenza antigelo attivo


@dataclass(frozen=True)
class PlantCommand:
    """Comandi deterministici in uscita per i generatori."""

    gas_demand: float
    hp_demand: float
    reason: str


def decide_heating(i: PlantInputs) -> PlantCommand:
    """Funzione pura deterministica per l'arbitraggio del riscaldamento."""
    d = max(0.0, min(100.0, float(i.demand)))
    gas = bool(i.gas_enabled)
    hp = bool(i.hp_enabled and i.hp_available)

    if not gas and not hp:
        return PlantCommand(0.0, 0.0, "NO_GENERATOR")

    # 1. Emergenza Antigelo: vince tassativamente su qualsiasi priorità o blocco.
    # Usa qualsiasi generatore disponibile per salvare l'impianto dal gelo.
    if i.frost_emergency:
        return PlantCommand(d if gas else 0.0, d if hp else 0.0, "FROST_ANY_AVAILABLE")

    # 2. Se uno dei due generatori non è disponibile/abilitato:
    if not hp:
        return PlantCommand(d if gas else 0.0, 0.0, "GAS_ONLY_NO_HP")
    if not gas:
        return PlantCommand(0.0, d if hp else 0.0, "HP_ONLY_NO_GAS")

    p = (i.priority or AUTO).lower()

    # 3. Modalità esplicite
    if p == GAS_ONLY:
        return PlantCommand(d, 0.0, "GAS_ONLY")

    if p == GAS_PRIORITY:
        # Opzione 1 Concordata: gas prioritario puro, nessuna commutazione automatica su solare
        return PlantCommand(d, 0.0, "GAS_PRIORITY")

    if p == ELECTRIC_ONLY:
        # Se la PDC è attiva, solo PDC
        return PlantCommand(0.0, d, "ELECTRIC_ONLY")

    if p == ELECTRIC_PRIORITY:
        # PDC per prima; se la PDC non fosse stata disponibile sarebbe già caduta nel ramo `not hp` sopra
        return PlantCommand(0.0, d, "ELECTRIC_PRIORITY")

    if p == COMBINED:
        # Gas come carico base, PDC assist se c'è surplus solare o alto scarto termico
        assist = bool(i.solar_surplus or i.max_zone_delta >= BOOST_DELTA)
        return PlantCommand(
            d,
            d if assist else 0.0,
            "COMBINED_ASSIST" if assist else "COMBINED_BASE",
        )

    # 4. AUTO o HYBRID: usa la Pompa di Calore durante surplus fotovoltaico solare, altrimenti Gas
    if i.solar_surplus:
        return PlantCommand(0.0, d, "SOLAR_SURPLUS_HP")

    return PlantCommand(d, 0.0, "GAS_DEFAULT")
