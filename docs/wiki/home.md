# Multizone Thermostat — Documentazione Ufficiale

Benvenuto nella Wiki e documentazione ufficiale di **Multizone Thermostat**, l'integrazione personalizzata completa per Home Assistant che trasforma la gestione termica della tua casa in un orchestratore autonomo e intelligente.

<div class="callout-beta">
  <strong>Attenzione: Funzionalità Beta (Fase 11 / v6.1.0-beta)</strong><br>
  Le sezioni contrassegnate con il badge <span class="badge-beta">BETA</span> descrivono le nuove funzionalità bivalenti, split AC, gestione solare off-grid e commutazione estiva attualmente disponibili sul ramo <code>beta</code> in preparazione al rilascio stabile.
</div>

---

## 🌟 Caratteristiche Principali

| Funzionalità | Stato | Descrizione |
|---|:---:|---|
| **Centrale Bivalente (Caldaia + Pompa di Calore)** | <span class="badge-beta">BETA</span> | Arbitraggio intelligente tra caldaia a gas e PDC idronica con 5 priorità operative. |
| **Climatizzatori Split AC d'Ambiente** | <span class="badge-beta">BETA</span> | Associazione split per stanza, bypass sonda a soffitto e Quick Heat Boost termico. |
| **Surplus Solare & Protezione Batterie Off-Grid** | <span class="badge-beta">BETA</span> | Algoritmo anti-clipping inverter, blocco anti-scarica batteria e bridge EMHASS/Predbat. |
| **Raffrescamento Estivo & Doppio Binario** | <span class="badge-beta">BETA</span> | Regolazione caldo/freddo, memorie preset isolate e doppio PID con autotuner per il freddo. |
| **Autotuning Dinamico (Hysteresis → PID)** | <span class="badge-stable">STABILE</span> | Apprendimento automatico della dispersione termica e transizione a PID senza oscillazioni. |
| **Valvole Proporzionali & 0-10V Analogiche** | <span class="badge-stable">STABILE</span> | Apertura continua per riscaldamento a pavimento, fancoil e TRV direct-pin senza PWM. |
| **Doppio Comando Caldaia (Relè PWM / OpenTherm)** | <span class="badge-stable">STABILE</span> | Calcolo temperatura di mandata scorrevole o cicli PWM con rispetto anti-short-cycle. |
| **Programmazione Settimanale & Smart Return** | <span class="badge-stable">STABILE</span> | Timeline 24h a matrice, gestione multi-profilo e radar termico predittivo di rientro. |
| **Sorveglianza Anomalie Meccaniche** | <span class="badge-stable">STABILE</span> | Rilevamento automatico valvole bloccate, trafilamenti di calore e aria nei radiatori. |
| **Schede Lovelace Visual Twin** | <span class="badge-stable">STABILE</span> | Parità estetica 1-a-1 con il termostato nativo Home Assistant, touch arco e pulsanti step. |

---

## 🗺️ Architettura Generale

```mermaid
flowchart TD
    Sensori["Sensori Ambiente & Finestre"] --> Coordinatore["Multizone Coordinator"]
    Coordinatore --> Autotuner{"Autotuner: Addestrato?"}
    Autotuner -->|No| Isteresi["Algoritmo a Isteresi"]
    Autotuner -->|Si| PID["Algoritmo PID"]
    Isteresi --> Fabbisogno["Calcolo Fabbisogno % 0-100%"]
    PID --> Fabbisogno
    Fabbisogno --> SplitCheck{"Stanza ha Split AC?"}
    SplitCheck -->|"Si + Surplus Solare"| SplitRun["Avvio Split Elettrico<br>Azzeramento Gas a 0%"]
    SplitCheck -->|"No o Senza Sole"| PlantOrch["Plant Orchestrator"]
    PlantOrch --> Caldaia["Caldaia Gas: Relè PWM / OpenTherm"]
    PlantOrch --> PDC["Pompa di Calore Idronica"]
    Coordinatore --> EnergyMgr["Energy Manager: Fotovoltaico & Batterie"]
    EnergyMgr -->|"Controllo Surplus / Clipping"| SplitCheck
```
