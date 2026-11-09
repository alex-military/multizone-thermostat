# Programmazione Settimanale & Smart Return

<span class="badge-stable">STABILE</span>


Multizone Thermostat integra un motore di programmazione oraria settimanale completo e nativo, visualizzabile tramite una matrice grafica a 24 ore e arricchito da algoritmi di anticipo termico predittivo.

---

## 1. La Scheda Scheduler (`custom:multizone-thermostat-scheduler-card`)

La scheda di programmazione consente di:
* **Visualizzare la Matrix 24 Ore**: Una vista orizzontale a fasce colorate che mostra l'alternanza dei preset (Comfort, Eco, Notte, Fuori Casa) per tutte le zone della casa.
* **Modifica Rapida delle Fasce**: Toccando qualsiasi blocco orario è possibile regolare ora di inizio, ora di fine e il preset assegnato alla stanza.
* **Copia Multi-Giorno**: Pulsante per replicare la configurazione dal Lunedì al Venerdì (giorni lavorativi) o sull'intero fine settimana con un solo tocco.

---

## 2. Gestione Multi-Profilo

Puoi salvare e alternare profili settimanali diversi in base alle tue abitudini di vita:
* **Standard**: Routine feriale tipica.
* **Festivo / Weekend**: Sveglia posticipata e comfort continuo durante il giorno.
* **Smart Working**: Riscaldamento continuativo per le stanze studio/lavoro durante le ore lavorative.
* **Personalizzato**: Nuovi profili creati liberamente.

I profili possono essere attivati manualmente, via automazione o con una scadenza temporale automatica (es. attiva "Ospiti" fino a domenica sera alle 23:00, con rientro automatico a "Standard").

---

## 3. Pianificatore Rientro Intelligente ("Smart Return")

Se sei fuori casa o l'impianto è spento (Master OFF) e vuoi trovare la casa calda al tuo arrivo:
1. Apri la schermata **Pianifica Rientro** dalla scheda del termostato o dallo Scheduler.
2. Imposta l'orario previsto di arrivo a casa (ad esempio le 18:30).
3. **Il Radar Termico Predittivo**:
   Il sistema conosce la velocità di riscaldamento (°C/ora) di ciascuna stanza grazie all'algoritmo di auto-apprendimento:
   * Se il salone impiega 45 minuti per scaldarsi e la camera da letto 1 ora e 15 minuti, l'impianto accenderà prima la camera (alle 17:15) e poi il salone (alle 17:45).
   * Alle 18:30 precise tutte le stanze saranno esattamente alla temperatura desiderata, senza sprecare energia accendendo prima del dovuto.
