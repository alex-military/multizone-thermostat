# Installazione & Requisiti

Guida passo-passo per installare **Multizone Thermostat** sulla tua istanza di Home Assistant.

---

## 1. Installazione via HACS (Consigliata)

HACS (Home Assistant Community Store) permette di gestire download e aggiornamenti con un semplice click.

### Versione Stabile

<span class="badge-stable">STABILE</span>

1. Apri **HACS** nella barra laterale di Home Assistant.
2. Fai clic sui **tre puntini in alto a destra** e seleziona **Repository personalizzati**.
3. Incolla l'indirizzo del repository:
   ```text
   https://github.com/alex-military/multizone-thermostat
   ```
4. Seleziona la categoria **Integrazione** e premi **Aggiungi**.
5. Cerca **"Multizone Thermostat"** nell'elenco di HACS e premi **Scarica**.
6. Riavvia Home Assistant.

### Versione Beta (Fase 11)

<span class="badge-beta">BETA</span>

Se desideri provare in anteprima le funzionalità della Fase 11 (centrale bivalente, split d'ambiente, gestione solare ed estiva):
1. Nella pagina di **Multizone Thermostat** all'interno di HACS, fai clic sui tre puntini in alto a destra della scheda.
2. Seleziona **Riscarica** (o *Redownload*).
3. Attiva l'interruttore **"Mostra versioni beta"** (o *Show beta versions*).
4. Seleziona la versione **`v6.1.0-beta.1`** (o successiva) e procedi al download.
5. Riavvia Home Assistant.

---

## 2. Installazione Manuale

1. Scarica lo zip o clona il repository dal ramo desiderato (`master` per la stabile, `beta` per la pre-release):
   ```bash
   git clone -b beta https://github.com/alex-military/multizone-thermostat.git
   ```
2. Copia l'intera cartella `custom_components/multizone_thermostat` all'interno della cartella `custom_components/` della tua installazione di Home Assistant.
3. Riavvia Home Assistant.

---

## 3. Prerequisiti

### Calendario Locale di Home Assistant *(Opzionale per la programmazione)*
Se desideri sincronizzare i profili orari o sfruttare la funzionalità **Smart Start (Accensione Intelligente Anticipata)** tramite eventi da calendario:
1. Vai in **Impostazioni → Dispositivi e Servizi → Aggiungi Integrazione**.
2. Cerca **"Calendario Locale"** (*Local Calendar*) e installalo.
3. Assegna un nome (es. `Calendario Termostato`).

Le risorse Lovelace (`multizone-thermostat-card.js`) vengono registrate in modo **completamente automatico** al primo avvio dell'integrazione, senza necessità di configurazioni manuali in risorse dashboard.
