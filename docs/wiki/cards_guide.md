# Guida alle Schede Lovelace & Dashboard Strategy

Multizone Thermostat include una suite completa di schede grafiche custom progettate specificamente per integrarsi nello stile di Home Assistant, con supporto a temi chiari, scuri, animazioni dinamiche e doppia visualizzazione **Luxury** e **Classic**.

---

## 1. Dial Thermostat Card (`custom:multizone-thermostat-dial-card`)

Un termostato circolare evoluto disponibile sia in versione **Luxury** (con aura dinamica luminescente) sia in versione **Classic** (allineata allo stile nativo di Home Assistant).

### Funzionalità Principali
* **Regolazione Rapida al Tocco**: Puoi toccare o cliccare direttamente in qualsiasi punto dell'arco circolare per impostare all'istante la temperatura desiderata, senza dover trascinare la manopola.
* **Pulsanti Step `[-]` e `[+]`**: Posizionati ergonomicamente nell'apertura inferiore dell'arco per incrementare o decrementare la temperatura di 0.5°C con un semplice tocco.
* **Doppio Stile Visivo (Classic / Luxury)**: Puoi scegliere nelle opzioni della scheda tra la modalità **Luxury** (con bagliore dinamico sfumato e pillole di stato) e la modalità **Classic** (stile pulito perfettamente integrato con il tema di Home Assistant).
* **Badge Dinamico della Sorgente Attiva**: Indica in tempo reale quale generatore sta erogando calore nella stanza:
  * `🔥 GAS` (Arancione): Riscaldamento attivo tramite caldaia a gas idronica.
  * `⚡ ELETTRICO` (Celeste): Climatizzazione attiva tramite condizionatore split locale o pompa di calore.
  * `🔥⚡ GAS + ELETTRICO` (Ambra): Funzionamento simultaneo (Quick Boost o modalità combinata).
* **Pulsante Accensione Split Locale Indipendente**:
  * Visibile nelle stanze dotate di condizionatore split d'ambiente.
  * **A Master Spento**: Permette di accendere manualmente il solo split elettrico della stanza per un comfort rapido localizzato, senza avviare la caldaia a gas e senza consumare combustibile.
  * **A Master Acceso (Blocco di Sicurezza)**: Il pulsante si disabilita automaticamente per impedire conflitti con l'orchestrazione globale della casa.
* **Filtro Estivo Automatico**: In modalità estiva (raffrescamento), le stanze prive di condizionatore split o di raffrescamento idronico vengono nascoste automaticamente per mantenere la dashboard ordinata.
* **Selettore Modalità Stanza Integrato**: Passaggio immediato con un click tra `Primaria`, `Secondaria` e `Bypassata`.

```yaml
type: custom:multizone-thermostat-dial-card
entity: climate.multizone_thermostat_salone
title: Salone
# card_style: luxury   # Opzionale: 'luxury' o 'classic'
```

---

## 2. Global Preset Card (`custom:multizone-thermostat-preset-card`)

Barra di controllo globale per la commutazione istantanea dei preset e della stagione in tutta la casa:
* **Selettore Priorità Calore**: Pulsanti a pillola per selezionare la priorità tra `Auto`, `Ibrido`, `Combinato`, `Elettrico` e `Gas`. In estate si commuta automaticamente nell'indicatore `❄️ Raffrescamento Elettrico`.
* **Switch Scorrevole Stagionale**: Commutazione istantanea tra **Caldo 🔥** (inverno) e **Freddo ❄️** (estate).
* **Pulsanti Preset Multipli**: Richiamo rapido di `Manuale`, `Eco`, `Comfort`, `Notte`, `Fuori Casa` con memorizzazione indipendente tra estate e inverno.

```yaml
type: custom:multizone-thermostat-preset-card
```

---

## 3. Status Card (`custom:multizone-thermostat-status-card`)

Scheda master per il controllo centrale con aura dinamica (Arancione: riscaldamento, Ciano: condizionamento estivo, Giallo: standby, Grigio: spento). Mostra lo stato in tempo reale della centrale (`Caldaia: ON`, `Caldaia: ON + Split`, `Split Elettrico: ON`, ecc.).

```yaml
type: custom:multizone-thermostat-status-card
```

---

## 4. Central Plant Card (`custom:multizone-thermostat-plant-card`)

Visualizza la salute della caldaia e della pompa di calore, la frequenza di accensioni orarie (cicli/ora con allarme di usura > 5 c/h) e l'elenco delle anomalie idrauliche attive in casa.

```yaml
type: custom:multizone-thermostat-plant-card
```

---

## 5. Zone Energy Card (`custom:multizone-thermostat-zone-energy-card`)

Mostra la classe energetica teorica dell'edificio (da A4 a G), le ore di ritenzione termica per perdere 1°C, il dimensionamento del radiatore e il livello della batteria delle valvole TRV.

```yaml
type: custom:multizone-thermostat-zone-energy-card
entity: climate.multizone_thermostat_salone
```

---

## 6. Generazione Automatica della Dashboard (Strategy)

Se non desideri scrivere codice YAML per ogni singola stanza, puoi usare la strategia automatica che scopre tutte le zone, i preset e il master, generando una vista completa con griglia responsive:

```yaml
views:
  - title: Termostati
    path: termostati
    icon: mdi:thermostat
    strategy:
      type: custom:multizone-thermostat-dashboard
      columns: 3   # 1, 2, 3 o 4 colonne responsive
```

---

## 🎮 Simulatore Live Ufficiale Home Assistant

Puoi provare le card reali direttamente nella simulazione qui sotto, oppure aprirla a schermo intero: [Apri Simulatore a Schermo Intero ↗](simulator.html).

<iframe src="simulator.html?v=beta11_rev3" style="width: 100%; height: 860px; border: 1px solid #283144; border-radius: 12px; background: #0f1218;" loading="lazy"></iframe>
