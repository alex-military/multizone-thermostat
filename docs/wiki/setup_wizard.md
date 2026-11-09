# Procedura Guidata (Config Flow)

La configurazione iniziale di **Multizone Thermostat** avviene al 100% tramite l'interfaccia grafica di Home Assistant (Config Flow), senza dover modificare file `configuration.yaml`.

---

## Avvio della Procedura
1. Vai in **Impostazioni → Dispositivi e Servizi**.
2. Fai clic su **Aggiungi Integrazione** in basso a destra.
3. Cerca **"Multizone Thermostat"** e selezionalo.

---

## Passaggi della Configurazione

### 1. Selezione Generatori Centrali

<span class="badge-beta">BETA</span>

Puoi selezionare uno o entrambi i generatori termici della casa:
* ☑️ **Caldaia a Gas / Combustibile**: Abilita il supporto a generatori a combustione.
* ☑️ **Pompa di Calore Idronica (PDC)**: Abilita il supporto alla pompa di calore centrale (per impianti bivalenti ibridi o full-electric).

### 1a. Configurazione Caldaia a Gas

<span class="badge-stable">STABILE</span>

* **Modalità Relè (ON/OFF PWM)**: Seleziona l'entità interruttore (`switch.*`) che comanda il consenso caldaia o la pompa di circolazione.
* **Modalità OpenTherm (Modulante)**: Seleziona l'entità gateway OpenTherm (`climate`, `water_heater` o `number`) e imposta i limiti di temperatura dell'acqua di mandata ($T_{\text{min}}$ es. 35°C, $T_{\text{max}}$ es. 75°C).

### 1b. Configurazione Pompa di Calore Idronica

<span class="badge-beta">BETA</span>

* **Tipo di Interfaccia**: `climate` (entità termostato PDC), `switch` (consenso ON/OFF o contatto SG-Ready) o `opentherm`.
* **Range Riscaldamento**: Temperatura mandata min/max (es. 25°C – 55°C).
* **Raffrescamento Idronico Reversibile (`heat_pump_cooling`)**: Abilita l'invio di acqua refrigerata in estate (es. impianto a pavimento con deumidificatori o fancoil), escludendo categoricamente la caldaia a gas.

---

### 2. Creazione della Zona Termica (Stanza)
La schermata di aggiunta zona è suddivisa in sezioni a fisarmonica:

* **Impostazioni Principali**: Nome della stanza, sensore di temperatura principale (`sensor.*`) e temperatura target di base.
* **▶ Teste Termostatiche TRV (Standard)** <span class="badge-stable">STABILE</span>: Assegna una o più valvole TRV (`climate.*`). Il sistema calcola la media e sincronizza i setpoint.
* **▶ Valvole Proporzionali & 0-10V** <span class="badge-stable">STABILE</span>: Per attuatori motorizzati graduali o dimmer 0-10V (`valve` o `number`), con scala in **Percentuale (0–100%)** o **Volt (0.0–10.0 V)**.
* **▶ Attuatori a Relè (PWM)** <span class="badge-stable">STABILE</span>: Relè o testine elettrotermiche ON/OFF pilotate con modulazione proporzionale temporale.
* **▶ Climatizzatore Split d'Ambiente** <span class="badge-beta">BETA</span>:
  * Entità del condizionatore split (`climate.*`).
  * **Ruolo Operativo**: `heat_cool` (tutto l'anno), `heating_only` (solo supporto riscaldamento), `cooling_only` (solo aria condizionata estiva).
  * **Bypass Sonda a Soffitto (Iniezione Sensore Reale)**: Inietta nello split un target ricalcolato per non farlo spegnere per accumulo di aria calda a soffitto.
  * **Quick Heat Boost**: Accende lo split a massima potenza se la stanza parte fredda con $\Delta T \ge 1.5^\circ\text{C}$.
* **▶ Protezioni & Avanzate** <span class="badge-stable">STABILE</span>: Sensori apertura finestre, timeout watchdog sonde wireless, anti-bloccaggio estivo e apporto termico passivo.

---

### 3. Gestione Energetica & Solare

<span class="badge-beta">BETA</span>

Se disponi di impianto fotovoltaico o accumulo a batteria:
* **Sensore Produzione Fotovoltaica**: Potenza istantanea dei pannelli in Watt.
* **Sensore Immissione in Rete**: Potenza esportata (opzionale: non indispensabile per impianti a isola).
* **Sensori Batteria & Protezione Notturna**:
  * Sensore percentuale carica SoC (es. non scaricare sotto l'80% per preservare la notte).
  * Sensore potenza batteria in Watt e **Guardia Anti-Scarica** (torna a gas se la batteria viene scaricata per più di 5 minuti).
* **Integrazione EMHASS / Predbat**: Entità segnale o sensore numerico di carico differibile (`sensor.p_deferrable0 > 0 W`).
* **Offset Accumulo Termico Gratuito**: Aumento setpoint ($0.0^\circ\text{C} \dots +3.0^\circ\text{C}$) durante le ore di sole per immagazzinare calore nei muri.

---

### 4. Impostazioni Globali (Calendario, Meteo, Presenza)
* **Calendario**: Associazione del Calendario Locale per gli orari.
* **Compensazione Climatica**: Sensore temperatura esterna per adattare la mandata in base alla dispersione dell'edificio.
* **Geofencing**: Sensore di presenza per impostare automaticamente il preset Fuori Casa (*Away*) quando tutti escono.
