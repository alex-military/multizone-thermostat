# Protezioni Meccaniche & Diagnostica Impianto

<span class="badge-stable">STABILE</span>


Multizone Thermostat agisce come supervisore centrale dell'impianto idraulico, proteggendo la caldaia dall'usura e rilevando guasti meccanici prima che causino danni o sprechi in bolletta.

---

## 1. Protezioni Meccaniche & Sicurezza

### Anti-Short-Cycle (Protezione Cicli Rapidi)
Impedisce accensioni e spegnimenti troppo frequenti della caldaia che danneggerebbero i relè e ridurrebbero l'efficienza della condensazione:
* `number.master_control_min_cycle_on`: Tempo minimo di accensione continuativa del bruciatore (default: 5 minuti).
* `number.master_control_min_cycle_off`: Tempo minimo di riposo prima di una nuova riaccensione (default: 5 minuti).

### Ritardo Apertura Valvole (`valve_opening_delay`)
Le testine elettrotermiche dei collettori a pavimento o le valvole di zona motorizzate impiegano da 90 a 180 secondi per aprirsi completamente.
Impostando un ritardo (es. 120 secondi), la pompa di circolazione della caldaia si avvia solo a valvole completamente aperte, evitando sovrapressioni nei tubi.

### Anti-Bloccaggio Estivo (Anti-Seize)
Durante l'estate le valvole dei radiatori e le giranti delle pompe rimangono ferme per mesi, rischiando di gripparsi con il calcare:
* Se l'impianto rimane inattivo per più di 15 giorni (`anti_seize_idle_days`), il sistema apre tutte le valvole ed esegue un ciclo di movimentazione di 2 minuti (`anti_seize_duration`), richiudendole subito dopo.

### Protezione Antigelo di Emergenza (Anti-Frost)
Se la temperatura di una stanza scende sotto la soglia di sicurezza (`frost_protection_temp`, default 7.0°C), il sistema forza l'accensione immediata al 100% scavalcando qualsiasi blocco (finestra aperta, Master spento o assenza) per evitare il congelamento e la rottura delle tubature.

---

## 2. Sorveglianza Guasti Idraulici

La diagnostica esamina in continuo l'evoluzione della temperatura delle stanze per individuare anomalie:

| Anomalia | Causa Rilevata | Azione Automatica |
|---|---|---|
| **Valvola Bloccata Chiusa** | La stanza richiede calore da >45 minuti con caldaia attiva, ma la temperatura ambiente continua a scendere. | Notifica persistente su Home Assistant e avviso rosso sulla scheda. |
| **Trafilamento Calore (Ghost Heating)** | La temperatura ambiente sale mentre la valvola della stanza dovrebbe essere chiusa a 0%. | Notifica di perdita idraulica o testina non a tenuta. |
| **Aria nel Radiatore** | La valvola è aperta al 100% ma la velocità di riscaldamento è anomala rispetto allo storico. | Segnalazione di sfiato aria necessario. |
| **Timeout Sonda Wireless (Watchdog)** | Il termometro Zigbee/Wi-Fi si scollega o esaurisce la batteria. | Fallback istantaneo sulla sonda interna della valvola TRV. |

---

## 3. Telemetria OpenTherm Avanzata

Se collegato a un gateway OpenTherm, il sistema espone:
* **Pressione Impianto (Bar)**: Con allarme di bassa pressione sotto 0.8 Bar.
* **Temperatura Mandata e Ritorno (°C)**: Calcolo del $\Delta T$ reale per verificare lo scambio termico.
* **Modulazione Fiamma (%)**: Percentuale istantanea di potenza erogata dal bruciatore.
* **Codici Errore OEM**: Cattura automatica dei codici di errore inviati dalla scheda madre della caldaia.
* **Priorità Sanitaria (DHW Freeze)**: Quando un rubinetto apre l'acqua calda sanitaria, il calcolo del riscaldamento viene temporaneamente congelato per non generare falsi allarmi e non accumulare errore integrale.
