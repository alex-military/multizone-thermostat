# Climatizzatori Split d'Ambiente

<span class="badge-beta">BETA</span>


La **Fase 11** consente di associare a ogni singola zona termica il proprio climatizzatore split (`climate.*`), integrandolo nell'orchestrazione con i termosifoni e le valvole idroniche.

---

## 1. Risoluzione del Problema della Sonda a Soffitto

Tutti gli split commerciali (Daikin, Mitsubishi, Gree, Haier, ecc.) integrano una sonda di temperatura direttamente all'interno dell'unità interna montata vicino al soffitto.
* **Il problema**: L'aria calda sale naturalmente verso l'alto e si accumula a soffitto in pochi minuti. Lo split "pensa" che la stanza sia calda e taglia prematuramente la potenza, lasciando il pavimento e l'altezza uomo ancora freddi.
* **La soluzione: Iniezione Dinamica della Sonda Reale**:
  Multizone Thermostat legge il termometro reale posizionato ad altezza d'uomo e inietta in tempo reale un setpoint compensato allo split:
  $$T_{\text{split\_inviato}} = T_{\text{desiderato}} + (T_{\text{split\_letto}} - T_{\text{sensore\_reale}})$$
  In questo modo lo split modula in modo fluido e costante fino a quando l'ambiente reale ha raggiunto il comfort perfetto.

---

## 2. Quick Heat Boost (Shock Termico a Freddo)

Quando una stanza parte completamente fredda con un dislivello termico significativo:
1. **Scatto del Boost**: Se $\Delta T = (T_{\text{target}} - T_{\text{ambiente}}) \ge 1.5^\circ\text{C}$, lo split parte a piena potenza insieme ai radiatori (**Dual Heat**).
2. **Raggiungimento Comfort**: Quando la stanza arriva a soli $0.3^\circ\text{C}$ dal target, lo split si spegne dolcemente.
3. **Mantenimento a Basso Consumo**: La fase stazionaria di mantenimento viene affidata alla sola caldaia/radiatori a regime termico minimo.

---

## 3. Disaccoppiamento Idronico Automatico

Quando una stanza viene riscaldata dallo split (per surplus solare, per boost o per accensione manuale), Multizone Thermostat **azzera a `0.0%` la richiesta idronica di quella specifica stanza**.
* La valvola di zona o la testina TRV del termosifone si chiude.
* La caldaia a gas non consuma combustibile per quella stanza.
* Le altre stanze prive di split continuano a essere scaldate regolarmente dalla caldaia a gas senza interferenze.

---

## 4. Pulsante Accensione Manuale Singola Stanza

Sulla scheda del termostato (Dial Card) è presente un pulsante centrale dedicato all'accensione locale dello split:

* **Visibile solo dove serve**: Compare unicamente nelle stanze dotate di condizionatore split.
* **A Master Spento (OFF)**: Premendo il pulsante a impianto centrale spento, **si accende soltanto lo split elettrico** di quella stanza per un riscaldamento rapido localizzato. La caldaia a gas rimane rigorosamente spenta. La card mostra il badge **`⚡ ELETTRICO`**.
* **Blocco di Sicurezza a Master Acceso**: Quando il Master generale della casa è acceso, il pulsante viene disabilitato per evitare che un tocco accidentale scolleghi la stanza dall'orchestrazione generale.
* **Sincronizzazione Automatica**: Se il Master viene acceso successivamente, l'accensione manuale locale si disattiva e la stanza si riallinea al preset globale della casa.
