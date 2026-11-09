# Installation & System Requirements

Step-by-step guide to installing, updating, and verifying **Multizone Thermostat** on your Home Assistant instance.

---

## 1. System Requirements

Ensure your setup meets the following requirements before installation:
* **Home Assistant Core**: Version `2024.1.0` or higher.
* **Home Assistant Local Calendar** *(Optional, recommended for scheduling and Smart Start)*: Native built-in integration.
* **Modern Web Browser**: Chrome, Safari, Firefox, Edge, or the official Home Assistant Companion app.

---

## 2. Method 1: Installation via HACS (Recommended)

HACS (Home Assistant Community Store) automatically manages downloading and notifying you of future updates.

### Stable Version Installation

<span class="badge-stable">STABLE</span>

1. Open **HACS** from the Home Assistant sidebar.
2. Click the **three vertical dots** in the top right corner and select **Custom repositories**.
3. Paste the repository URL:
   ```text
   https://github.com/alex-military/multizone-thermostat
   ```
4. Select the category **Integration** and click **Add**.
5. Search for **"Multizone Thermostat"** in HACS.
6. Click **Download** and confirm.
7. Restart Home Assistant (**Settings → System → Restart**).

---

### Beta Testing Installation (Phase 11 / v6.1.0-beta)

<span class="badge-beta">BETA</span>

To test Phase 11 features (bivalent central plant, room split AC, solar off-grid surplus, and summer cooling):
1. Navigate to the **Multizone Thermostat** page within HACS.
2. Click the **three dots in the top right corner** and select **Redownload**.
3. Enable the **"Show beta versions"** toggle.
4. Select the latest pre-release version (e.g. `v6.1.0-beta.1`).
5. Click **Download**.
6. Restart Home Assistant to load the updated integration.

---

## 3. Method 2: Manual Installation

If you prefer installing directly from source via Git:

1. Open your Home Assistant server terminal (or connect via SSH / Samba Share).
2. Navigate to your Home Assistant configuration folder:
   ```bash
   cd /config
   ```
3. Create the `custom_components` directory if it does not already exist:
   ```bash
   mkdir -p custom_components
   ```
4. Clone the repository for the desired branch:
   * **For Stable Branch**:
     ```bash
     git clone https://github.com/alex-military/multizone-thermostat.git /tmp/mzt
     cp -r /tmp/mzt/custom_components/multizone_thermostat custom_components/
     rm -rf /tmp/mzt
     ```
   * **For Beta Branch (Phase 11)**:
     ```bash
     git clone -b beta https://github.com/alex-military/multizone-thermostat.git /tmp/mzt
     cp -r /tmp/mzt/custom_components/multizone_thermostat custom_components/
     rm -rf /tmp/mzt
     ```
5. Restart Home Assistant.

---

## 4. Automatic Lovelace Resource Registration

No manual JavaScript copying or Dashboard Resource configuration is required:
* Upon startup, the integration **automatically registers** the bundled card asset:
  `/multizone_thermostat/multizone-thermostat-card.js`
* All custom cards (`custom:multizone-thermostat-dial-card`, `custom:multizone-thermostat-preset-card`, `custom:multizone-thermostat-status-card`, etc.) will immediately appear in your Lovelace card picker.

> [!TIP]
> If cards do not display updated graphics or icons after an upgrade, perform a hard refresh by pressing `Ctrl + F5` (or `Cmd + Shift + R` on macOS).
