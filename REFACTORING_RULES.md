# Regole del Refactoring (Refactoring Manifesto)

Questo documento definisce le regole inderogabili per l'intera fase di refactoring modulare dell'integrazione Multizone Thermostat. Ogni agente o sviluppatore coinvolto deve rispettare questi paletti.

## 1. Gestione Repository e Metodologia Step-by-Step
- **Nessuna Release Ufficiale / Branch Separato:** Si lavora in isolamento.
- **Una cosa alla volta:** Si estrae/modifica un solo modulo alla volta e ci si ferma.
- **Nessuna ottimizzazione preventiva ("As Is"):** Il codice si sposta così com'è per garantire parità di comportamento, niente ottimizzazioni logiche non strettamente necessarie.

## 2. Test Suite e Validazione a Strati (Novità)
- **Livello 1: Unit Test Suite Obbligatoria (Script):** Ogni modulo estratto DEVE essere dotato di una propria suite di test (script python/pytest all'interno della cartella `tests/`). Questa suite deve essere eseguita per verificare che il comportamento sia identico prima di toccare Docker.
- **Livello 2: Validazione in Docker:** Solo dopo il superamento dei test script, il modulo viene validato nel container Docker.
- **Livello 3: Validazione Umana (Fisica):** L'agente AI testerà il funzionamento nel container e fornirà **istruzioni fisiche ed esplicite** all'utente su cosa cliccare o verificare nell'interfaccia UI.
- **Doppia Conferma:** Il modulo è considerato valido SOLO se sia l'agente che l'utente confermano il corretto funzionamento.

## 3. Gestione Versioning e Deploy su Container
- **Bump Versione nel Manifest:** Prima di deployare sul container di validazione, l'agente DEVE aggiornare la versione nel `manifest.json` inserendo il numero dello step corrente (es. `"4.7.3-step2.1"`). Questo serve all'utente per verificare visivamente nella UI che l'ambiente abbia caricato l'esatta versione in test.
- **Container di Riferimento:** Le validazioni fisiche avvengono sul container Docker persistente dell'utente (che monta la cartella `C:\ha_config`). Per aggiornarlo, l'agente deve cancellare la vecchia cartella `custom_components/multizone_thermostat` in `C:\ha_config` e copiare la nuova versione in test dal workspace, per poi riavviare il container.

## 4. Gestione Roadmap e Chiusura
- **Aggiornamento Roadmap:** L'agente DEVE obbligatoriamente aggiornare la roadmap (marcando con una spunta ✅ lo step corrispondente) solo DOPO la "Doppia Conferma" del punto 2.
- **Contesto Pulito:** Una volta aggiornata la roadmap, la chat corrente deve essere considerata chiusa e il lavoro per il modulo successivo andrà fatto su una chat nuova.
