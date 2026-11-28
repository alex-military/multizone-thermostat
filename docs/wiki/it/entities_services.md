# Entità Generate & Servizi Esposti

Una panoramica esaustiva di tutte le entità create automaticamente da **Multizone Thermostat** all'interno di Home Assistant e dei servizi richiamabili tramite script e automazioni.

---

## 1. Entità Master (Supervisione Generale Impianto)

Queste entità coordinano lo stato globale dell'abitazione, i parametri di sicurezza e le modalità operative:

| Entity ID (Esempio) | Dominio | Tipo / Range | Descrizione |
|---|---|---|---|
| `switch.master_control_heating_master` | Switch | `on` / `off` | **Interruttore Master Generale**: spegne o accende l'intera termoregolazione dell'edificio. |
| `switch.master_control_weekly_scheduler` | Switch | `on` / `off` | Abilita o sospende la programmazione oraria settimanale integrata. |
| `switch.master_control_allow_split_heating` | Switch | `on` / `off` | <span class="badge-beta">BETA</span> Consente o inibisce l'uso degli split elettrici in riscaldamento. |
| `switch.master_control_allow_split_cooling` | Switch | `on` / `off` | <span class="badge-beta">BETA</span> Consente o inibisce l'uso degli split elettrici in condizionamento estivo. |
| `switch.master_control_anti_seize_summer_protection` | Switch | `on` / `off` | Abilita l'esercizio periodico estivo anti-bloccaggio delle valvole idroniche. |
| `switch.master_control_anti_frost_protection` | Switch | `on` / `off` | Protezione antigelo di emergenza (forza l'accensione se una stanza scende sotto soglia). |
| `switch.time_geofencing_geofencing` | Switch | `on` / `off` | Abilita la transizione automatica al preset *Away* all'uscita di tutti gli occupanti. |
| `switch.time_geofencing_auto_night_mode` | Switch | `on` / `off` | Abilita il passaggio orario automatico al preset *Sleep*. |
| `time.time_geofencing_night_time` | Time | `HH:MM` (default: `22:30`) | Orario di attivazione automatica della modalità Notte (*Sleep*). |
| `time.time_geofencing_morning_time` | Time | `HH:MM` (default: `07:00`) | Orario mattutino di uscita dalla modalità Notte. |
| `select.master_control_heat_source_priority` | Select | `auto`, `hybrid`, `combined`, `electric_only`, `gas_only`, `gas_priority`, `electric_priority` | <span class="badge-beta">BETA</span> Arbitraggio delle sorgenti di calore tra caldaia a gas e pompa di calore / split (7 modalità). |
| `select.master_control_master_operation_mode` | Select | `heat`, `cool` | <span class="badge-beta">BETA</span> Commutazione stagionale tra Riscaldamento e Raffrescamento. |
| `select.master_control_global_preset` | Select | `manual`, `eco`, `comfort`, `sleep`, `away` | Selettore globale del profilo di temperatura della casa. |
| `select.master_control_demand_strategy` | Select | `max`, `weighted_average`, `sum_capped` | Formula di calcolo del fabbisogno termico centrale aggregato. |
| `select.master_control_schedule_profile` | Select | ID Profili | Profilo settimanale attivo (`Standard`, `Smart Working`, `Holiday` o personalizzati). |
| `number.master_control_min_cycle_on` | Number | `0–60` min (default: `5`) | Durata minima di marcia continua del bruciatore (protezione anti-pendolamento). |
| `number.master_control_min_cycle_off` | Number | `0–60` min (default: `5`) | Durata minima di riposo della caldaia prima di una riaccensione. |
| `number.master_control_heat_pump_min_cycle_on` | Number | `0–30` min (default: `5`) | <span class="badge-beta">BETA</span> Durata minima di marcia continua del compressore della Pompa di Calore. |
| `number.master_control_heat_pump_min_cycle_off` | Number | `0–30` min (default: `5`) | <span class="badge-beta">BETA</span> Durata minima di riposo del compressore della Pompa di Calore. |
| `number.master_control_valve_delay` | Number | `0–300` sec (default: `0`) | Ritardo avvio circolatore per attendere la completa apertura meccanica delle valvole (eseguito dopo la guardia automatica TRV `HOLD_TRV_CLOSED` fino a 120 s). |
| `number.master_control_anti_seize_idle_days` | Number | `1–30` giorni (default: `15`) | Giorni di inattività prima di avviare il ciclo anti-bloccaggio estivo. |
| `number.master_control_anti_seize_duration` | Number | `1–15` min (default: `2`) | Durata in minuti dell'apertura completa delle valvole durante l'anti-seize. |
| `number.master_control_weather_curve` | Number | `0.0–3.0` (default: `1.0`) | Coefficiente moltiplicatore della curva climatica esterna (`0.0` disabilita il feed-forward). |
| `number.master_control_anti_frost_temperature` | Number | `5.0–16.0 °C` (default: **`12.0`**) | Temperatura soglia di emergenza sotto la quale scatta il riscaldamento forzato antigelo. |
| `number.master_control_frost_protection_flow_temp` | Number | `25.0–55.0 °C` (default: `40.0`) | Temperatura di mandata configurabile durante l'emergenza antigelo (impianti modulanti/PDC). |
| `sensor.master_control_master_demand` | Sensor | `0.0–100.0%` | Fabbisogno centrale aggregato dell'impianto (attivo sia in `heat` sia in `cool`). |
| `sensor.master_control_plant_health_status` | Sensor | `Optimal`, `Warning`, `Critical` | Stato globale della salute dell'impianto idraulico e motivazioni diagnostiche. |
| `sensor.master_control_boiler_cycles_per_hour` | Sensor | cicli/ora | Frequenza oraria delle accensioni con allarme short-cycle (`> 5 c/h`). |
| `sensor.master_control_boiler_daily_runtime_24h` | Sensor | ore | Tempo totale cumulativo di attività della caldaia/PDC nelle ultime 24 ore. |
| `binary_sensor.master_control_plant_anomaly` | Binary Sensor | `on` / `off` | Attivo (`on`) in presenza di anomalie idrauliche o telemetriche attive in casa. |

---

## 2. Entità di Singola Zona Termica

Tutte le entità di stanza (eccetto `climate.*`) sono raggruppate sotto il dispositivo dedicato alla singola zona (`Zona <Nome>`, generando entity ID `zona_<nome>_*`), suddivise nelle categorie **Controlli**, **Configurazione** e **Diagnostica**:

| Entity ID (Esempio per "Salone") | Dominio / Categoria | Tipo / Valori | Descrizione |
|---|---|---|---|
| `climate.multizone_thermostat_salone` | Climate (Controllo) | hvac_modes, setpoint, presets | **Termostato Principale di Stanza**: regola temperatura (step configurabile `target_temp_step`: `0.5°` o `0.1°`), modalità HVAC ed espone gli attributi TRV e PID (`trv_calibration_mode`, `trv_sensor_selects`, `trv_control_mode`, `trv_open_boost`, `trv_close_offset`, `trv_demand_valve_open`, `pid_kp`, `pid_ki`, `pid_kd`, `active_heating_source`, `safety_fallback_active`, `local_pwm_active`). |
| `select.zona_salone_mode` | Select (Controllo) | `primary`, `secondary`, `bypass` | **Ruolo Termico della Stanza**: determina se la stanza comanda l'accensione della caldaia. |
| `switch.zona_salone_pid_manual_unlock` | Switch (Config) | `on` / `off` | Sblocca la modifica manuale dei parametri PID stagionali (`Kp`, `Ki`, `Kd`). Bloccato di default. |
| `number.zona_salone_pid_kp` / `ki` / `kd` | Number (Config) | `Kp: 0.1–500`, `Ki: 0.0–10.0`, `Kd: 0.0–50000` | Guadagni PID stagionali della stanza per la stagione attiva (`heat` o `cool`). |
| `button.zona_salone_reset_autotuner` | Button (Config) | press | Resetta l'autotuner della sola stagione attiva (salvando un backup) e riblocca `PID Manual Unlock`. |
| `switch.zona_salone_physical_controls_sync` | Switch (Config) | `on` / `off` | Sincronizzazione bidirezionale se qualcuno modifica manualmente la manopola fisica della valvola TRV. |
| `switch.zona_salone_passive_heat` | Switch (Config) | `on` / `off` | Modalità apporto passivo (sopprime falsi allarmi *ghost heating* su open space). |
| `sensor.zona_salone_demand` | Sensor (Diagnostica) | `0.0–100.0%` | Fabbisogno termico istantaneo (Isteresi o PID). Espone live negli attributi `p_term`, `i_term`, `d_term`, `integral_accumulator`, `error`, `set_point`, `raw_output`, `clamped_output`, `kp`, `ki`, `kd`, `control_mode`, `weather_ff`, `smart_stop_offset`, `window_open` e `active_track`. |
| `sensor.zona_salone_autotuning` | Sensor (Diagnostica) | stato e parametri | Stato apprendimento SIMC, guadagni PID (`Kp`, `Ki`, `Kd`) e `weekly_guardrail_status` (`idle`, `monitoring`, `confirmed`, `reverted`). |
| `sensor.zona_salone_heating_rate` | Sensor (Diagnostica) | `°C/hr` (`°F/hr`) | Pendenza $R$ misurata durante la fase di riscaldamento a pieno carico. |
| `sensor.zona_salone_cooling_rate` | Sensor (Diagnostica) | `°C/hr` (`°F/hr`) | Tasso di dispersione naturale $D$ o velocità di raffrescamento attivo. |
| `sensor.zona_salone_thermal_inertia` | Sensor (Diagnostica) | **`°C` (`°F`)** | Stima delta di inerzia termica post-spegnimento. |
| `sensor.zona_salone_energy_class` | Sensor (Diagnostica) | `A4, A, B, C, D, E, F, G` | Classe energetica stimata dell'involucro (basata su `k_loss` di Newton indipendente dal meteo, con filtro spifferi e auto-riparazione all'avvio). |
| `sensor.zona_salone_thermal_retention_time` | Sensor (Diagnostica) | ore (`h`) | Ore necessarie all'ambiente per perdere `1.0 °C` in assenza di riscaldamento. |
| `sensor.zona_salone_radiator_sizing` | Sensor (Diagnostica) | `Undersized`, `Optimal`, `Oversized` | Valutazione quantitativa della potenza dei corpi scaldanti rispetto al volume della stanza. |
| `binary_sensor.zona_salone_anomaly` | Binary Sensor (Diagnostica) | `on` / `off` | Segnala anomalie locali (`stuck_closed`, `trv_not_opening`, `ghost_heating`, `overshoot`, `stale_sensor`, `sensor_fault`). |

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
Aggiorna in memoria la temperatura (`5.0–95.0`) associata a un preset (`manual`, `comfort`, `eco`, `sleep`, `away`) per una specifica zona termica senza dover riavviare Home Assistant:

```yaml
service: multizone_thermostat.set_preset_temperature
data:
  entity_id: climate.multizone_thermostat_camera
  preset: comfort
  temperature: 20.5
  hvac_mode: heat # Opzionale: 'heat' o 'cool'
```

---

### `multizone_thermostat.set_pid_parameters`
Imposta manualmente i guadagni PID stagionali (`kp`: `0.1–500.0`, `ki`: `0.0–10.0`, `kd`: `0.0–50000.0`), sblocca/blocca la modifica manuale (`lock_parameter` tra `Kp`/`Ki`/`Kd`/`all`, `unlock`) o esegue il seeding della baseline Auto EMA (`seed_autotuner`):

> **Scala PID:** I guadagni lavorano su uscita `0–100%` e `dt` in secondi (es. `kp: 100.0` equivale al `100%` di domanda per `1 °C` di errore). Impostando `kd: 0.0` con `seed_autotuner: true` si mantiene il controllo PI puro: il raffinamento settimanale EMA preserva `Kd = 0.0`.

```yaml
service: multizone_thermostat.set_pid_parameters
data:
  climate_entity: climate.multizone_thermostat_salone # Accetta anche lista legacy entity_id
  mode: heat            # Opzionale: 'heat' o 'cool' (default: stagione attiva)
  seed_autotuner: false # Opzionale: true per applicarli come baseline Auto EMA appresa
  unlock: true          # Opzionale: sblocca/blocca esplicitamente la modifica manuale
  lock_parameter: all   # Opzionale: ripristina 'Kp', 'Ki', 'Kd' o 'all' dall'autotuner
  kp: 35.0
  ki: 0.015
  kd: 150.0
```

---

### `multizone_thermostat.reset_autotune`
Resetta l'autotuner passivo per una o più zone sulla stagione indicata (salvando prima un backup automatico) e riblocca `PID Manual Unlock` salvo `keep_manual_overrides: true`:

```yaml
service: multizone_thermostat.reset_autotune
data:
  climate_entity: climate.multizone_thermostat_salone # Accetta anche lista legacy entity_id
  keep_manual_overrides: false # Opzionale: mantieni override manuali dopo il reset
  mode: heat                   # Opzionale: 'heat' o 'cool'
```

---

### `multizone_thermostat.restore_autotune`
Ripristina i parametri Smart PID appresi e i cicli salvati prima dell'ultimo reset dell'autotuner:

```yaml
service: multizone_thermostat.restore_autotune
data:
  climate_entity: climate.multizone_thermostat_salone
  keep_manual_overrides: false # Opzionale: mantieni eventuali override manuali
  mode: heat                   # Opzionale: 'heat' o 'cool'
```

---

### `multizone_thermostat.duplicate_schedule_profile`
Duplica un profilo di programmazione settimanale esistente con un nuovo ID e nome:

```yaml
service: multizone_thermostat.duplicate_schedule_profile
data:
  source_profile_id: standard
  target_profile_id: smart_working
  target_name: "Smart Working"
```
