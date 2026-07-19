import json
import os
import uuid
import datetime

def generate_entry_id():
    return uuid.uuid4().hex.upper()[:26]

def remove_from_json(filepath, condition_func):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r') as f:
        data = json.load(f)
        
    original_len = len(data['data'].get('entries', []) if 'entries' in data['data'] else data['data'].get('devices', []) if 'devices' in data['data'] else data['data'].get('entities', []))
    
    if 'entries' in data['data']:
        data['data']['entries'] = [e for e in data['data']['entries'] if not condition_func(e)]
        new_len = len(data['data']['entries'])
    elif 'devices' in data['data']:
        data['data']['devices'] = [e for e in data['data']['devices'] if not condition_func(e)]
        new_len = len(data['data']['devices'])
    elif 'entities' in data['data']:
        data['data']['entities'] = [e for e in data['data']['entities'] if not condition_func(e)]
        new_len = len(data['data']['entities'])
        
    if new_len < original_len:
        print(f"Removed {original_len - new_len} items from {filepath}")
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

def main():
    print("Resetting multizone_thermostat integration...")
    
    # Remove config entries
    remove_from_json('/config/.storage/core.config_entries', lambda e: e.get('domain') == 'multizone_thermostat')
    
    # Remove device registry entries
    remove_from_json('/config/.storage/core.device_registry', lambda e: any(i[0] == 'multizone_thermostat' for i in e.get('identifiers', [])))
    
    # Remove entity registry entries
    remove_from_json('/config/.storage/core.entity_registry', lambda e: e.get('platform') == 'multizone_thermostat')
    
    # Remove custom settings
    if os.path.exists('/config/.storage/multizone_thermostat.settings'):
        os.remove('/config/.storage/multizone_thermostat.settings')
        print("Removed /config/.storage/multizone_thermostat.settings")
        
    if os.path.exists('/config/.storage/multizone_thermostat.presets'):
        os.remove('/config/.storage/multizone_thermostat.presets')
        print("Removed /config/.storage/multizone_thermostat.presets")
        
    print("Re-creating clean config entry...")
    entry_id = generate_entry_id()
    
    with open('/config/.storage/core.config_entries', 'r') as f:
        config = json.load(f)
        
    new_entry = {
      "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "data": {
        "boiler_switch": "switch.switch_caldaia",
        "virtual_thermostats": [
          {
            "heater_switch": "switch.switch_relay_camera",
            "name": "test camera virtuale",
            "target_temperature": 20.0,
            "temperature_sensor": "sensor.sensor_camera",
            "tolerance": 0.5
          }
        ],
        "zones": [
          {
            "climate_entity": "climate.multizone_thermostat_vt_test_camera_virtuale",
            "name": "test camera virtuale",
            "trv_preset_sync": False
          },
          {
            "climate_entity": "climate.termostato_salone",
            "name": "Termostato Salone",
            "trv_preset_sync": False
          }
        ],
        "geofencing_enabled": True,
        "presence_sensor": "input_boolean.mock_presence"
      },
      "disabled_by": None,
      "discovery_keys": {},
      "domain": "multizone_thermostat",
      "entry_id": entry_id,
      "minor_version": 1,
      "modified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "options": {},
      "pref_disable_new_entities": False,
      "pref_disable_polling": False,
      "source": "user",
      "subentries": [],
      "title": "Multizone Thermostat",
      "unique_id": "multizone_thermostat",
      "version": 1
    }
    
    config['data']['entries'].append(new_entry)
    
    with open('/config/.storage/core.config_entries', 'w') as f:
        json.dump(config, f, indent=2)
        
    print(f"Created new entry with ID {entry_id}")
    print("Done! Restart HA to apply.")

if __name__ == '__main__':
    main()
