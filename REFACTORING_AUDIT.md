# 🕵️‍♂️ Refactoring Audit & Issues Report

Questo documento raccoglie i bug, i problemi architetturali e le ottimizzazioni individuati durante il check file-by-file post-refactoring.

## 📁 `demand_aggregator.py`
**Stato:** Analizzato
**Problemi e Ottimizzazioni rilevati:**

1.  **List Comprehension illeggibile e subottimale (`calculate`)**
    Alle righe 362-366, nella logica per la strategia `WEIGHTED_AVERAGE`, la variabile `active_items` viene costruita con una list comprehension molto complessa usando `zip` e array temporanei. 
    *Soluzione proposta:* Riscrivere il ciclo in modo esplicito e lineare iterando semplicemente su `zone_entries` per migliorare la leggibilità e l'efficienza.
2.  **Perdita di Configurazione (Parametri ignorati in `__init__`)**
    Nel costruttore `__init__`, se viene passato l'argomento opzionale `zones`, il ciclo legge solo `CONF_ZONE_NAME` per chiamare `register_zone`. Eventuali parametri come il peso (`weight`) o la modalità iniziale della zona vengono ignorati.
    *Soluzione proposta:* Estrarre anche `weight` e `mode` dal dizionario della zona e passarli a `register_zone`.
3.  **Rischio Mismatch Entity ID in `calculate(zones=...)`**
    Se `calculate()` viene invocato passando l'argomento `zones` (come fa probabilmente il coordinator per filtraggio), il codice rigenera l'ID con `cid = make_zone_entity_id(name)`. Se in fase di `register_zone` era stato usato un `climate_id` custom, qui si creerebbe un mismatch, portando a non trovare la demand e la modalità corrette per quella zona.
    *Soluzione proposta:* Invece di rigenerare il `cid` dal nome, usare una mappa inversa o assicurarsi che il parametro passato permetta di identificare il `cid` corretto senza ricostruirlo ciecamente.

## 📁 `zone_manager.py`
**Stato:** Analizzato
**Problemi e Ottimizzazioni rilevati:**

1.  **Residui di Debug (`print` statements in produzione)**
    Alle righe 192 e 200, all'interno di `async_on_window_state_changed`, sono rimaste delle funzioni `print(f"DEBUG ZONEMANAGER: ...")`. Questo sporca il log/stdout di sistema e andrebbe sostituito con `_LOGGER.debug` (che tra l'altro è già presente subito sotto).
2.  **Accoppiamento Forte (Tight Coupling con il Coordinator)**
    Il file viola in più punti l'incapsulamento accedendo direttamente alle variabili protette del coordinator: `self.coordinator._select_entities`, `self.coordinator._master_state`, `self.coordinator._climate_callbacks`, `self.coordinator._async_save_presets_storage()`. 
    *Soluzione proposta:* Esporre metodi pubblici nel coordinator o usare un sistema di eventi/segnali per slegare queste dipendenze.
3.  **Mancata gestione di `unavailable`/`unknown` per i sensori finestra**
    In `async_on_window_state_changed`, il codice mappa esplicitamente solo "on" (aperta) e "off" (chiusa). Se la batteria del sensore si scarica o si perde il segnale zigbee, lo stato diventa `unavailable`. Attualmente viene ignorato: se la finestra era aperta al momento del fault, la zona rimarrà freezata in BYPASS indefinitamente senza mai ripristinarsi, causando il blocco del riscaldamento in quella stanza.
    *Soluzione proposta:* Gestire lo stato `unavailable`/`unknown` forzando un fallback di sicurezza (es. assumere finestra chiusa per evitare che la stanza congeli o lanciare un alert).
4.  **Doppio trigger di salvataggio Storage**
    All'interno di `set_zone_mode`, vengono schedulati in parallelo due task di salvataggio: `async_set_persistent_data("zone_modes", ...)` e subito dopo `_async_save_presets_storage()`. Pur sperando che il `storage_manager` faccia un debounce corretto, è un pattern sporco che potrebbe causare I/O ridondante.
5.  **Sync TRV limitato ai "preset_modes"**
    La funzione `async_sync_trv_preset` tenta di spegnere/accendere i TRV slave usando solo `SERVICE_SET_PRESET_MODE`. Alcuni TRV (specialmente ibridi o non standard) non supportano presets ma solo `HVACMode.OFF` / `HVACMode.HEAT`.
    *Ottimizzazione proposta (retrocompatibile):* Se il TRV non supporta un preset di spegnimento, fare fallback su `SERVICE_SET_HVAC_MODE` con `HVACMode.OFF`.

## 📁 `routine_manager.py`
**Stato:** Analizzato
**Problemi e Ottimizzazioni rilevati:**

1.  **Bug Geofencing (Falso Positivo "Away" su glitch sensore)**
    Alla riga 96, il codice definisce l'assenza con `is_away = new_val != "home"`. Questo è un bug critico noto: se il sensore di presenza del telefono (es. app companion o integrazione router) perde temporaneamente la connessione, lo stato diventa `"unavailable"` o `"unknown"`. Il sistema interpreterà questo glitch come "tutti usciti di casa" e spegnerà l'impianto termico.
    *Soluzione proposta:* Aggiungere una clausola di guardia all'inizio di `_async_on_presence_changed` per fare `return` immediato (ignorare l'evento) se `new_val in ("unavailable", "unknown")`.
2.  **Fragilità dello Schedulatore (Rischio Trigger Saltati)**
    In `_async_check_schedule` (riga 154 e 173), il trigger delle routine automatiche diurne/notturne si basa sull'uguaglianza stretta del minuto attuale (`local_now.hour == hour and local_now.minute == minute`) interrogato da un timer periodico (`async_track_time_interval`) di 1 minuto. Se il thread di Home Assistant è sotto forte carico, il timer potrebbe slittare (es. girare alle 22:29:59 e poi alle 22:31:01), "saltando" il minuto esatto. Di conseguenza, la casa non passerebbe mai in modalità Notte per quel giorno.
    *Soluzione proposta:* Piuttosto che un timer periodico "cieco", è molto più affidabile usare `async_track_time_change` registrando l'ora esatta, oppure implementare una finestra di tolleranza memorizzando l'ultima esecuzione.
3.  **Exception Swallowing Silenzioso**
    Sempre nello schedulatore notturno/mattutino, il parsing dell'orario e la conversione in interi è avvolta in un generico `except Exception: pass` (righe 166-167 e 183-184). Se c'è un errore nei dati salvati nello storage (es. orario malformato tipo `"25:00"`), la routine smetterà di funzionare senza lasciare nessuna traccia nei log.
    *Soluzione proposta:* Loggare l'eccezione con `_LOGGER.error` o `_LOGGER.warning` per facilitare il debug all'utente.

## 📁 `calendar_manager.py`
**Stato:** Analizzato
**Problemi e Ottimizzazioni rilevati:**

1.  **Eventi Calendario Sovrapposti Ignorati (Bug di Logica)**
    Nel metodo `async_check_global_calendar` (riga 80-81), il ciclo for analizza gli eventi in corso ma si ferma al primo che trova (`if not current_event: current_event = event`). Se l'utente pianifica due eventi contemporanei sullo stesso calendario (es. un evento per riscaldare il Bagno e un altro evento separato per abbassare la temperatura in Salotto), il secondo evento verrà ignorato. 
    *Soluzione proposta:* Aggregare/mergiare i risultati di tutti gli eventi `current` attivi in un unico set di *overrides*.
2.  **Smart Start "Appiccicoso" (Assenza di Reset)**
    Alla riga 219, quando scatta la condizione di Smart Start, il sistema applica il setpoint inserendolo in `self.temp_overrides[climate_id]`. Questo dizionario viene ripulito solo quando l'evento *inizia* effettivamente (riga 109) o finisce. Tuttavia, se l'evento futuro viene cancellato dal calendario, posticipato, o se la stanza si scalda da sola (es. sole o stufa) invalidando la necessità di pre-riscaldo, il `temp_override` non viene mai cancellato, portando a un riscaldamento persistente errato.
    *Soluzione proposta:* Aggiungere una logica di reset all'inizio della routine di elaborazione dello Smart Start, per pulire gli override di pre-riscaldo se la condizione `now + time_needed >= start_time` non è più vera o se l'evento non esiste più.
3.  **Accoppiamento Forte e Violazione Demetra**
    Alle righe 150-156, il file manipola profondamente le strutture dati di altre classi: `self.coordinator.zone_manager._presets[self.coordinator.zone_manager.current_global_preset][climate_id]["target_temp"] = override.temperature`. È un grave anti-pattern (Violazione della Legge di Demetra). 
    *Soluzione proposta:* Il `zone_manager` deve esporre un metodo pubblico `update_preset_temperature(preset, zone_id, temp)` che nasconda la complessità dei dizionari e si occupi di chiamare il salvataggio su storage.

## 📁 `zone_controller.py`
**Stato:** Analizzato
**Problemi e Ottimizzazioni rilevati:**

1.  **DHW PID Integral Windup (Bug Critico P0 confermato)**
    Alle righe 134-139, quando l'acqua calda sanitaria (DHW) è in funzione, l'aggiornamento della zona viene saggiamente "congelato" facendo un `return` anticipato senza invocare il PID. Tuttavia, l'orologio interno dell'istanza `MultizonePID` non viene informato della pausa. Finita la doccia (es. dopo 20 minuti), la prima chiamata a `pid.calc()` leggerà un $\Delta t$ enorme (es. 1200 secondi), il che farà esplodere il calcolo dell'errore integrale (I-term windup). La demand schizzerà erroneamente al 100%.
    *Soluzione proposta:* Implementare e chiamare un metodo `pid.reset_time()` o `pid.pause()` per fare il *bumpless transfer* quando la zona riprende il controllo.
2.  **Surriscaldamento da Weather Compensation (Bug di Logica Matematica)**
    Alle righe 185-189, il feed-forward della compensazione climatica (`ff_demand`) viene sommato direttamente all'output del PID, ma senza controllare se c'è un reale bisogno di calore. Se la stanza è già a 22°C (su target 20°C), il PID produrrà 0%. Tuttavia, se fuori ci sono 0°C, la formula aggiungerà ciecamente +30% di PWM. Risultato: `0 + 30 = 30%`, i termosifoni si accendono e la stanza si surriscalda.
    *Soluzione proposta:* Aggiungere il `ff_demand` solo se la stanza è al di sotto del target, o se la `demand` del PID è > 0. In alternativa, scalare il weather bonus proporzionalmente all'errore termico.
3.  **Delegazione Obsoleta (Anti-Pattern)**
    Nonostante il `demand_aggregator` e lo `zone_manager` siano stati estratti, questo file continua a chiamare i metodi di routing legacy del `coordinator` (es. `self.coordinator.set_zone_demand`, `self.coordinator.get_zone_mode`).
    *Soluzione proposta:* Iniettare e usare direttamente le dipendenze corrette (es. `self.demand_aggregator.set_zone_demand`), decongestionando l'oggetto `coordinator` dal suo storico ruolo di *God Object*.

## 📁 `storage/storage_manager.py`
**Stato:** Analizzato
**Problemi e Ottimizzazioni rilevati:**

1.  **Rischio Perdita Dati (Debouncer custom difettoso)**
    Alla riga 98, la funzione `async_debounced_save_thermal_states` tenta di limitare l'usura della MicroSD ritardando il salvataggio di 120 secondi tramite `asyncio.sleep(120)`. Il grave problema è in `async_unload` (riga 112): se Home Assistant si riavvia o il componente viene ricaricato durante questa finestra temporale, il task viene brutalmente cancellato (`cancel()`), perdendo nel nulla i dati termici appena appresi.
    *Soluzione proposta:* Eliminare questo debouncer custom e utilizzare la funzione nativa di HA `self._settings_store.async_delay_save(get_data_func, 120.0)`. Questa API di HA garantisce nativamente l'aggregazione delle scritture e forza un *flush sincrono di sicurezza* su disco in caso di spegnimento/riavvio.
2.  **Bug Multi-Istanza (Conflitto di Chiavi)**
    Alla riga 12, la costante `WINDOW_STORAGE_KEY` è definita in modo globale come `multizone_thermostat.window_states`. A differenza degli altri due store (`_presets` e `_settings`) che includono correttamente `entry_id` nel nome del file, i dati delle finestre non sono isolati. Se un utente configura due istanze separate dell'integrazione (es. due piani della casa), queste si sovrascriveranno a vicenda lo storage delle finestre corrompendolo.
3.  **Spam di I/O non necessario**
    I metodi `async_set_data`, `async_save_windows` e `async_save_presets` invocano `async_save()` immediatamente a ogni singola modifica. Se lo `zone_manager` aggiorna tre zone di fila, il file viene sovrascritto tre volte in tre millisecondi.
    *Soluzione proposta:* Estendere l'uso di `async_delay_save` anche a questi metodi (con un delay più breve, es. 5 secondi) per raggruppare scritture simultanee in un'unica operazione di I/O.

## 📁 `coordinator.py`
**Stato:** Analizzato
**Problemi e Ottimizzazioni rilevati:**

1.  **Bug Crash in Unload (`AttributeError`)**
    Nel metodo `async_teardown_listeners` (riga 462), il codice tenta di spegnere un task in sospeso controllando `if self._pending_boiler_task and not self._pending_boiler_task.done():`. Il problema è che `self._pending_boiler_task` non viene mai inizializzato nel costruttore `__init__`. Se un utente disabilita o ricarica l'integrazione, l'Unload crasherà generando un `AttributeError: 'MultizoneCoordinator' object has no attribute '_pending_boiler_task'`, impedendo una pulizia sicura della memoria.
    *Soluzione proposta:* Inizializzare `self._pending_boiler_task = None` nel costruttore oppure usare `getattr()`.
2.  **Violazione dell'Incapsulamento (Legge di Demetra)**
    Nonostante l'estrazione dello `zone_manager`, dentro `_async_on_climate_state_changed` (righe 495-504) il coordinator manipola chirurgicamente i dizionari privati altrui: `self.zone_manager._presets[self.zone_manager.current_global_preset][entity_id]["target_temp"] = new_temp`. Questo genera un accoppiamento fragilissimo.
    *Soluzione proposta:* Spostare questa logica di salvataggio del target nello `ZoneManager` ed esporre semplicemente una API pubblica `self.zone_manager.update_preset_temperature(entity_id, new_temp)`.
3.  **Residui di Debugger in Produzione**
    Alla riga 610, all'interno di `_async_set_hvac_mode`, è rimasto un blocco `import traceback` che stampa l'intero stack trace in debug a ogni singolo cambio di modalità dei termosifoni (`_LOGGER.debug("DEBUG_TRACE: ... \n%s", ''.join(traceback.format_stack()))`). È pesantissimo per le performance e sporca inutilmente il log. Da rimuovere.
4.  **Logica di Dominio Fuori Posto**
    La funzione `is_passive_heat_allowed` esegue calcoli di mapping e parsing della configurazione di zona direttamente nel coordinator. Essendo logica specifica della zona, andrebbe ricollocata in `zone_manager.py` o `zone_controller.py`.

---
*Audit preliminare post-refactoring completato con successo. Tutti i bug logici, architetturali e prestazionali sono stati mappati e attendono risoluzione iterativa.*
