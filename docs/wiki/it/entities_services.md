# Entità Generate & Servizi Esposti

Una panoramica esaustiva di tutte le entità create automaticamente da **Multizone Thermostat** all'interno di Home Assistant e dei servizi richiamabili tramite script e automazioni.

---

## 1. Entità Master (Supervisione Generale Impianto)

Queste entità coordinano lo stato globale dell'abitazione, i parametri di sicurezza e le modalità operative:

| Entity ID (Esempio) | Dominio | Tipo / Range | Descrizione |
|---|---|---|---|
| `switch.master_control_heating_master` | Switch | `on` / `off` | **Interruttore Master Generale**: spegne o accende l'intera termoregolazione dell'edificio. |
| `switch.master_control_allow_split_heating` | Switch | `on` / `off` | <span class="badge-beta">BETA</span> Consente o inibisce l'uso degli split elettrici in riscaldamento. |
| `switch.master_control_allow_split_cooling` | Switch | `on` / `off` | <span class="badge-beta">BETA</span> Consente o inibisce l'uso degli split elettrici in condizionamento estivo. |
| `switch.master_control_anti_seize_summer_protection` | Switch | `on` / `off` | Abilita l'esercizio periodico estivo anti-bloccaggio delle valvole idroniche. |
| `switch.master_control_anti_frost_protection` | Switch | `on` / `off` | Protezione antigelo di emergenza (forza l'accensione se una stanza scende sotto soglia). |
| `switch.time_geofencing_geofencing` | Switch | `on` / `off` | Abilita la transizione automatica al preset *Away* all'uscita di tutti gli occupanti. |
| `switch.time_geofencing_auto_night_mode` | Switch | `on` / `off` | Abilita il passaggio orario automatico al preset *Sleep*. |
| `select.master_control_heat_source_priority` | Select | `auto`, `hybrid`, `combined`, `electric_only`, `gas_only` | <span class="badge-beta">BETA</span> Arbitraggio delle sorgenti di calore tra caldaia a gas e pompa di calore / split. |
| `select.master_control_master_operation_mode` | Select | `heat`, `cool` | <span class="badge-beta">BETA</span> Commutazione stagionale tra Riscaldamento e Raffrescamento. |
| `select.master_control_global_preset` | Select | `manual`, `eco`, `comfort`, `sleep`, `away` | Selettore globale del profilo di temperatura della casa. |
| `select.master_control_demand_strategy` | Select | `max`, `weighted_average`, `sum_capped` | Formula di calcolo del fabbisogno termico centrale aggregato. |
| `number.master_control_min_cycle_on` | Number | 1 – 30 min (default: 5) | Durata minima di marcia continua del bruciatore (protezione anti-pendolamento). |
| `number.master_control_min_cycle_off` | Number | 1 – 30 min (default: 5) | Durata minima di riposo della caldaia prima di una riaccensione. |
| `number.master_control_valve_delay` | Number | 0 – 300 sec (default: 0) | Ritardo avvio circolatore per attendere la completa apertura meccanica delle valvole. |
| `number.master_control_anti_seize_idle_days` | Number | 1 – 60 giorni (default: 15) | Giorni di inattività prima di avviare il ciclo anti-bloccaggio estivo. |
| `number.master_control_anti_seize_duration` | Number | 1 – 15 min (default: 2) | Durata in minuti dell'apertura completa delle valvole durante l'anti-seize. |
| `number.master_control_weather_curve` | Number | 0.0 – 3.0 (default: 0.0) | Coefficiente moltiplicatore della curva climatica esterna (feed-forward). |
| `number.master_control_anti_frost_temperature` | Number | 3.0 – 12.0 °C (default: 7.0) | Temperatura soglia di emergenza sotto la quale scatta il riscaldamento forzato antigelo. |
| `sensor.master_control_stato_salute_impianto` | Sensor | 0 – 100% | Indice diagnostico globale della salute dell'impianto idraulico. |
| `sensor.master_control_frequenza_accensioni_caldaia` | Sensor | cicli/ora | Frequenza oraria delle accensioni del bruciatore con allarme short-cycle (> 5 c/h). |
| `sensor.master_control_ore_funzionamento_caldaia_24h` | Sensor | ore | Tempo totale cumulativo di attività della caldaia nelle ultime 24 ore. |
| `binary_sensor.master_control_plant_anomaly` | Binary Sensor | `on` / `off` | Attivo (`on`) in presenza di anomalie idrauliche o telemetriche attive in casa. |

---

## 2. Entità di Singola Zona Termica

Create per ogni stanza configurata all'interno del sistema:

| Entity ID (Esempio per "Salone") | Dominio | Tipo / Valori | Descrizione |
|---|---|---|---|
| `climate.multizone_thermostat_salone` | Climate | hvac_modes, setpoint, presets | **Termostato Principale di Stanza**: regola temperatura, modalità HVAC e visualizza lo stato. |
| `select.zone_modes_salone_mode` | Select | `primary`, `secondary`, `bypass` | **Ruolo Termico della Stanza**: determina se la stanza comanda l'accensione della caldaia. |
| `switch.zone_modes_sync_controlli_fisici_salone` | Switch | `on` / `off` | Sincronizzazione bidirezionale se qualcuno modifica manualmente la manopola fisica della valvola TRV. |
| `switch.zone_modes_apporto_passivo_salone` | Switch | `on` / `off` | Modalità apporto passivo (la stanza riceve calore senza richiedere esplicitamente accensione alla caldaia). |
| `sensor.multizone_brain_salone_fabbisogno` | Sensor | 0.0 – 100.0% | Fabbisogno termico istantaneo calcolato dall'algoritmo (Isteresi o PID). |
| `sensor.multizone_brain_salone_autotuning` | Sensor | stato e parametri | Stato del motore di auto-apprendimento e guadagni PID correnti ($Kp, Ki, Kd$). |
| `sensor.multizone_brain_salone_velocita_riscaldamento`| Sensor | °C/ora | Pendenza $R$ misurata durante la fase di riscaldamento a pieno carico. |
| `sensor.multizone_brain_salone_dispersione` | Sensor | °C/ora | Tasso di dispersione termica naturale $D$ a riscaldamento spento. |
| `sensor.multizone_brain_salone_inerzia_termica` | Sensor | minuti | Stima dell'inerzia termica della stanza per il calcolo anticipato dello Smart Return. |
| `sensor.multizone_brain_salone_classe_energetica` | Sensor | A4, A, B, C, D, E, F, G | Classe energetica stimata dell'involucro edilizio della stanza. |
| `sensor.multizone_brain_salone_tempo_ritenzione_termica` | Sensor | ore | Ore necessarie all'ambiente per perdere $1.0^\circ\text{C}$ in assenza di riscaldamento. |
| `sensor.multizone_brain_salone_dimensionamento_radiatore`| Sensor | Sottodimensionato, Ottimale, Sovradimensionato | Valutazione quantitativa della potenza dei corpi scaldanti rispetto al volume della stanza. |
| `binary_sensor.heating_zones_salone_anomaly` | Binary Sensor | `on` / `off` | Segnala anomalie idrauliche locali (valvola bloccata, trafilamento di calore o perdita sensore). |

---

## 3. Servizi Esposti per Automazioni & Script

Multizone Thermostat registra una serie di servizi avanzati per consentire il controllo programmatico da automazioni, pulsanti fisici, tag NFC o assistenti vocali.

### `multizone_thermostat.set_master_operation_mode`
<span class="badge-beta">BETA</span>

Commuta la modalità di funzionamento globale dell'abitazione tra Riscaldamento invernale e Raffrescamento estivo, applicando istantaneamente il cambio di preset e il ricarico dei guadagni PID dedicati.

```yaml
service: multizone_thermostat.set_master_operation_mode
data:
  operation_mode: cool   # 'heat' oppure 'cool'
```

---

### `multizone_thermostat.set_smart_return`
Pianifica un rientro a casa intelligente. L'integrazione calcola l'anticipo di accensione differenziato stanza per stanza basandosi sulla velocità di riscaldamento (°C/ora) appresa dall'autotuner:

```yaml
service: multizone_thermostat.set_smart_return
data:
  arrival_time: "18:30"             # Orario previsto in formato HH:MM o ISO datetime
  preset: comfort                   # Preset desiderato al rientro (comfort, eco, ecc.)
  zones:                            # Opzionale: limita il rientro a specifiche zone
    - climate.multizone_thermostat_salone
    - climate.multizone_thermostat_camera
```

---

### `multizone_thermostat.cancel_smart_return`
Annulla immediatamente qualsiasi pianificazione di rientro intelligente attiva, ripristinando il normale stato precedente.

```yaml
service: multizone_thermostat.cancel_smart_return
```

---

### `multizone_thermostat.activate_schedule_profile`
Attiva istantaneamente un profilo orario settimanale, con la possibilità di impostare una scadenza temporale dopo la quale il sistema torna automaticamente al profilo standard.

```yaml
service: multizone_thermostat.activate_schedule_profile
data:
  profile_id: smart_working
  expires_at: "2026-11-15T19:00:00"   # Opzionale: torna al fallback a quest'ora
  fallback_profile: standard
```

---

### `multizone_thermostat.save_schedule_profile`
Salva o aggiorna la programmazione oraria per i giorni della settimana via codice:

```yaml
service: multizone_thermostat.save_schedule_profile
data:
  profile_id: standard
  name: "Programmazione Standard"
  baseline_preset: eco
  days:
    mon:
      climate.multizone_thermostat_salone:
        - start: "06:30"
          end: "08:30"
          preset: comfort
        - start: "17:00"
          end: "22:30"
          preset: comfort
```

---

### `multizone_thermostat.clear_zone_override`
Rimuove qualsiasi temperatura forzata manualmente su una stanza, riagganciando la zona al preset orario o globale corrente:

```yaml
service: multizone_thermostat.clear_zone_override
data:
  entity_id: climate.multizone_thermostat_salone   # Ometti per resettare tutte le zone
```

---

### `multizone_thermostat.set_preset_temperature`
Aggiorna in memoria la temperatura associata a un preset per una specifica zona termica senza dover riavviare Home Assistant:

```yaml
service: multizone_thermostat.set_preset_temperature
data:
  entity_id: climate.multizone_thermostat_camera
  preset: comfort
  temperature: 20.5
```
