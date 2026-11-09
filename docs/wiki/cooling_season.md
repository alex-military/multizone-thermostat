# Raffrescamento Estivo & Doppio Binario

<span class="badge-beta">BETA</span>


Con la **Fase 11**, Multizone Thermostat diventa una soluzione completa per tutte e quattro le stagioni, gestendo sia il riscaldamento invernale che il raffrescamento estivo (tramite split ad espansione diretta o pompa di calore idronica reversibile).

---

## 1. Commutazione Stagionale Master (Caldo 🔥 / Freddo ❄️)

Sulla **Global Preset Card** è presente l'interruttore stagionale scorrevole:
* **Inverno (Caldo 🔥)**: Il sistema attiva le logiche di riscaldamento (caldaia, pompe di circolazione, split in caldo).
* **Estate (Freddo ❄️)**: Il sistema attiva le logiche di condizionamento. La caldaia a gas viene bloccata tassativamente a `0%`, mentre le richieste di raffrescamento vengono inviate agli split o alla PDC reversibile.

---

## 2. Architettura a Doppio Binario per i Preset

In inverno e in estate le temperature ideali sono completamente diverse (es. in inverno 20.5°C in Comfort ed Eco a 18°C; in estate Comfort a 24°C ed Eco a 27°C).

Per evitare di dover riconfigurare tutte le temperature a ogni cambio di stagione:
* Il sistema memorizza due binari indipendenti:
  * `presets_heat`: memorizza setpoint e modalità zona per l'inverno.
  * `presets_cool`: memorizza setpoint e modalità zona per l'estate.
* Quando sposti lo switch da Caldo a Freddo, tutte le stanze richiamano istantaneamente i setpoint estivi memorizzati.

---

## 3. Doppio Binario Matematico PID & Autotuning Estivo

Il raffrescamento idronico (impianti radianti a pavimento con deumidificazione o fancoil con acqua fredda a 7–12°C) possiede costanti di tempo e dinamiche di scambio completamente diverse rispetto al riscaldamento invernale con acqua calda a 45–65°C:

* **PID Separati**: Ogni stanza mantiene in memoria due regolatori PID distinti (`_pids_heat` e `_pids_cool`).
* **Autotuning Passivo per il Freddo (`mode="cool"`)**:
  L'osservatore passivo analizza i cicli naturali di discesa della temperatura durante il funzionamento del raffrescamento, calcolando con la curva di reazione di Ziegler-Nichols i guadagni ottimali ($Kp, Ki, Kd$) specifici per l'estate.

---

## 4. Filtro Estivo Automatico delle Schede Lovelace

Nelle abitazioni moderne non tutte le stanze dispongono di climatizzatore (ad esempio ripostigli, disimpegni o bagni hanno spesso solo radiatori invernali).

Grazie al parametro automatico `hide_if_cannot_cool`:
* In modalità estiva, le schede delle stanze che **non dispongono di split o di raffrescamento idronico vengono nascoste automaticamente** dalla dashboard Lovelace.
* Con il ritorno all'inverno, tutte le stanze ricompaiono istantaneamente al loro posto nella griglia.
