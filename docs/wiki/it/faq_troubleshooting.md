# Risoluzione Problemi & Domande Frequenti (FAQ)

Una guida pratica per risolvere dubbi frequenti, diagnosticare comportamenti anomali e verificare il corretto funzionamento del tuo impianto.

---

## ❓ Domande Frequenti

### 1. Perché il pulsante dello split nella Dial Card è disabilitato (grigio con lucchetto)?
<span class="badge-beta">BETA</span>

Il pulsante centrale per l'avvio manuale dello split è **progettato per funzionare a Master Spento (OFF)**.
* Quando il Master generale è **acceso (ON)**, l'intera casa è gestita dal `PlantOrchestrator` e dall'algoritmo globale. Per prevenire conflitti termici o spegnimenti accidentali da parte di altri membri della famiglia, il pulsante viene bloccato con un tooltip esplicativo.
* A **Master spento**, il pulsante torna immediatamente interattivo: premendolo, si accende unicamente lo split di quella stanza per un comfort rapido, lasciando la caldaia a gas rigorosamente spenta.

---

### 2. In estate alcune card delle stanze sono scomparse dalla dashboard: come mai?
<span class="badge-beta">BETA</span>

Questo comportamento è gestito dal filtro intelligente `hide_if_cannot_cool: true`:
* Se una stanza (ad esempio un corridoio, un bagno o un ripostiglio) dispone **soltanto di radiatori invernali** e non possiede né uno split né un impianto a pavimento reversibile, la card viene nascosta per mantenere la vista estiva snella e focalizzata sulle sole stanze climatizzate.
* Commutando nuovamente lo switch stagionale su **Caldo 🔥**, tutte le stanze ricompaiono immediatamente nella griglia.
* Se desideri vedere sempre tutte le card anche in estate, imposta `hide_if_cannot_cool: false` nella configurazione YAML della card.

---

### 3. Come mai la caldaia a gas si è riaccesa anche se c'era il sole?
<span class="badge-beta">BETA</span>

Il motore di gestione energetica include la **Guardia Anti-Scarica della Batteria (`battery_max_discharge_time`)**:
* Se il passaggio improvviso di una nuvola densa o l'accensione simultanea di elettrodomestici energivori (forno, piano a induzione, lavatrice) costringe la casa a prelevare energia dalla batteria domestica (scarica continua $> 150\text{ W}$) per più di 5 minuti:
* Il sistema **interrompe immediatamente il surplus elettrico e riaccende la caldaia a gas**, per preservare l'autonomia della batteria in vista delle ore serali e notturne.

---

### 4. La valvola TRV segna una temperatura diversa rispetto al termometro a parete: cosa fare?
Le valvole termostatiche montate a pochi centimetri dal radiatore risentono inevitabilmente dell'aria calda che sale dal corpo scaldante.
* Assegna il termometro ad altezza uomo come **Sensore Principale** (`temp_sensor`) della stanza.
* Nella sezione **Calibrazione TRV**, configura `trv_calibration_mode` (`"auto"` default, `"offset"` oppure `"external"`):
  * In `"auto"`, l'integrazione rileva automaticamente `external_temperature_input` nell'ID dell'entità di calibrazione; altrimenti usa la modalità offset.
  * In `"external"` (es. Sonoff TRVZB, Aqara, Tuya/Zigbee2MQTT con `number.*external_temperature_input`), scrive direttamente la temperatura della sonda ambiente in °C (arrotondata allo step, limitata a min/max) con heartbeat anti-offline ogni `1200 s` (20 min) e rate-limit jitter di `60 s` su variazioni `<= 0.1 °C`.
* Opzionalmente associa ogni TRV `climate.*` alla sua entità `select.*` tramite `trv_sensor_selects`: la TRV passerà al sensore esterno/remoto quando attivo (escludendo opzioni `"offline"` come `remote_source_offline`) e tornerà al sensore interno/locale se si attiva `safety_fallback_active`.

---

### 5. Quanto tempo impiega l'Autotuner per passare da Isteresi a PID?
* L'autotuner necessita di osservare **almeno 2 o 3 cicli completi di riscaldamento naturale** (salita a regime con pendenza definita seguita da spegnimento con dispersione naturale).
* In un impianto a radiatori standard, la transizione avviene tipicamente entro **24–48 ore** di normale utilizzo, senza alcun intervento manuale. Lo stato dell'apprendimento è visibile nell'entità `sensor.multizone_brain_[stanza]_autotuning`.

---

### 6. Perché la mia TRV intelligente chiude troppo presto prima che la stanza raggiunga il target? (Modalità Demand-Driven)
Molte TRV usano un regolatore proporzionale interno che strozza la valvola troppo presto quando il radiatore si scalda.
* Imposta `trv_control_mode` su `"demand_driven"` (rispetto a `"standard"` di default) e regola `trv_open_boost` (default `+1.5 °C`, intervallo `0.0–5.0 °C`) e `trv_close_offset` (default `1.0 °C`, intervallo `0.0–5.0 °C`).
* La zona usa l'isteresi sulla domanda PID (`>= 5.0%` apre, `<= 0.0%` chiude), debounce anti-oscillazione di `60 s`, tick di valutazione ogni `10 s` e guardia idle anti-chatter.
* L'apertura usa **Smart Bounded Overdrive** (`min(trv_max, room_temp + trv_open_boost, zone_target + trv_open_boost)`, mai un valore fisso a 30 °C); la chiusura usa `max(trv_min, min(zone_target, room_temp - trv_close_offset))`.
* È compatibile con i delta relativi di `physical_sync` e torna automaticamente a `"standard"` se si attiva `safety_fallback_active` (sonda stanza scaduta o non disponibile).

---

### 7. Cosa significano `HOLD_TRV_CLOSED` e l'anomalia `trv_not_opening`?
* **`HOLD_TRV_CLOSED` (Guardia Idraulica di Centrale)**: `HOLD_TRV_CLOSED` sospende automaticamente l'avvio del generatore fino a **max 120 s** mentre le TRV delle zone in richiesta risultano chiuse—controllando gli attributi di posizione (`position`, `valve_position`, `pi_heating_demand`, `heating_demand` > 10%) e il fallback `hvac_action` (`"heating"` vs `"idle"`/`"off"`)—seguito dall'eventuale ritardo motorizzato `valve_delay` (`number.master_control_valve_delay`) se `> 0 s`. Si applica a **Caldaia a Relè** e **OpenTherm solo a freddo (cold-start)** (non spegne mai un bruciatore già acceso).
* **`trv_not_opening` (*"TRV valve not opening despite active zone heating demand"*)**: Allarme diagnostico **non bloccante** attivato quando la richiesta di zona è `> 20%` e il generatore centrale è attivo (`boiler_on`) per `> 5` minuti mentre tutte le TRV della zona risultano chiuse/`idle`, così la centrale continua a servire le altre stanze.

---

## 🛠️ Guida alla Diagnostica & Debug

### Abilitazione dei Log Dettagliati
Se desideri visualizzare nei registri di Home Assistant ogni decisione presa dal `PlantOrchestrator`, dall'`EnergyManager` o dal regolatore PID, inserisci questo blocco nel tuo file `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.multizone_thermostat: debug
```

Dopo aver salvato, riavvia Home Assistant e accedi a **Impostazioni → Sistema → Registri**.

---

### Tabella degli Errori Noti & Risoluzioni

| Sintomo | Possibile Causa | Soluzione Consigliata |
|---|---|---|
| Lo split riceve il comando di accensione ma non parte | L'entità del condizionatore split non supporta il modo `heat` o `cool` inviato | Controlla gli `hvac_modes` supportati dalla tua entità split nativa in **Strumenti per sviluppatori → Stati**. Verifica che sia impostato `split_role: heat_cool`. |
| La caldaia a gas si accende e si spegne a intervalli troppo brevi | Isteresi troppo stretta o tempi di ciclo non rispettati | Aumenta `number.master_control_min_cycle_on` e `min_cycle_off` ad almeno 5–7 minuti. |
| Errore "Impossibile caricare la risorsa Lovelace" | Cache del browser non aggiornata dopo il download del bundle | Esegui un aggiornamento forzato della pagina premendo `Ctrl + F5` (o `Cmd + Shift + R` su Mac) oppure svuota la cache dell'app Home Assistant Companion. |
| Segnalazione di "Valvola Bloccata Chiusa" | La stanza richiede calore da più di 45 minuti ma la temperatura ambiente cala | Verifica che la batteria della valvola TRV non sia esaurita, che il pistoncino meccanico non sia grippato dal calcare o che la pompa del collettore stia girando. |
| `HOLD_TRV_CLOSED` ritarda l'avvio caldaia | Le TRV della zona in richiesta risultano ancora chiuse (`<= 10%` o `idle`/`off`) | `HOLD_TRV_CLOSED` trattiene l'avvio fino a max 120 s in attesa apertura TRV, poi applica l'eventuale `valve_delay` (> 0 s); verifica reattività TRV e `trv_control_mode`. |
| Allarme diagnostico `trv_not_opening` | Richiesta zona > 20% e `boiler_on` > 5 min con tutte le TRV chiuse/`idle` | Allarme non bloccante: controlla batterie TRV, copertura Zigbee/Thread, spillo valvola o entità `trv_sensor_selects` / calibrazione. |
| Pressione OpenTherm sotto 0.8 Bar | Perdita d'acqua nel circuito o vaso di espansione scarico | Reintegrare l'acqua tramite il rubinetto di carico della caldaia fino a raggiungere 1.2–1.5 Bar. |
