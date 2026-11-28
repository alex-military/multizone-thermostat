# Weekly Scheduling & Smart Return

<span class="badge-stable">STABLE</span>

Multizone Thermostat integrates a native weekly schedule engine with a visual 24-hour timeline matrix and predictive thermal anticipation (**Smart Return**).

---

## 1. The Scheduler Card (`custom:multizone-thermostat-scheduler-card`)

* **24-Hour Timeline Matrix**: Visual timeline with color-coded preset blocks (Comfort, Eco, Sleep, Away) across all rooms throughout the day, including the **"🏠 All Zones (General)"** master summary row, dashed baseline gap blocks, and amber manual override indicators.
* **Touch-Friendly Block Editing**: Tap any time block to adjust start time, end time, and assigned preset mode.
* **Global Preset Sync without Pollution**: Synchronizes the `Global Preset` selector with the active weekly schedule while respecting geofencing `away` and preventing manual slot overrides from overwriting scheduled base presets.
* **Quick Multi-Day Copy**: Copy configurations across weekdays (Monday–Friday) or weekends with a single tap.

---

## 2. Multi-Profile Management & Timed Expirations

Three built-in profiles are seeded automatically, and users can create any number of custom profiles:
* **Standard (`standard`)**: Built-in typical weekday/weekly default schedule.
* **Smart Working (`smart_working`)**: Built-in daytime comfort profile for home offices.
* **Holiday (`holiday` / `Festivo`)**: Built-in schedule for holidays and continuous daytime comfort.
* **Custom Profiles** (e.g., *Guests / Vacation*): Create or duplicate unlimited custom profiles via UI or services.

### Temporary Profiles with Auto-Reversion
Activate special profiles with an expiration timestamp via UI or Home Assistant service:
* E.g.: Activate **"Guests"** until Sunday at 23:00.
* Once expired, the system automatically reverts to **"Standard"**, preventing accidental energy waste.

---

## 3. Predictive Smart Return (Pianifica Rientro)

Conventional setback systems rely on guesswork ("turn on heating 1 hour before arrival").
Multizone Thermostat deploys a **Predictive Thermal Radar**:

```mermaid
flowchart TD
    Arrivo["<b>Target Arrival Time: 18:30</b>"] --> Radar["<b>Multizone Predictive Thermal Radar</b><br>Computes pre-heating advance per room based on learned inertia"]
    Radar --> Z1["<b>Master Bedroom</b> (Inertia 1h 15m, R = 1.2 °C/h)<br>🚀 Pre-heat starts at <b>17:15</b>"]
    Radar --> Z2["<b>Living Room</b> (Inertia 45m, R = 2.0 °C/h)<br>🚀 Pre-heat starts at <b>17:45</b>"]
    Radar --> Z3["<b>Kitchen</b> (Inertia 30m, R = 2.8 °C/h)<br>🚀 Pre-heat starts at <b>18:00</b>"]
    Z1 --> Obiettivo["<b>Exact Arrival at 18:30</b><br>All rooms reach Comfort simultaneously!"]
    Z2 --> Obiettivo
    Z3 --> Obiettivo
```

### Pre-Heating / Pre-Cooling Time Calculation
Using the learned heating rate $R$ (or active cooling rate in `cool` mode; fallback default `1.5 °C/h` before initial learning, capped at `6.0 h` max lookahead):

$$\Delta t_{\text{lead\_time}} = \min\!\left(6.0\text{ h},\ \frac{|T_{\text{target}} - T_{\text{current}}|}{R}\right)$$

* Rooms adjust at their natural rates without wasted early energy (and in `cool` mode, non-cooling zones are automatically skipped on Smart Return completion).
* **Result**: At 18:30 sharp, every room reaches comfort simultaneously.

---

## 4. YAML Automation Examples

### Trigger Smart Return on Leaving the Office (GPS Geofence)
```yaml
automation:
  - alias: "Smart Return upon Leaving Work"
    trigger:
      - platform: zone
        entity_id: person.alex
        zone: zone.office
        event: leave
    action:
      - service: multizone_thermostat.set_smart_return
        data:
          arrival_time: "19:00"
          preset: comfort
```

### Switch to Smart Working Profile
```yaml
automation:
  - alias: "Activate Smart Working Profile"
    trigger:
      - platform: state
        entity_id: input_boolean.work_from_home
        to: "on"
    action:
      - service: multizone_thermostat.activate_schedule_profile
        data:
          profile_id: smart_working
          fallback_profile: standard
```
