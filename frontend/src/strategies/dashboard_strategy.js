class MultizoneThermostatDashboardStrategy extends HTMLElement {
  static async generateDashboard(info) {
    const view = await this.generateView(info);
    const schedView = await this.generateSchedulerView(info);
    const diagView = await this.generateDiagnosticView(info);
    return {
      title: "Multizone Thermostat",
      views: [
        {
          title: "Termostati",
          path: "home",
          icon: "mdi:radiator",
          panel: true,
          cards: view.cards,
        },
        {
          title: "Programmazione",
          path: "programmazione",
          icon: "mdi:calendar-clock",
          subview: true,
          panel: true,
          cards: schedView.cards,
        },
        {
          title: "Diagnostica & Efficienza",
          path: "diagnostica",
          icon: "mdi:chart-box-outline",
          subview: true,
          panel: true,
          cards: diagView.cards,
        }
      ]
    };
  }

  static async generateSchedulerView(info) {
    return {
      cards: [
        {
          type: "vertical-stack",
          cards: [
            {
              type: "custom:multizone-thermostat-scheduler-card"
            }
          ]
        }
      ]
    };
  }

  static async generateDiagnosticView(info) {
    const hass = info.hass;
    if (!hass || !hass.states) return { cards: [] };
    const strategyConfig = info.view?.strategy || info.config?.strategy || info.strategy || info.config || {};
    
    // Find all zones
    const zones = [];
    for (const entityId of Object.keys(hass.states)) {
      if (entityId.startsWith("select.") || entityId.startsWith("switch.")) {
        const stateObj = hass.states[entityId];
        const climateId = stateObj.attributes ? stateObj.attributes.climate_entity : null;
        if (climateId) {
          const climateState = hass.states[climateId];
          if (climateState && !zones.some(z => z.climate === climateId)) {
            let title = climateState.attributes.friendly_name || climateId;
            title = title.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
            zones.push({
              climate: climateId,
              title: title,
            });
          }
        }
      }
    }
    zones.sort((a, b) => a.title.localeCompare(b.title));

    let columns = parseInt(strategyConfig.columns, 10);
    if (isNaN(columns) || columns < 1) {
      columns = 3;
    }

    const zoneCards = zones.map(zone => ({
      type: "custom:multizone-thermostat-zone-energy-card",
      entity: zone.climate,
      title: zone.title,
      border_radius: "20px",
    }));

    return {
      cards: [
        {
          type: "vertical-stack",
          cards: [
            {
              type: "custom:multizone-thermostat-plant-card",
              border_radius: "20px",
            },
            {
              type: "custom:multizone-thermostat-responsive-grid",
              columns: columns,
              cards: zoneCards,
            }
          ]
        }
      ]
    };
  }

  static async generateView(info) {
    const hass = info.hass;
    if (!hass || !hass.states) return { cards: [] };
    // In view strategies, config is usually in info.config.strategy or info.strategy
    const strategyConfig = info.view?.strategy || info.config?.strategy || info.strategy || info.config || {};
    
    // Find master switch
    const masterEntity = findMasterEntity(hass);
    // Find preset entity
    const presetEntity = findPresetEntity(hass);
    
    // Find all zones (by checking for climate_entity attribute)
    const zones = [];
    for (const entityId of Object.keys(hass.states)) {
      if (entityId.startsWith("select.") || entityId.startsWith("switch.")) {
        const stateObj = hass.states[entityId];
        const climateId = stateObj.attributes ? stateObj.attributes.climate_entity : null;
        if (climateId) {
          const climateState = hass.states[climateId];
          if (climateState) {
            let title = climateState.attributes.friendly_name || climateId;
            title = title.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
            zones.push({
              climate: climateId,
              switch: entityId,
              title: title,
            });
          }
        }
      }
    }
    
    // Sort zones by title
    zones.sort((a, b) => a.title.localeCompare(b.title));
    
    // Build zone rows to get 'columns' config first
    let columns = parseInt(strategyConfig.columns, 10);
    if (isNaN(columns) || columns < 1) {
      columns = 3;
    }

    // Build top row
    const topRowCards = [];
    if (presetEntity) {
      topRowCards.push({
        type: "custom:multizone-thermostat-preset-card",
        entity: presetEntity,
        title: "",
        border_radius: "20px",
      });
    }
    
    topRowCards.push({
      type: "custom:multizone-thermostat-status-card",
      border_radius: "20px",
    });

    if (columns >= 4) {
      topRowCards.push({
        type: "custom:multizone-thermostat-schedule-summary-card",
        border_radius: "20px",
      });
      topRowCards.push({
        type: "custom:multizone-thermostat-health-summary-card",
        border_radius: "20px",
      });
    } else {
      // In standard 3-column layout, combine scheduler & diagnostica into the 3rd column
      topRowCards.push({
        type: "custom:multizone-thermostat-nav-card",
        border_radius: "20px",
      });
    }

    const cardStyle = strategyConfig.card_style || strategyConfig.style || "luxury";

    const zoneCards = zones.map(zone => ({
      type: "custom:multizone-thermostat-dial-card",
      entity: zone.climate,
      switch: zone.switch,
      title: zone.title,
      card_style: cardStyle,
      border_radius: "20px",
    }));

    if (columns === 1) {
      return {
        cards: [
          {
            type: "vertical-stack",
            cards: topRowCards.concat(zoneCards),
          }
        ]
      };
    }

    return {
      cards: [
        {
          type: "custom:multizone-thermostat-responsive-grid",
          columns: columns,
          cards: topRowCards.concat(zoneCards),
        }
      ]
    };
  }
}

// Register Strategy
window.customStrategies = window.customStrategies || [];
window.customStrategies.push({
  type: "multizone-thermostat-dashboard",
  name: "Multizone Thermostat Dashboard",
  description: "Auto-generated dashboard for your heating system."
});
window.customStrategies.push({
  type: "multizone-thermostat-diagnostics",
  name: "Multizone Thermostat Diagnostics",
  description: "Auto-generated diagnostic and energy efficiency view for your heating zones."
});
window.customStrategies.push({
  type: "multizone-thermostat-scheduler",
  name: "Multizone Thermostat Scheduler",
  description: "Auto-generated scheduler and Smart Return view for your heating zones."
});

class MultizoneThermostatViewStrategy extends MultizoneThermostatDashboardStrategy {}
class MultizoneThermostatDiagnosticViewStrategy extends HTMLElement {
  static async generateView(info) {
    return MultizoneThermostatDashboardStrategy.generateDiagnosticView(info);
  }
}
class MultizoneThermostatSchedulerViewStrategy extends HTMLElement {
  static async generateView(info) {
    return MultizoneThermostatDashboardStrategy.generateSchedulerView(info);
  }
}

if (!customElements.get("ll-strategy-dashboard-multizone-thermostat-dashboard")) {
  customElements.define("ll-strategy-dashboard-multizone-thermostat-dashboard", MultizoneThermostatDashboardStrategy);
}
if (!customElements.get("ll-strategy-view-multizone-thermostat-dashboard")) {
  customElements.define("ll-strategy-view-multizone-thermostat-dashboard", MultizoneThermostatViewStrategy);
}
if (!customElements.get("ll-strategy-view-multizone-thermostat-diagnostics")) {
  customElements.define("ll-strategy-view-multizone-thermostat-diagnostics", MultizoneThermostatDiagnosticViewStrategy);
}
if (!customElements.get("ll-strategy-view-multizone-thermostat-scheduler")) {
  customElements.define("ll-strategy-view-multizone-thermostat-scheduler", MultizoneThermostatSchedulerViewStrategy);
}

