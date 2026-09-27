## 🚀 v4.5.9: Smart Diagnostics & Rock-Solid Stability

This update brings a massive under-the-hood overhaul to system stability, mathematical precision, and user experience. 10 critical hidden bugs discovered during an extensive triple-audit have been resolved!

### 🔧 Core System & Asyncio
- **Emergency Shutdown Guarantee**: Summer Anti-Seize routine now safely catches `asyncio.CancelledError`, guaranteeing boilers/valves are never left ON if the integration reloads midway.
- **Memory Leak Fixed**: Safely tracked and cancelled background debounced SD-card save tasks upon unload.
- **Unblocked Event Loop**: Boot time checks for `www` directory now correctly run in the background executor to prevent freezing Home Assistant.

### 🌡️ Thermal Model & PID
- **Flawless Thermal Inertia**: Exponential Moving Average (EMA) for thermal inertia is now calculated strictly at the physical temperature peak, preventing over-estimation.
- **PID NaN Protection**: External weather temperature sensors passing `NaN` or invalid states will no longer permanently poison the PID Integral state.
- **Synchronized Physical Knobs**: Removed an aggressive async lock that was silently dropping physical knob changes while syncing TRVs. 

### 🩺 Plant Diagnostics
- **No More False Positives**: Adjusted the `boiler_on` logic so "Ghost Heating" and "Stuck Valve" anomalies are only calculated during active physical burns (not artificially extended by the hourly cycle count).
- **Expanded Memory**: Increased 24h cycle metrics buffer from 300 to 1000 items to support high-frequency PWM systems.

### 💻 Frontend & Config Flow
- **Indestructible UI Cards**: Re-engineered Lovelace DOM reconstruction to automatically repair the card structure when an entity recovers from an unavailable state (fixing a fatal JS null-reference crash).
- **Smart Config Flow**: Form validation errors when editing a Zone no longer destroy your unsaved inputs!
- **Anti-Frost Boost**: Anti-frost mode now correctly forces the TRV target temperature to `Frost Temp + 3°C` to ensure physical valves open immediately.

*All Python files have been fully statically compiled and validated before release.*
