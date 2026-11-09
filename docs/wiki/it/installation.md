# Installazione & Requisiti di Sistema

Guida passo-passo per installare, aggiornare e verificare **Multizone Thermostat** sulla tua istanza di Home Assistant.

---

## 1. Requisiti di Sistema

Prima di procedere all'installazione, verifica di soddisfare i seguenti requisiti minimi:
* **Home Assistant Core**: Versione `2024.1.0` o superiore.
* **Integrazione Calendario Locale** *(Facoltativo, consigliato per programmazione e Smart Start)*: Integrata nativamente in Home Assistant.
* **Browser Web**: Qualsiasi browser moderno per visualizzare le card Lovelace (Chrome, Safari, Firefox, Edge, app Home Assistant Companion).

---

## 2. Metodo 1: Installazione Tramite HACS (Consigliato)

HACS (Home Assistant Community Store) gestisce in automatico il download dei file e la notifica degli aggiornamenti futuri.

### Installazione Versione Stabile

<span class="badge-stable">STABILE</span>

1. Apri **HACS** dal menu laterale di Home Assistant.
2. Fai clic sui **tre puntini verticali** in alto a destra e seleziona **Repository personalizzati** (*Custom repositories*).
3. Incolla l'URL del repository:
   ```text
   https://github.com/alex-military/multizone-thermostat
   ```
4. Seleziona la categoria **Integrazione** (*Integration*) e clicca su **Aggiungi**.
5. Cerca **"Multizone Thermostat"** nella barra di ricerca di HACS.
6. Clicca su **Scarica** e conferma il download.
7. Riavvia Home Assistant (**Impostazioni → Sistema → Riavvia**).

---

### Installazione Versione Beta (Fase 11 / v6.1.0-beta)

<span class="badge-beta">BETA</span>

Se vuoi testare in anteprima la centrale bivalente, i condizionatori split, il surplus solare avanzato e la modalità estiva:
1. Accedi alla scheda di **Multizone Thermostat** già presente all'interno di HACS.
2. Fai clic sui **tre puntini in alto a destra** della pagina dell'integrazione e seleziona **Riscarica** (*Redownload*).
3. Attiva la casella **"Mostra versioni beta"** (*Show beta versions*).
4. Nel menu a tendina delle versioni, seleziona l'ultima release beta disponibile (es. `v6.1.0-beta.1`).
5. Clicca su **Scarica**.
6. Riavvia Home Assistant per caricare il nuovo componente Python.

---

## 3. Metodo 2: Installazione Manuale

Se non utilizzi HACS o desideri lavorare direttamente con Git:

1. Apri il terminale del tuo server Home Assistant (o accedi via SSH / Samba Share).
2. Spostati nella cartella di configurazione di Home Assistant (dove risiede `configuration.yaml`):
   ```bash
   cd /config
   ```
3. Se non esiste già, crea la cartella `custom_components`:
   ```bash
   mkdir -p custom_components
   ```
4. Clona il repository indicando il ramo desiderato:
   * **Per la versione Stabile**:
     ```bash
     git clone https://github.com/alex-military/multizone-thermostat.git /tmp/mzt
     cp -r /tmp/mzt/custom_components/multizone_thermostat custom_components/
     rm -rf /tmp/mzt
     ```
   * **Per la versione Beta (Fase 11)**:
     ```bash
     git clone -b beta https://github.com/alex-military/multizone-thermostat.git /tmp/mzt
     cp -r /tmp/mzt/custom_components/multizone_thermostat custom_components/
     rm -rf /tmp/mzt
     ```
5. Riavvia Home Assistant.

---

## 4. Registrazione Automatica delle Risorse Lovelace

Non è necessario copiare manualmente file JavaScript o modificare le Risorse Dashboard nelle impostazioni di Home Assistant:
* Al primo avvio, l'integrazione registra in modo **totalmente automatico** il bundle compilato:
  `/multizone_thermostat/multizone-thermostat-card.js`
* Tutte le card Lovelace (`custom:multizone-thermostat-dial-card`, `custom:multizone-thermostat-preset-card`, `custom:multizone-thermostat-status-card`, ecc.) risulteranno immediatamente disponibili nel selettore visivo delle schede della tua dashboard.

> [!TIP]
> Se dopo un aggiornamento le schede non mostrano la nuova grafica o le nuove icone, svuota la cache del browser premendo `Ctrl + F5` (o `Cmd + Shift + R` su Mac).
