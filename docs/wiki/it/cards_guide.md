# Guida Completa alle Schede Lovelace & Dashboard Strategy

Multizone Thermostat include una suite completa di schede grafiche personalizzate progettate appositamente per integrarsi nello stile di Home Assistant. Le schede offrono supporto completo ai temi chiaro e scuro, animazioni dinamiche, doppio stile visivo **Classic** (allineamento 1-a-1 nativo) e **Luxury** (con aura luminescente), oltre alla registrazione automatica delle risorse all'avvio dell'integrazione.

<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 14px; margin: 20px 0;">
  <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(249, 115, 22, 0.3); border-radius: 12px; padding: 10px; text-align: center;">
    <span style="font-weight: 700; color: #fb923c; font-size: 0.9rem; display: block; margin-bottom: 6px;">🔥 Visualizzazione Invernale (Riscaldamento)</span>
    <img src="images/dashboard_winter.jpg" alt="Dashboard Invernale" style="width: 100%; border-radius: 8px;">
  </div>
  <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 12px; padding: 10px; text-align: center;">
    <span style="font-weight: 700; color: #38bdf8; font-size: 0.9rem; display: block; margin-bottom: 6px;">❄️ Visualizzazione Estiva (Raffrescamento)</span>
    <img src="images/dashboard_summer.jpg" alt="Dashboard Estiva" style="width: 100%; border-radius: 8px;">
  </div>
</div>

---

## 1. Dial Thermostat Card (`custom:multizone-thermostat-dial-card`)

Un termostato circolare evoluto concepito come **Visual Twin 1-a-1** del componente termostato nativo di Home Assistant, arricchito con controlli ergonomici avanzati:

### Funzionalità Esclusive (v6.1.0-beta)
* **Regolazione Rapida al Tocco (Direct Arc Touch)**: Puoi toccare o cliccare direttamente in qualsiasi punto dell'arco circolare per impostare all'istante la temperatura desiderata, senza dover trascinare la manopola.
* **Pulsanti Step `[-]` e `[+]` Circolari**: Due pulsanti ergonomici posizionati simmetricamente nell'apertura inferiore dell'arco per incrementare o decrementare il setpoint a passi di $0.5^\circ\text{C}$ con un solo click.
* **Badge Dinamico della Sorgente Attiva (In alto a sinistra)**:
  * `🔥 GAS` (Arancione): Riscaldamento alimentato dalla caldaia idronica centrale a gas.
  * `⚡ ELETTRICO` (Celeste): Climatizzazione alimentata dallo split d'ambiente locale o dalla pompa di calore.
  * `🔥⚡ GAS + ELETTRICO` (Ambra): Funzionamento combinato simultaneo (Quick Heat Boost o priorità combinata).
* **Pulsante Accensione Split Locale Indipendente (Al centro dell'header)**:
  * Visibile unicamente per le stanze configurate con un condizionatore split (`split_climate_entity`).
  * **A Master Spento (OFF)**: Permette di accendere manualmente il solo split elettrico della stanza per un comfort rapido localizzato, senza avviare la caldaia e senza bruciare combustibile.
  * **A Master Acceso (Blocco di Sicurezza)**: Il pulsante viene automaticamente disabilitato per evitare che tocchi accidentali contrastino l'orchestrazione generale dell'abitazione.
* **Filtro Estivo Automatico (`hide_if_cannot_cool: true`)**: Nasconde automaticamente dalla dashboard le stanze sprovviste di capacità di raffrescamento quando il sistema è commutato in modalità estiva.
* **Selettore Modalità Stanza**: Tasto a pillola per commutare istantaneamente il ruolo della stanza tra `Primaria`, `Secondaria` e `Bypassata`.

```yaml
type: custom:multizone-thermostat-dial-card
entity: climate.multizone_thermostat_salone
title: Salone
card_style: classic          # 'classic' (stile nativo HA) oppure 'luxury' (con aura luminosa)
hide_if_cannot_cool: true    # Nascondi la card in estate se la stanza non ha condizionamento
border_radius: "20px"        # Raggio di curvatura angoli della scheda
```

---

## 2. Global Preset Card (`custom:multizone-thermostat-preset-card`)

Barra di supervisione globale che unisce il controllo stagionale, la priorità energetica e i profili di comfort in un'unica scheda ad **altezza costante garantita**:

* **Selettore Priorità Calore Segmentato**: Selettore orizzontale a pillola per alternare le 5 priorità (`Auto`, `Ibrido`, `Combinato`, `Elettrico`, `Gas`).
* **Transizione Estiva Identica**: In modalità raffrescamento estivo, il selettore priorità viene sostituito dal badge estetico `❄️ Raffrescamento Elettrico` con la **stessa identica altezza**, mantenendo le dimensioni della card perfettamente invariate tra estate e inverno.
* **Switch Scorrevole Stagionale (Caldo 🔥 / Freddo ❄️)**: Commuta all'istante l'intera casa tra riscaldamento e climatizzazione estiva.
* **Pulsanti Preset a Doppio Binario**: Richiamo istantaneo di `Manuale`, `Eco`, `Comfort`, `Notte`, `Fuori Casa` con memorizzazione indipendente tra estate e inverno.

```yaml
type: custom:multizone-thermostat-preset-card
```

---

## 3. Central Status Card (`custom:multizone-thermostat-status-card`)

Pulsante master a tutta larghezza con aura dinamica ad alta visibilità per accendere o spegnere la termoregolazione dell'intera abitazione con un solo tocco:

* **Aura Dinamica di Stato**:
  * **Arancione**: Riscaldamento invernale attivo.
  * **Ciano/Celeste**: Climatizzazione estiva attiva.
  * **Giallo**: Impianto abilitato ma in standby (tutte le stanze hanno raggiunto la temperatura desiderata).
  * **Grigio**: Impianto Master spento (OFF).
* **Sottotitolo Telemetrico Generatori**:
  Visualizza in tempo reale lo stato dei generatori della centrale termica:
  `Caldaia: ON`, `Caldaia: ON + Split`, `Split Elettrico: ON`, `Zone attive: 2/4`.

```yaml
type: custom:multizone-thermostat-status-card
```

---

## 4. Button Thermostat Card (`custom:multizone-thermostat-button-card`)

Una scheda termostato compatta a pulsante, concepita per griglie dense (es. su tablet a parete o schermate con molte stanze su una sola riga) dove il quadrante circolare risulterebbe troppo ingombrante:

* Pulsanti rapidi di incremento e decremento `+` e `-`.
* Lettura chiara di temperatura ambiente, target e stato HVAC.
* Include il badge dinamico della sorgente (`🔥 GAS`, `⚡ ELETTRICO`, `🔥⚡ GAS + ELETTRICO`).
* Bordo luminescente sincronizzato con il ciclo di lavoro della stanza.

```yaml
type: custom:multizone-thermostat-button-card
entity: climate.multizone_thermostat_camera
title: Camera Matrimoniale
```

---

## 5. Weekly Scheduler Card (`custom:multizone-thermostat-scheduler-card`)

L'interfaccia visuale della programmazione oraria settimanale:

* **Timeline 24h a Matrice di Colori**: Mostra graficamente la sequenza dei blocchi orari per tutte le zone.
* **Modifica al Tocco**: Regolazione intuitiva di orari e preset associati per ogni stanza.
* **Pianificazione Rientro Intelligente ("Smart Return")**: Pulsante integrato per impostare l'orario di rientro desiderato con calcolo automatico dell'anticipo termico per ciascuna stanza.

```yaml
type: custom:multizone-thermostat-scheduler-card
```

---

## 6. Central Plant Health Card (`custom:multizone-thermostat-plant-card`)

Scheda di supervisione tecnica della centrale termica e telemetria caldaia:

* **Indice di Salute Impianto**: Punteggio percentuale globale della salute idraulica dell'edificio.
* **Frequenza di Accensione Caldaia (Short-Cycle)**: Monitoraggio dei cicli/ora con allarme visivo in caso di usura elevata (> 5 cicli/ora).
* **Telemetria OpenTherm**: Pressione del circuito (Bar), temperatura di mandata e ritorno con calcolo del $\Delta T$, modulazione istantanea della fiamma in % e codici di errore della caldaia.
* **Riepilogo Anomalie Attive**: Elenco dinamico dei guasti idraulici riscontrati in casa (valvole bloccate, aria nei termosifoni o trafilamenti).

```yaml
type: custom:multizone-thermostat-plant-card
```

---

## 7. Zone Energy Efficiency Card (`custom:multizone-thermostat-zone-energy-card`)

Visualizza le prestazioni dell'involucro edilizio e i parametri termici fisici della singola stanza:

* **Classe Energetica Europea (A4 → G)**: Calcolata matematicamente dalla curva di dispersione naturale e dal salto termico interno/esterno.
* **Tempo di Ritenzione Termica**: Numero di ore necessarie all'ambiente per perdere $1.0^\circ\text{C}$ a riscaldamento spento.
* **Dimensionamento Radiatore**: Valutazione dell'adeguatezza della potenza installata (Sottodimensionato, Ottimale, Sovradimensionato).
* **Livello Batteria TRV**: Monitoraggio universale dello stato di carica delle valvole termostatiche Zigbee / Z-Wave.
* **Controlli Interattivi**: Possibilità di ciclare la modalità della stanza o abilitare l'Apporto Passivo direttamente dalla card.

```yaml
type: custom:multizone-thermostat-zone-energy-card
entity: climate.multizone_thermostat_salone
```

---

## 8. Generazione Automatica della Dashboard (Strategy)

Non desideri creare manualmente la dashboard e scrivere codice YAML per ogni singola card? Puoi sfruttare le strategie native che scoprono in tempo reale tutte le zone e compongono la vista automaticamente.

### Strategia Termostati Principale (`custom:multizone-thermostat-dashboard`)
Costruisce automaticamente l'intera dashboard con Master Switch, Global Preset Card e tutte le Dial Card disposte su griglia responsive:

```yaml
views:
  - title: Termostati
    path: termostati
    icon: mdi:thermostat
    strategy:
      type: custom:multizone-thermostat-dashboard
      columns: 3   # Colonne responsive (1, 2, 3 o 4 colonne)
```

### Strategia Diagnostica & Efficienza (`custom:multizone-thermostat-diagnostics`)
Genera la vista completa di salute dell'impianto con Central Plant Card e tutte le Zone Energy Cards:

```yaml
views:
  - title: Diagnostica Impianto
    path: diagnostica
    icon: mdi:chart-box-outline
    strategy:
      type: custom:multizone-thermostat-diagnostics
      columns: 3
```

---

## 🎮 Prova le Card nel Simulatore Live

Puoi testare interattivamente tutte le card, la commutazione caldo/freddo, il tocco sull'arco e i pulsanti step direttamente nella pagina dedicata:

👉 [**Vai al Simulatore Live Ufficiale (3 Dashboard)**](simulator_view.md) oppure [**Apri a Schermo Intero in una Nuova Scheda ↗**](simulator.html)
