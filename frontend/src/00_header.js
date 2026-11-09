// window.customCards definition to register the cards in Lovelace UI card picker
window.customCards = window.customCards || [];
window.customCards.push({
  type: "multizone-thermostat-style-switcher",
  name: "Multizone Thermostat Style Switcher (Floating Button)",
  description: "Floating action button that opens an interactive modal to switch between Luxury and Classic styles.",
  preview: true,
});

window.customCards.push({
  type: "multizone-thermostat-button-card",
  name: "Multizone Thermostat Card (Buttons)",
  description: "A card to control a heating zone using simple buttons and a bypass switch.",
  preview: true,
});
window.customCards.push({
  type: "multizone-thermostat-dial-card",
  name: "Multizone Thermostat Card (Dial)",
  description: "A card wrapping the native Home Assistant thermostat dial with an integrated zone bypass switch.",
  preview: true,
});
window.customCards.push({
  type: "multizone-thermostat-status-card",
  name: "Multizone Thermostat Master Card",
  description: "A zero-config button card that controls the Heating Master switch and displays system status (Gray = Off, Yellow = Standby, Orange = Heating).",
  preview: true,
});
window.customCards.push({
  type: "multizone-thermostat-preset-card",
  name: "Multizone Thermostat Preset Card",
  description: "A quick selection card for Global Presets (Comfort, Eco, Sleep, Away).",
  preview: true,
});
window.customCards.push({
  type: "multizone-thermostat-plant-card",
  name: "Multizone Thermostat Plant Health Card",
  description: "A modern card displaying boiler telemetry, short-cycling frequency and physical plant health.",
  preview: true,
});
window.customCards.push({
  type: "multizone-thermostat-zone-energy-card",
  name: "Multizone Thermostat Zone Energy Card",
  description: "A modern card displaying room energy efficiency class (A4-G), thermal retention time and radiator sizing.",
  preview: true,
});

window.customCards.push({
  type: "multizone-thermostat-scheduler-card",
  name: "Multizone Thermostat Scheduler & Smart Return",
  description: "Interactive 24h multi-zone weekly scheduler, multi-profile manager and Smart Return planner.",
  preview: true,
});
window.customCards.push({
  type: "multizone-thermostat-schedule-summary-card",
  name: "Multizone Thermostat Schedule Summary Button",
  description: "Navigation button card displaying active schedule profile and linking to the Scheduler view.",
  preview: true,
});
window.customCards.push({
  type: "multizone-thermostat-health-summary-card",
  name: "Multizone Thermostat Health Summary Button",
  description: "Navigation button card displaying system health/anomaly status and linking to Diagnostics view.",
  preview: true,
});
window.customCards.push({
  type: "multizone-thermostat-nav-card",
  name: "Multizone Thermostat Navigation Card",
  description: "Navigation button card with icon, title, subtitle and badge linking to views.",
  preview: true,
});
window.customCards.push({
  type: "multizone-thermostat-responsive-grid",
  name: "Multizone Thermostat Responsive Grid",
  description: "Responsive auto-fitting grid container for multizone cards.",
  preview: true,
});

