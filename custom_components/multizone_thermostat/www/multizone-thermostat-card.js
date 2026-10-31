// window.customCards definition to register the cards in Lovelace UI card picker
window.customCards = window.customCards || [];
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

const TRANSLATIONS = {
  it: {
    enabled: "Abilitata",
    heating: "Riscaldamento",
    heating_active: "Riscaldamento Attivo",
    idle: "Standby (In Attesa)",
    off: "Spento",
    excluded: "Zona Esclusa",
    bypass_msg: "Zona Esclusa / Bypassata",
    caldaia_circ: "Caldaia/Circolatore",
    system_active: "Sistema Attivo",
    system_off: "Sistema Spento",
    searching: "Ricerca...",
    master_not_found: "Master non trovato",
    temp_detected: "Rilevata",
    custom_error: "Errore scheda Multizone Thermostat",
    heat_mode: "Caldo",
    primary: "Prioritaria",
    secondary: "Secondaria",
    primary_tooltip: "Primaria (Accende Caldaia)",
    secondary_tooltip: "Secondaria (Passiva)",
    passive_heat_active_tooltip: "Apporto Passivo ATTIVO (Clicca per disattivare)",
    passive_heat_inactive_tooltip: "Apporto Passivo non attivo (Clicca per attivare)",
    anomaly_detected: "Anomalia Rilevata",
    card_error_title: "Errore scheda Multizone Thermostat",
    bypass_tooltip: "Bypass (Esclusa)",
    master_title: "Riscaldamento Centrale",
    thermostat: "Termostato",
    edit_title: "Titolo Personalizzato (Opzionale)",
    edit_climate: "Termostato (Climate Entity)",
    edit_switch: "Switch di Zona (Abilita/Escludi)",
    preset_manual: "Manuale",
    preset_eco: "Eco",
    preset_comfort: "Comfort",
    preset_sleep: "Notte",
    preset_away: "Fuori Casa",
    preset_card_title: "Preset Globale",
    edit_preset: "Entità Preset (Opzionale)",
    // Diagnostic translations
    plant_health_title: "Salute Impianto & Caldaia",
    plant_health_sub: "Supervisione idraulica e usura relè",
    cycles_label: "Frequenza Accensioni (Short-Cycle)",
    cycles_unit: "cicli/h",
    wear_low: "Usura Bassa (< 3.5 c/h)",
    wear_moderate: "Usura Moderata (3.5 - 5 c/h)",
    wear_high: "⚠️ Short-Cycling Elevato (> 5 c/h)",
    runtime_24h: "Funzionamento Ultime 24h",
    runtime_sub: "Attività cumulativa relè / mandata",
    all_circuits_ok: "Tutti i circuiti operativi",
    no_anomalies: "Nessun blocco valvola, trafilamento o short-cycling rilevato.",
    attention_cycles: "Attenzione: frequenza di accensioni caldaia elevata o parametri da ottimizzare.",
    retention_label: "Ritenzione (-1°C)",
    hours: "ore",
    learning: "In apprendimento...",
    opt_insulation: "Ottimo isolamento",
    med_insulation: "Isolamento medio",
    fast_dispersion: "Dispersione rapida",
    sizing_label: "Resa Termoarredo",
    sizing_opt: "Rapporto potenza/perdite OK",
    sizing_under: "Richiede tempo per salire",
    sizing_over: "Potenza elevata",
    sizing_waiting: "In attesa dati termici",
    valve_status: "Stato Valvola:",
    valve_ok: "Nessuna anomalia",
    valve_closed_bypass: "Valvola Chiusa (Bypass)",
    passive_heat_active: "Apporto passivo attivo",
    bypassed_tag: "BYPASSATA",
    primary_tag: "PRIMARIA",
    secondary_tag: "SECONDARIA",
    target: "target",
    optimal: "OTTIMALE",
    warning: "ATTENZIONE",
    critical: "CRITICO",
    ot_telemetry: "Telemetria OpenTherm",
    ot_dhw_active: "🚿 Acqua Calda (ACS)",
    ot_pressure: "Pressione",
    ot_flow_temp: "Mandata Acqua",
    ot_return_temp: "Ritorno Acqua",
    ot_modulation: "Modulazione",
    ot_flame_status: "Stato Fiamma",
    ot_flame_on: "🔥 Accesa",
    ot_flame_off: "Spenta",
    ot_condensing_ok: "Condensazione OK",
    ot_return_hot: "Ritorno caldo (>54°C)",
sched_nav_title: "Programmazione",
    sched_title: "Multizone Scheduler",
    sched_active: "Attivo",
    sched_paused: "In Pausa",
    sched_in_use: "In uso",
    sched_baseline: "Baseline fuori fascia",
    sched_activate_btn: "Attiva Profilo / Scadenza",
    sched_smart_return_btn: "Pianifica Rientro (Smart Return)",
    sched_reset_overrides: "Ripristina tutte le deroghe",
    sched_override_until: "Deroga fino alle",
    sched_restore: "Ripristina",
    sched_explicit_off: "Spento Esplicito",
    sched_turn_on: "Riaccendi",
    sched_editor_profile: "Editor Profilo",
    sched_duplicate: "Duplica Profilo",
    sched_bg_edit_notice: "Modifica in background (Non altera il profilo attivo)",
    sched_new_block: "+ Nuova Fascia Oraria",
    sched_brush: "Pennello 24h",
    sched_erase: "Gomma",
    sched_copy_weekdays: "Copia giorno su Lun–Ven",
    sched_copy_weekend: "Copia giorno su Sab–Dom",
    sched_preset_matrix_title: "Matrice Preset Multizone (Temperature di riferimento per stanza)",
    day_mon: "Lunedì",
    day_tue: "Martedì",
    day_wed: "Mercoledì",
    day_thu: "Giovedì",
    day_fri: "Venerdì",
    day_sat: "Sabato",
    day_sun: "Domenica",
    prof_standard: "Standard",
    prof_smart_working: "Smart Working",
    prof_holiday: "Festivo"
  },
  en: {
    enabled: "Enabled",
    heating: "Heating",
    heating_active: "Active Heating",
    idle: "Standby (Idle)",
    off: "Off",
    excluded: "Zone Excluded",
    bypass_msg: "Zone Excluded / Bypassed",
    caldaia_circ: "Boiler/Circulator",
    system_active: "System Active",
    system_off: "System Off",
    searching: "Searching...",
    master_not_found: "Master not found",
    temp_detected: "Detected",
    custom_error: "Multizone Thermostat Card Error",
    heat_mode: "Heat",
    primary: "Primary",
    secondary: "Secondary",
    primary_tooltip: "Primary (Calls for Heat)",
    secondary_tooltip: "Secondary (Passive)",
    bypass_tooltip: "Bypass (Excluded)",
    master_title: "Central Heating",
    thermostat: "Thermostat",
    edit_title: "Custom Title (Optional)",
    edit_climate: "Thermostat (Climate Entity)",
    edit_switch: "Zone Switch (Enable/Exclude)",
    preset_manual: "Manual",
    preset_eco: "Eco",
    preset_comfort: "Comfort",
    preset_sleep: "Sleep",
    preset_away: "Away",
    preset_card_title: "Global Preset",
    edit_preset: "Preset Entity (Optional)",
    // Diagnostic translations
    plant_health_title: "Plant Health & Boiler",
    plant_health_sub: "Hydraulic supervision and relay wear",
    cycles_label: "Ignition Frequency (Short-Cycle)",
    cycles_unit: "cycles/h",
    wear_low: "Low Wear (< 3.5 c/h)",
    wear_moderate: "Moderate Wear (3.5 - 5 c/h)",
    wear_high: "⚠️ High Short-Cycling (> 5 c/h)",
    runtime_24h: "Runtime Past 24h",
    runtime_sub: "Cumulative relay / burner activity",
    all_circuits_ok: "All circuits operational",
    no_anomalies: "No valve lock, leakage or short-cycling detected.",
    attention_cycles: "Warning: high boiler cycling frequency or parameters need tuning.",
    retention_label: "Retention (-1°C)",
    hours: "hours",
    learning: "Learning...",
    opt_insulation: "Great insulation",
    med_insulation: "Average insulation",
    fast_dispersion: "Fast heat loss",
    sizing_label: "Radiator Sizing",
    sizing_opt: "Heat output ratio OK",
    sizing_under: "Slow warm-up (undersized)",
    sizing_over: "High power (oversized)",
    sizing_waiting: "Waiting for thermal data",
    valve_status: "Valve Status:",
    valve_ok: "No anomalies",
    valve_closed_bypass: "Valve Closed (Bypass)",
    passive_heat_active: "Passive heat active",
    bypassed_tag: "BYPASSED",
    primary_tag: "PRIMARY",
    secondary_tag: "SECONDARY",
    target: "target",
    optimal: "OPTIMAL",
    warning: "WARNING",
    critical: "CRITICAL",
    passive_heat_active_tooltip: "Passive Heat ACTIVE (Click to disable)",
    passive_heat_inactive_tooltip: "Passive Heat inactive (Click to enable)",
    anomaly_detected: "Anomaly Detected",
    card_error_title: "Multizone Thermostat Card Error",
    ot_telemetry: "OpenTherm Telemetry",
    ot_dhw_active: "🚿 Hot Water (DHW)",
    ot_pressure: "Pressure",
    ot_flow_temp: "Supply Temp",
    ot_return_temp: "Return Temp",
    ot_modulation: "Modulation",
    ot_flame_status: "Flame Status",
    ot_flame_on: "🔥 Active",
    ot_flame_off: "Off",
    ot_condensing_ok: "Condensing OK",
    ot_return_hot: "High return (>54°C)",
sched_nav_title: "Schedule",
    sched_title: "Multizone Scheduler",
    sched_active: "Active",
    sched_paused: "Paused",
    sched_in_use: "Active Profile",
    sched_baseline: "Gap Baseline",
    sched_activate_btn: "Activate Profile / Expiry",
    sched_smart_return_btn: "Smart Return Planner",
    sched_reset_overrides: "Reset all overrides",
    sched_override_until: "Override until",
    sched_restore: "Restore",
    sched_explicit_off: "Explicit OFF",
    sched_turn_on: "Turn ON",
    sched_editor_profile: "Edit Profile",
    sched_duplicate: "Duplicate Profile",
    sched_bg_edit_notice: "Editing in background (Does not affect active profile)",
    sched_new_block: "+ New Time Block",
    sched_brush: "24h Brush",
    sched_erase: "Eraser",
    sched_copy_weekdays: "Copy day to Mon–Fri",
    sched_copy_weekend: "Copy day to Sat–Sun",
    sched_preset_matrix_title: "Multizone Preset Matrix (Room reference temperatures)",
    day_mon: "Monday",
    day_tue: "Tuesday",
    day_wed: "Wednesday",
    day_thu: "Thursday",
    day_fri: "Friday",
    day_sat: "Saturday",
    day_sun: "Sunday",
    prof_standard: "Standard",
    prof_smart_working: "Smart Working",
    prof_holiday: "Holiday"
  },
  ru: {
    enabled: "Включено",
    heating: "Отопление",
    heating_active: "Активный нагрев",
    idle: "Ожидание (Idle)",
    off: "Выкл",
    excluded: "Зона исключена",
    bypass_msg: "Зона исключена / Байпас",
    caldaia_circ: "Котел/Насос",
    system_active: "Система активна",
    system_off: "Система выключена",
    searching: "Поиск...",
    master_not_found: "Мастер не найден",
    temp_detected: "Текущая",
    custom_error: "Ошибка карточки Multizone Thermostat",
    heat_mode: "Нагрев",
    primary: "Основная",
    secondary: "Вторичная",
    primary_tooltip: "Основная (запускает котел)",
    secondary_tooltip: "Вторичная (пассивная)",
    bypass_tooltip: "Байпас (исключена)",
    master_title: "Центральное отопление",
    thermostat: "Термостат",
    edit_title: "Пользовательское имя (опционально)",
    edit_climate: "Термостат (Climate Entity)",
    edit_switch: "Переключатель зоны",
    preset_manual: "Ручной",
    preset_eco: "Эко",
    preset_comfort: "Комфорт",
    preset_sleep: "Сон",
    preset_away: "Вне дома",
    preset_card_title: "Глобальный пресет",
    edit_preset: "Сущность пресета",
    // Diagnostic translations
    plant_health_title: "Здоровье системы и котла",
    plant_health_sub: "Гидравлический контроль и износ реле",
    cycles_label: "Частота розжига (Short-Cycle)",
    cycles_unit: "циклов/ч",
    wear_low: "Низкий износ (< 3.5 ц/ч)",
    wear_moderate: "Умеренный износ (3.5 - 5 ц/ч)",
    wear_high: "⚠️ Частые циклы (> 5 ц/ч)",
    runtime_24h: "Время работы за 24ч",
    runtime_sub: "Суммарная активность реле",
    all_circuits_ok: "Все контуры в норме",
    no_anomalies: "Заеданий, утечек и частых циклов не обнаружено.",
    attention_cycles: "Внимание: частый розжиг котла, требуется настройка параметров.",
    retention_label: "Удержание (-1°C)",
    hours: "ч",
    learning: "Обучение...",
    opt_insulation: "Отличная изоляция",
    med_insulation: "Средняя изоляция",
    fast_dispersion: "Быстрая потеря тепла",
    sizing_label: "Размер радиатора",
    sizing_opt: "Баланс мощности в норме",
    sizing_under: "Медленный прогрев",
    sizing_over: "Высокая мощность",
    sizing_waiting: "Ожидание данных",
    valve_status: "Статус клапана:",
    valve_ok: "Без аномалий",
    valve_closed_bypass: "Клапан закрыт (Байпас)",
    passive_heat_active: "Пассивное тепло активно",
    bypassed_tag: "БАЙПАС",
    primary_tag: "ОСНОВНАЯ",
    secondary_tag: "ВТОРИЧНАЯ",
    target: "цель",
    optimal: "ОПТИМАЛЬНО",
    warning: "ВНИМАНИЕ",
    critical: "КРИТИЧНО",
    passive_heat_active_tooltip: "Пассивный нагрев АКТИВЕН (Нажмите для отключения)",
    passive_heat_inactive_tooltip: "Пассивный нагрев неактивен (Нажмите для включения)",
    anomaly_detected: "Обнаружена аномалия",
    card_error_title: "Ошибка карточки Multizone Thermostat",
    ot_telemetry: "Телеметрия OpenTherm",
    ot_dhw_active: "🚿 Горячая вода (ГВС)",
    ot_pressure: "Давление",
    ot_flow_temp: "Подача воды",
    ot_return_temp: "Обратка воды",
    ot_modulation: "Модуляция",
    ot_flame_status: "Состояние пламени",
    ot_flame_on: "🔥 Горит",
    ot_flame_off: "Выкл",
    ot_condensing_ok: "Конденсация в норме",
    ot_return_hot: "Горячая обратка (>54°C)",
sched_nav_title: "Расписание",
    sched_title: "Multizone Планировщик",
    sched_active: "Активно",
    sched_paused: "На паузе",
    sched_in_use: "Используется",
    sched_baseline: "Базовый уровень вне интервалов",
    sched_activate_btn: "Активировать профиль / Срок",
    sched_smart_return_btn: "Умное возвращение (Smart Return)",
    sched_reset_overrides: "Сбросить все переопределения",
    sched_override_until: "Переопределение до",
    sched_restore: "Сбросить",
    sched_explicit_off: "Выключено вручную",
    sched_turn_on: "Включить",
    sched_editor_profile: "Редактор профиля",
    sched_duplicate: "Дублировать профиль",
    sched_bg_edit_notice: "Фоновое редактирование (не влияет на активный профиль)",
    sched_new_block: "+ Новый интервал",
    sched_brush: "Кисть 24ч",
    sched_erase: "Ластик",
    sched_copy_weekdays: "Копировать на Пн–Пт",
    sched_copy_weekend: "Копировать на Сб–Вс",
    sched_preset_matrix_title: "Матрица предустановок (Целевые температуры)",
    day_mon: "Понедельник",
    day_tue: "Вторник",
    day_wed: "Среда",
    day_thu: "Четверг",
    day_fri: "Пятница",
    day_sat: "Суббота",
    day_sun: "Воскресенье",
    prof_standard: "Стандарт",
    prof_smart_working: "Удалённая работа",
    prof_holiday: "Выходной"
  },
  fr: {
    enabled: "Activé",
    heating: "Chauffage",
    heating_active: "Chauffage Actif",
    idle: "En attente",
    off: "Désactivé",
    excluded: "Zone Exclue",
    bypass_msg: "Zone Exclue / Contournée",
    caldaia_circ: "Chaudière/Circulateur",
    system_active: "Système Actif",
    system_off: "Système Désactivé",
    searching: "Recherche...",
    master_not_found: "Maître non trouvé",
    temp_detected: "Détectée",
    custom_error: "Erreur de carte Multizone Thermostat",
    heat_mode: "Chauffer",
    primary: "Principale",
    secondary: "Secondaire",
    primary_tooltip: "Principale (Allume la chaudière)",
    secondary_tooltip: "Secondaire (Passive)",
    bypass_tooltip: "Contournement (Exclue)",
    master_title: "Chauffage Central",
    thermostat: "Thermostat",
    edit_title: "Titre Personnalisé (Optionnel)",
    edit_climate: "Thermostat (Entité Climate)",
    edit_switch: "Interrupteur de Zone",
    preset_manual: "Manuel",
    preset_eco: "Éco",
    preset_comfort: "Confort",
    preset_sleep: "Nuit",
    preset_away: "Absent",
    preset_card_title: "Préréglage Global",
    edit_preset: "Entité Préréglage",
    plant_health_title: "Santé de l'installation et Chaudière",
    plant_health_sub: "Supervision hydraulique et usure des relais",
    cycles_label: "Fréquence d'allumage (Court-cycle)",
    cycles_unit: "cycles/h",
    wear_low: "Usure Faible (< 3.5 c/h)",
    wear_moderate: "Usure Modérée (3.5 - 5 c/h)",
    wear_high: "⚠️ Court-cycle Élevé (> 5 c/h)",
    runtime_24h: "Fonctionnement dernières 24h",
    runtime_sub: "Activité cumulative du relais",
    all_circuits_ok: "Tous les circuits sont opérationnels",
    no_anomalies: "Aucun blocage de vanne, fuite ou court-cycle détecté.",
    attention_cycles: "Attention : fréquence d'allumage élevée, paramètres à optimiser.",
    retention_label: "Rétention (-1°C)",
    hours: "heures",
    learning: "Apprentissage...",
    opt_insulation: "Excellente isolation",
    med_insulation: "Isolation moyenne",
    fast_dispersion: "Dispersion rapide",
    sizing_label: "Dimensionnement Radiateur",
    sizing_opt: "Ratio de puissance OK",
    sizing_under: "Chauffe lente (sous-dimensionné)",
    sizing_over: "Puissance élevée (surdimensionné)",
    sizing_waiting: "En attente de données thermiques",
    valve_status: "État de la vanne :",
    valve_ok: "Aucune anomalie",
    valve_closed_bypass: "Vanne Fermée (Bypass)",
    passive_heat_active: "Chaleur passive active",
    bypassed_tag: "CONTOURNÉ",
    primary_tag: "PRINCIPALE",
    secondary_tag: "SECONDAIRE",
    target: "cible",
    optimal: "OPTIMAL",
    warning: "ATTENTION",
    critical: "CRITIQUE",
    passive_heat_active_tooltip: "Chaleur passive ACTIVE (Cliquez pour désactiver)",
    passive_heat_inactive_tooltip: "Chaleur passive inactive (Cliquez pour activer)",
    anomaly_detected: "Anomalie Détectée",
    card_error_title: "Erreur de carte Multizone Thermostat",
    ot_telemetry: "Télémétrie OpenTherm",
    ot_dhw_active: "🚿 Eau Chaude (ECS)",
    ot_pressure: "Pression",
    ot_flow_temp: "Départ eau",
    ot_return_temp: "Retour eau",
    ot_modulation: "Modulation",
    ot_flame_status: "État flamme",
    ot_flame_on: "🔥 Allumée",
    ot_flame_off: "Éteinte",
    ot_condensing_ok: "Condensation OK",
    ot_return_hot: "Retour chaud (>54°C)",
sched_nav_title: "Programmation",
    sched_title: "Planificateur Multizone",
    sched_active: "Actif",
    sched_paused: "En pause",
    sched_in_use: "En cours",
    sched_baseline: "Ligne de base hors créneau",
    sched_activate_btn: "Activer Profil / Expiration",
    sched_smart_return_btn: "Retour Intelligent (Smart Return)",
    sched_reset_overrides: "Réinitialiser toutes les dérogations",
    sched_override_until: "Dérogation jusqu'à",
    sched_restore: "Rétablir",
    sched_explicit_off: "Éteint Explicite",
    sched_turn_on: "Rallumer",
    sched_editor_profile: "Modifier le profil",
    sched_duplicate: "Dupliquer profil",
    sched_bg_edit_notice: "Modification en arrière-plan (n'affecte pas le profil actif)",
    sched_new_block: "+ Nouveau créneau",
    sched_brush: "Pinceau 24h",
    sched_erase: "Gomme",
    sched_copy_weekdays: "Copier le jour sur Lun–Ven",
    sched_copy_weekend: "Copier le jour sur Sam–Dim",
    sched_preset_matrix_title: "Matrice de Préréglages Multizone",
    day_mon: "Lundi",
    day_tue: "Mardi",
    day_wed: "Mercredi",
    day_thu: "Jeudi",
    day_fri: "Vendredi",
    day_sat: "Samedi",
    day_sun: "Dimanche",
    prof_standard: "Standard",
    prof_smart_working: "Télétravail",
    prof_holiday: "Vacances"
  },
  de: {
    enabled: "Aktiviert",
    heating: "Heizen",
    heating_active: "Heizung Aktiv",
    idle: "Standby",
    off: "Aus",
    excluded: "Zone Ausgeschlossen",
    bypass_msg: "Zone Ausgeschlossen / Umgangen",
    caldaia_circ: "Kessel/Umwälzpumpe",
    system_active: "System Aktiv",
    system_off: "System Aus",
    searching: "Suchen...",
    master_not_found: "Master nicht gefunden",
    temp_detected: "Erkannt",
    custom_error: "Multizone Thermostat Karte Fehler",
    heat_mode: "Heizen",
    primary: "Primär",
    secondary: "Sekundär",
    primary_tooltip: "Primär (Schaltet Kessel ein)",
    secondary_tooltip: "Sekundär (Passiv)",
    bypass_tooltip: "Bypass (Ausgeschlossen)",
    master_title: "Zentralheizung",
    thermostat: "Thermostat",
    edit_title: "Benutzerdefinierter Titel (Optional)",
    edit_climate: "Thermostat (Climate-Entität)",
    edit_switch: "Zonenschalter",
    preset_manual: "Manuell",
    preset_eco: "Eco",
    preset_comfort: "Komfort",
    preset_sleep: "Nacht",
    preset_away: "Abwesend",
    preset_card_title: "Globales Preset",
    edit_preset: "Preset-Entität",
    plant_health_title: "Anlagenzustand & Kessel",
    plant_health_sub: "Hydrauliküberwachung und Relaisverschleiß",
    cycles_label: "Zündhäufigkeit (Kurztakten)",
    cycles_unit: "Zyklen/h",
    wear_low: "Geringer Verschleiß (< 3.5 Z/h)",
    wear_moderate: "Mittlerer Verschleiß (3.5 - 5 Z/h)",
    wear_high: "⚠️ Hohes Kurztakten (> 5 Z/h)",
    runtime_24h: "Laufzeit letzte 24h",
    runtime_sub: "Kumulierte Relaisaktivität",
    all_circuits_ok: "Alle Kreise betriebsbereit",
    no_anomalies: "Keine Ventilblockierung, Leckage oder Kurztakten erkannt.",
    attention_cycles: "Achtung: Hohe Zündhäufigkeit, Parameter optimieren.",
    retention_label: "Wärmespeicherung (-1°C)",
    hours: "Stunden",
    learning: "Lernen...",
    opt_insulation: "Hervorragende Isolierung",
    med_insulation: "Mittlere Isolierung",
    fast_dispersion: "Schneller Wärmeverlust",
    sizing_label: "Heizkörperdimensionierung",
    sizing_opt: "Leistungsverhältnis OK",
    sizing_under: "Langsames Aufheizen (unterdimensioniert)",
    sizing_over: "Hohe Leistung (überdimensioniert)",
    sizing_waiting: "Warten auf thermische Daten",
    valve_status: "Ventilstatus:",
    valve_ok: "Keine Anomalien",
    valve_closed_bypass: "Ventil Geschlossen (Bypass)",
    passive_heat_active: "Passive Wärme aktiv",
    bypassed_tag: "UMGANGEN",
    primary_tag: "PRIMÄR",
    secondary_tag: "SEKUNDÄR",
    target: "ziel",
    optimal: "OPTIMAL",
    warning: "WARNUNG",
    critical: "KRITISCH",
    passive_heat_active_tooltip: "Passive Heizung AKTIV (Klicken zum Deaktivieren)",
    passive_heat_inactive_tooltip: "Passive Heizung inaktiv (Klicken zum Aktivieren)",
    anomaly_detected: "Anomalie Erkannt",
    card_error_title: "Multizone Thermostat Karte Fehler",
    ot_telemetry: "OpenTherm-Telemetrie",
    ot_dhw_active: "🚿 Warmwasser (WW)",
    ot_pressure: "Druck",
    ot_flow_temp: "Vorlauftemp.",
    ot_return_temp: "Rücklauftemp.",
    ot_modulation: "Modulation",
    ot_flame_status: "Flammenstatus",
    ot_flame_on: "🔥 An",
    ot_flame_off: "Aus",
    ot_condensing_ok: "Brennwert OK",
    ot_return_hot: "Hoher Rücklauf (>54°C)",
sched_nav_title: "Zeitplan",
    sched_title: "Multizone Zeitplan",
    sched_active: "Aktiv",
    sched_paused: "Pausiert",
    sched_in_use: "In Benutzung",
    sched_baseline: "Basiswert außerhalb",
    sched_activate_btn: "Profil aktivieren / Ablauf",
    sched_smart_return_btn: "Intelligente Rückkehr (Smart Return)",
    sched_reset_overrides: "Alle Übersteuerungen zurücksetzen",
    sched_override_until: "Übersteuerung bis",
    sched_restore: "Zurücksetzen",
    sched_explicit_off: "Explizit AUS",
    sched_turn_on: "Einschalten",
    sched_editor_profile: "Profil bearbeiten",
    sched_bg_edit_notice: "Hintergrundbearbeitung (beeinflusst aktives Profil nicht)",
    sched_new_block: "+ Neuer Zeitblock",
    sched_brush: "24h Pinsel",
    sched_erase: "Radierer",
    sched_copy_weekdays: "Tag auf Mo–Fr kopieren",
    sched_copy_weekend: "Tag auf Sa–So kopieren",
    sched_preset_matrix_title: "Multizone Preset-Matrix",
    day_mon: "Montag",
    day_tue: "Dienstag",
    day_wed: "Mittwoch",
    day_thu: "Donnerstag",
    day_fri: "Freitag",
    day_sat: "Samstag",
    day_sun: "Sonntag",
    prof_standard: "Standard",
    prof_smart_working: "Homeoffice",
    prof_holiday: "Feiertag"
  },
  es: {
    enabled: "Activado",
    heating: "Calefacción",
    heating_active: "Calefacción Activa",
    idle: "En espera",
    off: "Apagado",
    excluded: "Zona Excluida",
    bypass_msg: "Zona Excluida / Ignorada",
    caldaia_circ: "Caldera/Bomba",
    system_active: "Sistema Activo",
    system_off: "Sistema Apagado",
    searching: "Buscando...",
    master_not_found: "Maestro no encontrado",
    temp_detected: "Detectada",
    custom_error: "Error en tarjeta Multizone Thermostat",
    heat_mode: "Calor",
    primary: "Principal",
    secondary: "Secundaria",
    primary_tooltip: "Principal (Enciende la caldera)",
    secondary_tooltip: "Secundaria (Pasiva)",
    bypass_tooltip: "Ignorar (Excluida)",
    master_title: "Calefacción Central",
    thermostat: "Termostato",
    edit_title: "Título Personalizado (Opcional)",
    edit_climate: "Termostato (Entidad Climate)",
    edit_switch: "Interruptor de Zona",
    preset_manual: "Manual",
    preset_eco: "Eco",
    preset_comfort: "Confort",
    preset_sleep: "Noche",
    preset_away: "Ausente",
    preset_card_title: "Preajuste Global",
    edit_preset: "Entidad de Preajuste",
    plant_health_title: "Salud de la Planta y Caldera",
    plant_health_sub: "Supervisión hidráulica y desgaste de relés",
    cycles_label: "Frecuencia de encendido (Ciclo corto)",
    cycles_unit: "ciclos/h",
    wear_low: "Desgaste Bajo (< 3.5 c/h)",
    wear_moderate: "Desgaste Moderado (3.5 - 5 c/h)",
    wear_high: "⚠️ Ciclo corto elevado (> 5 c/h)",
    runtime_24h: "Funcionamiento últimas 24h",
    runtime_sub: "Actividad acumulativa del relé",
    all_circuits_ok: "Todos los circuitos operativos",
    no_anomalies: "No se detectaron bloqueos de válvulas, fugas ni ciclos cortos.",
    attention_cycles: "Atención: alta frecuencia de encendido, optimizar parámetros.",
    retention_label: "Retención (-1°C)",
    hours: "horas",
    learning: "Aprendiendo...",
    opt_insulation: "Excelente aislamiento",
    med_insulation: "Aislamiento medio",
    fast_dispersion: "Pérdida de calor rápida",
    sizing_label: "Tamaño del radiador",
    sizing_opt: "Relación de potencia OK",
    sizing_under: "Calentamiento lento (infradimensionado)",
    sizing_over: "Potencia elevada (sobredimensionado)",
    sizing_waiting: "Esperando datos térmicos",
    valve_status: "Estado de la válvula:",
    valve_ok: "Sin anomalías",
    valve_closed_bypass: "Válvula Cerrada (Bypass)",
    passive_heat_active: "Calor pasivo activo",
    bypassed_tag: "IGNORADA",
    primary_tag: "PRINCIPAL",
    secondary_tag: "SECUNDARIA",
    target: "objetivo",
    optimal: "ÓPTIMO",
    warning: "ADVERTENCIA",
    critical: "CRÍTICO",
    passive_heat_active_tooltip: "Calor Pasivo ACTIVO (Clic para desactivar)",
    passive_heat_inactive_tooltip: "Calor Pasivo inactivo (Clic para activar)",
    anomaly_detected: "Anomalía Detectada",
    card_error_title: "Error en tarjeta Multizone Thermostat",
    ot_telemetry: "Telemetría OpenTherm",
    ot_dhw_active: "🚿 Agua Caliente (ACS)",
    ot_pressure: "Presión",
    ot_flow_temp: "Impulsión agua",
    ot_return_temp: "Retorno agua",
    ot_modulation: "Modulación",
    ot_flame_status: "Estado llama",
    ot_flame_on: "🔥 Encendida",
    ot_flame_off: "Apagada",
    ot_condensing_ok: "Condensación OK",
    ot_return_hot: "Retorno caliente (>54°C)",
sched_nav_title: "Programación",
    sched_title: "Planificador Multizona",
    sched_active: "Activo",
    sched_paused: "En pausa",
    sched_in_use: "En uso",
    sched_baseline: "Línea base fuera de bloque",
    sched_activate_btn: "Activar Perfil / Caducidad",
    sched_smart_return_btn: "Retorno Inteligente (Smart Return)",
    sched_reset_overrides: "Restablecer todas las anulaciones",
    sched_override_until: "Anulación hasta",
    sched_restore: "Restablecer",
    sched_explicit_off: "Apagado Explícito",
    sched_turn_on: "Encender",
    sched_editor_profile: "Editar perfil",
    sched_duplicate: "Duplicar perfil",
    sched_bg_edit_notice: "Edición en segundo plano (no afecta al perfil activo)",
    sched_new_block: "+ Nuevo bloque de tiempo",
    sched_brush: "Pincel 24h",
    sched_erase: "Borrador",
    sched_copy_weekdays: "Copiar día a Lun–Vie",
    sched_copy_weekend: "Copiar día a Sáb–Dom",
    sched_preset_matrix_title: "Matriz de Ajustes Multizona",
    day_mon: "Lunes",
    day_tue: "Martes",
    day_wed: "Miércoles",
    day_thu: "Jueves",
    day_fri: "Viernes",
    day_sat: "Sábado",
    day_sun: "Domingo",
    prof_standard: "Estándar",
    prof_smart_working: "Teletrabajo",
    prof_holiday: "Festivo"
  }
};

function getTranslation(hass, key) {
  const lang = hass && hass.language ? hass.language.split('-')[0] : 'en';
  const translations = TRANSLATIONS[lang] || TRANSLATIONS['en'];
  return translations[key] || TRANSLATIONS['en'][key] || key;
}

// Helper function to auto-discover the bypass switch for a climate entity
function autoDiscoverSwitch(hass, climateId) {
  if (!hass || !hass.states || !climateId) return "";
  for (const entityId of Object.keys(hass.states)) {
    // Check both legacy switches and new select entities for the climate_entity attribute
    if ((entityId.startsWith("select.") || entityId.startsWith("switch.")) && 
        hass.states[entityId].attributes && 
        hass.states[entityId].attributes.climate_entity === climateId) {
      return entityId;
    }
  }
  
  // Fallback: check if the entityId contains the climate device name AND is a zone_mode entity
  const rawName = climateId.split('.')[1] || "";
  const slug = rawName.replace(/^multizone_thermostat_/, "");
  for (const entityId of Object.keys(hass.states)) {
    if (entityId.startsWith("select.") && 
        (entityId.includes(slug) || (rawName && entityId.includes(rawName))) &&
        (entityId.includes("mode") || entityId.includes("zone"))) {
      return entityId;
    }
  }
  
  return "";
}

// Helper function to auto-discover the master switch entity
function findMasterEntity(hass) {
  if (!hass) return null;
  
  // Search for switch with multizone_type: master attribute
  const found = Object.keys(hass.states).find(key => {
    const state = hass.states[key];
    return state.attributes && state.attributes.multizone_type === "master";
  });
  if (found) return found;

  // Fallback to name search
  return Object.keys(hass.states).find(key => {
    return key.startsWith('switch.') && key.includes('heating_master');
  }) || null;
}

// Helper function to auto-discover the preset select entity
function findPresetEntity(hass) {
  if (!hass) return null;
  
  // Robust method: find the select entity that has our specific global presets
  const found = Object.keys(hass.states).find(key => {
    if (!key.startsWith('select.')) return false;
    const state = hass.states[key];
    if (state && state.attributes && state.attributes.options) {
      const opts = state.attributes.options;
        if (opts.includes('manual') && opts.includes('comfort') && opts.includes('sleep')) {
          return true;
        }
    }
    return false;
  });
  if (found) return found;

  // Fallback
  return Object.keys(hass.states).find(key => {
    return key.startsWith('select.') && key.includes('global_preset');
  }) || null;
}


/* ==================== BUTTON CARD CLASS ==================== */
class MultizoneThermostatButtonCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.renderStructure();
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Specificare un termostato (climate entity)");
    }
    this._config = config;
  }

  getCardSize() {
    return 3;
  }

  static getConfigElement() {
    return document.createElement("multizone-thermostat-card-editor");
  }

  static getStubConfig() {
    return {
      entity: "",
      switch: "",
      title: ""
    };
  }

  updateCard() {
    if (!this._hass || !this._hass.states) return;
    if (!this._hass || !this._config) return;

    const climateEntity = this._config.entity;
    let switchEntity = this._config.switch;

    // Auto-migrate legacy zone_enable switch configs
    if (switchEntity && switchEntity.endsWith('_zone_enable')) {
      switchEntity = null;
    }

    if (!switchEntity || !this._hass.states[switchEntity]) {
      const discovered = autoDiscoverSwitch(this._hass, climateEntity);
      if (discovered) switchEntity = discovered;
      // Only update config if we discovered something new so we don't keep searching
      if (discovered && this._config.switch !== discovered) {
        this._config = {...this._config, switch: discovered};
      }
    }

    const climateState = this._hass.states[climateEntity];
    const switchState = switchEntity ? this._hass.states[switchEntity] : null;

    if (!climateState) {
      this.renderError(getTranslation(this._hass, 'custom_error') + `: ${climateEntity} not found.`);
      return;
    }

    if (!this._rendered) {
      this.renderStructure();
    }

    const currentTemp = climateState.attributes.current_temperature;
    const targetTemp = climateState.attributes.temperature;
    const hvacMode = climateState.state;
    const hvacAction = climateState.attributes.hvac_action;
    
    // Use temporary switch state if toggled locally to avoid flickering
    const actualSwitchState = this._tempSwitchState !== undefined 
      ? this._tempSwitchState 
      : (switchState ? switchState.state : "primary");

    const title = this._config.title || climateState.attributes.friendly_name || getTranslation(this._hass, 'thermostat');

    // Update title
    this.shadowRoot.querySelector('.title').textContent = title;

    // Update segmented buttons state
    const segContainer = this.shadowRoot.querySelector('#zone-modes-container');
    const segPrimary = this.shadowRoot.querySelector('#seg-primary');
    const segSecondary = this.shadowRoot.querySelector('#seg-secondary');
    const segBypass = this.shadowRoot.querySelector('#seg-bypass');
    
    if (switchEntity) {
      if (segContainer) segContainer.style.display = 'flex';
      if (segPrimary) segPrimary.classList.toggle('active', actualSwitchState === "primary" || actualSwitchState === "on");
      if (segSecondary) segSecondary.classList.toggle('active', actualSwitchState === "secondary");
      if (segBypass) segBypass.classList.toggle('active', actualSwitchState === "bypass" || actualSwitchState === "off");
    } else {
      if (segContainer) segContainer.style.display = 'none';
    }

    // Apply active/disabled styling
    const controlsArea = this.shadowRoot.querySelector('.thermostat-body');
    const wrapper = this.shadowRoot.querySelector('#wrapper');
    const disabledOverlay = this.shadowRoot.querySelector('.disabled-msg');
    const disabledMsgBox = this.shadowRoot.querySelector('.disabled-msg-box');
    if (disabledMsgBox) {
      disabledMsgBox.innerHTML = `<ha-icon icon="mdi:alert-circle-outline" style="margin-right: 6px;"></ha-icon>${getTranslation(this._hass, 'bypass_msg')}`;
    }
    if (actualSwitchState !== "bypass" && actualSwitchState !== "off") {
      controlsArea.classList.remove('disabled');
      wrapper.classList.remove('disabled');
      if (disabledOverlay) disabledOverlay.style.display = 'none';
      if (hvacAction === 'heating') {
        controlsArea.classList.add('heating');
      } else {
        controlsArea.classList.remove('heating');
      }
    } else {
      controlsArea.classList.add('disabled');
      wrapper.classList.add('disabled');
      if (disabledOverlay) disabledOverlay.style.display = 'block';
    }

    // Update temperatures
    const tempCurrentEl = this.shadowRoot.querySelector('.temp-current');
    if (tempCurrentEl) {
      const curStr = currentTemp !== undefined ? `${currentTemp}°C` : '--°C';
      tempCurrentEl.innerHTML = `<span class="temp-current-val">${curStr}</span>`;
    }
    const step = this.getStep(climateState);
    const decimals = step.toString().includes('.') ? (step.toString().split('.')[1] || '').length : 0;
    let targetDisplay = '--';
    if (targetTemp !== undefined && targetTemp !== null) {
      const num = parseFloat(targetTemp);
      targetDisplay = !isNaN(num) ? (decimals > 0 && !Number.isInteger(num) ? num.toFixed(decimals) : num) : targetTemp;
    }
    this.shadowRoot.querySelector('.temp-target-val').textContent = `${targetDisplay}°C`;
    
    const tempTargetEl = this.shadowRoot.querySelector('.temp-target');
    if (tempTargetEl) {
      if (hvacAction === 'heating') {
        tempTargetEl.classList.add('heating');
      } else {
        tempTargetEl.classList.remove('heating');
      }
    }

    const badge = this.shadowRoot.querySelector('.status-badge');
    badge.className = 'status-badge';
    if (actualSwitchState === "bypass" || actualSwitchState === "off") {
      badge.innerHTML = "";
    } else if (actualSwitchState === "secondary") {
      badge.style.color = '#607d8b';
      badge.innerHTML = `<ha-icon icon="mdi:link-variant" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>${getTranslation(this._hass, 'secondary')}`;
    } else {
      badge.style.color = 'var(--primary-color, #03a9f4)';
      badge.innerHTML = `<ha-icon icon="mdi:star-circle-outline" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>${getTranslation(this._hass, 'primary')}`;
    }
  }


  renderStructure() {
    this.shadowRoot.innerHTML = '';
    const card = document.createElement('ha-card');
    const style = document.createElement('style');

    style.textContent = `
      ha-card {
        padding: 16px;
        position: relative;
        overflow: hidden;
      }
      .wrapper {
        position: relative;
        display: block;
      }
      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
      }
      .title {
        font-size: 18px;
        font-weight: 500;
        color: var(--primary-text-color);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 70%;
      }
      .switch-container {
        display: flex;
        align-items: center;
        z-index: 10;
      }
      .switch-container label {
        margin-right: 8px;
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      /* Segmented Control Styles */
      .segmented-control {
        display: flex;
        align-items: center;
        background-color: var(--secondary-background-color, #e0e0e0);
        border-radius: 8px;
        padding: 2px;
        position: relative;
      }
      .seg-btn {
        background: transparent;
        border: none;
        color: var(--secondary-text-color);
        padding: 6px 12px;
        cursor: pointer;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.3s, color 0.3s;
      }
      .seg-btn.active {
        background-color: var(--primary-color, #03a9f4);
        color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
      }
      .seg-btn ha-icon {
        --mdc-icon-size: 18px;
      }

      .thermostat-body {
        transition: opacity 0.3s ease;
        border-radius: var(--ha-card-border-radius, 12px);
        position: relative;
      }
      .thermostat-body.disabled {
        opacity: 0.25;
        pointer-events: none;
      }

      .disabled-msg {
        display: none;
        position: absolute;
        top: 40px; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.15);
        z-index: 10;
        border-radius: 0 0 var(--ha-card-border-radius, 12px) var(--ha-card-border-radius, 12px);
        backdrop-filter: blur(2px);
      }
      .disabled-msg-box {
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        background: var(--card-background-color);
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: 500;
        color: var(--secondary-text-color);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        white-space: nowrap;
      }

      .controls-container {
        display: flex;
        justify-content: space-around;
        align-items: center;
        margin: 16px 0;
      }
      .btn-temp {
        width: 50px;
        height: 50px;
        border-radius: 50%;
        border: 1px solid var(--divider-color);
        background-color: var(--secondary-background-color);
        color: var(--primary-text-color);
        font-size: 24px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background-color 0.2s, transform 0.1s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
      }
      .btn-temp:hover {
        background-color: var(--divider-color);
      }
      .btn-temp:active {
        transform: scale(0.95);
      }

      .temp-display {
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;
        z-index: 0;
      }
      .thermostat-body.heating .temp-display::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 440px;
        height: 440px;
        border-radius: 50%;
        background: radial-gradient(closest-side, rgba(255, 111, 0, 0.35) 0%, rgba(255, 111, 0, 0.15) 30%, rgba(255, 111, 0, 0.02) 75%, transparent 100%);
        z-index: -1;
        pointer-events: none;
        animation: pulse-halo 2s infinite alternate;
      }
      @keyframes pulse-halo {
        0% { opacity: 0.8; transform: translate(-50%, -50%) scale(0.95); }
        100% { opacity: 1; transform: translate(-50%, -50%) scale(1.05); }
      }
      .temp-target-val {
        font-size: 42px;
        font-weight: 300;
        color: var(--primary-text-color);
        line-height: 1.1;
        transition: text-shadow 0.3s, color 0.3s;
      }
      .temp-target.heating .temp-target-val {
        color: rgb(255, 152, 0);
        text-shadow: 0 0 10px rgba(255, 152, 0, 0.5), 0 0 20px rgba(255, 152, 0, 0.3);
        animation: pulse-glow 1.5s infinite alternate;
      }
      @keyframes pulse-glow {
        0% { text-shadow: 0 0 10px rgba(255, 152, 0, 0.5), 0 0 20px rgba(255, 152, 0, 0.3); }
        100% { text-shadow: 0 0 15px rgba(255, 111, 0, 0.9), 0 0 30px rgba(255, 111, 0, 0.6); }
      }
      .temp-current {
        font-size: 14px;
        color: var(--secondary-text-color);
        margin-top: 4px;
      }

      .status-bar {
        display: flex;
        justify-content: center;
        margin-bottom: 16px;
      }
      .status-badge {
        display: inline-flex;
        align-items: center;
        font-size: 14px;
        font-weight: 400;
        color: var(--secondary-text-color);
      }
      .status-badge.heating { color: rgb(255, 111, 0); }
      .status-badge.idle { color: rgb(0, 150, 136); }
      .status-badge.disabled { color: rgb(244, 67, 54); }

      .glow-flame {
        animation: pulse-flame 1.5s infinite alternate;
      }
      @keyframes pulse-flame {
        0% { transform: scale(1); filter: drop-shadow(0 0 1px rgba(255,111,0,0.5)); }
        100% { transform: scale(1.1); filter: drop-shadow(0 0 5px rgba(255,111,0,0.8)); }
      }

    `;

    card.innerHTML = `
      <div class="wrapper" id="wrapper">
        <div class="header">
          <div class="title">Termostato</div>
          <div class="segmented-control" id="zone-modes-container">
            <button class="seg-btn primary" id="seg-primary"><ha-icon icon="mdi:star-circle-outline"></ha-icon></button>
            <button class="seg-btn secondary" id="seg-secondary"><ha-icon icon="mdi:link-variant"></ha-icon></button>
            <button class="seg-btn bypass" id="seg-bypass"><ha-icon icon="mdi:cancel"></ha-icon></button>
          </div>
        </div>

        <div class="disabled-msg">
          <div class="disabled-msg-box">
            <ha-icon icon="mdi:alert-circle-outline" style="margin-right: 6px;"></ha-icon>Zona Esclusa / Bypassata
          </div>
        </div>

        <div class="thermostat-body">
          <div class="controls-container">
            <button class="btn-temp" id="temp-down">-</button>
            <div class="temp-display">
              <div class="temp-target">
                <span class="temp-target-val">--°C</span>
              </div>
              <div class="temp-current"><span class="temp-current-val">--°C</span></div>
            </div>
            <button class="btn-temp" id="temp-up">+</button>
          </div>

          <div class="status-bar">
            <div class="status-badge"></div>
          </div>


        </div>
      </div>
    `;

    // Hook events
    card.querySelector('#seg-primary').addEventListener('click', () => this.setZoneMode("primary"));
    card.querySelector('#seg-secondary').addEventListener('click', () => this.setZoneMode("secondary"));
    card.querySelector('#seg-bypass').addEventListener('click', () => this.setZoneMode("bypass"));

    card.querySelector('#temp-down').addEventListener('click', () => this.changeTemp(-1));
    card.querySelector('#temp-up').addEventListener('click', () => this.changeTemp(1));



    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  setZoneMode(mode) {
    const switchEntity = this._config.switch;
    if (!switchEntity) return;

    this._tempSwitchState = mode;
    this.updateCard(); // immediate local UI update
    
    // If it's a switch entity (legacy), map back to on/off
    if (switchEntity.startsWith("switch.")) {
      const enable = mode !== "bypass";
      this._hass.callService("switch", enable ? "turn_on" : "turn_off", {
        entity_id: switchEntity
      });
    } else {
      // It's a select entity
      this._hass.callService("select", "select_option", {
        entity_id: switchEntity,
        option: mode
      });
    }

    if (this._tempTimer) clearTimeout(this._tempTimer);
    this._tempTimer = setTimeout(() => {
      this._tempSwitchState = undefined;
      this.updateCard();
    }, 1000);
  }

  getStep(climateState) {
    if (this._config && (this._config.step !== undefined || this._config.target_temp_step !== undefined)) {
      const cfgStep = parseFloat(this._config.step ?? this._config.target_temp_step);
      if (!isNaN(cfgStep) && cfgStep > 0) return cfgStep;
    }
    const state = climateState || (this._hass && this._config && this._config.entity ? this._hass.states[this._config.entity] : null);
    if (state && state.attributes && state.attributes.target_temp_step !== undefined && state.attributes.target_temp_step !== null) {
      const attrStep = parseFloat(state.attributes.target_temp_step);
      if (!isNaN(attrStep) && attrStep > 0) return attrStep;
    }
    return 0.5;
  }

  changeTemp(stepOrDirection) {
    const climateEntity = this._config.entity;
    const state = this._hass.states[climateEntity];
    if (!state) return;

    const currentTarget = state.attributes.temperature;
    if (currentTarget === undefined || currentTarget === null) return;

    const step = this.getStep(state);

    let delta = 0;
    if (typeof stepOrDirection === 'number') {
      if (stepOrDirection > 0) {
        delta = step;
      } else if (stepOrDirection < 0) {
        delta = -step;
      }
    } else {
      delta = step;
    }

    const stepStr = step.toString();
    const decimals = stepStr.includes('.') ? (stepStr.split('.')[1] || '').length : 0;
    const rawTarget = Math.round((currentTarget + delta) / step) * step;
    const newTarget = parseFloat(rawTarget.toFixed(decimals));

    const minTemp = state.attributes.min_temp !== undefined ? parseFloat(state.attributes.min_temp) : undefined;
    const maxTemp = state.attributes.max_temp !== undefined ? parseFloat(state.attributes.max_temp) : undefined;
    let clampedTarget = newTarget;
    if (minTemp !== undefined && !isNaN(minTemp)) clampedTarget = Math.max(clampedTarget, minTemp);
    if (maxTemp !== undefined && !isNaN(maxTemp)) clampedTarget = Math.min(clampedTarget, maxTemp);

    this._hass.callService("climate", "set_temperature", {
      entity_id: climateEntity,
      temperature: clampedTarget
    });
  }

  disconnectedCallback() {
    // HTMLElement has no disconnectedCallback, so do NOT call super
    if (this._tempTimer) {
        clearTimeout(this._tempTimer);
        this._tempTimer = null;
    }
  }

  renderError(msg) {
    this.shadowRoot.innerHTML = `
      <ha-card style="padding: 16px; color: red;">
        <h3>${this._hass ? getTranslation(this._hass, 'card_error_title') : 'Multizone Thermostat Card Error'}</h3>
        <p>${msg}</p>
      </ha-card>
    `;
    this._rendered = false;
  }
}


/* ==================== DIAL (NATIVE WRAPPER) CARD CLASS ==================== */
class MultizoneThermostatDialCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.renderStructure();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._childCard) {
      this._childCard.hass = hass;
    }
    this.updateCard();
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Specificare un termostato (climate entity)");
    }
    this._config = config;
    this.loadHelpers();
  }

  async loadHelpers() {
    try {
      this._helpers = await window.loadCardHelpers();
      this.createChildCard();
    } catch (err) {
      console.error("Errore nel caricamento dei card helpers di Home Assistant:", err);
    }
  }

  getCardSize() {
    return 3;
  }

  static getConfigElement() {
    return document.createElement("multizone-thermostat-card-editor");
  }

  static getStubConfig() {
    return {
      entity: "",
      switch: "",
      title: ""
    };
  }

  createChildCard() {
    if (!this._helpers || !this._config) return;

    const cardConfig = {
      type: "thermostat",
      entity: this._config.entity,
      name: " ", // Empty space to hide native title and avoid duplicate titles
    };

    this._childCard = this._helpers.createCardElement(cardConfig);
    
    if (this._hass) {
      this._childCard.hass = this._hass;
    }

    const body = this.shadowRoot.querySelector('#card-body');
    if (body) {
      body.innerHTML = '';
      body.appendChild(this._childCard);
    }
  }

  updateCard() {
    if (!this._hass || !this._hass.states) return;
    if (!this._hass || !this._config) return;

    const card = this.shadowRoot.querySelector('ha-card');
    if (card) {
      if (this._config.height) card.style.height = this._config.height;
      if (this._config.width) card.style.width = this._config.width;
      if (this._config.border_radius) card.style.borderRadius = this._config.border_radius;
      if (this._config.min_height) card.style.minHeight = this._config.min_height;
      if (this._config.max_height) card.style.maxHeight = this._config.max_height;
      if (this._config.padding) card.style.padding = this._config.padding;
    }

    const climateEntity = this._config.entity;
    let switchEntity = this._config.switch;
    
    // Auto-migrate legacy zone_enable switch configs
    if (switchEntity && switchEntity.endsWith('_zone_enable')) {
      switchEntity = null;
    }

    if (!switchEntity || !this._hass.states[switchEntity]) {
      const discovered = autoDiscoverSwitch(this._hass, climateEntity);
      if (discovered) switchEntity = discovered;
      if (discovered && this._config.switch !== discovered) {
        this._config = {...this._config, switch: discovered};
      }
    }
    
    const climateState = this._hass.states[climateEntity];
    const switchState = switchEntity ? this._hass.states[switchEntity] : null;

    if (!climateState) {
      this.renderError(getTranslation(this._hass, 'custom_error') + `: ${climateEntity} not found.`);
      return;
    }

    if (!this._rendered) {
      this.renderStructure();
    }

    let displayTitle = this._config.title || climateState.attributes.friendly_name || climateEntity;
    if (displayTitle) {
      displayTitle = displayTitle.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
    }

    const titleEl = this.shadowRoot.querySelector('.title');
    if (titleEl) {
      titleEl.textContent = displayTitle;
    }

    // Use temporary switch state if toggled locally to avoid flickering
    let actualSwitchState = "primary";
    if (this._tempSwitchState !== undefined) {
      actualSwitchState = this._tempSwitchState;
    } else if (switchState && switchState.state) {
      actualSwitchState = switchState.state;
    } else if (climateState && climateState.attributes && climateState.attributes.zone_mode) {
      actualSwitchState = climateState.attributes.zone_mode;
    }

    // Update segmented buttons state and tooltips
    const segPrimary = this.shadowRoot.querySelector('#seg-primary');
    const segSecondary = this.shadowRoot.querySelector('#seg-secondary');
    const segBypass = this.shadowRoot.querySelector('#seg-bypass');
    
    if (segPrimary) {
      segPrimary.classList.toggle('active', actualSwitchState === "primary" || actualSwitchState === "on");
      segPrimary.title = getTranslation(this._hass, 'primary_tooltip');
    }
    if (segSecondary) {
      segSecondary.classList.toggle('active', actualSwitchState === "secondary");
      segSecondary.title = getTranslation(this._hass, 'secondary_tooltip');
    }
    if (segBypass) {
      segBypass.classList.toggle('active', actualSwitchState === "bypass" || actualSwitchState === "off");
      segBypass.title = getTranslation(this._hass, 'bypass_tooltip');
    }
    
    // Update disabled overlay text
    const disabledMsgBox = this.shadowRoot.querySelector('.disabled-msg-box');
    if (disabledMsgBox) {
      disabledMsgBox.innerHTML = `<ha-icon icon="mdi:alert-circle-outline" style="margin-right: 6px;"></ha-icon>${getTranslation(this._hass, 'bypass_msg')}`;
    }

    // Update status text
    const badge = this.shadowRoot.querySelector('.status-badge');
    if (badge) {
      badge.className = 'status-badge';
      if (actualSwitchState === "bypass" || actualSwitchState === "off") {
        badge.innerHTML = "";
      } else if (actualSwitchState === "secondary") {
        badge.style.color = '#607d8b';
        badge.innerHTML = `<ha-icon icon="mdi:link-variant" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>${getTranslation(this._hass, 'secondary')}`;
      } else {
        badge.style.color = 'var(--primary-color, #03a9f4)';
        badge.innerHTML = `<ha-icon icon="mdi:star-circle-outline" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>${getTranslation(this._hass, 'primary')}`;
      }
    }

    // Apply active/disabled styling and overlay
    const wrapper = this.shadowRoot.querySelector('#wrapper');
    if (wrapper) {
      if (actualSwitchState !== "bypass" && actualSwitchState !== "off") {
        wrapper.classList.remove('disabled');
      } else {
        wrapper.classList.add('disabled');
      }
    }
  }

  renderStructure() {
    const style = document.createElement('style');

    style.textContent = `
      ha-card {
        padding: 16px;
        position: relative;
        overflow: hidden;
      }
      .wrapper {
        position: relative;
        display: block;
      }
      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
        padding-bottom: 4px;
        padding-left: 8px;
        position: relative;
        z-index: 20;
      }
      .title {
        font-size: 16px;
        font-weight: 500;
        color: var(--primary-text-color);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 60%;
      }
      .status-bar {
        position: absolute;
        top: 100px;
        left: 0;
        right: 0;
        display: flex;
        justify-content: center;
        z-index: 10;
        pointer-events: none;
      }
      .status-badge {
        display: inline-flex;
        align-items: center;
        font-size: 14px;
        font-weight: 400;
        color: var(--secondary-text-color);
      }
      .status-badge.heating { color: rgb(255, 111, 0); }
      .status-badge.idle { color: rgb(0, 150, 136); }
      .status-badge.disabled { color: rgb(244, 67, 54); }

      .glow-flame {
        animation: pulse-flame 1.5s infinite alternate;
      }
      @keyframes pulse-flame {
        0% { transform: scale(1); filter: drop-shadow(0 0 1px rgba(255,111,0,0.5)); }
        100% { transform: scale(1.1); filter: drop-shadow(0 0 5px rgba(255,111,0,0.8)); }
      }

      /* Segmented Control Styles */
      .segmented-control {
        display: flex;
        align-items: center;
        background-color: var(--secondary-background-color, #e0e0e0);
        border-radius: 8px;
        padding: 2px;
        position: relative;
        z-index: 21;
      }
      .seg-btn {
        background: transparent;
        border: none;
        color: var(--secondary-text-color);
        padding: 6px 12px;
        cursor: pointer;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.3s, color 0.3s;
      }
      .seg-btn.active {
        background-color: var(--primary-color, #03a9f4);
        color: white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
      }
      .seg-btn ha-icon {
        --mdc-icon-size: 18px;
      }

      .disabled-overlay {
        display: none;
        position: absolute;
        top: 40px; /* Positioned below our custom header, covering only the native card body */
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 8;
        background: rgba(0, 0, 0, 0.15);
        backdrop-filter: blur(2px);
        align-items: center;
        justify-content: center;
        border-radius: 0 0 var(--ha-card-border-radius, 12px) var(--ha-card-border-radius, 12px);
        pointer-events: none;
      }
      .disabled-msg-box {
        display: inline-flex;
        align-items: center;
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        padding: 10px 16px;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        color: var(--secondary-text-color);
        font-weight: 500;
        pointer-events: auto;
      }

      /* Native Thermostat card styles styling (custom variables are passed down shadow bounds) */
      #card-body {
        --ha-card-background: none;
        --ha-card-box-shadow: none;
        --ha-card-border-width: 0px;
        --ha-card-border-color: transparent;
        margin-top: -16px; /* pull the native card slightly up to align it nicely */
      }

      /* When zone is disabled: fade out the native card */
      .wrapper.disabled #card-body {
        opacity: 0.25;
        pointer-events: none;
      }
      .wrapper.disabled .disabled-overlay {
        display: flex;
      }
    `;

    const card = document.createElement('ha-card');
    
    const wrapper = document.createElement('div');
    wrapper.className = 'wrapper';
    wrapper.id = 'wrapper';

    // The layout renders our custom header inside our own ha-card.
    // The native card below is stripped of its borders/title/shadows.
    wrapper.innerHTML = `
      <div class="header">
        <div class="title" id="card-title">Termostato</div>
        <div class="segmented-control" id="zone-modes-container">
          <button class="seg-btn primary" id="seg-primary"><ha-icon icon="mdi:star-circle-outline"></ha-icon></button>
          <button class="seg-btn secondary" id="seg-secondary"><ha-icon icon="mdi:link-variant"></ha-icon></button>
          <button class="seg-btn bypass" id="seg-bypass"><ha-icon icon="mdi:cancel"></ha-icon></button>
        </div>
      </div>
      
      <div class="status-bar">
        <div class="status-badge"></div>
      </div>

      <div class="disabled-overlay">
        <div class="disabled-msg-box">
          <ha-icon icon="mdi:alert-circle-outline" style="margin-right: 6px;"></ha-icon>Zona Esclusa / Bypassata
        </div>
      </div>

      <div id="card-body"></div>
    `;

    // Hook events
    wrapper.querySelector('#seg-primary').addEventListener('click', () => this.setZoneMode("primary"));
    wrapper.querySelector('#seg-secondary').addEventListener('click', () => this.setZoneMode("secondary"));
    wrapper.querySelector('#seg-bypass').addEventListener('click', () => this.setZoneMode("bypass"));

    card.appendChild(wrapper);
    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  setZoneMode(mode) {
    let switchEntity = this._config.switch;
    if (!switchEntity || !this._hass.states[switchEntity]) {
      switchEntity = autoDiscoverSwitch(this._hass, this._config.entity);
      if (switchEntity) {
        this._config = {...this._config, switch: switchEntity};
      }
    }
    if (!switchEntity) return;

    this._tempSwitchState = mode;
    this.updateCard(); // immediate local UI update

    // If it's a switch entity (legacy), map back to on/off
    if (switchEntity.startsWith("switch.")) {
      const enable = mode !== "bypass";
      this._hass.callService("switch", enable ? "turn_on" : "turn_off", {
        entity_id: switchEntity
      });
    } else {
      // It's a select entity
      this._hass.callService("select", "select_option", {
        entity_id: switchEntity,
        option: mode
      });
    }

    if (this._tempTimer) clearTimeout(this._tempTimer);
    this._tempTimer = setTimeout(() => {
      this._tempSwitchState = undefined;
      this.updateCard();
    }, 1000);
  }

  disconnectedCallback() {
    // HTMLElement has no disconnectedCallback, so do NOT call super
    if (this._tempTimer) {
        clearTimeout(this._tempTimer);
        this._tempTimer = null;
    }
  }

  renderError(msg) {
    this.shadowRoot.innerHTML = `
      <ha-card style="padding: 16px; color: red;">
        <h3>${this._hass ? getTranslation(this._hass, 'card_error_title') : 'Multizone Thermostat Card Error'}</h3>
        <p>${msg}</p>
      </ha-card>
    `;
    this._rendered = false;
  }
}


/* ==================== UNIFIED CARD CONFIGURATION EDITOR ==================== */
class MultizoneThermostatCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  set hass(hass) {
    this._hass = hass;
    if (this._climatePicker) this._climatePicker.hass = hass;
    if (this._switchPicker) this._switchPicker.hass = hass;
    this.translateLabels();
  }

  setConfig(config) {
    this._config = config;
    this.render();
  }

  translateLabels() {
    if (!this._hass) return;
    const titleLabel = this.shadowRoot.querySelector('#title-label');
    if (titleLabel) titleLabel.textContent = getTranslation(this._hass, 'edit_title');
    const mainLabel = this.shadowRoot.querySelector('#main-label');
    if (mainLabel) mainLabel.textContent = getTranslation(this._hass, 'edit_climate');
    const switchLabel = this.shadowRoot.querySelector('#switch-label');
    if (switchLabel) switchLabel.textContent = getTranslation(this._hass, 'edit_switch');
  }

  render() {
    if (!this._config) return;
    
    // Only build DOM once — prevent focus loss on every keystroke
    if (this.shadowRoot && this.shadowRoot.querySelector('.card-editor-container')) {
        // Just update values if already built
        const titleInput = this.shadowRoot.querySelector('#card-title-input');
        if (titleInput && document.activeElement !== titleInput && this.shadowRoot.activeElement !== titleInput) {
            titleInput.value = this._config.title || '';
        }
        if (this._climatePicker) this._climatePicker.value = this._config.entity || '';
        if (this._switchPicker) this._switchPicker.value = this._config.switch || '';
        this.translateLabels();
        return;
    }

    const style = document.createElement('style');
    style.textContent = `
      .form-row {
        margin-bottom: 16px;
        display: flex;
        flex-direction: column;
      }
      label {
        font-weight: 500;
        margin-bottom: 8px;
        color: var(--primary-text-color);
      }
      input[type="text"] {
        padding: 10px;
        border-radius: 4px;
        border: 1px solid var(--divider-color);
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font-size: 14px;
      }
    `;

    const container = document.createElement('div');
    container.className = 'card-editor-container';

    // Title Row
    const titleRow = document.createElement('div');
    titleRow.className = 'form-row';
    const titleLabel = document.createElement('label');
    titleLabel.id = 'title-label';
    titleLabel.textContent = 'Titolo Personalizzato (Opzionale)';
    const titleInput = document.createElement('input');
    titleInput.type = 'text';
    titleInput.id = 'card-title-input';
    titleInput.value = this._config.title || '';
    titleInput.addEventListener('input', (e) => this._updateConfig('title', e.target.value));
    titleRow.appendChild(titleLabel);
    titleRow.appendChild(titleInput);
    container.appendChild(titleRow);

    // Climate Entity Picker Row
    const climateRow = document.createElement('div');
    climateRow.className = 'form-row';
    const climateLabel = document.createElement('label');
    climateLabel.id = 'main-label';
    climateLabel.textContent = 'Termostato (Climate Entity)';
    const climatePicker = document.createElement('ha-entity-picker');
    climatePicker.includeDomains = ['climate'];
    climatePicker.value = this._config.entity || '';
    climatePicker.hass = this._hass;
    
    // Automatically pre-fill the corresponding switch when the climate entity changes
    climatePicker.addEventListener('value-changed', (e) => {
      const selectedClimate = e.detail.value;
      const discoveredSwitch = autoDiscoverSwitch(this._hass, selectedClimate);
      
      const newConfig = { 
        ...this._config, 
        entity: selectedClimate,
        switch: discoveredSwitch || ''
      };
      
      this._switchPicker.value = discoveredSwitch || '';
      
      this.dispatchEvent(new CustomEvent('config-changed', {
        detail: { config: newConfig },
        bubbles: true,
        composed: true
      }));
    });
    
    this._climatePicker = climatePicker;
    climateRow.appendChild(climateLabel);
    climateRow.appendChild(climatePicker);
    container.appendChild(climateRow);

    // Switch Entity Picker Row
    const switchRow = document.createElement('div');
    switchRow.className = 'form-row';
    const switchLabel = document.createElement('label');
    switchLabel.id = 'switch-label';
    switchLabel.textContent = 'Switch di Zona (Abilita/Escludi)';
    const switchPicker = document.createElement('ha-entity-picker');
    switchPicker.includeDomains = ['switch', 'select'];
    switchPicker.value = this._config.switch || '';
    switchPicker.hass = this._hass;
    switchPicker.addEventListener('value-changed', (e) => this._updateConfig('switch', e.detail.value));
    this._switchPicker = switchPicker;
    switchRow.appendChild(switchLabel);
    switchRow.appendChild(switchPicker);
    container.appendChild(switchRow);

    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(container);
    this._rendered = true;
    this.translateLabels();
  }

  _updateConfig(key, value) {
    if (!this._config) return;
    const newConfig = { ...this._config, [key]: value };
    const event = new CustomEvent('config-changed', {
      detail: { config: newConfig },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }
}

/* ==================== STATUS (BUTTON-STYLE MASTER SWITCH) CARD CLASS ==================== */
class MultizoneThermostatStatusCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  setConfig(config) {
    this._config = config || {};
    if (!this._rendered) {
      this.renderStructure();
    }
  }

  getCardSize() {
    return 1;
  }

  renderStructure() {
    const card = document.createElement('ha-card');
    const style = document.createElement('style');

    style.textContent = `
      ha-card {
        padding: 16px;
        border-radius: var(--ha-card-border-radius, 12px);
        color: white;
        transition: background-color 0.5s ease, transform 0.2s ease, box-shadow 0.2s ease;
        cursor: pointer;
        display: flex;
        align-items: center;
        min-height: 90px;
        position: relative;
        overflow: hidden;
        border: none;
      }
      ha-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.25);
      }
      ha-card:active {
        transform: translateY(0);
      }
      .card-content {
        display: flex;
        align-items: center;
        width: 100%;
        gap: 16px;
        pointer-events: none;
      }
      .icon-container {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 52px;
        height: 52px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.15);
        flex-shrink: 0;
      }
      .icon-container ha-icon {
        --mdc-icon-size: 28px;
        color: white;
      }
      .info-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        flex-grow: 1;
        overflow: hidden;
      }
      .name {
        font-size: 18px;
        font-weight: 600;
        margin: 0;
        text-shadow: 0 1px 2px rgba(0,0,0,0.15);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .state {
        font-size: 13px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 4px 0;
        opacity: 0.9;
        text-shadow: 0 1px 1px rgba(0,0,0,0.1);
      }
      .temp-row {
        font-size: 12px;
        opacity: 0.85;
      }
      .glow-flame {
        animation: pulse-flame 1.5s infinite alternate;
      }
      @keyframes pulse-flame {
        0% { transform: scale(1); filter: drop-shadow(0 0 1px rgba(255,255,255,0.4)); }
        100% { transform: scale(1.1); filter: drop-shadow(0 0 6px rgba(255,255,255,0.7)); }
      }
    `;

    card.innerHTML = `
      <div class="card-content">
        <div class="icon-container">
          <ha-icon icon="mdi:power"></ha-icon>
        </div>
        <div class="info-container">
          <div class="name">Riscaldamento Centrale</div>
          <div class="state">Ricerca...</div>
          <div class="temp-row">Caldaia: --</div>
        </div>
      </div>
    `;

    // Hook tap event to toggle the master entity
    card.addEventListener('click', () => this.handleTap());

    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  handleTap() {
    const masterEntity = findMasterEntity(this._hass);
    if (!masterEntity) return;

    const domain = masterEntity.split('.')[0];
    this._hass.callService(domain, "toggle", {
      entity_id: masterEntity
    });
  }

  updateCard() {
    if (!this._hass || !this._hass.states) return;
    if (!this._hass || !this._rendered) return;

    // Use the actual master switch entity to determine if system is ON
    const masterEntity = findMasterEntity(this._hass);
    let isMasterOn = false;
    let boilerEntity = null;

    if (masterEntity) {
      const masterState = this._hass.states[masterEntity];
      if (masterState) {
        isMasterOn = masterState.state === "on";
      }
    }

    // Try to find the boiler switch directly or through climate attributes
    boilerEntity = this._config.entity || this._config.boiler_entity;
    if (!boilerEntity) {
      // First try to find a climate entity that has the boiler_entity_id attribute
      const zoneClimate = Object.values(this._hass.states).find(s => 
        s.entity_id.startsWith('climate.') && s.attributes && s.attributes.hybrid_zone === true && s.attributes.boiler_entity_id
      );
      
      if (zoneClimate) {
        boilerEntity = zoneClimate.attributes.boiler_entity_id;
      } else {
        // Fallback to name heuristic
        const boilerFound = this._hass && this._hass.states && Object.keys(this._hass.states).find(key => {
          return key.startsWith('switch.') && (key.includes('boiler') || key.includes('caldaia'));
        });
        if (boilerFound) {
           boilerEntity = boilerFound;
        }
      }
    }
    const boilerState = boilerEntity ? this._hass.states[boilerEntity] : null;
    let isBoilerOn = false;

    if (boilerEntity && boilerState) {
      // In relay mode, strictly reflect the physical state of the configured boiler relay
      isBoilerOn = boilerState.state === "on";
    } else {
      // Fallback only if no boiler switch entity exists (e.g. OpenTherm): check active PRIMARY zones
      const isAnyPrimaryHeating = Object.values(this._hass.states).some(s => 
        s.entity_id.startsWith('climate.') && 
        s.attributes && 
        s.attributes.hybrid_zone === true &&
        s.attributes.zone_mode === 'primary' &&
        s.attributes.hvac_action === 'heating'
      );
      if (isAnyPrimaryHeating) {
        isBoilerOn = true;
      }
    }

    let bgColor = "#37474f"; // grigio quando spento
    let stateText = getTranslation(this._hass, 'off');
    let iconName = this._config.icon || "mdi:power";
    let glowClass = false;

    if (!isMasterOn) {
      bgColor = "#37474f"; // grigio quando spento
      stateText = getTranslation(this._hass, 'off');
      iconName = this._config.icon || "mdi:power";
    } else {
      // Master acceso
      if (isBoilerOn) {
        bgColor = "#f57c00"; // arancione quando caldaia/circolatore acceso
        stateText = getTranslation(this._hass, 'heating_active');
        iconName = this._config.icon || "mdi:fire";
        glowClass = true;
      } else {
        bgColor = "#fbc02d"; // giallo quando caldaia/circolatore spento
        stateText = getTranslation(this._hass, 'idle');
        iconName = this._config.icon || "mdi:radiator-off";
      }
    }

    // Update the ha-card element's background color and custom styles
    const card = this.shadowRoot.querySelector('ha-card');
    if (card) {
      card.style.backgroundColor = bgColor;
      if (this._config.height) card.style.height = this._config.height;
      if (this._config.width) card.style.width = this._config.width;
      if (this._config.border_radius) card.style.borderRadius = this._config.border_radius;
    }

    // Update title / name
    const nameEl = this.shadowRoot.querySelector('.name');
    if (nameEl) {
      nameEl.textContent = this._config.title || getTranslation(this._hass, 'heating');
    }

    // Update state text
    const stateEl = this.shadowRoot.querySelector('.state');
    if (stateEl) {
      stateEl.textContent = stateText;
    }

    // Update icon
    const iconEl = this.shadowRoot.querySelector('ha-icon');
    if (iconEl) {
      iconEl.setAttribute('icon', iconName);
      if (glowClass) {
        iconEl.classList.add('glow-flame');
      } else {
        iconEl.classList.remove('glow-flame');
      }
    }

    // Update subtext info
    const infoEl = this.shadowRoot.querySelector('.temp-row');
    if (infoEl) {
      if (boilerEntity && boilerState) {
        infoEl.textContent = `${getTranslation(this._hass, 'caldaia_circ')}: ${isBoilerOn ? 'ON' : 'OFF'}`;
      } else {
        infoEl.textContent = isMasterOn ? getTranslation(this._hass, 'system_active') : getTranslation(this._hass, 'system_off');
      }
    }
  }

  renderError(msg) {
    this.shadowRoot.innerHTML = `
      <ha-card style="padding: 16px; color: red; background-color: rgba(255,0,0,0.15);">
        <h3>${this._hass ? getTranslation(this._hass, 'card_error_title') : 'Multizone Thermostat Card Error'}</h3>
        <p>${msg}</p>
      </ha-card>
    `;
    this._rendered = false;
  }
}

/* ==================== PRESET CARD CLASS ==================== */
class MultizoneThermostatPresetCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.renderStructure();
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  setConfig(config) {
    this._config = config;
  }

  getCardSize() {
    return 2;
  }

  static getConfigElement() {
    return document.createElement("multizone-thermostat-preset-card-editor");
  }

  static getStubConfig() {
    return {
      entity: "",
      title: ""
    };
  }

  get presetEntity() {
    if (this._config && this._config.entity) {
      return this._config.entity;
    }
    return findPresetEntity(this._hass);
  }

  renderStructure() {
    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          padding: 16px;
          border-radius: 12px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          background: var(--ha-card-background, var(--card-background-color, white));
        }
        .header {
          font-weight: 500;
          font-size: 16px;
          color: var(--primary-text-color);
        }
        .buttons-row {
          display: flex;
          flex-direction: row;
          justify-content: space-between;
          gap: 8px;
        }
        .preset-btn {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          background: var(--secondary-background-color);
          color: var(--secondary-text-color);
          border-radius: 12px;
          padding: 12px 4px;
          cursor: pointer;
          transition: all 0.3s ease;
          border: 2px solid transparent;
          gap: 6px;
        }
        .preset-btn:hover {
          background: rgba(var(--rgb-primary-color), 0.1);
        }
        .preset-btn.active {
          background: rgba(var(--rgb-primary-color), 0.15);
          color: var(--primary-color);
          border-color: var(--primary-color);
        }
        .preset-btn ha-icon {
          --mdc-icon-size: 28px;
        }
        .preset-label {
          font-size: 11px;
          font-weight: 500;
          text-align: center;
          word-break: break-word;
        }
      </style>
      <ha-card>
        <div class="header" id="card-title">Preset Globale</div>
        <div class="buttons-row">
          <div class="preset-btn" data-preset="manual" id="btn-manual">
            <ha-icon icon="mdi:power"></ha-icon>
            <div class="preset-label" id="lbl-manual">Manual</div>
          </div>
          <div class="preset-btn" data-preset="eco" id="btn-eco">
            <ha-icon icon="mdi:leaf"></ha-icon>
            <div class="preset-label" id="lbl-eco">Eco</div>
          </div>
          <div class="preset-btn" data-preset="comfort" id="btn-comfort">
            <ha-icon icon="mdi:sofa"></ha-icon>
            <div class="preset-label" id="lbl-comfort">Comfort</div>
          </div>
          <div class="preset-btn" data-preset="sleep" id="btn-sleep">
            <ha-icon icon="mdi:bed"></ha-icon>
            <div class="preset-label" id="lbl-sleep">Sleep</div>
          </div>
          <div class="preset-btn" data-preset="away" id="btn-away">
            <ha-icon icon="mdi:car"></ha-icon>
            <div class="preset-label" id="lbl-away">Away</div>
          </div>
        </div>
      </ha-card>
    `;

    // Add click listeners
    const buttons = this.shadowRoot.querySelectorAll('.preset-btn');
    buttons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const preset = e.currentTarget.getAttribute('data-preset');
        this.setPreset(preset);
      });
    });
  }

  setPreset(preset) {
    if (!this._hass || !this.presetEntity) return;
    this._hass.callService('select', 'select_option', {
      entity_id: this.presetEntity,
      option: preset
    });
  }

  updateCard() {
    if (!this._hass || !this._hass.states) return;
    if (!this._hass) return;

    // Apply custom styling from config
    const card = this.shadowRoot.querySelector('ha-card');
    if (card && this._config) {
      if (this._config.height) card.style.height = this._config.height;
      if (this._config.width) card.style.width = this._config.width;
      if (this._config.border_radius) card.style.borderRadius = this._config.border_radius;
    }

    // Title
    const titleEl = this.shadowRoot.getElementById('card-title');
    titleEl.textContent = (this._config && this._config.title) || getTranslation(this._hass, 'preset_card_title');

    // Labels
    this.shadowRoot.getElementById('lbl-manual').textContent = getTranslation(this._hass, 'preset_manual');
    this.shadowRoot.getElementById('lbl-eco').textContent = getTranslation(this._hass, 'preset_eco');
    this.shadowRoot.getElementById('lbl-comfort').textContent = getTranslation(this._hass, 'preset_comfort');
    this.shadowRoot.getElementById('lbl-sleep').textContent = getTranslation(this._hass, 'preset_sleep');
    this.shadowRoot.getElementById('lbl-away').textContent = getTranslation(this._hass, 'preset_away');

    const entityId = this.presetEntity;
    if (!entityId || !this._hass.states[entityId]) {
      return; // Not found yet
    }

    const state = this._hass.states[entityId].state;

    // Update active class
    const buttons = this.shadowRoot.querySelectorAll('.preset-btn');
    buttons.forEach(btn => {
      if (btn.getAttribute('data-preset') === state) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }
}

/* ==================== PRESET CARD EDITOR CLASS ==================== */
class MultizoneThermostatPresetCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    this._config = config;
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this.render();
      this._rendered = true;
    }
  }

  configChanged(newConfig) {
    const event = new Event("config-changed", {
      bubbles: true,
      composed: true
    });
    event.detail = { config: newConfig };
    this.dispatchEvent(event);
  }

  render() {
    if (!this._config) return;
    
    // Only build DOM once, then just update values
    if (this.shadowRoot.querySelector('.editor-container')) {
        // Update existing input values
        const titleInput = this.shadowRoot.querySelector('#title-input');
        if (titleInput && titleInput.value !== (this._config.title || '')) {
            titleInput.value = this._config.title || '';
        }
        return;
    }

    if (!this._hass) return;
    const config = this._config || {};
    
    // Auto-discover preset entity if not configured
    let currentEntity = config.entity;
    if (!currentEntity) {
      currentEntity = findPresetEntity(this._hass) || '';
      if (currentEntity) {
        // Defer the config change slightly to let the editor finish rendering
        setTimeout(() => {
          this._config = { ...this._config, entity: currentEntity };
          this.configChanged(this._config);
        }, 100);
      }
    }

    if (this.shadowRoot.hasChildNodes()) {
      this.shadowRoot.innerHTML = '';
    }

    const container = document.createElement('div');
    container.className = 'card-config editor-container';

    // Title Row
    const titleRow = document.createElement('div');
    titleRow.className = 'form-row';
    const titleLabel = document.createElement('label');
    titleLabel.textContent = getTranslation(this._hass, 'edit_title');
    titleLabel.style.display = 'block';
    titleLabel.style.marginBottom = '8px';
    const titleInput = document.createElement('input');
    titleInput.id = 'title-input';
    titleInput.type = 'text';
    titleInput.value = config.title || '';
    titleInput.style.width = '100%';
    titleInput.style.padding = '8px';
    titleInput.style.boxSizing = 'border-box';
    titleInput.addEventListener('input', (e) => {
      if (!this._config) return;
      this._config = { ...this._config, title: e.target.value };
      this.configChanged(this._config);
    });
    titleRow.appendChild(titleLabel);
    titleRow.appendChild(titleInput);
    container.appendChild(titleRow);

    // Entity Row
    const entityRow = document.createElement('div');
    entityRow.className = 'form-row';
    entityRow.style.marginTop = '16px';
    const entityLabel = document.createElement('label');
    entityLabel.textContent = getTranslation(this._hass, 'edit_preset');
    const entityPicker = document.createElement('ha-entity-picker');
    entityPicker.includeDomains = ['select'];
    entityPicker.value = config.entity || '';
    entityPicker.hass = this._hass;
    entityPicker.addEventListener('value-changed', (e) => {
      if (!this._config) return;
      this._config = { ...this._config, entity: e.detail.value };
      this.configChanged(this._config);
    });
    
    entityRow.appendChild(entityLabel);
    entityRow.appendChild(entityPicker);
    container.appendChild(entityRow);

    this.shadowRoot.appendChild(container);
  }
}

// Define elements safely to avoid "already been used" errors on hot-reloads
if (!customElements.get("multizone-thermostat-button-card")) {
  customElements.define("multizone-thermostat-button-card", MultizoneThermostatButtonCard);
}
if (!customElements.get("multizone-thermostat-dial-card")) {
  customElements.define("multizone-thermostat-dial-card", MultizoneThermostatDialCard);
}
if (!customElements.get("multizone-thermostat-status-card")) {
  customElements.define("multizone-thermostat-status-card", MultizoneThermostatStatusCard);
}
if (!customElements.get("multizone-thermostat-card-editor")) {
  customElements.define("multizone-thermostat-card-editor", MultizoneThermostatCardEditor);
}
if (!customElements.get("multizone-thermostat-preset-card")) {
  customElements.define("multizone-thermostat-preset-card", MultizoneThermostatPresetCard);
}
if (!customElements.get("multizone-thermostat-preset-card-editor")) {
  customElements.define("multizone-thermostat-preset-card-editor", MultizoneThermostatPresetCardEditor);
}

/* ==================== SPACER CARD ==================== */
class MultizoneThermostatSpacer extends HTMLElement {
  setConfig(config) {}
  set hass(hass) {}
}

if (!customElements.get("multizone-thermostat-spacer")) {
  customElements.define("multizone-thermostat-spacer", MultizoneThermostatSpacer);
}

/* ==================== HEALTH SUMMARY CARD ==================== */
/* ==================== SCHEDULE SUMMARY NAVIGATION BUTTON CARD ==================== */

class MultizoneThermostatScheduleSummaryCard extends HTMLElement {
  getCardSize() { return 3; }
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  setConfig(config) {
    this._config = config || {};
    if (!this._rendered) this.renderStructure();
  }

  renderStructure() {
    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          padding: 16px;
          border-radius: var(--ha-card-border-radius, 20px);
          background-color: var(--card-background-color, #1c1c1c);
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          height: 100%;
          min-height: 80px;
          cursor: pointer;
          transition: background-color 0.2s, transform 0.2s;
          box-sizing: border-box;
        }
        ha-card:hover {
          background-color: var(--secondary-background-color, #2c2c2c);
          transform: translateY(-2px);
        }
        .container {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
          text-align: center;
        }
        ha-icon {
          --mdc-icon-size: 32px;
          transition: color 0.3s ease;
        }
        .title { font-weight: bold; font-size: 1.1em; }
        .subtitle { font-size: 0.9em; opacity: 0.9; }
      </style>
      <ha-card id="sched-card">
        <div class="container">
          <ha-icon id="sched-icon" icon="mdi:calendar-clock"></ha-icon>
          <div class="title" id="sched-title">Programmazione</div>
          <div class="subtitle" id="sched-subtitle">In Pausa</div>
        </div>
      </ha-card>
    `;

    this.shadowRoot.querySelector('#sched-card').addEventListener('click', () => {
      const event = new Event('hass-action', { bubbles: true, composed: true });
      event.detail = {
        config: { tap_action: { action: 'navigate', navigation_path: 'programmazione' } },
        action: 'tap'
      };
      this.dispatchEvent(event);
    });
    this._rendered = true;
  }

  updateCard() {
    if (!this._hass || !this._hass.states || !this._rendered) return;

    let schedStatus = null;
    for (const eid of Object.keys(this._hass.states)) {
      const s = this._hass.states[eid];
      if (s.attributes && s.attributes.multizone_type === "scheduler" && s.attributes.schedule_status) {
        schedStatus = s.attributes.schedule_status;
        break;
      }
    }

    if (!schedStatus) {
      const masterEid = findMasterEntity(this._hass);
      if (masterEid && this._hass.states[masterEid]?.attributes?.schedule_status) {
        schedStatus = this._hass.states[masterEid].attributes.schedule_status;
      }
    }

    if (!schedStatus) {
      for (const eid of Object.keys(this._hass.states)) {
        if (this._hass.states[eid]?.attributes?.schedule_status) {
          schedStatus = this._hass.states[eid].attributes.schedule_status;
          break;
        }
      }
    }

    const titleEl = this.shadowRoot.querySelector('#sched-title');
    const subtitleEl = this.shadowRoot.querySelector('#sched-subtitle');
    const iconEl = this.shadowRoot.querySelector('#sched-icon');

    if (titleEl) {
      titleEl.textContent = getTranslation(this._hass, 'sched_nav_title');
    }

    if (!schedStatus) {
      if (subtitleEl) subtitleEl.textContent = getTranslation(this._hass, 'sched_paused');
      if (iconEl) {
        iconEl.icon = "mdi:calendar-clock";
        iconEl.style.color = "#94a3b8";
      }
      return;
    }

    const sr = schedStatus.smart_return;
    if (sr && sr.active) {
      const arrival = sr.arrival_time ? sr.arrival_time.substring(0, 5) : "";
      if (subtitleEl) subtitleEl.textContent = "🚗 Rientro " + arrival;
      if (iconEl) {
        iconEl.icon = "mdi:car-clock";
        iconEl.style.color = "#f59e0b";
      }
      return;
    }

    if (schedStatus.scheduler_enabled) {
      let pId = schedStatus.active_profile || 'standard';
      let pName = (schedStatus.profiles && schedStatus.profiles[pId] && schedStatus.profiles[pId].name) || pId;
      
      let prefix = "🟢";
      if (pId === 'smart_working') prefix = "💼";
      else if (pId === 'holiday') prefix = "🎉";
      
      let text = prefix + " " + pName;
      if (schedStatus.profile_expires_at) {
        text += " ⏳";
      }
      if (subtitleEl) subtitleEl.textContent = text;
      if (iconEl) {
        iconEl.icon = "mdi:calendar-clock";
        iconEl.style.color = "#10b981";
      }
    } else {
      if (subtitleEl) subtitleEl.textContent = getTranslation(this._hass, 'sched_paused');
      if (iconEl) {
        iconEl.icon = "mdi:calendar-clock";
        iconEl.style.color = "#94a3b8";
      }
    }
  }
}

if (!customElements.get("multizone-thermostat-schedule-summary-card")) {
  customElements.define("multizone-thermostat-schedule-summary-card", MultizoneThermostatScheduleSummaryCard);
}

class MultizoneThermostatHealthSummaryCard extends HTMLElement {
  getCardSize() { return 3; }
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  setConfig(config) {
    this._config = config || {};
    if (!this._rendered) this.renderStructure();
  }

  renderStructure() {
    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          padding: 16px;
          border-radius: var(--ha-card-border-radius, 20px);
          background-color: var(--card-background-color, #1c1c1c);
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          height: 100%;
          min-height: 80px;
          cursor: pointer;
          transition: background-color 0.2s;
          box-sizing: border-box;
        }
        ha-card:hover {
          background-color: var(--secondary-background-color, #2c2c2c);
        }
        .container {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
        }
        ha-icon {
          --mdc-icon-size: 32px;
        }
        .healthy { color: #4CAF50; }
        .warning { color: #FF9800; }
        .title { font-weight: bold; font-size: 1.1em; }
        .subtitle { font-size: 0.9em; opacity: 0.8; }
      </style>
      <ha-card id="health-card">
        <div class="container">
          <ha-icon id="health-icon" icon="mdi:shield-check" class="healthy"></ha-icon>
          <div class="title" id="health-title">Diagnostica</div>
          <div class="subtitle" id="health-subtitle">Sistema Ok</div>
        </div>
      </ha-card>
    `;

    this.shadowRoot.querySelector('#health-card').addEventListener('click', () => {
      const event = new Event('hass-action', { bubbles: true, composed: true });
      event.detail = {
          config: { tap_action: { action: 'navigate', navigation_path: 'diagnostica' } },
          action: 'tap'
      };
      this.dispatchEvent(event);
    });
    this._rendered = true;
  }

  updateCard() {
    if (!this._hass || !this._hass.states) return;
    if (!this._hass || !this._rendered) return;
    
    let healthEntity = null;
    for (const eid of Object.keys(this._hass.states)) {
      if (eid.startsWith("sensor.") && 
          this._hass.states[eid].attributes && 
          this._hass.states[eid].attributes.hasOwnProperty("anomalies_count")) {
        healthEntity = eid;
        break;
      }
    }

    const iconEl = this.shadowRoot.querySelector('#health-icon');
    const subtitleEl = this.shadowRoot.querySelector('#health-subtitle');

    if (!healthEntity) {
      subtitleEl.textContent = "Non trovato";
      iconEl.icon = "mdi:shield-off";
      iconEl.className = "";
      return;
    }

    const stateObj = this._hass.states[healthEntity];
    const anomalies = stateObj.attributes.anomalies || [];
    
    if (anomalies.length === 0) {
      subtitleEl.textContent = "Sistema Ok";
      iconEl.icon = "mdi:shield-check";
      iconEl.className = "healthy";
    } else {
      subtitleEl.textContent = anomalies.length + (anomalies.length === 1 ? " Anomalia" : " Anomalie");
      iconEl.icon = "mdi:alert";
      iconEl.className = "warning";
    }
  }
}

if (!customElements.get("multizone-thermostat-health-summary-card")) {
  customElements.define("multizone-thermostat-health-summary-card", MultizoneThermostatHealthSummaryCard);
}

/* ==================== PLANT DIAGNOSTIC CARD ==================== */
class MultizoneThermostatPlantCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._rendered = false;
  }

  setConfig(config) {
    this._config = Object.assign({}, config || {});
  }

  getCardSize() {
    return 3;
  }

  static getStubConfig() {
    return {};
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this.render();
    }
    this.updateCard();
  }

  render() {
    const style = document.createElement('style');
    style.textContent = `
      ha-card {
        background: var(--ha-card-background, var(--card-background-color, rgba(30, 41, 59, 0.7)));
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.08));
        border-radius: var(--card-border-radius, 20px);
        padding: 20px;
        box-shadow: var(--ha-card-box-shadow, 0 4px 20px rgba(0, 0, 0, 0.15));
        font-family: var(--paper-font-body1_-_font-family, inherit);
        color: var(--primary-text-color, #e2e8f0);
        box-sizing: border-box;
      }
      .header-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
      }
      .title-group {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .icon-wrap {
        width: 46px;
        height: 46px;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(14, 165, 233, 0.15);
        color: #38bdf8;
      }
      .icon-wrap ha-icon {
        --mdc-icon-size: 28px;
      }
      .title-text {
        font-size: 20px;
        font-weight: 800;
        margin: 0;
        line-height: 1.2;
      }
      .subtitle-text {
        font-size: 13px;
        color: var(--secondary-text-color, #94a3b8);
        margin-top: 3px;
      }
      .status-badge {
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 13px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .status-optimal {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
      }
      .status-warning {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
      }
      .status-critical {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
      }
      .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: currentColor;
      }
      .kpi-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 14px;
        margin-bottom: 14px;
      }
      @media (max-width: 480px) {
        .kpi-grid { grid-template-columns: 1fr; }
      }
      .kpi-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        padding: 16px;
      }
      .kpi-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--secondary-text-color, #94a3b8);
        display: block;
        margin-bottom: 6px;
      }
      .kpi-value-row {
        display: flex;
        align-items: baseline;
        gap: 6px;
      }
      .kpi-val {
        font-size: 30px;
        font-weight: 900;
        line-height: 1;
      }
      .kpi-unit {
        font-size: 13px;
        font-weight: 600;
        color: var(--secondary-text-color, #94a3b8);
      }
      .kpi-sub {
        font-size: 12px;
        margin-top: 8px;
        font-weight: 600;
      }
      .alert-box {
        padding: 14px 16px;
        border-radius: 14px;
        font-size: 13px;
        line-height: 1.5;
        display: flex;
        flex-direction: column;
        gap: 6px;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.06);
      }
      .alert-box.alert-ok {
        background: rgba(16, 185, 129, 0.08);
        border-color: rgba(16, 185, 129, 0.2);
        color: #a7f3d0;
      }
      .alert-box.alert-err {
        background: rgba(239, 68, 68, 0.12);
        border-color: rgba(239, 68, 68, 0.35);
        color: #fca5a5;
      }
      .alert-title {
        font-weight: 700;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
      }
    `;

    const t = (k) => getTranslation(this._hass, k);
    const card = document.createElement('ha-card');
    card.innerHTML = `
      <div class="header-row">
        <div class="title-group">
          <div class="icon-wrap">
            <ha-icon icon="mdi:shield-check"></ha-icon>
          </div>
          <div>
            <div class="title-text" id="plant-title">${t('plant_health_title')}</div>
            <div class="subtitle-text" id="plant-sub">${t('plant_health_sub')}</div>
          </div>
        </div>
        <div class="status-badge status-optimal" id="health-badge">
          <span class="status-dot"></span>
          <span id="health-text">${t('optimal')}</span>
        </div>
      </div>

      <div class="kpi-grid">
        <div class="kpi-card">
          <span class="kpi-label" id="cycles-label">${t('cycles_label')}</span>
          <div class="kpi-value-row">
            <span class="kpi-val" id="cycles-val">--</span>
            <span class="kpi-unit" id="cycles-unit">${t('cycles_unit')}</span>
          </div>
          <div class="kpi-sub" id="cycles-sub" style="color: #34d399;">${t('wear_low')}</div>
        </div>

        <div class="kpi-card">
          <span class="kpi-label" id="runtime-label">${t('runtime_24h')}</span>
          <div class="kpi-value-row">
            <span class="kpi-val" id="runtime-val" style="color: #60a5fa;">--</span>
            <span class="kpi-unit" id="runtime-unit">${t('hours')}</span>
          </div>
          <div class="kpi-sub" id="runtime-sub" style="color: #94a3b8;">${t('runtime_sub')}</div>
        </div>
      </div>

      <div class="ot-grid" id="ot-grid" style="display:none; margin-bottom: 14px; background: rgba(14, 165, 233, 0.05); border: 1px solid rgba(14, 165, 233, 0.2); border-radius: 14px; padding: 12px 16px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
          <div style="font-weight: 700; font-size: 13px; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
            <ha-icon icon="mdi:pipe-valve" style="--mdc-icon-size: 16px;"></ha-icon>
            <span id="ot-telemetry-title">${t('ot_telemetry')}</span>
          </div>
          <div id="ot-dhw-badge" style="display:none; font-size: 11px; font-weight: 700; background: rgba(59, 130, 246, 0.2); color: #60a5fa; border-radius: 6px; padding: 2px 8px; border: 1px solid rgba(59, 130, 246, 0.3);">
            ${t('ot_dhw_active')}
          </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(75px, 1fr)); gap: 10px;">
          <div>
            <div style="font-size: 11px; color: var(--secondary-text-color, #94a3b8);">${t('ot_pressure')}</div>
            <div style="font-size: 16px; font-weight: 800;" id="ot-pressure-val">-- bar</div>
          </div>
          <div>
            <div style="font-size: 11px; color: var(--secondary-text-color, #94a3b8);">${t('ot_flow_temp')}</div>
            <div style="font-size: 16px; font-weight: 800;" id="ot-flow-val">--°C</div>
          </div>
          <div>
            <div style="font-size: 11px; color: var(--secondary-text-color, #94a3b8);">${t('ot_return_temp')}</div>
            <div style="font-size: 16px; font-weight: 800;" id="ot-return-val">--°C</div>
            <div style="font-size: 10px; font-weight: 600;" id="ot-condense-eval"></div>
          </div>
          <div>
            <div style="font-size: 11px; color: var(--secondary-text-color, #94a3b8);">${t('ot_modulation')}</div>
            <div style="font-size: 16px; font-weight: 800;" id="ot-mod-val">--%</div>
          </div>
          <div>
            <div style="font-size: 11px; color: var(--secondary-text-color, #94a3b8);">${t('ot_flame_status')}</div>
            <div style="font-size: 14px; font-weight: 700;" id="ot-flame-val">${t('ot_flame_off')}</div>
          </div>
        </div>
      </div>

      <div class="alert-box alert-ok" id="alert-box">
        <div class="alert-title" id="alert-title-wrap">
          <ha-icon icon="mdi:check-circle-outline" style="--mdc-icon-size: 18px; color: #34d399;"></ha-icon>
          <span id="alert-title-text">${t('all_circuits_ok')}</span>
        </div>
        <div id="alert-desc">${t('no_anomalies')}</div>
      </div>
    `;

    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  updateCard() {
    if (!this._hass || !this._hass.states) return;
    if (!this._hass || !this._rendered) return;

    try {
      const t = (k) => getTranslation(this._hass, k);
      let healthEntity = this._config.health_entity;
      let cyclesEntity = this._config.cycles_entity;
      let runtimeEntity = this._config.runtime_entity;
      let anomalyEntity = this._config.anomaly_entity;

      if (!healthEntity) {
        healthEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
          k.startsWith('sensor.') && (k.includes('plant_health') || k.includes('stato_salute_impianto'))
        );
      }
      if (!cyclesEntity) {
        cyclesEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
          k.startsWith('sensor.') && (k.includes('boiler_cycles_per_hour') || k.includes('frequenza_accensioni_caldaia'))
        );
      }
      if (!runtimeEntity) {
        runtimeEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
          k.startsWith('sensor.') && (k.includes('boiler_daily_runtime') || k.includes('ore_funzionamento_caldaia_24h'))
        );
      }
      if (!anomalyEntity) {
        anomalyEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k => k.startsWith('binary_sensor.') && k.includes('plant_anomaly'));
      }

      const healthState = healthEntity ? this._hass.states[healthEntity] : null;
      const cyclesState = cyclesEntity ? this._hass.states[cyclesEntity] : null;
      const runtimeState = runtimeEntity ? this._hass.states[runtimeEntity] : null;
      const anomalyState = anomalyEntity ? this._hass.states[anomalyEntity] : null;

      const healthBadge = this.shadowRoot.getElementById('health-badge');
      const healthText = this.shadowRoot.getElementById('health-text');
      const cyclesVal = this.shadowRoot.getElementById('cycles-val');
      const cyclesSub = this.shadowRoot.getElementById('cycles-sub');
      const runtimeVal = this.shadowRoot.getElementById('runtime-val');
      const alertBox = this.shadowRoot.getElementById('alert-box');
      const alertDesc = this.shadowRoot.getElementById('alert-desc');

      const statusVal = healthState ? healthState.state : "Optimal";
      const isCritical = statusVal === "Critical" || statusVal === "Critico";
      const isWarning = statusVal === "Warning" || statusVal === "Attenzione";
      const isOptimal = statusVal === "Optimal" || statusVal === "Ottimale";
      if (healthBadge && healthText) {
        if (isCritical) {
          healthText.innerText = t('critical');
          healthBadge.className = "status-badge status-critical";
        } else if (isWarning) {
          healthText.innerText = t('warning');
          healthBadge.className = "status-badge status-warning";
        } else {
          healthText.innerText = t('optimal');
          healthBadge.className = "status-badge status-optimal";
        }
      }

      if (cyclesVal && cyclesState) {
        const c = parseFloat(cyclesState.state) || 0;
        cyclesVal.innerText = c.toFixed(1);
        if (cyclesSub) {
          if (c <= 3.5) {
            cyclesSub.innerText = t('wear_low');
            cyclesSub.style.color = "#34d399";
          } else if (c <= 5.0) {
            cyclesSub.innerText = t('wear_moderate');
            cyclesSub.style.color = "#fbbf24";
          } else {
            cyclesSub.innerText = t('wear_high');
            cyclesSub.style.color = "#f87171";
          }
        }
      }

      if (runtimeVal && runtimeState) {
        const r = parseFloat(runtimeState.state) || 0;
        runtimeVal.innerText = r.toFixed(1);
      }

      if (alertBox && alertDesc) {
        const hasAnomaly = anomalyState ? anomalyState.state === "on" : !isOptimal;
        if (hasAnomaly && healthState && healthState.attributes && healthState.attributes.anomalies && healthState.attributes.anomalies.length > 0) {
          alertBox.className = "alert-box alert-err";
          const items = healthState.attributes.anomalies.map(a => `• <b>${a.zone}</b>: ${a.description}`).join('<br>');
          alertDesc.innerHTML = items;
        } else if (isWarning) {
          alertBox.className = "alert-box alert-err";
          alertDesc.innerText = t('attention_cycles');
        } else {
          alertBox.className = "alert-box alert-ok";
          alertDesc.innerText = t('no_anomalies');
        }
      }

      // OpenTherm Telemetry Update
      const otGrid = this.shadowRoot.getElementById('ot-grid');
      const otPressure = this.shadowRoot.getElementById('ot-pressure-val');
      const otFlow = this.shadowRoot.getElementById('ot-flow-val');
      const otReturn = this.shadowRoot.getElementById('ot-return-val');
      const otCondense = this.shadowRoot.getElementById('ot-condense-eval');
      const otMod = this.shadowRoot.getElementById('ot-mod-val');
      const otFlame = this.shadowRoot.getElementById('ot-flame-val');
      const otDhw = this.shadowRoot.getElementById('ot-dhw-badge');

      if (otGrid && healthState && healthState.attributes && healthState.attributes.opentherm && healthState.attributes.opentherm.enabled) {
        const ot = healthState.attributes.opentherm;
        otGrid.style.display = 'block';

        if (otPressure) {
          if (ot.water_pressure !== null && ot.water_pressure !== undefined) {
            otPressure.innerText = `${ot.water_pressure} bar`;
            otPressure.style.color = (ot.water_pressure < 0.8) ? '#f87171' : (ot.water_pressure > 2.5 ? '#fbbf24' : '#34d399');
          } else {
            otPressure.innerText = '-- bar';
            otPressure.style.color = 'inherit';
          }
        }

        if (otFlow) {
          const flowVal = ot.flow_temperature !== undefined && ot.flow_temperature !== null ? ot.flow_temperature :
                          (ot.flow_temp !== undefined && ot.flow_temp !== null ? ot.flow_temp : ot.water_flow_temperature);
          if (flowVal !== null && flowVal !== undefined && flowVal !== "") {
            const num = parseFloat(flowVal);
            const displayVal = !isNaN(num) ? (Number.isInteger(num) ? num : num.toFixed(1)) : flowVal;
            otFlow.innerText = `${displayVal}°C`;
          } else {
            otFlow.innerText = '--°C';
          }
        }

        if (otReturn) {
          if (ot.return_temperature !== null && ot.return_temperature !== undefined) {
            otReturn.innerText = `${ot.return_temperature}°C`;
            if (otCondense) {
              if (ot.condensing_optimal) {
                otCondense.innerText = t('ot_condensing_ok');
                otCondense.style.color = '#34d399';
              } else {
                otCondense.innerText = t('ot_return_hot');
                otCondense.style.color = '#fbbf24';
              }
            }
          } else {
            otReturn.innerText = '--°C';
            if (otCondense) otCondense.innerText = '';
          }
        }

        if (otMod) {
          if (ot.modulation_level !== null && ot.modulation_level !== undefined) {
            otMod.innerText = `${ot.modulation_level}%`;
          } else {
            otMod.innerText = '--%';
          }
        }

        if (otFlame) {
          if (ot.flame_active) {
            otFlame.innerHTML = `<span style="color: #f59e0b;">${t('ot_flame_on')}</span>`;
          } else {
            otFlame.innerHTML = `<span style="color: #94a3b8;">${t('ot_flame_off')}</span>`;
          }
        }

        if (otDhw) {
          otDhw.style.display = ot.dhw_active ? 'inline-block' : 'none';
          otDhw.innerText = t('ot_dhw_active');
        }
      } else if (otGrid) {
        otGrid.style.display = 'none';
      }
    } catch (err) {
      console.error("Error updating MultizoneThermostatPlantCard:", err);
    }
  }
}

if (!customElements.get("multizone-thermostat-plant-card")) {
  customElements.define("multizone-thermostat-plant-card", MultizoneThermostatPlantCard);
}

/* ==================== ZONE ENERGY CARD ==================== */
class MultizoneThermostatZoneEnergyCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._rendered = false;
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Devi specificare un'entità climate");
    }
    this._config = Object.assign({}, config);
  }

  getCardSize() {
    return 3;
  }

  static getStubConfig(hass, entities) {
    const climate = entities ? entities.find(e => e.startsWith("climate.")) : "";
    return {
      entity: climate || "",
      title: ""
    };
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this.render();
    }
    this.updateCard();
  }

  render() {
    const style = document.createElement('style');
    style.textContent = `
      ha-card {
        background: var(--ha-card-background, var(--card-background-color, rgba(30, 41, 59, 0.7)));
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.08));
        border-radius: var(--card-border-radius, 20px);
        padding: 20px;
        box-shadow: var(--ha-card-box-shadow, 0 4px 20px rgba(0, 0, 0, 0.15));
        font-family: var(--paper-font-body1_-_font-family, inherit);
        color: var(--primary-text-color, #e2e8f0);
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
      }
      .top-row {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        margin-bottom: 14px;
      }
      .zone-name {
        font-size: 20px;
        font-weight: 800;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .zone-mode-badge {
        font-size: 11px;
        font-weight: 800;
        padding: 4px 9px;
        border-radius: 6px;
        text-transform: uppercase;
        background: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
        cursor: pointer;
        transition: opacity 0.2s ease, transform 0.1s ease;
      }
      .zone-mode-badge:hover {
        opacity: 0.85;
      }
      .zone-mode-badge:active {
        transform: scale(0.96);
      }
      .zone-sub {
        font-size: 14px;
        font-weight: 500;
        color: var(--secondary-text-color, #94a3b8);
        margin-top: 4px;
      }
      .energy-badge {
        padding: 6px 14px;
        border-radius: 10px;
        font-weight: 900;
        font-size: 18px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        min-width: 48px;
        background: #10b981;
        color: white;
      }
      .ribbon-scale {
        display: flex;
        height: 6px;
        border-radius: 3px;
        overflow: hidden;
        margin-bottom: 16px;
        opacity: 0.85;
        gap: 2px;
      }
      .ribbon-step {
        flex: 1;
        height: 100%;
        transition: transform 0.2s ease;
      }
      .ribbon-step.active {
        transform: scaleY(1.8);
        box-shadow: 0 0 6px white;
        z-index: 2;
      }
      .step-A4 { background-color: #00873d; }
      .step-A  { background-color: #139f37; }
      .step-B  { background-color: #55b726; }
      .step-C  { background-color: #96c818; }
      .step-D  { background-color: #e0d100; }
      .step-E  { background-color: #f39200; }
      .step-F  { background-color: #e64213; }
      .step-G  { background-color: #cb0019; }

      .stats-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin-bottom: 14px;
      }
      .stat-box {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 14px;
        padding: 12px 14px;
      }
      .stat-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--secondary-text-color, #94a3b8);
        display: block;
        margin-bottom: 5px;
      }
      .stat-val {
        font-size: 22px;
        font-weight: 800;
        line-height: 1.2;
      }
      .stat-unit {
        font-size: 13px;
        color: var(--secondary-text-color, #94a3b8);
        font-weight: 600;
        margin-left: 2px;
      }
      .stat-eval {
        font-size: 13px;
        margin-top: 5px;
        font-weight: 600;
        display: block;
      }
      .bottom-row {
        padding-top: 14px;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 14px;
      }
      .valve-status {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
      }
      .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
      }
      .pulse-green { background: #10b981; }
      .pulse-red { background: #ef4444; animation: blink 1s infinite; }
      @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
    `;

    const t = (k) => getTranslation(this._hass, k);
    const card = document.createElement('ha-card');
    card.innerHTML = `
      <div class="top-row">
        <div>
          <div class="zone-name">
            <span id="zone-title">Stanza</span>
            <span class="zone-mode-badge" id="zone-mode-badge" title="Click to cycle zone mode">${t('primary_tag')}</span>
          </div>
          <div class="zone-sub" id="temp-sub">-- °C</div>
        </div>
        <div class="energy-badge" id="energy-badge">--</div>
      </div>

      <div class="ribbon-scale" id="ribbon-scale">
        <div class="ribbon-step step-A4" id="step-A4"></div>
        <div class="ribbon-step step-A" id="step-A"></div>
        <div class="ribbon-step step-B" id="step-B"></div>
        <div class="ribbon-step step-C" id="step-C"></div>
        <div class="ribbon-step step-D" id="step-D"></div>
        <div class="ribbon-step step-E" id="step-E"></div>
        <div class="ribbon-step step-F" id="step-F"></div>
        <div class="ribbon-step step-G" id="step-G"></div>
      </div>

      <div class="stats-grid">
        <div class="stat-box">
          <span class="stat-label" id="retention-label">${t('retention_label')}</span>
          <div>
            <span class="stat-val" id="retention-val">--</span>
            <span class="stat-unit" id="retention-unit">${t('hours')}</span>
          </div>
          <span class="stat-eval" id="retention-eval" style="color: #38bdf8;">--</span>
        </div>

        <div class="stat-box">
          <span class="stat-label" id="sizing-label">${t('sizing_label')}</span>
          <div>
            <span class="stat-val" id="sizing-val">--</span>
          </div>
          <span class="stat-eval" id="sizing-eval" style="color: #34d399;">--</span>
        </div>
      </div>

      <div class="bottom-row">
        <span style="color: var(--secondary-text-color, #94a3b8);" id="valve-status-label">${t('valve_status')}</span>
        <div class="valve-status" id="valve-status" style="margin-right: auto; padding-left: 10px;">
          <span class="pulse-dot pulse-green" id="valve-dot"></span>
          <span id="valve-text">${t('valve_ok')}</span>
        </div>
        <div class="battery-status" id="battery-status" style="display:flex; align-items:center; gap: 4px; font-weight:600;">
          <ha-icon icon="mdi:battery" id="battery-icon" style="--mdc-icon-size: 18px;"></ha-icon>
          <span id="battery-text">--%</span>
        </div>
      </div>
    `;

    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  updateCard() {
    if (!this._hass || !this._hass.states) return;
    if (!this._hass || !this._rendered || !this._config || !this._config.entity) return;

    try {
      const t = (k) => getTranslation(this._hass, k);
      const climateId = this._config.entity;
      const climateState = this._hass.states[climateId];
      if (!climateState) return;

      let title = this._config.title || climateState.attributes.friendly_name || climateId;
      title = title.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
      let slug = climateId.replace("climate.multizone_thermostat_", "").replace("climate.", "");

      const energyEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
        k.startsWith('sensor.') && (k.includes('energy_class') || k.includes('classe_energetica')) && k.includes(slug)
      );
      const retentionEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
        k.startsWith('sensor.') && (k.includes('thermal_retention') || k.includes('tempo_ritenzione_termica')) && k.includes(slug)
      );
      const sizingEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
        k.startsWith('sensor.') && (k.includes('radiator_sizing') || k.includes('dimensionamento_radiatore')) && k.includes(slug)
      );
      const anomalyEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k => k.startsWith('binary_sensor.') && k.includes('anomaly') && k.includes(slug));

      const titleEl = this.shadowRoot.getElementById('zone-title');
      const tempSubEl = this.shadowRoot.getElementById('temp-sub');
      const badgeEl = this.shadowRoot.getElementById('energy-badge');
      const modeBadge = this.shadowRoot.getElementById('zone-mode-badge');
      const retentionVal = this.shadowRoot.getElementById('retention-val');
      const retentionEval = this.shadowRoot.getElementById('retention-eval');
      const sizingVal = this.shadowRoot.getElementById('sizing-val');
      const sizingEval = this.shadowRoot.getElementById('sizing-eval');
      const valveDot = this.shadowRoot.getElementById('valve-dot');
      const valveText = this.shadowRoot.getElementById('valve-text');
      const batteryText = this.shadowRoot.getElementById('battery-text');
      const batteryIcon = this.shadowRoot.getElementById('battery-icon');

      // Robust determination of zone mode (primary, secondary, bypass)
      let zoneMode = "primary";
      const switchEntity = autoDiscoverSwitch(this._hass, climateId);
      if (switchEntity && this._hass.states[switchEntity]) {
        const sState = this._hass.states[switchEntity];
        if (switchEntity.startsWith("switch.")) {
          zoneMode = (sState.state === "off") ? "bypass" : "primary";
        } else {
          zoneMode = sState.state || "primary";
        }
      } else if (climateState.attributes && climateState.attributes.zone_mode) {
        zoneMode = climateState.attributes.zone_mode;
      } else {
        const selectObj = Object.values(this._hass.states).find(s => 
          s.entity_id.startsWith('select.') && (
            (s.attributes && s.attributes.climate_entity === climateId) ||
            (s.entity_id.includes(slug) && (s.entity_id.includes('mode') || s.entity_id.includes('zone')))
          )
        );
        if (selectObj && selectObj.state) {
          zoneMode = selectObj.state;
        }
      }

      if (titleEl) titleEl.innerText = title;

      if (tempSubEl) {
        const cur = climateState.attributes.current_temperature;
        const tgt = climateState.attributes.temperature;
        if (zoneMode === "bypass") {
          tempSubEl.innerText = `${cur !== undefined ? cur : '--'}°C / (${t('bypassed_tag')})`;
        } else {
          tempSubEl.innerText = `${cur !== undefined ? cur : '--'}°C / ${t('target')} ${tgt !== undefined ? tgt : '--'}°C`;
        }
      }

      this._currentZoneMode = zoneMode;
      this._currentSwitchEntity = switchEntity;

      if (modeBadge) {
        if (!this._modeListenerAttached && switchEntity) {
          this._modeListenerAttached = true;
          modeBadge.addEventListener('click', (e) => {
            e.stopPropagation();
            const activeSwitchEntity = this._currentSwitchEntity;
            const activeZoneMode = this._currentZoneMode || 'primary';
            if (!activeSwitchEntity) return;
            if (activeSwitchEntity.startsWith('select.')) {
              const modes = ['primary', 'secondary', 'bypass'];
              const curIdx = modes.indexOf(activeZoneMode);
              const nextMode = modes[(curIdx + 1) % modes.length];
              this._hass.callService('select', 'select_option', {
                entity_id: activeSwitchEntity,
                option: nextMode
              });
            } else if (activeSwitchEntity.startsWith('switch.')) {
              this._hass.callService('switch', 'toggle', {
                entity_id: activeSwitchEntity
              });
            }
          });
        }

        if (zoneMode === "bypass") {
          modeBadge.innerText = t('bypassed_tag');
          modeBadge.style.background = "rgba(100, 116, 139, 0.25)";
          modeBadge.style.color = "#94a3b8";
          modeBadge.style.border = "1px solid rgba(148, 163, 184, 0.3)";
        } else if (zoneMode === "secondary") {
          modeBadge.innerText = t('secondary_tag');
          modeBadge.style.background = "rgba(168, 85, 247, 0.2)";
          modeBadge.style.color = "#c084fc";
          modeBadge.style.border = "1px solid rgba(168, 85, 247, 0.3)";
        } else {
          modeBadge.innerText = t('primary_tag');
          modeBadge.style.background = "rgba(59, 130, 246, 0.2)";
          modeBadge.style.color = "#60a5fa";
          modeBadge.style.border = "1px solid rgba(59, 130, 246, 0.3)";
        }
      }

      const eState = energyEntity ? this._hass.states[energyEntity] : null;
      const energyClass = eState ? eState.state : "--";
      const colors = {
        'A4': '#00873d', 'A': '#139f37', 'B': '#55b726', 'C': '#96c818',
        'D': '#e0d100', 'E': '#f39200', 'F': '#e64213', 'G': '#cb0019'
      };

      if (badgeEl) {
        badgeEl.innerText = energyClass;
        if (colors[energyClass]) {
          badgeEl.style.backgroundColor = colors[energyClass];
          badgeEl.style.color = (['C', 'D'].includes(energyClass)) ? '#111' : '#fff';
        } else {
          badgeEl.style.backgroundColor = '#64748b';
          badgeEl.style.color = '#fff';
        }
      }

      ['A4', 'A', 'B', 'C', 'D', 'E', 'F', 'G'].forEach(cls => {
        const stepEl = this.shadowRoot.getElementById('step-' + cls);
        if (stepEl) {
          if (cls === energyClass) {
            stepEl.classList.add('active');
          } else {
            stepEl.classList.remove('active');
          }
        }
      });

      const rState = retentionEntity ? this._hass.states[retentionEntity] : null;
      if (retentionVal && rState) {
        const r = parseFloat(rState.state);
        retentionVal.innerText = isNaN(r) ? "--" : r.toFixed(1);
        if (retentionEval) {
          if (isNaN(r)) retentionEval.innerText = t('learning');
          else if (r >= 6.0) retentionEval.innerText = t('opt_insulation');
          else if (r >= 3.5) retentionEval.innerText = t('med_insulation');
          else retentionEval.innerText = t('fast_dispersion');
        }
      }

      const sState = sizingEntity ? this._hass.states[sizingEntity] : null;
      if (sizingVal && sState) {
        sizingVal.innerText = sState.state;
        if (sizingEval) {
          if (sState.state === "Optimal" || sState.state === "Ottimale") {
            sizingEval.innerText = t('sizing_opt');
            sizingEval.style.color = "#34d399";
          } else if (sState.state === "Undersized" || sState.state === "Sottodimensionato") {
            sizingEval.innerText = t('sizing_under');
            sizingEval.style.color = "#f87171";
          } else if (sState.state === "Oversized" || sState.state === "Sovradimensionato") {
            sizingEval.innerText = t('sizing_over');
            sizingEval.style.color = "#fbbf24";
          } else {
            sizingEval.innerText = t('sizing_waiting');
            sizingEval.style.color = "#94a3b8";
          }
        }
      }

      const aState = anomalyEntity ? this._hass.states[anomalyEntity] : null;
      const passiveHeatSwitch = this._hass && this._hass.states && Object.keys(this._hass.states).find(k => 
        k.startsWith('switch.') && k.includes('passive_heat') && k.includes(slug)
      );
      const swState = passiveHeatSwitch ? this._hass.states[passiveHeatSwitch] : null;
      const allowPassive = (swState && swState.state === 'on') || (climateState.attributes && climateState.attributes.allow_passive_heat);

      const valveStatusEl = this.shadowRoot.getElementById('valve-status');
      if (valveStatusEl) {
        if (!this._valveListenerAttached) {
          this._valveListenerAttached = true;
          valveStatusEl.style.cursor = 'pointer';
          valveStatusEl.addEventListener('click', (e) => {
            e.stopPropagation();
            const sw = this._hass && this._hass.states && Object.keys(this._hass.states).find(k => 
              k.startsWith('switch.') && k.includes('passive_heat') && k.includes(slug)
            );
            if (sw) {
              this._hass.callService('switch', 'toggle', { entity_id: sw });
            }
          });
        }
        valveStatusEl.title = allowPassive 
          ? getTranslation(this._hass, 'passive_heat_active_tooltip') 
          : getTranslation(this._hass, 'passive_heat_inactive_tooltip');
      }

      if (valveDot && valveText) {
        const hasAnomaly = aState && aState.state === "on";
        if (hasAnomaly) {
          valveDot.className = "pulse-dot pulse-red";
          valveText.innerText = (aState.attributes && aState.attributes.details) || getTranslation(this._hass, 'anomaly_detected');
          valveText.style.color = "#f87171";
        } else if (zoneMode === "bypass") {
          valveDot.className = "pulse-dot pulse-green";
          valveText.innerText = allowPassive ? `${t('valve_closed_bypass')} (${t('passive_heat_active')})` : t('valve_closed_bypass');
          valveText.style.color = "#94a3b8";
        } else {
          valveDot.className = "pulse-dot pulse-green";
          valveText.innerText = allowPassive ? `${t('valve_ok')} (${t('passive_heat_active')})` : t('valve_ok');
          valveText.style.color = "#34d399";
        }
      }

      if (batteryText && batteryIcon) {
        let batVal = null;
        if (climateState.attributes && climateState.attributes.battery_level !== undefined && climateState.attributes.battery_level !== null) {
          batVal = climateState.attributes.battery_level;
        } else if (this._hass && this._hass.states) {
          const checkEntityBattery = (entId) => {
            if (!entId) return null;
            const clean = entId.replace('sensor.', '').replace('climate.', '').replace(/_temperature|_temp|_current_temperature$/, '');
            const candidateKeys = [
              `sensor.${clean}_battery`,
              `sensor.${clean}_battery_level`,
            ];
            for (const cand of candidateKeys) {
              if (this._hass.states[cand] && !['unavailable', 'unknown'].includes(this._hass.states[cand].state)) {
                const p = parseFloat(this._hass.states[cand].state);
                if (!isNaN(p)) return Math.round(p);
              }
            }
            const targetState = this._hass.states[entId];
            if (targetState && targetState.attributes) {
              for (const attr of ['battery', 'battery_level', 'battery_percent']) {
                if (targetState.attributes[attr] !== undefined) {
                  const p = parseFloat(targetState.attributes[attr]);
                  if (!isNaN(p)) return Math.round(p);
                }
              }
            }
            return null;
          };

          if (climateState.attributes && climateState.attributes.temperature_sensor) {
            batVal = checkEntityBattery(climateState.attributes.temperature_sensor);
          }
          if (batVal === null && climateState.attributes && Array.isArray(climateState.attributes.climates)) {
            for (const trv of climateState.attributes.climates) {
              const trvBat = checkEntityBattery(trv);
              if (trvBat !== null) {
                batVal = trvBat;
                break;
              }
            }
          }
          if (batVal === null) {
            const batEntity = Object.keys(this._hass.states).find(k => 
              k.startsWith('sensor.') && 
              (k.includes('battery') || k.includes('batteria')) && 
              k.includes(slug) &&
              !['unavailable', 'unknown'].includes(this._hass.states[k].state)
            );
            if (batEntity && this._hass.states[batEntity]) {
              const parsed = parseFloat(this._hass.states[batEntity].state);
              if (!isNaN(parsed)) {
                batVal = Math.round(parsed);
              }
            }
          }
        }

        if (batVal !== null && batVal !== undefined) {
          batteryText.innerText = batVal + "%";
          if (batVal > 80) {
            batteryIcon.icon = "mdi:battery";
            batteryIcon.style.color = "#10b981";
          } else if (batVal > 40) {
            batteryIcon.icon = "mdi:battery-50";
            batteryIcon.style.color = "#f39c12";
          } else if (batVal > 15) {
            batteryIcon.icon = "mdi:battery-20";
            batteryIcon.style.color = "#e67e22";
          } else {
            batteryIcon.icon = "mdi:battery-alert";
            batteryIcon.style.color = "#ef4444";
          }
        } else {
          batteryText.innerText = "--%";
          batteryIcon.icon = "mdi:battery-unknown";
          batteryIcon.style.color = "var(--secondary-text-color, #94a3b8)";
        }
      }
    } catch (err) {
      console.error("Error updating MultizoneThermostatZoneEnergyCard:", err);
    }
  }
}

if (!customElements.get("multizone-thermostat-zone-energy-card")) {
  customElements.define("multizone-thermostat-zone-energy-card", MultizoneThermostatZoneEnergyCard);
}

/* ==================== DASHBOARD STRATEGY ==================== */
/* ==================== MULTIZONE SCHEDULER & SMART RETURN MAIN CARD ==================== */

class MultizoneThermostatSchedulerCard extends HTMLElement {
  getCardSize() { return 6; }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._hass = null;
    this._config = {};
    this._editorProfileId = 'standard';
    const dayMap = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
    this._selectedDay = dayMap[new Date().getDay()] || 'mon';
    this._activeBrush = 'comfort'; // 'comfort', 'eco', 'sleep', 'away', 'erase'
    this._activeModal = null; // null | 'slot' | 'activate' | 'smart_return' | 'duplicate'
    this._modalData = {};
    this._copiedRoomSchedule = null;
    this._localScheduleCache = null;
    this._lastHaScheduleJson = "";
    this._rendered = false;
    this._refreshTimer = null;
  }

  setConfig(config) {
    this._config = config || {};
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this.render();
      this._rendered = true;
      const raw = this._extractHaScheduleStatus();
      this._lastHaScheduleJson = raw ? JSON.stringify(raw) : "";
    } else {
      const raw = this._extractHaScheduleStatus();
      const currentJson = raw ? JSON.stringify(raw) : "";
      if (currentJson && currentJson !== this._lastHaScheduleJson) {
        this._lastHaScheduleJson = currentJson;
        this._localScheduleCache = null;
        this.renderHeader();
        this.renderLiveZones();
        this.renderEditor();
        this.renderPresetMatrixTable();
      } else {
        this.updateDynamicState();
      }
    }
  }

  connectedCallback() {
    this._refreshTimer = setInterval(() => {
      this.updateCurrentTimeIndicator();
    }, 60000);
  }

  disconnectedCallback() {
    if (this._refreshTimer) {
      clearInterval(this._refreshTimer);
      this._refreshTimer = null;
    }
  }

  _t(key) {
    return getTranslation(this._hass, key);
  }

  _extractHaScheduleStatus() {
    if (!this._hass || !this._hass.states) return null;
    for (const eid of Object.keys(this._hass.states)) {
      if (eid.startsWith('switch.') && (eid.includes('weekly_scheduler') || eid.includes('scheduler'))) {
        const s = this._hass.states[eid];
        if (s.attributes && s.attributes.schedule_status) {
          return s.attributes.schedule_status;
        }
      }
    }
    const masterEid = findMasterEntity(this._hass);
    if (masterEid && this._hass.states[masterEid]?.attributes?.schedule_status) {
      return this._hass.states[masterEid].attributes.schedule_status;
    }
    for (const eid of Object.keys(this._hass.states)) {
      if (this._hass.states[eid]?.attributes?.schedule_status) {
        return this._hass.states[eid].attributes.schedule_status;
      }
    }
    return null;
  }

  _getScheduleStatus() {
    if (this._localScheduleCache) {
      return this._localScheduleCache;
    }
    const haSched = this._extractHaScheduleStatus();
    if (haSched) return haSched;
    return this._getDefaultSchedule();
  }

  _getDefaultSchedule() {
    return {
      scheduler_enabled: true,
      active_profile: 'standard',
      profile_expires_at: null,
      fallback_profile: 'standard',
      profiles: {
        standard: {
          name: 'Standard',
          baseline_preset: 'eco',
          days: { mon: {}, tue: {}, wed: {}, thu: {}, fri: {}, sat: {}, sun: {} }
        },
        smart_working: {
          name: 'Smart Working',
          baseline_preset: 'eco',
          days: { mon: {}, tue: {}, wed: {}, thu: {}, fri: {}, sat: {}, sun: {} }
        },
        holiday: {
          name: 'Festivo',
          baseline_preset: 'eco',
          days: { mon: {}, tue: {}, wed: {}, thu: {}, fri: {}, sat: {}, sun: {} }
        }
      },
      manual_overrides: {},
      smart_start_info: {},
      smart_return: null,
      smart_return_plan: {},
      preset_matrix: {
        comfort: {},
        eco: {},
        sleep: {},
        away: {}
      }
    };
  }

  _getZones() {
    if (!this._hass || !this._hass.states) return [];
    const zones = [];
    const seenClimates = new Set();

    for (const eid of Object.keys(this._hass.states)) {
      const s = this._hass.states[eid];
      const climateId = s.attributes ? s.attributes.climate_entity : null;
      if (climateId && this._hass.states[climateId] && !seenClimates.has(climateId)) {
        seenClimates.add(climateId);
        const cState = this._hass.states[climateId];
        let name = cState.attributes.friendly_name || climateId;
        name = name.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
        zones.push({
          id: climateId,
          climate: climateId,
          switch: eid,
          name: name,
          current_temp: typeof cState.attributes.current_temperature === 'number' ? cState.attributes.current_temperature : 20.0,
          target_temp: typeof cState.attributes.temperature === 'number' ? cState.attributes.temperature : 20.0,
          hvac_mode: cState.state,
          heating_rate: typeof cState.attributes.heating_rate === 'number' ? cState.attributes.heating_rate : 1.0,
          manual_override: !!cState.attributes.schedule_manual_override,
          override_until: cState.attributes.schedule_override_until || null,
          smart_start: !!cState.attributes.smart_start_active,
          smart_start_detail: cState.attributes.smart_start_detail || ""
        });
      }
    }

    for (const eid of Object.keys(this._hass.states)) {
      if (eid.startsWith('climate.') && (eid.includes('multizone_thermostat_') || this._hass.states[eid]?.attributes?.hybrid_zone === true)) {
        if (!seenClimates.has(eid)) {
          seenClimates.add(eid);
          const cState = this._hass.states[eid];
          let name = cState.attributes.friendly_name || eid;
          name = name.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
          zones.push({
            id: eid,
            climate: eid,
            switch: null,
            name: name,
            current_temp: typeof cState.attributes.current_temperature === 'number' ? cState.attributes.current_temperature : 20.0,
            target_temp: typeof cState.attributes.temperature === 'number' ? cState.attributes.temperature : 20.0,
            hvac_mode: cState.state,
            heating_rate: typeof cState.attributes.heating_rate === 'number' ? cState.attributes.heating_rate : 1.0,
            manual_override: !!cState.attributes.schedule_manual_override,
            override_until: cState.attributes.schedule_override_until || null,
            smart_start: !!cState.attributes.smart_start_active,
            smart_start_detail: cState.attributes.smart_start_detail || ""
          });
        }
      }
    }

    zones.sort((a, b) => a.name.localeCompare(b.name));
    return zones;
  }

  _resolvePresetTemp(zoneId, preset) {
    const sched = this._getScheduleStatus();
    if (sched.preset_matrix && sched.preset_matrix[preset]) {
      if (typeof sched.preset_matrix[preset][zoneId] === 'number') {
        return sched.preset_matrix[preset][zoneId];
      }
    }
    const defaults = { comfort: 21.0, eco: 19.0, sleep: 17.0, away: 15.0 };
    return defaults[preset] || 20.0;
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          --card-border-radius: var(--ha-card-border-radius, 20px);
          font-family: var(--paper-font-body1_-_font-family, sans-serif);
        }
        ha-card {
          padding: 20px;
          border-radius: var(--card-border-radius);
          background-color: var(--card-background-color, #1e293b);
          color: var(--primary-text-color, #f8fafc);
          box-sizing: border-box;
          position: relative;
        }
        .header-bar {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          margin-bottom: 20px;
          padding-bottom: 16px;
          border-bottom: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
        }
        .header-title-box {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .header-title-box ha-icon {
          --mdc-icon-size: 32px;
          color: #38bdf8;
        }
        .header-title {
          font-size: 1.35rem;
          font-weight: 700;
        }
        .header-badges {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 8px;
        }
        .badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border-radius: 9999px;
          font-size: 0.85rem;
          font-weight: 600;
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.12);
        }
        .badge-btn {
          cursor: pointer;
          transition: all 0.2s ease;
        }
        .badge-btn:hover {
          background: rgba(255, 255, 255, 0.18);
          transform: translateY(-1px);
        }
        .badge-green {
          background: rgba(16, 185, 129, 0.2);
          border-color: rgba(16, 185, 129, 0.4);
          color: #34d399;
        }
        .badge-orange {
          background: rgba(249, 115, 22, 0.2);
          border-color: rgba(249, 115, 22, 0.4);
          color: #fb923c;
        }
        .badge-amber {
          background: rgba(245, 158, 11, 0.2);
          border-color: rgba(245, 158, 11, 0.4);
          color: #fcd34d;
        }
        .badge-blue {
          background: rgba(56, 189, 248, 0.2);
          border-color: rgba(56, 189, 248, 0.4);
          color: #38bdf8;
        }
        .badge-gray {
          background: rgba(148, 163, 184, 0.15);
          border-color: rgba(148, 163, 184, 0.3);
          color: #94a3b8;
        }
        .header-actions {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 10px;
        }
        .btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          padding: 8px 14px;
          border-radius: 8px;
          font-size: 0.875rem;
          font-weight: 600;
          cursor: pointer;
          border: none;
          transition: all 0.2s ease;
          background: rgba(255, 255, 255, 0.1);
          color: white;
        }
        .btn:hover {
          background: rgba(255, 255, 255, 0.2);
          transform: translateY(-1px);
        }
        .btn-primary { background: #0284c7; color: white; }
        .btn-primary:hover { background: #0369a1; }
        .btn-amber { background: #d97706; color: white; }
        .btn-amber:hover { background: #b45309; }
        .btn-danger { background: #dc2626; color: white; }
        .btn-danger:hover { background: #b91c1c; }
        
        .live-zones-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
          gap: 14px;
          margin-bottom: 24px;
        }
        .zone-card {
          background: rgba(255, 255, 255, 0.04);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 14px;
          padding: 14px;
          display: flex;
          flex-direction: column;
          gap: 10px;
          transition: border-color 0.2s;
        }
        .zone-card:hover { border-color: rgba(255, 255, 255, 0.18); }
        .zone-card-top {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }
        .zone-card-title {
          font-weight: 700;
          font-size: 1.05rem;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .zone-card-mid {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }
        .temp-display {
          display: flex;
          align-items: baseline;
          gap: 6px;
        }
        .current-temp { font-size: 1.45rem; font-weight: 800; }
        .target-temp { font-size: 1.15rem; font-weight: 600; opacity: 0.85; }
        .temp-controls {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .btn-circle {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(255, 255, 255, 0.1);
          color: white;
          border: none;
          font-size: 1.1rem;
          cursor: pointer;
          transition: all 0.2s;
        }
        .btn-circle:hover { background: rgba(255, 255, 255, 0.25); }
        .zone-card-bottom {
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 0.8rem;
          opacity: 0.85;
          border-top: 1px solid rgba(255, 255, 255, 0.06);
          padding-top: 6px;
        }

        .editor-box {
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 16px;
          padding: 16px;
          margin-bottom: 24px;
        }
        .editor-header-bar {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 14px;
        }
        .profile-tabs {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }
        .profile-tab {
          padding: 8px 16px;
          border-radius: 10px;
          background: rgba(255, 255, 255, 0.06);
          color: var(--primary-text-color, #f8fafc);
          font-weight: 600;
          cursor: pointer;
          border: 1px solid transparent;
          transition: all 0.2s;
        }
        .profile-tab.active {
          background: #0284c7;
          color: white;
          border-color: #38bdf8;
        }
        .editor-controls {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 10px;
        }
        .baseline-select-box {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 0.875rem;
        }
        select, input[type="text"], input[type="number"], input[type="time"], input[type="datetime-local"] {
          background: rgba(15, 23, 42, 0.8);
          border: 1px solid rgba(255, 255, 255, 0.15);
          color: white;
          padding: 6px 10px;
          border-radius: 6px;
          font-size: 0.875rem;
          outline: none;
        }
        select:focus, input:focus { border-color: #38bdf8; }
        .bg-notice-banner {
          background: rgba(245, 158, 11, 0.12);
          border: 1px solid rgba(245, 158, 11, 0.3);
          color: #fcd34d;
          padding: 8px 12px;
          border-radius: 8px;
          font-size: 0.85rem;
          margin-bottom: 14px;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .toolbar-bar {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 16px;
          background: rgba(255, 255, 255, 0.03);
          padding: 10px 14px;
          border-radius: 12px;
        }
        .day-pills { display: flex; gap: 4px; }
        .day-pill {
          padding: 6px 12px;
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.06);
          cursor: pointer;
          font-size: 0.85rem;
          font-weight: 600;
          transition: all 0.2s;
        }
        .day-pill.active { background: #0284c7; color: white; }
        .day-pill.today::after { content: " •"; color: #38bdf8; font-weight: 900; }

        .matrix-container {
          overflow-x: auto;
          margin-bottom: 20px;
        }
        .time-ruler {
          display: flex;
          margin-left: 140px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          padding-bottom: 4px;
          margin-bottom: 8px;
          position: relative;
        }
        .ruler-hour {
          flex: 1;
          text-align: left;
          font-size: 0.75rem;
          color: rgba(255, 255, 255, 0.6);
        }
        .matrix-row {
          display: flex;
          align-items: center;
          margin-bottom: 8px;
          gap: 10px;
        }
        .room-label-box {
          width: 130px;
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 4px;
        }
        .room-title {
          font-size: 0.875rem;
          font-weight: 600;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .room-copy-btn {
          background: none;
          border: none;
          color: rgba(255, 255, 255, 0.6);
          cursor: pointer;
          padding: 2px;
          font-size: 0.85rem;
        }
        .room-copy-btn:hover { color: white; }
        .timeline-track {
          flex: 1;
          height: 38px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 8px;
          position: relative;
          cursor: crosshair;
          overflow: hidden;
          border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .grid-line {
          position: absolute;
          top: 0;
          bottom: 0;
          width: 1px;
          background: rgba(255, 255, 255, 0.04);
          pointer-events: none;
        }
        .current-time-line {
          position: absolute;
          top: 0;
          bottom: 0;
          width: 2px;
          background: #ef4444;
          z-index: 10;
          pointer-events: none;
          box-shadow: 0 0 6px #ef4444;
        }
        .time-block {
          position: absolute;
          top: 3px;
          bottom: 3px;
          border-radius: 6px;
          display: flex;
          align-items: center;
          padding: 0 6px;
          font-size: 0.75rem;
          font-weight: 700;
          color: white;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          cursor: pointer;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
          transition: transform 0.1s, filter 0.1s;
          z-index: 2;
        }
        .time-block:hover {
          transform: scaleY(1.08);
          filter: brightness(1.15);
          z-index: 5;
        }
        .block-comfort { background: linear-gradient(135deg, #f97316, #ea580c); }
        .block-eco { background: linear-gradient(135deg, #22c55e, #16a34a); }
        .block-sleep { background: linear-gradient(135deg, #6366f1, #4f46e5); }
        .block-away { background: linear-gradient(135deg, #06b6d4, #0891b2); }

        .matrix-table-container {
          margin-top: 24px;
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 14px;
          padding: 16px;
          overflow-x: auto;
        }
        .matrix-table-title {
          font-size: 1.1rem;
          font-weight: 700;
          margin-bottom: 12px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.875rem;
        }
        th, td {
          padding: 10px 12px;
          text-align: left;
          border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }
        th { font-weight: 600; color: rgba(255, 255, 255, 0.7); }
        /* Preset summary card */
        .preset-summary-card {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 14px;
          padding: 14px;
          margin-top: 14px;
        }
        .preset-summary-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }
        .preset-summary-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
          gap: 10px;
        }
        .preset-summary-zone-card {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 10px;
          padding: 10px 12px;
        }
        .preset-zone-name {
          font-weight: 600;
          font-size: 0.85rem;
          margin-bottom: 6px;
          color: rgba(255, 255, 255, 0.9);
        }
        .preset-badges-row {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
        }
        .preset-badge {
          font-size: 0.75rem;
          font-weight: 600;
          padding: 3px 7px;
          border-radius: 6px;
        }
        .preset-badge.badge-comfort {
          background: rgba(239, 68, 68, 0.15);
          color: #f87171;
          border: 1px solid rgba(239, 68, 68, 0.3);
        }
        .preset-badge.badge-eco {
          background: rgba(34, 197, 94, 0.15);
          color: #4ade80;
          border: 1px solid rgba(34, 197, 94, 0.3);
        }
        .preset-badge.badge-sleep {
          background: rgba(59, 130, 246, 0.15);
          color: #60a5fa;
          border: 1px solid rgba(59, 130, 246, 0.3);
        }
        .preset-badge.badge-away {
          background: rgba(148, 163, 184, 0.15);
          color: #cbd5e1;
          border: 1px solid rgba(148, 163, 184, 0.3);
        }

        /* Slot modal enhancements */
        .slot-modal-wide {
          max-width: 580px;
          width: 100%;
        }
        .form-section {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.07);
          border-radius: 12px;
          padding: 12px 14px;
          margin-bottom: 14px;
        }
        .sub-label {
          font-size: 0.75rem;
          color: rgba(255, 255, 255, 0.6);
          display: block;
          margin-bottom: 4px;
        }
        .time-input {
          background: rgba(0, 0, 0, 0.25);
          border: 1px solid rgba(255, 255, 255, 0.15);
          border-radius: 8px;
          color: white;
          padding: 8px 10px;
          font-size: 1rem;
          width: 100%;
          box-sizing: border-box;
          font-family: inherit;
        }
        .duration-badge {
          font-size: 0.78rem;
          background: rgba(56, 189, 248, 0.15);
          color: #38bdf8;
          border: 1px solid rgba(56, 189, 248, 0.3);
          border-radius: 6px;
          padding: 3px 8px;
        }
        .quick-duration-bar {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
          margin-top: 10px;
          align-items: center;
        }
        .duration-pill {
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.12);
          color: white;
          border-radius: 14px;
          padding: 4px 10px;
          font-size: 0.75rem;
          cursor: pointer;
          transition: all 0.15s ease;
        }
        .duration-pill:hover {
          background: rgba(255, 255, 255, 0.12);
          border-color: rgba(255, 255, 255, 0.25);
        }
        .duration-pill.active {
          background: #0284c7;
          border-color: #38bdf8;
          color: white;
          font-weight: 600;
        }
        .general-preset-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 8px;
        }
        .general-preset-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 10px 6px;
          border-radius: 10px;
          border: 2px solid rgba(255, 255, 255, 0.1);
          background: rgba(255, 255, 255, 0.04);
          color: white;
          cursor: pointer;
          transition: all 0.15s ease;
        }
        .general-preset-card:hover {
          border-color: rgba(255, 255, 255, 0.25);
          background: rgba(255, 255, 255, 0.08);
        }
        .general-preset-card.active {
          border-color: #38bdf8;
          background: rgba(56, 189, 248, 0.2);
          box-shadow: 0 0 12px rgba(56, 189, 248, 0.3);
        }
        .preset-card-icon {
          font-size: 1.4rem;
          margin-bottom: 4px;
        }
        .preset-card-name {
          font-size: 0.8rem;
          font-weight: 600;
        }
        .zone-exceptions-container {
          display: flex;
          flex-direction: column;
          gap: 8px;
          max-height: 220px;
          overflow-y: auto;
          padding-right: 4px;
        }
        .zone-exception-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 10px;
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 8px;
          gap: 12px;
        }
        .zone-exception-name {
          font-weight: 600;
          font-size: 0.82rem;
          color: rgba(255, 255, 255, 0.9);
          flex: 1;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .zone-override-select {
          background: #0f172a;
          border: 1px solid rgba(255, 255, 255, 0.18);
          color: white;
          border-radius: 6px;
          padding: 5px 8px;
          font-size: 0.8rem;
          max-width: 280px;
          font-family: inherit;
        }
        .btn-xs {
          padding: 2px 7px;
          font-size: 0.72rem;
        }

        .modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.75);
          backdrop-filter: blur(4px);
          z-index: 9999;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 16px;
          box-sizing: border-box;
        }
        .modal-box {
          background: #1e293b;
          border: 1px solid rgba(255, 255, 255, 0.15);
          border-radius: 18px;
          padding: 24px;
          max-width: 520px;
          width: 100%;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
          color: white;
          max-height: 90vh;
          overflow-y: auto;
        }
        .modal-title {
          font-size: 1.25rem;
          font-weight: 700;
          margin-bottom: 16px;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .modal-close-btn {
          background: none;
          border: none;
          color: rgba(255, 255, 255, 0.6);
          font-size: 1.2rem;
          cursor: pointer;
        }
        .form-group {
          margin-bottom: 16px;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .form-label {
          font-size: 0.85rem;
          font-weight: 600;
          color: rgba(255, 255, 255, 0.8);
        }
        .checkbox-group { display: flex; flex-wrap: wrap; gap: 8px; }
        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 0.85rem;
          background: rgba(255, 255, 255, 0.05);
          padding: 4px 8px;
          border-radius: 6px;
          cursor: pointer;
        }
        .modal-actions {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
          margin-top: 20px;
        }
        .radar-list {
          margin-top: 14px;
          display: flex;
          flex-direction: column;
          gap: 8px;
          max-height: 250px;
          overflow-y: auto;
        }
        .radar-item {
          background: rgba(255, 255, 255, 0.04);
          padding: 10px 12px;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-left: 4px solid #f97316;
        }
        .radar-item-left { display: flex; flex-direction: column; gap: 2px; }
        .radar-item-right { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
      </style>
      <ha-card>
        <div id="header-container"></div>
        <div id="zones-container"></div>
        <div id="editor-container"></div>
        <div id="preset-matrix-container"></div>
        <div id="modal-container"></div>
      </ha-card>
    `;

    this.renderHeader();
    this.renderLiveZones();
    this.renderEditor();
    this.renderPresetMatrixTable();
  }

  updateDynamicState() {
    this.renderHeader();
    this.renderLiveZones();
    if (!this._activeModal) {
      this.updateCurrentTimeIndicator();
    }
  }

  renderHeader() {
    const container = this.shadowRoot.querySelector('#header-container');
    if (!container) return;

    const sched = this._getScheduleStatus();
    const enabled = !!sched.scheduler_enabled;
    const activeProf = sched.active_profile || 'standard';
    const profName = sched.profiles?.[activeProf]?.name || activeProf;

    let profPrefix = "🟢";
    if (activeProf === 'smart_working') profPrefix = "💼";
    else if (activeProf === 'holiday') profPrefix = "🎉";

    let expiryHtml = '';
    if (sched.profile_expires_at) {
      const expDate = new Date(sched.profile_expires_at);
      const expStr = isNaN(expDate.getTime()) ? String(sched.profile_expires_at) : expDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      expiryHtml = `
        <span class="badge badge-amber badge-btn" id="btn-cancel-expiry" title="Annulla scadenza">
          ⏳ Fino a ${expStr} ✕
        </span>
      `;
    }

    let srHtml = '';
    const sr = sched.smart_return;
    if (sr && sr.active) {
      const arr = sr.arrival_time ? sr.arrival_time.substring(0, 5) : '';
      srHtml = `
        <span class="badge badge-orange badge-btn" id="btn-cancel-sr" title="Annulla Smart Return">
          🚗 Rientro ore ${arr} ✕
        </span>
      `;
    }

    container.innerHTML = `
      <div class="header-bar">
        <div class="header-title-box">
          <ha-icon icon="mdi:calendar-clock"></ha-icon>
          <div class="header-title">${this._t('sched_title')}</div>
          <div class="header-badges">
            <button class="badge ${enabled ? 'badge-green' : 'badge-gray'} badge-btn" id="btn-toggle-sched">
              ${enabled ? '🟢 ' + this._t('sched_active') : '⚪ ' + this._t('sched_paused')}
            </button>
            <span class="badge badge-blue">
              ${profPrefix} ${profName}
            </span>
            ${expiryHtml}
            ${srHtml}
          </div>
        </div>
        <div class="header-actions">
          <button class="btn btn-primary" id="btn-open-activate">
            📅 ${this._t('sched_activate_btn')}
          </button>
          <button class="btn btn-amber" id="btn-open-sr">
            🚗 ${this._t('sched_smart_return_btn')}
          </button>
          <button class="btn" id="btn-reset-overrides" title="${this._t('sched_reset_overrides')}">
            ↺ ${this._t('sched_reset_overrides')}
          </button>
        </div>
      </div>
    `;

    container.querySelector('#btn-toggle-sched')?.addEventListener('click', () => {
      this._toggleScheduler(!enabled);
    });
    container.querySelector('#btn-cancel-expiry')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this._cancelProfileExpiry();
    });
    container.querySelector('#btn-cancel-sr')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this._cancelSmartReturn();
    });
    container.querySelector('#btn-open-activate')?.addEventListener('click', () => {
      this.openActivateModal();
    });
    container.querySelector('#btn-open-sr')?.addEventListener('click', () => {
      this.openSmartReturnModal();
    });
    container.querySelector('#btn-reset-overrides')?.addEventListener('click', () => {
      this._clearAllOverrides();
    });
  }

  _toggleScheduler(enable) {
    if (!this._hass) return;
    for (const eid of Object.keys(this._hass.states)) {
      if (eid.startsWith('switch.') && (eid.includes('weekly_scheduler') || eid.includes('scheduler'))) {
        this._hass.callService('switch', enable ? 'turn_on' : 'turn_off', { entity_id: eid });
        return;
      }
    }
    for (const eid of Object.keys(this._hass.states)) {
      if (eid.startsWith('switch.') && this._hass.states[eid].attributes?.schedule_status && this._hass.states[eid].attributes?.multizone_type !== 'master') {
        this._hass.callService('switch', enable ? 'turn_on' : 'turn_off', { entity_id: eid });
        return;
      }
    }
  }

  _cancelProfileExpiry() {
    if (!this._hass) return;
    const sched = this._getScheduleStatus();
    this._hass.callService('multizone_thermostat', 'activate_schedule_profile', {
      profile_id: sched.fallback_profile || 'standard',
      expires_at: ''
    });
  }

  _cancelSmartReturn() {
    if (!this._hass) return;
    this._hass.callService('multizone_thermostat', 'cancel_smart_return', {});
  }

  _clearAllOverrides() {
    if (!this._hass) return;
    this._hass.callService('multizone_thermostat', 'clear_zone_override', {});
  }

  renderLiveZones() {
    const container = this.shadowRoot.querySelector('#zones-container');
    if (!container) return;

    const zones = this._getZones();
    if (zones.length === 0) {
      container.innerHTML = `<div style="opacity:0.6; margin-bottom: 20px;">Nessuna zona termostato configurata.</div>`;
      return;
    }

    container.innerHTML = `
      <div class="live-zones-grid">
        ${zones.map(z => {
          let badgeHtml = '';
          if (z.hvac_mode === 'off') {
            badgeHtml = `<span class="badge badge-gray" style="color: #f87171;">⛔ ${this._t('sched_explicit_off')}</span>`;
          } else if (z.manual_override) {
            let untilStr = '';
            if (z.override_until) {
              const d = new Date(z.override_until);
              untilStr = isNaN(d.getTime()) ? String(z.override_until) : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }
            badgeHtml = `
              <span class="badge badge-amber badge-btn btn-clear-zone-override" data-zone="${z.climate}" title="${this._t('sched_restore')}">
                ✋ ${z.target_temp.toFixed(1)}°C ${untilStr ? this._t('sched_override_until') + ' ' + untilStr : ''} ✕
              </span>
            `;
          } else if (z.smart_start) {
            badgeHtml = `<span class="badge badge-orange">🔥 Smart Start ${z.smart_start_detail || ''}</span>`;
          } else {
            badgeHtml = `<span class="badge badge-green">🌿 ${z.target_temp.toFixed(1)}°C</span>`;
          }

          const isOff = z.hvac_mode === 'off';
          return `
            <div class="zone-card" data-zone="${z.climate}">
              <div class="zone-card-top">
                <span class="zone-card-title">${z.name}</span>
                ${badgeHtml}
              </div>
              <div class="zone-card-mid">
                <div class="temp-display">
                  <span class="current-temp">${z.current_temp.toFixed(1)}°C</span>
                  <span style="opacity:0.6;">➔</span>
                  <span class="target-temp">${z.target_temp.toFixed(1)}°C</span>
                </div>
                <div class="temp-controls">
                  <button class="btn-circle btn-temp-down" data-zone="${z.climate}" data-target="${z.target_temp}">-</button>
                  <button class="btn-circle btn-temp-up" data-zone="${z.climate}" data-target="${z.target_temp}">+</button>
                  <button class="btn ${isOff ? 'btn-primary' : 'btn-danger'}" data-zone="${z.climate}" data-action="toggle-power" style="padding: 4px 10px; font-size: 0.75rem;">
                    ${isOff ? this._t('sched_turn_on') : 'OFF'}
                  </button>
                </div>
              </div>
              <div class="zone-card-bottom">
                <span>Inerzia: ${z.heating_rate.toFixed(1)} °C/h</span>
                <span>${z.climate}</span>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;

    container.querySelectorAll('.btn-clear-zone-override').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const cid = btn.getAttribute('data-zone');
        if (this._hass && cid) {
          this._hass.callService('multizone_thermostat', 'clear_zone_override', { entity_id: cid });
        }
      });
    });

    container.querySelectorAll('.btn-temp-down').forEach(btn => {
      btn.addEventListener('click', () => {
        const cid = btn.getAttribute('data-zone');
        const cur = parseFloat(btn.getAttribute('data-target')) || 20.0;
        this._setZoneTemp(cid, Math.max(5.0, cur - 0.5));
      });
    });

    container.querySelectorAll('.btn-temp-up').forEach(btn => {
      btn.addEventListener('click', () => {
        const cid = btn.getAttribute('data-zone');
        const cur = parseFloat(btn.getAttribute('data-target')) || 20.0;
        this._setZoneTemp(cid, Math.min(35.0, cur + 0.5));
      });
    });

    container.querySelectorAll('[data-action="toggle-power"]').forEach(btn => {
      btn.addEventListener('click', () => {
        const cid = btn.getAttribute('data-zone');
        const z = zones.find(item => item.climate === cid);
        if (z && this._hass) {
          const nextMode = z.hvac_mode === 'off' ? 'heat' : 'off';
          this._hass.callService('climate', 'set_hvac_mode', { entity_id: cid, hvac_mode: nextMode });
        }
      });
    });
  }

  _setZoneTemp(entityId, temp) {
    if (!this._hass) return;
    this._hass.callService('climate', 'set_temperature', {
      entity_id: entityId,
      temperature: temp
    });
  }

  renderEditor() {
    const container = this.shadowRoot.querySelector('#editor-container');
    if (!container) return;

    const sched = this._getScheduleStatus();
    const activeProf = sched.active_profile || 'standard';
    const isBgEdit = this._editorProfileId !== activeProf;

    const profilesList = Object.keys(sched.profiles || { standard: {} });
    if (!profilesList.includes('standard')) profilesList.unshift('standard');
    if (!profilesList.includes('smart_working')) profilesList.push('smart_working');
    if (!profilesList.includes('holiday')) profilesList.push('holiday');

    const currentProfileData = sched.profiles?.[this._editorProfileId] || { baseline_preset: 'eco', days: {} };
    const currentBaseline = currentProfileData.baseline_preset || 'eco';

    const dayLabels = {
      mon: this._t('day_mon').substring(0, 3),
      tue: this._t('day_tue').substring(0, 3),
      wed: this._t('day_wed').substring(0, 3),
      thu: this._t('day_thu').substring(0, 3),
      fri: this._t('day_fri').substring(0, 3),
      sat: this._t('day_sat').substring(0, 3),
      sun: this._t('day_sun').substring(0, 3),
    };
    const dayMap = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
    const todayDay = dayMap[new Date().getDay()];

    container.innerHTML = `
      <div class="editor-box">
        <div class="editor-header-bar">
          <div class="profile-tabs">
            ${profilesList.map(pId => {
              const pObj = sched.profiles?.[pId];
              let pLabel = pObj?.name || pId.toUpperCase();
              let icon = "🟢";
              if (pId === 'smart_working') icon = "💼";
              else if (pId === 'holiday') icon = "🎉";
              const isActive = this._editorProfileId === pId;
              return `
                <button class="profile-tab ${isActive ? 'active' : ''}" data-profile="${pId}">
                  ${icon} ${pLabel}
                </button>
              `;
            }).join('')}
          </div>
          <div class="editor-controls">
            <div class="baseline-select-box">
              <span>${this._t('sched_baseline')}:</span>
              <select id="select-baseline">
                <option value="eco" ${currentBaseline === 'eco' ? 'selected' : ''}>🌿 Eco</option>
                <option value="sleep" ${currentBaseline === 'sleep' ? 'selected' : ''}>🌙 Notte</option>
                <option value="away" ${currentBaseline === 'away' ? 'selected' : ''}>🚶 Away</option>
                <option value="comfort" ${currentBaseline === 'comfort' ? 'selected' : ''}>🔥 Comfort</option>
              </select>
            </div>
            <button class="btn" id="btn-duplicate-profile">
              📋 ${this._t('sched_duplicate')}
            </button>
            <button class="btn btn-primary" id="btn-new-slot">
              ${this._t('sched_new_block')}
            </button>
          </div>
        </div>

        ${isBgEdit ? `
          <div class="bg-notice-banner">
            <span>✏️</span>
            <span>${this._t('sched_bg_edit_notice')}</span>
          </div>
        ` : ''}

        <div class="toolbar-bar">
          <div class="day-pills">
            ${['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'].map(d => {
              const isSel = this._selectedDay === d;
              const isToday = todayDay === d;
              return `
                <button class="day-pill ${isSel ? 'active' : ''} ${isToday ? 'today' : ''}" data-day="${d}">
                  ${dayLabels[d]}
                </button>
              `;
            }).join('')}
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn" id="btn-copy-weekdays" style="padding:4px 8px; font-size:0.75rem;">
              ⚡ ${this._t('sched_copy_weekdays')}
            </button>
            <button class="btn" id="btn-copy-weekend" style="padding:4px 8px; font-size:0.75rem;">
              ⚡ ${this._t('sched_copy_weekend')}
            </button>
          </div>
        </div>

        <div class="matrix-container" id="matrix-scroll-area">
          <div class="time-ruler">
            ${Array.from({ length: 13 }).map((_, i) => {
              const h = String(i * 2).padStart(2, '0');
              return `<div class="ruler-hour">${h}:00</div>`;
            }).join('')}
          </div>
          <div id="matrix-rows-container"></div>
        </div>
      </div>
    `;

    container.querySelectorAll('.profile-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this._editorProfileId = tab.getAttribute('data-profile');
        this.renderEditor();
      });
    });

    container.querySelector('#select-baseline')?.addEventListener('change', (e) => {
      this._updateBaselinePreset(e.target.value);
    });

    container.querySelector('#btn-duplicate-profile')?.addEventListener('click', () => {
      this.openDuplicateModal();
    });

    container.querySelector('#btn-new-slot')?.addEventListener('click', () => {
      this.openSlotModal({
        isEdit: false,
        preset: 'comfort',
        start: '07:00',
        end: '09:00',
        selectedDays: [this._selectedDay]
      });
    });

    container.querySelectorAll('.day-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        this._selectedDay = pill.getAttribute('data-day');
        this.renderEditor();
      });
    });

    container.querySelector('#btn-copy-weekdays')?.addEventListener('click', () => {
      this._copyDayToRange(['mon', 'tue', 'wed', 'thu', 'fri']);
    });

    container.querySelector('#btn-copy-weekend')?.addEventListener('click', () => {
      this._copyDayToRange(['sat', 'sun']);
    });

    this.renderMatrixRows();
  }

  _updateBaselinePreset(newPreset) {
    const sched = JSON.parse(JSON.stringify(this._getScheduleStatus()));
    if (!sched.profiles[this._editorProfileId]) {
      sched.profiles[this._editorProfileId] = { name: this._editorProfileId, baseline_preset: 'eco', days: {} };
    }
    sched.profiles[this._editorProfileId].baseline_preset = newPreset;
    this._localScheduleCache = sched;
    this._saveProfileToServer(this._editorProfileId, sched.profiles[this._editorProfileId]);
  }

  _copyDayToRange(targetDays) {
    const sched = JSON.parse(JSON.stringify(this._getScheduleStatus()));
    const prof = sched.profiles?.[this._editorProfileId];
    if (!prof) return;
    if (!prof.days) prof.days = {};

    const sourceDayBlocks = prof.days[this._selectedDay] || {};
    for (const d of targetDays) {
      if (d === this._selectedDay) continue;
      prof.days[d] = JSON.parse(JSON.stringify(sourceDayBlocks));
    }
    this._localScheduleCache = sched;
    this._saveProfileToServer(this._editorProfileId, prof);
    this.renderMatrixRows();
  }

  renderMatrixRows() {
    const rowsContainer = this.shadowRoot.querySelector('#matrix-rows-container');
    if (!rowsContainer) return;

    const zones = this._getZones();
    const sched = this._getScheduleStatus();
    const prof = sched.profiles?.[this._editorProfileId] || {};
    const daySchedule = prof.days?.[this._selectedDay] || {};

    const dayMap = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
    const isToday = dayMap[new Date().getDay()] === this._selectedDay;
    const now = new Date();
    const nowMinutes = now.getHours() * 60 + now.getMinutes();
    const nowPercent = (nowMinutes / 1440) * 100;

    rowsContainer.innerHTML = zones.map(z => {
      const blocks = daySchedule[z.climate] || daySchedule[z.id] || [];
      return `
        <div class="matrix-row" data-zone="${z.climate}">
          <div class="room-label-box">
            <span class="room-title" title="${z.name}">${z.name}</span>
            <button class="room-copy-btn btn-copy-room" data-zone="${z.climate}" title="Copia/Incolla programmazione stanza">
              📋
            </button>
          </div>
          <div class="timeline-track" data-zone="${z.climate}">
            ${Array.from({ length: 12 }).map((_, i) => `
              <div class="grid-line" style="left: ${(i + 1) * (100 / 12)}%;"></div>
            `).join('')}
            ${isToday ? `
              <div class="current-time-line" style="left: ${nowPercent}%;"></div>
            ` : ''}
            ${blocks.map((b, idx) => {
              const startMin = this._toMinutes(b.start);
              const endMin = this._toMinutes(b.end);
              const left = (startMin / 1440) * 100;
              const width = Math.max(1.5, ((endMin - startMin) / 1440) * 100);
              const presetClass = 'block-' + (b.preset || 'comfort');
              return `
                <div class="time-block ${presetClass}" style="left: ${left}%; width: ${width}%;"
                     data-zone="${z.climate}" data-index="${idx}" title="${(b.preset || 'comfort').toUpperCase()}: ${b.start} - ${b.end}">
                  ${(b.preset || 'comfort').substring(0, 3).toUpperCase()} ${b.start}-${b.end}
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }).join('');

    rowsContainer.querySelectorAll('.btn-copy-room').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const cid = btn.getAttribute('data-zone');
        this._handleRoomCopyPaste(cid);
      });
    });

    rowsContainer.querySelectorAll('.timeline-track').forEach(track => {
      track.addEventListener('click', (e) => {
        if (e.target.closest('.time-block')) return;
        const cid = track.getAttribute('data-zone');
        const rect = track.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const ratio = Math.max(0, Math.min(1, clickX / rect.width));
        const clickMin = Math.floor(ratio * 1440);
        const startMin = Math.floor(clickMin / 30) * 30;
        const endMin = Math.min(1440, startMin + 120);

        this.openSlotModal({
          isEdit: false,
          zoneId: cid,
          day: this._selectedDay,
          start: this._toTimeStr(startMin),
          end: this._toTimeStr(endMin),
          selectedDays: [this._selectedDay]
        });
      });
    });

    rowsContainer.querySelectorAll('.time-block').forEach(block => {
      block.addEventListener('click', (e) => {
        e.stopPropagation();
        const cid = block.getAttribute('data-zone');
        const idx = parseInt(block.getAttribute('data-index'), 10);
        const blocks = (sched.profiles?.[this._editorProfileId]?.days?.[this._selectedDay]?.[cid]) || [];
        const slot = blocks[idx];
        if (slot) {
          this.openSlotModal({
            isEdit: true,
            zoneId: cid,
            day: this._selectedDay,
            blockIndex: idx,
            preset: slot.preset || 'comfort',
            start: slot.start,
            end: slot.end,
            selectedDays: [this._selectedDay]
          });
        }
      });
    });
  }

  _handleRoomCopyPaste(zoneId) {
    const sched = this._getScheduleStatus();
    const prof = sched.profiles?.[this._editorProfileId];
    if (!prof) return;

    if (!this._copiedRoomSchedule) {
      const blocks = prof.days?.[this._selectedDay]?.[zoneId] || [];
      this._copiedRoomSchedule = {
        sourceZone: zoneId,
        blocks: JSON.parse(JSON.stringify(blocks))
      };
      alert("Programmazione stanza copiata! Clicca di nuovo 📋 su un'altra stanza per incollare.");
    } else {
      if (!prof.days) prof.days = {};
      if (!prof.days[this._selectedDay]) prof.days[this._selectedDay] = {};
      prof.days[this._selectedDay][zoneId] = JSON.parse(JSON.stringify(this._copiedRoomSchedule.blocks));

      const updatedSched = JSON.parse(JSON.stringify(sched));
      updatedSched.profiles[this._editorProfileId] = prof;
      this._localScheduleCache = updatedSched;
      this._saveProfileToServer(this._editorProfileId, prof);
      this.renderMatrixRows();
      this._copiedRoomSchedule = null;
    }
  }

  _toMinutes(timeStr) {
    if (!timeStr) return 0;
    const parts = timeStr.split(':').map(Number);
    return (parts[0] || 0) * 60 + (parts[1] || 0);
  }

  _toTimeStr(min) {
    const h = String(Math.floor(min / 60)).padStart(2, '0');
    const m = String(min % 60).padStart(2, '0');
    return h + ":" + m;
  }

  _applySlotToZone(prof, day, zoneId, startStr, endStr, preset) {
    if (!prof.days) prof.days = {};
    if (!prof.days[day]) prof.days[day] = {};
    if (!prof.days[day][zoneId]) prof.days[day][zoneId] = [];

    const startMin = this._toMinutes(startStr);
    let endMin = this._toMinutes(endStr);
    if (endStr === "23:59" || endStr === "24:00") endMin = 1440;
    if (startMin >= endMin) return;

    const existing = prof.days[day][zoneId];
    const newBlocks = [];

    for (const b of existing) {
      const bStart = this._toMinutes(b.start);
      let bEnd = this._toMinutes(b.end);
      if (b.end === "23:59" || b.end === "24:00") bEnd = 1440;
      const bPreset = b.preset || 'comfort';

      // No overlap
      if (bEnd <= startMin || bStart >= endMin) {
        newBlocks.push({ startMin: bStart, endMin: bEnd, preset: bPreset });
        continue;
      }
      // Overlap left remainder
      if (bStart < startMin) {
        newBlocks.push({ startMin: bStart, endMin: startMin, preset: bPreset });
      }
      // Overlap right remainder
      if (bEnd > endMin) {
        newBlocks.push({ startMin: endMin, endMin: bEnd, preset: bPreset });
      }
    }

    if (preset && preset !== 'none') {
      newBlocks.push({ startMin, endMin, preset });
    }

    newBlocks.sort((a, b) => a.startMin - b.startMin);

    const merged = [];
    for (const blk of newBlocks) {
      if (blk.startMin >= blk.endMin) continue;
      if (merged.length > 0) {
        const last = merged[merged.length - 1];
        if (last.endMin === blk.startMin && last.preset === blk.preset) {
          last.endMin = blk.endMin;
          continue;
        }
      }
      merged.push({ ...blk });
    }

    prof.days[day][zoneId] = merged.map(b => ({
      start: this._toTimeStr(b.startMin),
      end: b.endMin >= 1440 ? "24:00" : this._toTimeStr(b.endMin),
      preset: b.preset
    }));
  }

  _addSlot(zoneId, day, start, end, preset) {
    const sched = JSON.parse(JSON.stringify(this._getScheduleStatus()));
    if (!sched.profiles[this._editorProfileId]) {
      sched.profiles[this._editorProfileId] = {
        name: this._editorProfileId.toUpperCase(),
        baseline_preset: 'eco',
        days: {}
      };
    }
    const prof = sched.profiles[this._editorProfileId];
    this._applySlotToZone(prof, day, zoneId, start, end, preset);

    this._localScheduleCache = sched;
    this._saveProfileToServer(this._editorProfileId, prof);
    this.renderMatrixRows();
  }

  _deleteSlot(zoneId, day, blockIndex) {
    const sched = JSON.parse(JSON.stringify(this._getScheduleStatus()));
    const prof = sched.profiles?.[this._editorProfileId];
    if (prof && prof.days?.[day]?.[zoneId]) {
      prof.days[day][zoneId].splice(blockIndex, 1);
      this._localScheduleCache = sched;
      this._saveProfileToServer(this._editorProfileId, prof);
      this.renderMatrixRows();
    }
  }

  _saveProfileToServer(profileId, profObj) {
    if (!this._hass) return;
    this._hass.callService('multizone_thermostat', 'save_schedule_profile', {
      profile_id: profileId,
      name: profObj.name || profileId,
      baseline_preset: profObj.baseline_preset || 'eco',
      days: profObj.days || {}
    });
  }

  updateCurrentTimeIndicator() {
    const dayMap = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
    if (dayMap[new Date().getDay()] !== this._selectedDay) return;

    const now = new Date();
    const nowMinutes = now.getHours() * 60 + now.getMinutes();
    const nowPercent = (nowMinutes / 1440) * 100;
    this.shadowRoot.querySelectorAll('.current-time-line').forEach(el => {
      el.style.left = nowPercent + '%';
    });
  }

  renderPresetMatrixTable() {
    const container = this.shadowRoot.querySelector('#preset-matrix-container');
    if (!container) return;

    const zones = this._getZones();
    if (zones.length === 0) {
      container.innerHTML = '';
      return;
    }

    container.innerHTML = `
      <div class="preset-summary-card">
        <div class="preset-summary-header">
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:1.15rem;">🌡️</span>
            <div>
              <div style="font-weight:600; font-size:0.925rem;">Temperature Preset Standard</div>
              <div style="font-size:0.75rem; opacity:0.65;">Valori di riferimento in sola lettura sincronizzati dai Preset Standard dell'impianto</div>
            </div>
          </div>
        </div>
        <div class="preset-summary-grid">
          ${zones.map(z => {
            const cVal = this._resolvePresetTemp(z.climate, 'comfort');
            const eVal = this._resolvePresetTemp(z.climate, 'eco');
            const sVal = this._resolvePresetTemp(z.climate, 'sleep');
            const aVal = this._resolvePresetTemp(z.climate, 'away');
            return `
              <div class="preset-summary-zone-card">
                <div class="preset-zone-name">${z.name}</div>
                <div class="preset-badges-row">
                  <span class="preset-badge badge-comfort" title="Comfort">🔥 ${cVal.toFixed(1)}°C</span>
                  <span class="preset-badge badge-eco" title="Eco">🌿 ${eVal.toFixed(1)}°C</span>
                  <span class="preset-badge badge-sleep" title="Notte">🌙 ${sVal.toFixed(1)}°C</span>
                  <span class="preset-badge badge-away" title="Away">🚶 ${aVal.toFixed(1)}°C</span>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }
  /* ==================== MODALS ==================== */

  closeModal() {
    this._activeModal = null;
    this._modalData = {};
    const modalBox = this.shadowRoot.querySelector('#modal-container');
    if (modalBox) modalBox.innerHTML = '';
  }

  openSlotModal(data) {
    this._activeModal = 'slot';
    this._modalData = data || {};
    const modalContainer = this.shadowRoot.querySelector('#modal-container');
    if (!modalContainer) return;

    const zones = this._getZones();
    const sched = this._getScheduleStatus();
    const prof = sched.profiles?.[this._editorProfileId] || {};
    const currentBaseline = prof.baseline_preset || 'eco';
    const daySchedule = prof.days?.[data.day || this._selectedDay] || {};

    const days = [
      { id: 'mon', label: 'Lun' },
      { id: 'tue', label: 'Mar' },
      { id: 'wed', label: 'Mer' },
      { id: 'thu', label: 'Gio' },
      { id: 'fri', label: 'Ven' },
      { id: 'sat', label: 'Sab' },
      { id: 'sun', label: 'Dom' }
    ];

    const isEdit = !!data.isEdit;
    let curStart = data.start || '07:00';
    let curEnd = data.end || '09:00';
    if (curEnd === '24:00') curEnd = '23:59';
    const selDays = data.selectedDays || [this._selectedDay];

    // Determine initial General Preset and per-zone initial choices
    let initialGeneralPreset = data.preset || 'comfort';
    const initialZoneChoices = {}; // climateId -> 'inherit' | 'comfort' | 'eco' | 'sleep' | 'away' | 'none'

    if (isEdit) {
      const slotStart = data.start;
      const slotEnd = data.end;
      const presetCounts = { comfort: 0, eco: 0, sleep: 0, away: 0 };
      const zoneMatchPreset = {};

      for (const z of zones) {
        const zBlocks = daySchedule[z.climate] || daySchedule[z.id] || [];
        const match = zBlocks.find(b => b.start === slotStart && b.end === slotEnd)
                   || zBlocks.find(b => {
                       const bS = this._toMinutes(b.start);
                       let bE = this._toMinutes(b.end);
                       if (b.end === '23:59' || b.end === '24:00') bE = 1440;
                       const sS = this._toMinutes(slotStart);
                       let sE = this._toMinutes(slotEnd);
                       if (slotEnd === '23:59' || slotEnd === '24:00') sE = 1440;
                       return Math.max(bS, sS) < Math.min(bE, sE);
                     });
        if (match) {
          const p = match.preset || 'comfort';
          zoneMatchPreset[z.climate] = p;
          presetCounts[p] = (presetCounts[p] || 0) + 1;
        } else {
          zoneMatchPreset[z.climate] = 'none';
        }
      }

      let maxC = 0;
      for (const [p, c] of Object.entries(presetCounts)) {
        if (c > maxC) {
          maxC = c;
          initialGeneralPreset = p;
        }
      }

      for (const z of zones) {
        const matchedP = zoneMatchPreset[z.climate];
        if (matchedP === initialGeneralPreset) {
          initialZoneChoices[z.climate] = 'inherit';
        } else if (matchedP && matchedP !== 'none') {
          initialZoneChoices[z.climate] = matchedP;
        } else {
          initialZoneChoices[z.climate] = 'none';
        }
      }
    } else {
      initialGeneralPreset = data.preset || 'comfort';
      for (const z of zones) {
        initialZoneChoices[z.climate] = 'inherit';
      }
    }

    let currentGeneralPreset = initialGeneralPreset;

    const parseTimeInput = (val) => {
      if (!val) return 0;
      if (val === '23:59' || val === '24:00') return 1440;
      const p = val.split(':').map(Number);
      return (p[0] || 0) * 60 + (p[1] || 0);
    };

    const formatTimeInput = (min) => {
      if (min >= 1440) return '23:59';
      const h = String(Math.floor(min / 60)).padStart(2, '0');
      const m = String(min % 60).padStart(2, '0');
      return `${h}:${m}`;
    };

    const formatDurationText = (min) => {
      if (min <= 0) return '0m';
      const h = Math.floor(min / 60);
      const m = min % 60;
      if (h === 0) return `${m}m`;
      if (m === 0) return `${h}h`;
      return `${h}h ${String(m).padStart(2, '0')}m`;
    };

    let startMin = parseTimeInput(curStart);
    let endMin = parseTimeInput(curEnd);
    if (endMin <= startMin) endMin = Math.min(1440, startMin + 120);
    let durationMin = endMin - startMin;

    modalContainer.innerHTML = `
      <div class="modal-overlay" id="slot-modal-backdrop">
        <div class="modal-box slot-modal-wide">
          <div class="modal-title">
            <div style="display:flex; align-items:center; gap:8px;">
              <span>${isEdit ? '✏️ Modifica Fascia Oraria' : '➕ Nuova Fascia Oraria'}</span>
            </div>
            <button class="modal-close-btn" id="modal-close-x">✕</button>
          </div>

          <!-- 1. Orario di Partenza + Durata e Fine sincronizzati -->
          <div class="form-section">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <label class="form-label">⏰ Orario e Durata:</label>
              <div id="slot-duration-badge" class="duration-badge">⏱️ Durata: <strong>${formatDurationText(durationMin)}</strong></div>
            </div>
            <div style="display:flex; gap:12px; align-items:flex-end;">
              <div class="form-group" style="flex:1; margin-bottom:0;">
                <span class="sub-label">Orario Inizio</span>
                <input type="time" id="slot-start-time" class="time-input" step="900" value="${curStart}">
              </div>
              <div class="form-group" style="flex:1; margin-bottom:0;">
                <span class="sub-label">Orario Fine</span>
                <input type="time" id="slot-end-time" class="time-input" step="900" value="${curEnd}">
              </div>
            </div>
            <div class="quick-duration-bar">
              <span class="sub-label" style="align-self:center; margin-bottom:0; margin-right:4px;">Durata rapida:</span>
              <button type="button" class="duration-pill ${durationMin === 30 ? 'active' : ''}" data-minutes="30">30m</button>
              <button type="button" class="duration-pill ${durationMin === 60 ? 'active' : ''}" data-minutes="60">1h</button>
              <button type="button" class="duration-pill ${durationMin === 90 ? 'active' : ''}" data-minutes="90">1.5h</button>
              <button type="button" class="duration-pill ${durationMin === 120 ? 'active' : ''}" data-minutes="120">2h</button>
              <button type="button" class="duration-pill ${durationMin === 180 ? 'active' : ''}" data-minutes="180">3h</button>
              <button type="button" class="duration-pill ${durationMin === 240 ? 'active' : ''}" data-minutes="240">4h</button>
              <button type="button" class="duration-pill ${durationMin === 360 ? 'active' : ''}" data-minutes="360">6h</button>
            </div>
          </div>

          <!-- 2. Giorni della Settimana -->
          <div class="form-section">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <label class="form-label">📅 Giorni di Applicazione:</label>
              <div style="display:flex; gap:6px;">
                <button type="button" class="btn btn-xs" id="btn-quick-weekdays">Lun-Ven</button>
                <button type="button" class="btn btn-xs" id="btn-quick-weekend">Sab-Dom</button>
                <button type="button" class="btn btn-xs" id="btn-quick-all">Tutti</button>
              </div>
            </div>
            <div class="checkbox-group" id="slot-days-group">
              ${days.map(d => `
                <label class="checkbox-label ${selDays.includes(d.id) ? 'checked' : ''}">
                  <input type="checkbox" value="${d.id}" ${selDays.includes(d.id) ? 'checked' : ''}>
                  ${d.label}
                </label>
              `).join('')}
            </div>
          </div>

          <!-- 3. Preset Generale della Fascia -->
          <div class="form-section">
            <label class="form-label">🎯 Preset Generale della Fascia:</label>
            <div class="sub-label" style="margin-bottom:8px;">Preset principale applicato a tutte le stanze per questa fascia:</div>
            <div class="general-preset-grid">
              <button type="button" class="general-preset-card preset-card-comfort ${initialGeneralPreset === 'comfort' ? 'active' : ''}" data-preset="comfort">
                <div class="preset-card-icon">🔥</div>
                <div class="preset-card-name">Comfort</div>
              </button>
              <button type="button" class="general-preset-card preset-card-eco ${initialGeneralPreset === 'eco' ? 'active' : ''}" data-preset="eco">
                <div class="preset-card-icon">🌿</div>
                <div class="preset-card-name">Eco</div>
              </button>
              <button type="button" class="general-preset-card preset-card-sleep ${initialGeneralPreset === 'sleep' ? 'active' : ''}" data-preset="sleep">
                <div class="preset-card-icon">🌙</div>
                <div class="preset-card-name">Notte</div>
              </button>
              <button type="button" class="general-preset-card preset-card-away ${initialGeneralPreset === 'away' ? 'active' : ''}" data-preset="away">
                <div class="preset-card-icon">🚶</div>
                <div class="preset-card-name">Away</div>
              </button>
            </div>
          </div>

          <!-- 4. Eccezioni per Singole Zone -->
          <div class="form-section">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <label class="form-label">🏠 Eccezioni per Singole Zone (Opzionale):</label>
            </div>
            <div class="sub-label" style="margin-bottom:8px;">Personalizza o escludi specifiche stanze mantenendo il resto dell'impianto sul Preset Generale:</div>
            <div class="zone-exceptions-container">
              ${zones.map(z => {
                const cTemp = this._resolvePresetTemp(z.climate, 'comfort');
                const eTemp = this._resolvePresetTemp(z.climate, 'eco');
                const sTemp = this._resolvePresetTemp(z.climate, 'sleep');
                const aTemp = this._resolvePresetTemp(z.climate, 'away');
                const baseTemp = this._resolvePresetTemp(z.climate, currentBaseline);
                const initialVal = initialZoneChoices[z.climate] || 'inherit';

                return `
                  <div class="zone-exception-row" data-zone="${z.climate}">
                    <div class="zone-exception-name" title="${z.name}">🏠 ${z.name}</div>
                    <div class="zone-exception-control">
                      <select class="zone-override-select" data-zone="${z.climate}">
                        <option value="inherit" ${initialVal === 'inherit' ? 'selected' : ''}>🔗 Segui Preset Generale</option>
                        <option value="comfort" ${initialVal === 'comfort' ? 'selected' : ''}>🔥 Comfort (${cTemp.toFixed(1)}°C)</option>
                        <option value="eco" ${initialVal === 'eco' ? 'selected' : ''}>🌿 Eco (${eTemp.toFixed(1)}°C)</option>
                        <option value="sleep" ${initialVal === 'sleep' ? 'selected' : ''}>🌙 Notte (${sTemp.toFixed(1)}°C)</option>
                        <option value="away" ${initialVal === 'away' ? 'selected' : ''}>🚶 Away (${aTemp.toFixed(1)}°C)</option>
                        <option value="none" ${initialVal === 'none' ? 'selected' : ''}>⏸️ Nessuna modifica / Baseline (${baseTemp.toFixed(1)}°C)</option>
                      </select>
                    </div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>

          <!-- Azioni Modale -->
          <div class="modal-actions">
            ${isEdit ? `
              <button type="button" class="btn btn-danger" id="btn-delete-slot">
                🗑️ Elimina Fascia
              </button>
            ` : ''}
            <button type="button" class="btn" id="btn-cancel-modal">
              Annulla
            </button>
            <button type="button" class="btn btn-primary" id="btn-save-slot">
              💾 Salva Fascia
            </button>
          </div>
        </div>
      </div>
    `;

    // Dynamic inherit labels updater
    const updateZoneSelectLabels = (genPreset) => {
      const pInfo = {
        comfort: { label: 'Comfort', icon: '🔥' },
        eco: { label: 'Eco', icon: '🌿' },
        sleep: { label: 'Notte', icon: '🌙' },
        away: { label: 'Away', icon: '🚶' }
      }[genPreset] || { label: 'Comfort', icon: '🔥' };

      modalContainer.querySelectorAll('.zone-override-select').forEach(sel => {
        const zid = sel.getAttribute('data-zone');
        const temp = this._resolvePresetTemp(zid, genPreset);
        const inheritOpt = sel.querySelector('option[value="inherit"]');
        if (inheritOpt) {
          inheritOpt.textContent = `🔗 Segui Preset Generale (${pInfo.icon} ${pInfo.label} · ${temp.toFixed(1)}°C)`;
        }
      });
    };

    updateZoneSelectLabels(currentGeneralPreset);

    // Event listeners
    modalContainer.querySelector('#modal-close-x')?.addEventListener('click', () => this.closeModal());
    modalContainer.querySelector('#btn-cancel-modal')?.addEventListener('click', () => this.closeModal());

    const startInput = modalContainer.querySelector('#slot-start-time');
    const endInput = modalContainer.querySelector('#slot-end-time');
    const badge = modalContainer.querySelector('#slot-duration-badge');

    const updatePillActives = (curDur) => {
      modalContainer.querySelectorAll('.duration-pill').forEach(pill => {
        const m = parseInt(pill.getAttribute('data-minutes'), 10);
        if (m === curDur) pill.classList.add('active');
        else pill.classList.remove('active');
      });
    };

    startInput?.addEventListener('change', () => {
      startMin = parseTimeInput(startInput.value);
      endMin = Math.min(1440, startMin + durationMin);
      endInput.value = formatTimeInput(endMin);
      badge.innerHTML = `⏱️ Durata: <strong>${formatDurationText(durationMin)}</strong>`;
      updatePillActives(durationMin);
    });

    endInput?.addEventListener('change', () => {
      endMin = parseTimeInput(endInput.value);
      if (endMin <= startMin) {
        startMin = Math.max(0, endMin - 15);
        startInput.value = formatTimeInput(startMin);
      }
      durationMin = endMin - startMin;
      badge.innerHTML = `⏱️ Durata: <strong>${formatDurationText(durationMin)}</strong>`;
      updatePillActives(durationMin);
    });

    modalContainer.querySelectorAll('.duration-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        durationMin = parseInt(pill.getAttribute('data-minutes'), 10);
        endMin = Math.min(1440, startMin + durationMin);
        endInput.value = formatTimeInput(endMin);
        badge.innerHTML = `⏱️ Durata: <strong>${formatDurationText(durationMin)}</strong>`;
        updatePillActives(durationMin);
      });
    });

    modalContainer.querySelectorAll('.general-preset-card').forEach(card => {
      card.addEventListener('click', () => {
        currentGeneralPreset = card.getAttribute('data-preset');
        modalContainer.querySelectorAll('.general-preset-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        updateZoneSelectLabels(currentGeneralPreset);
      });
    });

    modalContainer.querySelector('#btn-quick-weekdays')?.addEventListener('click', () => {
      modalContainer.querySelectorAll('#slot-days-group input').forEach(cb => {
        cb.checked = ['mon', 'tue', 'wed', 'thu', 'fri'].includes(cb.value);
      });
    });

    modalContainer.querySelector('#btn-quick-weekend')?.addEventListener('click', () => {
      modalContainer.querySelectorAll('#slot-days-group input').forEach(cb => {
        cb.checked = ['sat', 'sun'].includes(cb.value);
      });
    });

    modalContainer.querySelector('#btn-quick-all')?.addEventListener('click', () => {
      modalContainer.querySelectorAll('#slot-days-group input').forEach(cb => {
        cb.checked = true;
      });
    });

    modalContainer.querySelector('#btn-delete-slot')?.addEventListener('click', () => {
      const schedObj = JSON.parse(JSON.stringify(this._getScheduleStatus()));
      const profObj = schedObj.profiles?.[this._editorProfileId];
      if (profObj) {
        const checkedDays = Array.from(modalContainer.querySelectorAll('#slot-days-group input:checked')).map(cb => cb.value);
        const daysToProcess = checkedDays.length > 0 ? checkedDays : [data.day || this._selectedDay];
        for (const d of daysToProcess) {
          for (const z of zones) {
            this._applySlotToZone(profObj, d, z.climate, curStart, (curEnd === '23:59' ? '24:00' : curEnd), 'none');
          }
        }
        this._localScheduleCache = schedObj;
        this._saveProfileToServer(this._editorProfileId, profObj);
        this.renderMatrixRows();
      }
      this.closeModal();
    });

    modalContainer.querySelector('#btn-save-slot')?.addEventListener('click', () => {
      const sVal = modalContainer.querySelector('#slot-start-time').value;
      const eVal = modalContainer.querySelector('#slot-end-time').value;
      const sMin = parseTimeInput(sVal);
      const eMin = parseTimeInput(eVal);

      if (sMin >= eMin) {
        alert("L'orario di inizio deve precedere quello di fine!");
        return;
      }

      const checkedDays = Array.from(modalContainer.querySelectorAll('#slot-days-group input:checked')).map(cb => cb.value);
      if (checkedDays.length === 0) {
        alert("Seleziona almeno un giorno della settimana!");
        return;
      }

      const schedObj = JSON.parse(JSON.stringify(this._getScheduleStatus()));
      if (!schedObj.profiles[this._editorProfileId]) {
        schedObj.profiles[this._editorProfileId] = {
          name: this._editorProfileId.toUpperCase(),
          baseline_preset: 'eco',
          days: {}
        };
      }
      const profObj = schedObj.profiles[this._editorProfileId];

      const effectiveEndStr = eMin >= 1440 ? '24:00' : eVal;

      for (const d of checkedDays) {
        for (const z of zones) {
          const sel = modalContainer.querySelector(`.zone-override-select[data-zone="${z.climate}"]`);
          const choice = sel ? sel.value : 'inherit';
          const zonePreset = choice === 'inherit' ? currentGeneralPreset : choice;
          this._applySlotToZone(profObj, d, z.climate, sVal, effectiveEndStr, zonePreset);
        }
      }

      this._localScheduleCache = schedObj;
      this._saveProfileToServer(this._editorProfileId, profObj);
      this.renderMatrixRows();
      this.closeModal();
    });
  }  openActivateModal() {
    this._activeModal = 'activate';
    const modalContainer = this.shadowRoot.querySelector('#modal-container');
    if (!modalContainer) return;

    const sched = this._getScheduleStatus();
    const profilesList = Object.keys(sched.profiles || { standard: {} });
    const currentActive = sched.active_profile || 'standard';

    modalContainer.innerHTML = `
      <div class="modal-overlay">
        <div class="modal-box">
          <div class="modal-title">
            <span>📅 ${this._t('sched_activate_btn')}</span>
            <button class="modal-close-btn" id="modal-close-x">✕</button>
          </div>

          <div class="form-group">
            <label class="form-label">Seleziona Profilo da Attivare:</label>
            <select id="activate-profile-select">
              ${profilesList.map(pId => {
                const p = sched.profiles?.[pId];
                return `<option value="${pId}" ${currentActive === pId ? 'selected' : ''}>${p?.name || pId.toUpperCase()}</option>`;
              }).join('')}
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Durata Attivazione / Scadenza:</label>
            <div style="display:flex; flex-direction:column; gap:8px;">
              <label class="checkbox-label">
                <input type="radio" name="expiry-type" value="permanent" checked>
                Permanente (Nessuna scadenza)
              </label>
              <label class="checkbox-label">
                <input type="radio" name="expiry-type" value="temporary">
                Temporanea con scadenza
              </label>
            </div>
          </div>

          <div id="temporary-expiry-box" style="display:none; flex-direction:column; gap:10px; margin-top:8px;">
            <div style="display:flex; flex-wrap:wrap; gap:6px;">
              <button class="btn" id="btn-exp-24h" style="padding:4px 8px; font-size:0.8rem;">+24 ore</button>
              <button class="btn" id="btn-exp-today" style="padding:4px 8px; font-size:0.8rem;">Fine Oggi 23:59</button>
              <button class="btn" id="btn-exp-sunday" style="padding:4px 8px; font-size:0.8rem;">Fine Domenica 23:59</button>
              <button class="btn" id="btn-exp-3d" style="padding:4px 8px; font-size:0.8rem;">+3 giorni</button>
            </div>
            <input type="datetime-local" id="activate-expires-at">
            <div class="form-group" style="margin-top:6px;">
              <label class="form-label">Profilo di Ripristino (Fallback):</label>
              <select id="activate-fallback-select">
                ${profilesList.map(pId => {
                  return `<option value="${pId}" ${pId === 'standard' ? 'selected' : ''}>${pId.toUpperCase()}</option>`;
                }).join('')}
              </select>
            </div>
          </div>

          <div class="modal-actions">
            <button class="btn" id="btn-cancel-modal">Annulla</button>
            <button class="btn btn-primary" id="btn-confirm-activate">Attiva Profilo</button>
          </div>
        </div>
      </div>
    `;

    modalContainer.querySelector('#modal-close-x')?.addEventListener('click', () => this.closeModal());
    modalContainer.querySelector('#btn-cancel-modal')?.addEventListener('click', () => this.closeModal());

    const expBox = modalContainer.querySelector('#temporary-expiry-box');
    modalContainer.querySelectorAll('input[name="expiry-type"]').forEach(r => {
      r.addEventListener('change', () => {
        expBox.style.display = r.value === 'temporary' ? 'flex' : 'none';
      });
    });

    const dtInput = modalContainer.querySelector('#activate-expires-at');
    const setDt = (d) => {
      const pad = (n) => String(n).padStart(2, '0');
      const s = d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + 'T' + pad(d.getHours()) + ':' + pad(d.getMinutes());
      dtInput.value = s;
    };

    modalContainer.querySelector('#btn-exp-24h')?.addEventListener('click', () => {
      setDt(new Date(Date.now() + 24 * 3600 * 1000));
    });
    modalContainer.querySelector('#btn-exp-today')?.addEventListener('click', () => {
      const d = new Date();
      d.setHours(23, 59, 0, 0);
      setDt(d);
    });
    modalContainer.querySelector('#btn-exp-sunday')?.addEventListener('click', () => {
      const d = new Date();
      const day = d.getDay();
      const diff = (7 - day) % 7;
      d.setDate(d.getDate() + (diff === 0 ? 7 : diff));
      d.setHours(23, 59, 0, 0);
      setDt(d);
    });
    modalContainer.querySelector('#btn-exp-3d')?.addEventListener('click', () => {
      setDt(new Date(Date.now() + 72 * 3600 * 1000));
    });

    modalContainer.querySelector('#btn-confirm-activate')?.addEventListener('click', () => {
      const profId = modalContainer.querySelector('#activate-profile-select').value;
      const isTemp = modalContainer.querySelector('input[name="expiry-type"]:checked').value === 'temporary';
      let expIso = '';
      let fbProf = 'standard';
      if (isTemp) {
        expIso = dtInput.value ? new Date(dtInput.value).toISOString() : '';
        fbProf = modalContainer.querySelector('#activate-fallback-select').value || 'standard';
      }

      if (this._hass) {
        this._hass.callService('multizone_thermostat', 'activate_schedule_profile', {
          profile_id: profId,
          expires_at: expIso,
          fallback_profile: fbProf
        });
      }
      this.closeModal();
    });
  }

  openSmartReturnModal() {
    this._activeModal = 'smart_return';
    const modalContainer = this.shadowRoot.querySelector('#modal-container');
    if (!modalContainer) return;

    const zones = this._getZones();
    const now = new Date();
    const defArr = new Date(now.getTime() + 2 * 3600 * 1000);
    const defArrStr = String(defArr.getHours()).padStart(2, '0') + ':' + String(defArr.getMinutes()).padStart(2, '0');

    modalContainer.innerHTML = `
      <div class="modal-overlay">
        <div class="modal-box" style="max-width: 580px;">
          <div class="modal-title">
            <span>🚗 ${this._t('sched_smart_return_btn')}</span>
            <button class="modal-close-btn" id="modal-close-x">✕</button>
          </div>

          <div style="display:flex; gap:12px;">
            <div class="form-group" style="flex:1;">
              <label class="form-label">Orario di Rientro Previsto:</label>
              <input type="time" id="sr-arrival-time" value="${defArrStr}">
            </div>
            <div class="form-group" style="flex:1;">
              <label class="form-label">Preset Obiettivo:</label>
              <select id="sr-preset-select">
                <option value="comfort" selected>🔥 Comfort</option>
                <option value="eco">🌿 Eco</option>
              </select>
            </div>
          </div>

          <div style="display:flex; gap:6px; margin-bottom:12px;">
            <button class="btn" id="btn-sr-add-1h" style="padding:4px 8px; font-size:0.8rem;">+1 ora</button>
            <button class="btn" id="btn-sr-add-2h" style="padding:4px 8px; font-size:0.8rem;">+2 ore</button>
            <button class="btn" id="btn-sr-add-3h" style="padding:4px 8px; font-size:0.8rem;">+3 ore</button>
          </div>

          <div class="form-group">
            <label class="form-label">Radar Termico & Accensione Scaglionata (Anteprima Live):</label>
            <div class="radar-list" id="sr-radar-preview"></div>
          </div>

          <div class="modal-actions">
            <button class="btn" id="btn-cancel-modal">Annulla</button>
            <button class="btn btn-amber" id="btn-confirm-sr">🔥 Pianifica Rientro</button>
          </div>
        </div>
      </div>
    `;

    modalContainer.querySelector('#modal-close-x')?.addEventListener('click', () => this.closeModal());
    modalContainer.querySelector('#btn-cancel-modal')?.addEventListener('click', () => this.closeModal());

    const timeInput = modalContainer.querySelector('#sr-arrival-time');
    const presetSelect = modalContainer.querySelector('#sr-preset-select');
    const previewList = modalContainer.querySelector('#sr-radar-preview');

    const updateRadar = () => {
      const arrVal = timeInput.value;
      const chosenPreset = presetSelect.value;
      if (!arrVal) return;

      const [ah, am] = arrVal.split(':').map(Number);
      const arrDate = new Date();
      arrDate.setHours(ah, am, 0, 0);
      if (arrDate.getTime() < Date.now()) {
        arrDate.setDate(arrDate.getDate() + 1);
      }

      const plan = zones.map(z => {
        const targetTemp = this._resolvePresetTemp(z.climate, chosenPreset);
        const curTemp = z.current_temp;
        const delta = Math.max(0, targetTemp - curTemp);
        const rate = z.heating_rate > 0.05 ? z.heating_rate : 1.0;
        const reqMin = Math.ceil((delta / rate) * 60);
        const ignDate = new Date(arrDate.getTime() - reqMin * 60000);
        const ignStr = String(ignDate.getHours()).padStart(2, '0') + ':' + String(ignDate.getMinutes()).padStart(2, '0');
        return {
          zone: z,
          targetTemp,
          curTemp,
          delta,
          rate,
          reqMin,
          ignDate,
          ignStr
        };
      });

      plan.sort((a, b) => b.reqMin - a.reqMin);

      previewList.innerHTML = plan.map(item => {
        const isReady = item.reqMin <= 0;
        return `
          <div class="radar-item">
            <div class="radar-item-left">
              <strong>${item.zone.name}</strong>
              <span style="font-size:0.8rem; opacity:0.8;">
                Attuale: ${item.curTemp.toFixed(1)}°C ➔ Target: ${item.targetTemp.toFixed(1)}°C (Δ ${item.delta.toFixed(1)}°C, ${item.rate.toFixed(1)}°C/h)
              </span>
            </div>
            <div class="radar-item-right">
              ${isReady ? `
                <span class="badge badge-green" style="font-size:0.75rem;">✅ In temperatura</span>
              ` : `
                <span class="badge badge-orange" style="font-size:0.75rem;">⏱️ ${item.reqMin} min</span>
                <span style="font-size:0.75rem; font-weight:700; color:#fcd34d;">Accensione: ${item.ignStr}</span>
              `}
            </div>
          </div>
        `;
      }).join('');
    };

    timeInput.addEventListener('input', updateRadar);
    presetSelect.addEventListener('change', updateRadar);

    modalContainer.querySelector('#btn-sr-add-1h')?.addEventListener('click', () => {
      const d = new Date(Date.now() + 1 * 3600 * 1000);
      timeInput.value = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
      updateRadar();
    });
    modalContainer.querySelector('#btn-sr-add-2h')?.addEventListener('click', () => {
      const d = new Date(Date.now() + 2 * 3600 * 1000);
      timeInput.value = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
      updateRadar();
    });
    modalContainer.querySelector('#btn-sr-add-3h')?.addEventListener('click', () => {
      const d = new Date(Date.now() + 3 * 3600 * 1000);
      timeInput.value = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
      updateRadar();
    });

    updateRadar();

    modalContainer.querySelector('#btn-confirm-sr')?.addEventListener('click', () => {
      const arrival = timeInput.value;
      const preset = presetSelect.value;
      if (this._hass && arrival) {
        this._hass.callService('multizone_thermostat', 'set_smart_return', {
          arrival_time: arrival,
          preset: preset
        });
      }
      this.closeModal();
    });
  }

  openDuplicateModal() {
    this._activeModal = 'duplicate';
    const modalContainer = this.shadowRoot.querySelector('#modal-container');
    if (!modalContainer) return;

    modalContainer.innerHTML = `
      <div class="modal-overlay">
        <div class="modal-box">
          <div class="modal-title">
            <span>📋 ${this._t('sched_duplicate')}</span>
            <button class="modal-close-btn" id="modal-close-x">✕</button>
          </div>

          <div class="form-group">
            <label class="form-label">Profilo Sorgente:</label>
            <input type="text" value="${this._editorProfileId}" disabled style="opacity:0.7;">
          </div>

          <div class="form-group">
            <label class="form-label">Nuovo ID Profilo (es. standard_spring):</label>
            <input type="text" id="dup-target-id" placeholder="es. standard_spring">
          </div>

          <div class="form-group">
            <label class="form-label">Nome Visualizzato (es. Standard Primavera):</label>
            <input type="text" id="dup-target-name" placeholder="es. Standard Primavera">
          </div>

          <div class="modal-actions">
            <button class="btn" id="btn-cancel-modal">Annulla</button>
            <button class="btn btn-primary" id="btn-confirm-dup">Duplica</button>
          </div>
        </div>
      </div>
    `;

    modalContainer.querySelector('#modal-close-x')?.addEventListener('click', () => this.closeModal());
    modalContainer.querySelector('#btn-cancel-modal')?.addEventListener('click', () => this.closeModal());

    modalContainer.querySelector('#btn-confirm-dup')?.addEventListener('click', () => {
      const targetId = modalContainer.querySelector('#dup-target-id').value.trim();
      const targetName = modalContainer.querySelector('#dup-target-name').value.trim() || targetId;

      if (!targetId) {
        alert("Inserisci un ID per il nuovo profilo!");
        return;
      }

      if (this._hass) {
        this._hass.callService('multizone_thermostat', 'duplicate_schedule_profile', {
          source_profile_id: this._editorProfileId,
          target_profile_id: targetId,
          target_name: targetName
        });
      }

      this._editorProfileId = targetId;
      this.closeModal();
      this.renderEditor();
    });
  }
}

if (!customElements.get("multizone-thermostat-scheduler-card")) {
  customElements.define("multizone-thermostat-scheduler-card", MultizoneThermostatSchedulerCard);
}

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
          panel: true,
          cards: schedView.cards,
        },
        {
          title: "Diagnostica & Efficienza",
          path: "diagnostica",
          icon: "mdi:chart-box-outline",
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
    const strategyConfig = info.config?.strategy || info.strategy || info.config || {};
    
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

    const stackCards = [
      {
        type: "custom:multizone-thermostat-plant-card",
        border_radius: "20px",
      }
    ];

    for (let i = 0; i < zones.length; i += columns) {
      const chunk = zones.slice(i, i + columns);
      const rowCards = chunk.map(zone => ({
        type: "custom:multizone-thermostat-zone-energy-card",
        entity: zone.climate,
        title: zone.title,
        border_radius: "20px",
      }));
      
      while (rowCards.length < columns && columns <= 3) {
        rowCards.push({
          type: "custom:multizone-thermostat-spacer"
        });
      }

      stackCards.push({
        type: "horizontal-stack",
        cards: rowCards
      });
    }

    return {
      cards: [
        {
          type: "vertical-stack",
          cards: stackCards
        }
      ]
    };
  }

  static async generateView(info) {
    const hass = info.hass;
    if (!hass || !hass.states) return { cards: [] };
    // In view strategies, config is usually in info.config.strategy or info.strategy
    const strategyConfig = info.config?.strategy || info.strategy || info.config || {};
    
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

    // Schedule summary card: posizionato esattamente tra Master Control e Diagnostica!
    topRowCards.push({
      type: "custom:multizone-thermostat-schedule-summary-card",
      border_radius: "20px",
    });

    // Health summary card: Diagnostica
    topRowCards.push({
      type: "custom:multizone-thermostat-health-summary-card",
      border_radius: "20px",
    });

    // Fill the rest of the top row with spacers so it's aligned with columns if needed
    while (topRowCards.length < columns && columns <= 4) {
      topRowCards.push({
        type: "custom:multizone-thermostat-spacer"
      });
    }

    const stackCards = [
      {
        type: "horizontal-stack",
        cards: topRowCards
      }
    ];

    for (let i = 0; i < zones.length; i += columns) {
      const chunk = zones.slice(i, i + columns);
      const rowCards = chunk.map(zone => ({
        type: "custom:multizone-thermostat-dial-card",
        entity: zone.climate,
        switch: zone.switch,
        title: zone.title,
        min_height: "300px",
        max_height: "400px",
        padding: "1px",
        border_radius: "20px",
      }));
      
      stackCards.push({
        type: "horizontal-stack",
        cards: rowCards
      });
    }

    return {
      cards: [
        {
          type: "vertical-stack",
          cards: stackCards
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

