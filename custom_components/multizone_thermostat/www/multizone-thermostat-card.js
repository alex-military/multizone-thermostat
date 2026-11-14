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

const TRANSLATIONS = {
  it: {
    heat_source_gas: "Gas",
    heat_priority: "Priorità Calore",
    heat_source_electric: "Elettrico",
    heat_source_dual: "Gas + Elettrico",
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
    master_mode_heat: "Caldo",
    master_mode_cool: "Freddo",
    cooling_active: "In Raffrescamento",
    hide_non_cooling: "Nascondi se non climatizzata (Estate)",
    minimize_non_cooling: "Minimizza se non climatizzata (Estate)",
    winter_only: "Solo Inverno",
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
    prof_holiday: "Festivo",
    pid_section_title: "PID & Autotuner",
    pid_auto_badge: "Auto EMA",
    pid_manual_badge: "Manuale",
    pid_reset_btn: "Reset Autotuner",
    pid_click_to_edit: "Clicca per sbloccare e modificare",
    pid_modal_title: "Avviso di Sicurezza PID",
    pid_modal_warn: "I guadagni Kp, Ki e Kd sono gestiti dall'autotuner adattivo settimanale. Sbloccare questo parametro sospende la calibrazione automatica su quel coefficiente e può causare oscillazioni se errato.",
    pid_modal_value: "Nuovo valore",
    pid_modal_save: "Sblocca e Salva",
    pid_modal_restore: "Ripristina Automatico",
    pid_modal_cancel: "Annulla",
    pid_reset_title: "Conferma Reset Autotuner",
    pid_reset_confirm_msg: "Azzerare i cicli appresi e riavviare la calibrazione iniziale (3 cicli) per questa zona?",
    pid_reset_confirm_btn: "Resetta Autotuner",
    pid_learning_status: "Apprendimento",
    sched_all_zones_row: "Tutte le Zone (Generale)",
    sched_base_tag: "Base"
  },
  en: {
    heat_source_gas: "Gas",
    heat_source_electric: "Electric",
    heat_source_dual: "Gas + Electric",
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
    master_mode_heat: "Heat",
    master_mode_cool: "Cool",
    cooling_active: "Cooling",
    hide_non_cooling: "Hide non-cooled room in summer",
    minimize_non_cooling: "Minimize non-cooled room in summer",
    winter_only: "Winter only",
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
    prof_holiday: "Holiday",
    pid_section_title: "PID & Autotuner",
    pid_auto_badge: "Auto EMA",
    pid_manual_badge: "Manual",
    pid_reset_btn: "Reset Autotuner",
    pid_click_to_edit: "Click to unlock and edit",
    pid_modal_title: "PID Safety Warning",
    pid_modal_warn: "Kp, Ki, and Kd gains are continuously tuned by the weekly adaptive autotuner. Unlocking a parameter pauses automatic tuning on it and may cause temperature oscillations if misconfigured.",
    pid_modal_value: "New value",
    pid_modal_save: "Unlock & Save",
    pid_modal_restore: "Restore Automatic",
    pid_modal_cancel: "Cancel",
    pid_reset_title: "Confirm Autotuner Reset",
    pid_reset_confirm_msg: "Clear learned cycles and restart the 3-cycle initial calibration for this zone?",
    pid_reset_confirm_btn: "Reset Autotuner",
    pid_learning_status: "Learning",
    sched_all_zones_row: "All Zones (General)",
    sched_base_tag: "Base"
  },
  ru: {
    heat_source_gas: "Газ",
    heat_source_electric: "Электро",
    heat_source_dual: "Газ + Электро",
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
    master_mode_heat: "Отопление",
    master_mode_cool: "Охлаждение",
    cooling_active: "Охлаждение",
    hide_non_cooling: "Скрыть неохлаждаемые комнаты летом",
    minimize_non_cooling: "Свернуть неохлаждаемые комнаты летом",
    winter_only: "Только зимой",
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
    prof_holiday: "Выходной",
    pid_section_title: "PID и Автонастройка",
    pid_auto_badge: "Авто EMA",
    pid_manual_badge: "Вручную",
    pid_reset_btn: "Сброс автонастройки",
    pid_click_to_edit: "Нажмите для разблокировки",
    pid_modal_title: "Предупреждение безопасности PID",
    pid_modal_warn: "Параметры Kp, Ki и Kd автоматически калибруются каждую неделю. Ручное изменение отключает автонастройку для параметра и может вызвать колебания температуры.",
    pid_modal_value: "Новое значение",
    pid_modal_save: "Разблокировать и сохранить",
    pid_modal_restore: "Вернуть авто",
    pid_modal_cancel: "Отмена",
    pid_reset_title: "Сброс автонастройки зоны",
    pid_reset_confirm_msg: "Сбросить обученные циклы и перезапустить начальную калибровку (3 цикла)?",
    pid_reset_confirm_btn: "Сбросить",
    pid_learning_status: "Обучение",
    sched_all_zones_row: "Все зоны (Общее)",
    sched_base_tag: "База"
  },
  fr: {
    heat_source_gas: "Gaz",
    heat_source_electric: "Électrique",
    heat_source_dual: "Gaz + Électrique",
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
    master_mode_heat: "Chaud",
    master_mode_cool: "Froid",
    cooling_active: "Refroidissement",
    hide_non_cooling: "Masquer les pièces non climatisées en été",
    minimize_non_cooling: "Réduire les pièces non climatisées en été",
    winter_only: "Hiver uniquement",
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
    prof_holiday: "Vacances",
    pid_section_title: "PID & Autotuner",
    pid_auto_badge: "Auto EMA",
    pid_manual_badge: "Manuel",
    pid_reset_btn: "Reset Autotuner",
    pid_click_to_edit: "Cliquer pour déverrouiller",
    pid_modal_title: "Avertissement de sécurité PID",
    pid_modal_warn: "Les gains Kp, Ki et Kd sont ajustés par l'autotuner adaptatif hebdomadaire. Le déverrouillage manuel suspend la calibration automatique sur ce paramètre.",
    pid_modal_value: "Nouvelle valeur",
    pid_modal_save: "Déverrouiller et enregistrer",
    pid_modal_restore: "Rétablir Auto",
    pid_modal_cancel: "Annuler",
    pid_reset_title: "Réinitialiser l'Autotuner",
    pid_reset_confirm_msg: "Effacer les cycles appris et relancer la calibration initiale (3 cycles) ?",
    pid_reset_confirm_btn: "Réinitialiser",
    pid_learning_status: "Apprentissage",
    sched_all_zones_row: "Toutes les Zones (Général)",
    sched_base_tag: "Base"
  },
  de: {
    heat_source_gas: "Gas",
    heat_source_electric: "Elektrisch",
    heat_source_dual: "Gas + Elektrisch",
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
    master_mode_heat: "Heizen",
    master_mode_cool: "Kühlen",
    cooling_active: "Kühlen aktiv",
    hide_non_cooling: "Nicht gekühlte Räume im Sommer ausblenden",
    minimize_non_cooling: "Nicht gekühlte Räume im Sommer minimieren",
    winter_only: "Nur Winter",
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
    prof_holiday: "Feiertag",
    pid_section_title: "PID & Autotuner",
    pid_auto_badge: "Auto EMA",
    pid_manual_badge: "Manuell",
    pid_reset_btn: "Autotuner Zurücksetzen",
    pid_click_to_edit: "Zum Entsperren klicken",
    pid_modal_title: "PID-Sicherheitswarnung",
    pid_modal_warn: "Kp, Ki und Kd werden wöchentlich automatisch angepasst. Manuelles Entsperren pausiert das Auto-Tuning für diesen Wert.",
    pid_modal_value: "Neuer Wert",
    pid_modal_save: "Entsperren & Speichern",
    pid_modal_restore: "Automatik wiederherstellen",
    pid_modal_cancel: "Abbrechen",
    pid_reset_title: "Autotuner Zurücksetzen",
    pid_reset_confirm_msg: "Gelernte Zyklen löschen und 3-Zyklus-Kalibrierung neu starten?",
    pid_reset_confirm_btn: "Zurücksetzen",
    pid_learning_status: "Lernen",
    sched_all_zones_row: "Alle Zonen (Allgemein)",
    sched_base_tag: "Basis"
  },
  es: {
    heat_source_gas: "Gas",
    heat_source_electric: "Eléctrico",
    heat_source_dual: "Gas + Eléctrico",
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
    master_mode_heat: "Calor",
    master_mode_cool: "Frío",
    cooling_active: "Refrigerando",
    hide_non_cooling: "Ocultar habitaciones no climatizadas en verano",
    minimize_non_cooling: "Minimizar habitaciones no climatizadas en verano",
    winter_only: "Solo invierno",
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
    prof_holiday: "Festivo",
    pid_section_title: "PID y Autotuner",
    pid_auto_badge: "Auto EMA",
    pid_manual_badge: "Manual",
    pid_reset_btn: "Reiniciar Autotuner",
    pid_click_to_edit: "Clic para desbloquear",
    pid_modal_title: "Aviso de Seguridad PID",
    pid_modal_warn: "Los valores Kp, Ki y Kd se calibran automáticamente cada semana. Desbloquearlos pausa el ajuste automático y puede causar oscilaciones.",
    pid_modal_value: "Nuevo valor",
    pid_modal_save: "Desbloquear y Guardar",
    pid_modal_restore: "Restaurar Automático",
    pid_modal_cancel: "Cancelar",
    pid_reset_title: "Confirmar Reinicio Autotuner",
    pid_reset_confirm_msg: "¿Borrar los ciclos aprendidos y reiniciar la calibración inicial de 3 ciclos?",
    pid_reset_confirm_btn: "Reiniciar",
    pid_learning_status: "Aprendiendo",
    sched_all_zones_row: "Todas las Zonas (General)",
    sched_base_tag: "Base"
  }
};

function getTranslation(hass, key) {
  const lang = hass && hass.language ? hass.language.split('-')[0] : 'en';
  const translations = TRANSLATIONS[lang] || TRANSLATIONS['en'];
  return translations[key] || TRANSLATIONS['en'][key] || key;
}

// Helper function to match entity_id to zone slug accurately without false positives
function isZoneEntityMatch(id, slug) {
  if (!id || !slug) return false;
  const objId = (id.includes('.') ? id.split('.')[1] : id).toLowerCase();
  const cleanSlug = String(slug).toLowerCase().replace(/^(multizone_thermostat_|zona_|zone_)/, '');

  let stripped = objId.replace(/^(multizone_thermostat_|zona_|zone_)/, '');
  if (stripped === cleanSlug) return true;

  const suffixes = [
    '_energy_class', '_classe_energetica',
    '_thermal_retention', '_tempo_ritenzione_termica', '_tempo_di_ritenzione_termica',
    '_radiator_sizing', '_dimensionamento_radiatore',
    '_anomaly', '_anomalia',
    '_passive_heat', '_apporto_passivo',
    '_battery', '_batteria',
    '_heating_rate', '_velocita_riscaldamento',
    '_cooling_rate', '_velocita_raffrescamento',
    '_thermal_loss', '_dispersione_termica',
    '_thermal_inertia', '_inerzia_termica',
    '_duty_cycle', '_ciclo_di_lavoro',
    '_demand', '_fabbisogno',
    '_autotune',
    '_window_open', '_finestra_aperta',
    '_split_boost', '_boost_split',
    '_physical_sync',
    '_zone_mode', '_modalita_zona', '_modalita', '_mode', '_preset',
    '_status', '_stato'
  ];

  for (const sfx of suffixes) {
    if (stripped.endsWith(sfx)) {
      if (stripped.slice(0, -sfx.length) === cleanSlug) return true;
    }
  }

  // Legacy patterns where entity ends with _<cleanSlug> or _zona_<cleanSlug>
  // e.g. ciclo_di_lavoro_zona_salotto or modalita_zona_salotto
  if (objId.endsWith('_' + cleanSlug) || objId.endsWith('_zona_' + cleanSlug) || objId.endsWith('_zone_' + cleanSlug)) {
    return true;
  }

  return false;
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
  const cleanSlug = slug.replace(/^zona_/, "");
  const isSlugMatch = (id) => isZoneEntityMatch(id, cleanSlug);

  for (const entityId of Object.keys(hass.states)) {
    if ((entityId.startsWith("select.") || entityId.startsWith("switch.")) && 
        isSlugMatch(entityId) &&
        (entityId.includes("mode") || entityId.includes("zone") || entityId.includes("modalita"))) {
      return entityId;
    }
  }
  
  return "";
}

// Helper function to auto-discover the master switch entity
function findMasterEntity(hass) {
  if (!hass || !hass.states) return null;
  
  // Search for switch with multizone_type: master attribute
  const found = Object.keys(hass.states).find(key => {
    const state = hass.states[key];
    return state && state.attributes && state.attributes.multizone_type === "master";
  });
  if (found) return found;

  // Fallback to name search
  return Object.keys(hass.states).find(key => {
    return key.startsWith('switch.') && (key.includes('heating_master') || key.includes('master_control'));
  }) || null;
}

// Helper function to auto-discover the boiler switch/sensor entity
function findBoilerEntity(hass) {
  if (!hass || !hass.states) return null;

  // 1. Check master switch attribute boiler_switch
  const masterId = findMasterEntity(hass);
  if (masterId && hass.states[masterId] && hass.states[masterId].attributes) {
    const bSwitch = hass.states[masterId].attributes.boiler_switch;
    if (bSwitch && hass.states[bSwitch]) return bSwitch;
  }

  // 2. Check climate entity attributes for boiler_entity_id
  for (const key of Object.keys(hass.states)) {
    if (key.startsWith('climate.')) {
      const attrs = hass.states[key].attributes || {};
      if (attrs.boiler_entity_id && hass.states[attrs.boiler_entity_id]) {
        return attrs.boiler_entity_id;
      }
    }
  }

  // 3. Fallback name search
  return Object.keys(hass.states).find(key => {
    return key.startsWith('switch.') && (key.includes('boiler') || key.includes('caldaia'));
  }) || null;
}

// Helper function to auto-discover the preset select entity
function findPresetEntity(hass) {
  if (!hass || !hass.states) return null;
  
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


// Helper function to auto-discover Heat Source Priority entity (select)
function findHeatSourcePriorityEntity(hass) {
  if (!hass || !hass.states) return null;
  const found = Object.keys(hass.states).find(key => {
    return key.startsWith('select.') && key.includes('heat_source_priority');
  });
  if (found) return found;

  return Object.keys(hass.states).find(key => {
    if (!key.startsWith('select.')) return false;
    const st = hass.states[key];
    if (st && st.attributes && Array.isArray(st.attributes.options)) {
      const opts = st.attributes.options;
      return opts.includes('auto') && opts.includes('hybrid') && opts.includes('combined');
    }
    return false;
  }) || null;
}

// Helper function to auto-discover Master Operation Mode entity (select)
function findMasterOperationModeEntity(hass) {
  if (!hass || !hass.states) return null;
  // 1. Exact match on select name
  const found = Object.keys(hass.states).find(key => {
    return key.startsWith('select.') && (key.includes('master_operation_mode') || key.includes('master_hvac_mode'));
  });
  if (found) return found;

  // 2. Select with options ['heat', 'cool']
  return Object.keys(hass.states).find(key => {
    if (!key.startsWith('select.')) return false;
    const st = hass.states[key];
    if (st && st.attributes && Array.isArray(st.attributes.options)) {
      const opts = st.attributes.options;
      return opts.includes('heat') && opts.includes('cool') && opts.length === 2;
    }
    return false;
  }) || null;
}

// Helper function to get current master HVAC mode ('heat' or 'cool')
function getMasterHVACMode(hass) {
  if (!hass || !hass.states) return 'heat';
  const opSelect = findMasterOperationModeEntity(hass);
  if (opSelect && hass.states[opSelect]) {
    const s = hass.states[opSelect].state;
    if (s === 'heat' || s === 'cool') return s;
  }
  const masterSwitch = findMasterEntity(hass);
  if (masterSwitch && hass.states[masterSwitch]) {
    const attrs = hass.states[masterSwitch].attributes || {};
    if (attrs.master_hvac_mode) return attrs.master_hvac_mode;
  }
  return 'heat';
}

/* ==================== BUTTON CARD CLASS ==================== */
class MultizoneThermostatButtonCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._rendered = false;
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

    const currentTemp = climateState.attributes.current_temperature;
    const targetTemp = climateState.attributes.temperature;
    const hvacMode = climateState.state;
    const hvacAction = climateState.attributes.hvac_action;
    const canCool = (climateState.attributes.can_cool !== false);
    const masterMode = typeof getMasterHVACMode === 'function' ? getMasterHVACMode(this._hass) : 'heat';
    const isSummer = (masterMode === 'cool');
    const title = this._config.title || climateState.attributes.friendly_name || getTranslation(this._hass, 'thermostat');

    // Conditional visibility in summer mode if room cannot cool
    if (isSummer && !canCool) {
      if (this._config.hide_if_cannot_cool) {
        this.style.display = 'none';
        return;
      }
      if (this._config.minimize_if_cannot_cool) {
        this.style.display = '';
        this.renderMinimized(title, currentTemp);
        return;
      }
    }
    this.style.display = '';

    if (!this._rendered) {
      this.renderStructure();
    }
    
    // Use temporary switch state if toggled locally to avoid flickering
    const actualSwitchState = this._tempSwitchState !== undefined 
      ? this._tempSwitchState 
      : (switchState ? switchState.state : "primary");

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
    // Update HVAC mode buttons
    const btnHeat = this.shadowRoot.querySelector('#btn-hvac-heat');
    const btnCool = this.shadowRoot.querySelector('#btn-hvac-cool');
    const btnOff = this.shadowRoot.querySelector('#btn-hvac-off');
    if (btnHeat) btnHeat.className = (hvacMode === 'heat') ? 'hvac-mode-btn active heat' : 'hvac-mode-btn';
    if (btnCool) {
      if (!canCool) {
        btnCool.style.display = 'none';
      } else {
        btnCool.style.display = '';
        btnCool.className = (hvacMode === 'cool') ? 'hvac-mode-btn active cool' : 'hvac-mode-btn';
      }
    }
    if (btnOff) btnOff.className = (hvacMode === 'off') ? 'hvac-mode-btn active off' : 'hvac-mode-btn';

    const isCooling = (hvacAction === 'cooling' || hvacMode === 'cool');
    const isHeating = (hvacAction === 'heating');

    if (actualSwitchState !== "bypass" && actualSwitchState !== "off") {
      controlsArea.classList.remove('disabled');
      wrapper.classList.remove('disabled');
      if (disabledOverlay) disabledOverlay.style.display = 'none';
      controlsArea.classList.remove('heating', 'cooling');
      if (isCooling) {
        controlsArea.classList.add('cooling');
      } else if (isHeating) {
        controlsArea.classList.add('heating');
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
      tempTargetEl.classList.remove('heating', 'cooling');
      if (isCooling) {
        tempTargetEl.classList.add('cooling');
      } else if (isHeating) {
        tempTargetEl.classList.add('heating');
      }
    }

    const badge = this.shadowRoot.querySelector('.status-badge');
    badge.className = 'status-badge';
    if (actualSwitchState === "bypass" || actualSwitchState === "off") {
      badge.innerHTML = "";
    } else if (isCooling) {
      badge.style.color = '#38bdf8';
      badge.innerHTML = `<ha-icon icon="mdi:snowflake" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>${getTranslation(this._hass, 'cooling_active') || 'In Raffrescamento'}`;
    } else if (actualSwitchState === "secondary") {
      badge.style.color = '#607d8b';
      badge.innerHTML = `<ha-icon icon="mdi:link-variant" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>${getTranslation(this._hass, 'secondary')}`;
    } else {
      badge.style.color = 'var(--primary-color, #03a9f4)';
      badge.innerHTML = `<ha-icon icon="mdi:star-circle-outline" style="margin-right: 4px; --mdc-icon-size: 16px;"></ha-icon>${getTranslation(this._hass, 'primary')}`;
    }

    const sourceBadge = this.shadowRoot.querySelector('.heat-source-badge');
    if (sourceBadge) {
      let heatSource = climateState.attributes.active_heating_source;
      const isHeatingActive = (hvacAction === 'heating' || Boolean(climateState.attributes.split_active));
      if (!heatSource && isHeatingActive) {
        const splitActive = Boolean(climateState.attributes.split_active);
        const hydronicSuppressed = Boolean(climateState.attributes.split_hydronic_suppressed);
        if (splitActive && !hydronicSuppressed) {
          heatSource = "dual";
        } else if (splitActive) {
          heatSource = "electric";
        } else if (hvacAction === 'heating') {
          heatSource = "gas";
        } else {
          heatSource = "none";
        }
      }

      if (isHeatingActive && actualSwitchState !== "bypass" && actualSwitchState !== "off" && heatSource && heatSource !== "none") {
        sourceBadge.style.display = "inline-flex";
        sourceBadge.className = "heat-source-badge";
        if (heatSource === "electric") {
          sourceBadge.classList.add("badge-source-electric");
          sourceBadge.innerHTML = `<ha-icon icon="mdi:lightning-bolt" style="--mdc-icon-size: 14px; color: #38bdf8;"></ha-icon><span>${getTranslation(this._hass, 'heat_source_electric')}</span>`;
        } else if (heatSource === "dual") {
          sourceBadge.classList.add("badge-source-dual");
          sourceBadge.innerHTML = `<ha-icon icon="mdi:fire" style="--mdc-icon-size: 14px; color: #fb923c;"></ha-icon><ha-icon icon="mdi:lightning-bolt" style="--mdc-icon-size: 14px; color: #38bdf8;"></ha-icon><span>${getTranslation(this._hass, 'heat_source_dual')}</span>`;
        } else {
          sourceBadge.classList.add("badge-source-gas");
          sourceBadge.innerHTML = `<ha-icon icon="mdi:fire" style="--mdc-icon-size: 14px; color: #fb923c;"></ha-icon><span>${getTranslation(this._hass, 'heat_source_gas')}</span>`;
        }
      } else {
        sourceBadge.style.display = "none";
      }
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
        border-radius: var(--ha-card-border-radius, 20px);
        border: 1px solid var(--ha-card-border-color, rgba(255, 255, 255, 0.08));
        box-shadow: var(--ha-card-box-shadow, 0 4px 12px rgba(0, 0, 0, 0.15));
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
      .thermostat-body.cooling .temp-display::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 440px;
        height: 440px;
        border-radius: 50%;
        background: radial-gradient(closest-side, rgba(56, 189, 248, 0.35) 0%, rgba(56, 189, 248, 0.15) 30%, rgba(56, 189, 248, 0.02) 75%, transparent 100%);
        z-index: -1;
        pointer-events: none;
        animation: pulse-halo-cool 2s infinite alternate;
      }
      @keyframes pulse-halo-cool {
        0% { opacity: 0.8; transform: translate(-50%, -50%) scale(0.95); }
        100% { opacity: 1; transform: translate(-50%, -50%) scale(1.05); }
      }
      .temp-target.cooling .temp-target-val {
        color: #38bdf8;
        text-shadow: 0 0 10px rgba(56, 189, 248, 0.5), 0 0 20px rgba(56, 189, 248, 0.3);
        animation: pulse-glow-cool 1.5s infinite alternate;
      }
      @keyframes pulse-glow-cool {
        0% { text-shadow: 0 0 10px rgba(56, 189, 248, 0.5), 0 0 20px rgba(56, 189, 248, 0.3); }
        100% { text-shadow: 0 0 15px rgba(14, 165, 233, 0.9), 0 0 30px rgba(14, 165, 233, 0.6); }
      }
      .header-controls {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .hvac-mode-bar {
        display: flex;
        align-items: center;
        background: var(--secondary-background-color, rgba(255, 255, 255, 0.05));
        border-radius: 8px;
        padding: 2px;
        gap: 2px;
      }
      .hvac-mode-btn {
        background: transparent;
        border: none;
        color: var(--secondary-text-color, #94a3b8);
        padding: 4px 7px;
        cursor: pointer;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.2s, color 0.2s;
      }
      .hvac-mode-btn:hover { color: var(--primary-text-color, #ffffff); background: rgba(255, 255, 255, 0.08); }
      .hvac-mode-btn.active.heat { background-color: rgba(249, 115, 22, 0.25); color: #fb923c; }
      .hvac-mode-btn.active.cool { background-color: rgba(56, 189, 248, 0.25); color: #38bdf8; }
      .hvac-mode-btn.active.off { background-color: rgba(255, 255, 255, 0.15); color: #ffffff; }
      .hvac-mode-btn ha-icon { --mdc-icon-size: 16px; }
      .temp-current {
        font-size: 14px;
        color: var(--secondary-text-color);
        margin-top: 4px;
      }

      .status-bar {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
      }
      .status-badge {
        display: inline-flex;
        align-items: center;
        font-size: 14px;
        font-weight: 400;
        color: var(--secondary-text-color);
      }
      .heat-source-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 11px;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 9999px;
        text-transform: uppercase;
        letter-spacing: 0.3px;
      }
      .badge-source-gas {
        background: rgba(249, 115, 22, 0.15);
        color: #fb923c;
        border: 1px solid rgba(249, 115, 22, 0.35);
      }
      .badge-source-electric {
        background: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.35);
      }
      .badge-source-dual {
        background: linear-gradient(135deg, rgba(249, 115, 22, 0.2), rgba(56, 189, 248, 0.2));
        color: #fcd34d;
        border: 1px solid rgba(251, 191, 36, 0.4);
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
          <div class="header-controls">
            <div class="segmented-control" id="zone-modes-container">
              <button class="seg-btn primary" id="seg-primary"><ha-icon icon="mdi:star-circle-outline"></ha-icon></button>
              <button class="seg-btn secondary" id="seg-secondary"><ha-icon icon="mdi:link-variant"></ha-icon></button>
              <button class="seg-btn bypass" id="seg-bypass"><ha-icon icon="mdi:cancel"></ha-icon></button>
            </div>
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
            <div class="heat-source-badge" style="display: none;"></div>
          </div>

          <div class="bottom-hvac-row" style="display: flex; justify-content: center; margin-top: 6px;">
            <div class="hvac-mode-bar" id="hvac-mode-bar">
              <button type="button" class="hvac-mode-btn" id="btn-hvac-heat" title="Caldo"><ha-icon icon="mdi:fire"></ha-icon></button>
              <button type="button" class="hvac-mode-btn" id="btn-hvac-cool" title="Freddo"><ha-icon icon="mdi:snowflake"></ha-icon></button>
              <button type="button" class="hvac-mode-btn" id="btn-hvac-off" title="Spento"><ha-icon icon="mdi:power"></ha-icon></button>
            </div>
          </div>
        </div>
      </div>
    `;

    // Hook events
    card.querySelector('#btn-hvac-heat').addEventListener('click', () => this.setHvacMode("heat"));
    card.querySelector('#btn-hvac-cool').addEventListener('click', () => this.setHvacMode("cool"));
    card.querySelector('#btn-hvac-off').addEventListener('click', () => this.setHvacMode("off"));
    card.querySelector('#seg-primary').addEventListener('click', () => this.setZoneMode("primary"));
    card.querySelector('#seg-secondary').addEventListener('click', () => this.setZoneMode("secondary"));
    card.querySelector('#seg-bypass').addEventListener('click', () => this.setZoneMode("bypass"));

    card.querySelector('#temp-down').addEventListener('click', () => this.changeTemp(-1));
    card.querySelector('#temp-up').addEventListener('click', () => this.changeTemp(1));



    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  toggleLocalSplit() {
    if (!this._hass || !this._config) return;
    const climateEntity = this._config.entity;
    const climateState = this._hass.states[climateEntity];
    if (!climateState) return;
    const splitEntity = climateState.attributes.split_climate_entity;
    if (!splitEntity) return;

    const masterEntity = typeof findMasterEntity === 'function' ? findMasterEntity(this._hass) : null;
    const isMasterOn = Boolean(masterEntity && this._hass.states[masterEntity] && this._hass.states[masterEntity].state === 'on');
    if (isMasterOn) {
      // Guard: when master is active, individual manual split override is disabled
      return;
    }

    const masterMode = typeof getMasterHVACMode === 'function' ? getMasterHVACMode(this._hass) : 'heat';
    const splitState = this._hass.states[splitEntity];
    const isSplitOn = (splitState && splitState.state !== 'off') || Boolean(climateState.attributes.split_active) || Boolean(climateState.attributes.split_manual_on);
    const targetHvac = isSplitOn ? 'off' : (masterMode === 'cool' ? 'cool' : 'heat');

    // Turn both the virtual thermostat zone and the split entity to target HVAC mode
    this._hass.callService("climate", "set_hvac_mode", {
      entity_id: climateEntity,
      hvac_mode: targetHvac
    });
    this._hass.callService("climate", "set_hvac_mode", {
      entity_id: splitEntity,
      hvac_mode: targetHvac
    });
  }

  setHvacMode(mode) {
    if (!this._hass) return;
    const climateEntity = this._config.entity;
    if (!climateEntity) return;
    this._hass.callService("climate", "set_hvac_mode", {
      entity_id: climateEntity,
      hvac_mode: mode
    });
  }

  renderMinimized(title, currentTemp) {
    const curStr = currentTemp !== undefined ? `${currentTemp}°C` : '--°C';
    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          padding: 12px 16px;
          border-radius: var(--ha-card-border-radius, 14px);
          background: rgba(30, 41, 59, 0.6);
          border: 1px dashed rgba(255, 255, 255, 0.12);
          display: flex;
          align-items: center;
          justify-content: space-between;
          color: #94a3b8;
          font-size: 12px;
          box-sizing: border-box;
        }
        .min-left { display: flex; align-items: center; gap: 8px; }
        .min-tag {
          font-size: 10px;
          text-transform: uppercase;
          background: rgba(148, 163, 184, 0.15);
          color: #94a3b8;
          padding: 2px 6px;
          border-radius: 4px;
          font-weight: 700;
        }
        .min-temp { font-size: 14px; font-weight: 700; color: #cbd5e1; }
      </style>
      <ha-card>
        <div class="min-left">
          <ha-icon icon="mdi:snowflake-off" style="--mdc-icon-size: 18px; color: #64748b;"></ha-icon>
          <span style="font-weight: 600;">${title}</span>
          <span class="min-tag">${getTranslation(this._hass, 'winter_only') || 'Solo Inverno'}</span>
        </div>
        <div class="min-temp">${curStr}</div>
      </ha-card>
    `;
    this._rendered = false;
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
/* ==================== DIAL CARD (BESPOKE VECTOR ARC & DRAG SLIDER) ==================== */
/* ==================== DIAL CARD (BESPOKE VECTOR ARC & DRAG SLIDER) ==================== */
class MultizoneThermostatDialCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._rendered = false;
    this._isDragging = false;
    this._dragTargetTemp = undefined;
    this._minTemp = 10;
    this._maxTemp = 30;
    this._targetTemp = 20;
    this._currentTemp = 20;
    this._isHeating = false;
    this._isCooling = false;
    this._isStandby = false;
    this._isOff = false;
    this._switchEntity = null;
    this._switchTimeout = null;
  }

  formatTemperature(val) {
    if (typeof val !== 'number' || isNaN(val)) return '--';
    return val.toFixed(1).replace('.', ',');
  }

  updateTargetTempDisplay(val) {
    const formatted = this.formatTemperature(val);
    const parts = formatted.split(',');
    const intPart = parts[0] || '--';
    const decPart = parts.length > 1 ? ',' + parts[1] : '';
    const intEl = this.shadowRoot.querySelector('#target-temp-int');
    const decEl = this.shadowRoot.querySelector('#target-temp-dec');
    if (intEl) intEl.textContent = intPart;
    if (decEl) decEl.textContent = decPart;
    const legacyEl = this.shadowRoot.querySelector('#target-temp');
    if (legacyEl) legacyEl.textContent = formatted;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) {
      this.renderStructure();
    }
    this.updateCard();
  }

  connectedCallback() {
    this._styleListener = (e) => {
      const newStyle = e.detail?.style || 'luxury';
      this._effectiveStyle = newStyle;
      if (this._config) this._config.card_style = newStyle;
      this.renderStructure();
      this.updateCard();
    };
    window.addEventListener('mz-style-changed', this._styleListener);
  }

  disconnectedCallback() {
    this._isDragging = false;
    if (this._onWindowPointerUp) {
      window.removeEventListener('pointerup', this._onWindowPointerUp);
      window.removeEventListener('pointercancel', this._onWindowPointerUp);
      this._onWindowPointerUp = null;
    }
    if (this._styleListener) {
      window.removeEventListener('mz-style-changed', this._styleListener);
    }
    if (this._switchTimeout) {
      clearTimeout(this._switchTimeout);
      this._switchTimeout = null;
    }
  }

  getEffectiveStyle() {
    if (this._effectiveStyle) return this._effectiveStyle;
    const saved = localStorage.getItem('mz_card_style');
    if (saved) return saved;
    if (this._config && (this._config.card_style || this._config.style)) {
      return this._config.card_style || this._config.style;
    }
    return 'luxury';
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Specificare un termostato (climate entity)");
    }
    const prevStyle = this.getEffectiveStyle();
    this._config = Object.assign({}, config);
    const newStyle = this.getEffectiveStyle();

    if (!this._rendered || prevStyle !== newStyle) {
      this.renderStructure();
    }
    this.updateCard();
  }

  getStep() {
    if (this._config && (this._config.step !== undefined || this._config.target_temp_step !== undefined)) {
      const cfgStep = parseFloat(this._config.step ?? this._config.target_temp_step);
      if (!isNaN(cfgStep) && cfgStep > 0) return cfgStep;
    }
    const climateState = this._hass && this._config && this._config.entity ? this._hass.states[this._config.entity] : null;
    if (climateState && climateState.attributes && climateState.attributes.target_temp_step !== undefined && climateState.attributes.target_temp_step !== null) {
      const attrStep = parseFloat(climateState.attributes.target_temp_step);
      if (!isNaN(attrStep) && attrStep > 0) return attrStep;
    }
    return 0.5;
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
      title: "",
      card_style: "luxury"
    };
  }

  renderStructure() {
    const radius = (this._config && this._config.border_radius) ? this._config.border_radius : '20px';
    const isClassic = (this.getEffectiveStyle() === "classic");
    this.renderUnifiedStructure(radius, isClassic);
    this._rendered = true;
  }

  renderClassicStructure(radius) {
    this.renderUnifiedStructure(radius, true);
  }

  renderLuxuryStructure(radius) {
    this.renderUnifiedStructure(radius, false);
  }

  renderUnifiedStructure(radius, isClassic) {
    const cardBgStyle = isClassic ? `
        ha-card {
          padding: 16px 16px 14px 16px;
          position: relative;
          overflow: hidden !important;
          border-radius: ${radius} !important;
          background: var(--ha-card-background, var(--card-background-color, #1c1c1e)) !important;
          border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, rgba(255, 255, 255, 0.12))) !important;
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0, 0, 0, 0.2)) !important;
          backdrop-filter: none !important;
          -webkit-backdrop-filter: none !important;
          transition: all 0.3s ease;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          box-sizing: border-box;
          user-select: none;
          touch-action: pan-y;
        }
        .dial-track {
          stroke: rgba(255, 255, 255, 0.12);
          stroke-width: 24;
          stroke-linecap: round;
          fill: none;
        }
        .step-btn {
          pointer-events: auto;
          width: 48px;
          height: 48px;
          border-radius: 50%;
          background: transparent;
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.22));
          color: var(--primary-text-color, #ffffff);
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        .step-btn:hover {
          background: rgba(255, 255, 255, 0.08);
          border-color: rgba(255, 255, 255, 0.35);
        }
        .segmented-control {
          display: flex;
          align-items: center;
          background: var(--card-background-color, #202b38);
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.15));
          border-radius: 9999px;
          padding: 2px;
          gap: 2px;
          z-index: 21;
        }
        .split-pill-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: var(--card-background-color, #202b38);
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.15));
          color: var(--secondary-text-color, #94a3b8);
          padding: 4px 12px;
          border-radius: 9999px;
          font-size: 11px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          white-space: nowrap;
        }
    ` : `
        ha-card {
          padding: 16px 16px 14px 16px;
          position: relative;
          overflow: hidden !important;
          border-radius: ${radius} !important;
          background: linear-gradient(135deg, rgba(20, 27, 41, 0.88) 0%, rgba(15, 23, 42, 0.94) 100%) !important;
          backdrop-filter: blur(20px) !important;
          -webkit-backdrop-filter: blur(20px) !important;
          border: 1px solid rgba(255, 255, 255, 0.08) !important;
          box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
          transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          box-sizing: border-box;
          user-select: none;
          touch-action: pan-y;
        }
        ha-card:hover {
          border-color: rgba(255, 255, 255, 0.16) !important;
          transform: translateY(-2px);
          box-shadow: 0 16px 40px -10px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
        }
        .heating-aura {
          background: radial-gradient(circle at 50% 120%, rgba(249, 115, 22, 0.22) 0%, rgba(239, 68, 68, 0.06) 45%, rgba(20, 27, 41, 0.92) 75%) !important;
        }
        .cooling-aura {
          background: radial-gradient(circle at 50% 120%, rgba(56, 189, 248, 0.22) 0%, rgba(14, 165, 233, 0.06) 45%, rgba(20, 27, 41, 0.92) 75%) !important;
        }
        .idle-aura {
          background: radial-gradient(circle at 50% 120%, rgba(255, 255, 255, 0.06) 0%, rgba(20, 27, 41, 0.92) 75%) !important;
        }
        .dial-track {
          stroke: rgba(255, 255, 255, 0.08);
          stroke-width: 24;
          stroke-linecap: round;
          fill: none;
        }
        .step-btn {
          pointer-events: auto;
          width: 48px;
          height: 48px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.16);
          color: #ffffff;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        }
        .step-btn:hover {
          background: rgba(255, 255, 255, 0.14);
          border-color: rgba(255, 255, 255, 0.28);
          transform: scale(1.04);
        }
        .segmented-control {
          display: flex;
          align-items: center;
          background: rgba(15, 23, 42, 0.85);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 9999px;
          padding: 2px;
          gap: 2px;
          z-index: 21;
        }
        .split-pill-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: rgba(15, 23, 42, 0.85);
          border: 1px solid rgba(255, 255, 255, 0.12);
          color: #cbd5e1;
          padding: 4px 12px;
          border-radius: 9999px;
          font-size: 11px;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
          white-space: nowrap;
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
        }
    `;

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          box-sizing: border-box;
        }
        ${cardBgStyle}
        .header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          min-height: 44px;
          margin-bottom: 4px;
          position: relative;
          z-index: 20;
        }
        .title-box {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          gap: 4px;
        }
        .title {
          font-size: 16px;
          font-weight: 700;
          color: var(--primary-text-color, #ffffff);
          line-height: 1.2;
        }
        .pills-row {
          display: flex;
          align-items: center;
          gap: 6px;
          flex-wrap: wrap;
        }
        .header-center {
          position: absolute;
          left: 50%;
          top: 4px;
          transform: translateX(-50%);
          display: flex;
          align-items: center;
          justify-content: center;
          pointer-events: auto;
          z-index: 22;
        }
        .split-pill-btn:hover {
          color: #ffffff;
          border-color: rgba(255, 255, 255, 0.25);
          background: rgba(255, 255, 255, 0.12);
        }
        .split-pill-btn.active.heat {
          background: linear-gradient(135deg, #f97316, #ea580c);
          border-color: #fb923c;
          color: #ffffff;
          box-shadow: 0 2px 10px rgba(249, 115, 22, 0.5);
        }
        .split-pill-btn.active.cool {
          background: linear-gradient(135deg, #38bdf8, #0284c7);
          border-color: #7dd3fc;
          color: #ffffff;
          box-shadow: 0 2px 10px rgba(56, 189, 248, 0.5);
        }
        .split-pill-btn ha-icon {
          --mdc-icon-size: 14px;
        }
        .luxury-pill {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          padding: 2px 8px;
          border-radius: 9999px;
          font-size: 10px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.4px;
        }
        .pulse-dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: currentColor;
          box-shadow: 0 0 6px currentColor;
        }
        .pill-cyan {
          background: rgba(56, 189, 248, 0.15);
          color: #38bdf8;
          border: 1px solid rgba(56, 189, 248, 0.3);
        }
        .pill-amber {
          background: rgba(251, 191, 36, 0.15);
          color: #fbbf24;
          border: 1px solid rgba(251, 191, 36, 0.3);
        }
        .pill-gray {
          background: rgba(148, 163, 184, 0.15);
          color: #94a3b8;
          border: 1px solid rgba(148, 163, 184, 0.3);
        }
        .pill-gas {
          background: rgba(249, 115, 22, 0.15);
          color: #fb923c;
          border: 1px solid rgba(249, 115, 22, 0.35);
        }
        .pill-electric {
          background: rgba(56, 189, 248, 0.15);
          color: #38bdf8;
          border: 1px solid rgba(56, 189, 248, 0.35);
        }
        .pill-dual {
          background: linear-gradient(135deg, rgba(249, 115, 22, 0.2), rgba(56, 189, 248, 0.2));
          color: #fcd34d;
          border: 1px solid rgba(251, 191, 36, 0.4);
        }
        .header-controls {
          display: flex;
          align-items: center;
          gap: 6px;
          z-index: 21;
        }
        .seg-btn {
          background: transparent;
          border: none;
          color: #94a3b8;
          padding: 4px 8px;
          cursor: pointer;
          border-radius: 9999px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          transition: all 0.2s ease;
        }
        .seg-btn:hover { color: white; background: rgba(255, 255, 255, 0.08); }
        .seg-btn.active { background-color: #0284c7; color: white; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3); }
        .seg-btn ha-icon { --mdc-icon-size: 16px; }
        
        /* 1-to-1 HA Native Circular Slider & Info Geometry (320x320, r=145, stroke=24) */
        .gauge-container {
          position: relative;
          width: 100%;
          max-width: 280px;
          aspect-ratio: 1 / 1;
          margin: 2px auto 0 auto;
          display: flex;
          align-items: center;
          justify-content: center;
          user-select: none;
          touch-action: pan-y;
        }
        .dial-svg {
          width: 100%;
          height: 100%;
          display: block;
          touch-action: pan-y;
          overflow: visible;
          cursor: pointer;
        }
        .dial-meter {
          stroke-width: 24;
          stroke-linecap: round;
          fill: none;
          transition: stroke-dashoffset 0.12s ease, stroke 0.3s ease;
        }
        .dial-knob {
          fill: #ffffff;
          cursor: grab;
          filter: drop-shadow(0 1px 4px rgba(0, 0, 0, 0.5));
          transition: transform 0.1s ease;
        }
        /* Centered Info Block (Matches HA .info) */
        .gauge-center {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          pointer-events: none;
          gap: 6px;
        }
        .dial-sub-text {
          font-size: 15px;
          font-weight: 500;
          line-height: 1.4;
          letter-spacing: 0.1px;
          text-transform: none;
          margin: 0;
          text-align: center;
        }
        .heating-text { color: #fb923c; }
        .cooling-text { color: #38bdf8; }
        .standby-text { color: var(--primary-text-color, #ffffff); }
        .off-text { color: var(--secondary-text-color, #94a3b8); }

        /* HA Native ha-big-number Layout (57px with stacked unit & decimal) */
        .target-temp-val {
          font-size: 57px;
          font-weight: 400;
          line-height: 1.12;
          letter-spacing: -0.25px;
          color: var(--primary-text-color, #ffffff);
          display: flex;
          margin: 0;
          direction: ltr;
        }
        .displayed-value {
          display: inline-flex;
          flex-direction: row;
          align-items: flex-end;
        }
        .addon {
          display: flex;
          flex-direction: column-reverse;
          padding: 4px 0;
          margin-left: 2px;
        }
        .decimal {
          font-size: 0.42em;
          line-height: 1.33;
          min-height: 1.33em;
        }
        .unit {
          font-size: 0.33em;
          line-height: 1.15;
        }
        .current-temp-badge {
          font-size: 15px;
          font-weight: 400;
          line-height: 1.4;
          color: var(--primary-text-color, #e2e8f0);
          background: transparent;
          border: none;
          padding: 0;
          margin: 0;
          display: flex;
          align-items: center;
          gap: 3px;
        }

        /* Bottom Arc Opening Step Buttons (Matches HA .buttons) */
        .step-buttons {
          position: absolute;
          bottom: 8px;
          left: 0;
          right: 0;
          margin: 0 auto;
          gap: 24px;
          display: flex;
          flex-direction: row;
          align-items: center;
          justify-content: center;
          pointer-events: none;
        }
        .step-btn ha-icon {
          --mdc-icon-size: 24px;
        }
        .step-btn:active {
          transform: scale(0.94);
          background: rgba(255, 255, 255, 0.2);
        }

        .disabled-overlay {
          position: absolute;
          inset: 0;
          z-index: 30;
          background: rgba(11, 15, 23, 0.85);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          display: none;
          align-items: center;
          justify-content: center;
          flex-direction: column;
          gap: 8px;
          color: #f87171;
          font-weight: 700;
          font-size: 13px;
        }
      </style>

      <ha-card id="zone-card">
        <div class="disabled-overlay" id="disabled-overlay">
          <ha-icon icon="mdi:close-circle-outline" style="--mdc-icon-size: 32px;"></ha-icon>
          <span>Zona Esclusa / Bypass</span>
          <button id="re-enable-btn" style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; padding: 4px 12px; border-radius: 8px; font-size: 11px; font-weight: 600; cursor: pointer; margin-top: 4px;">Riattiva</button>
        </div>

        <div class="header">
          <div class="title-box">
            <div class="title" id="zone-title">Termostato</div>
            <div class="pills-row">
              <div class="luxury-pill pill-cyan" id="mode-pill">
                <span class="pulse-dot"></span>
                <span id="mode-text">Prioritaria</span>
              </div>
              <div class="luxury-pill pill-gas" id="heat-source-pill" style="display: none;">
                <ha-icon id="heat-source-icon" icon="mdi:fire" style="--mdc-icon-size: 13px;"></ha-icon>
                <span id="heat-source-text">Gas</span>
              </div>
            </div>
          </div>

          <div class="header-center">
            <button class="split-pill-btn" id="btn-split-toggle" style="display: none;" title="Split Locale">
              <ha-icon id="split-toggle-icon" icon="mdi:fire"></ha-icon>
              <span id="split-toggle-text">Split</span>
            </button>
          </div>

          <div class="header-controls">
            <div class="segmented-control">
              <button class="seg-btn active" id="seg-primary" title="Prioritaria"><ha-icon icon="mdi:target"></ha-icon></button>
              <button class="seg-btn" id="seg-secondary" title="Secondaria"><ha-icon icon="mdi:link-variant"></ha-icon></button>
              <button class="seg-btn" id="seg-bypass" title="Bypass"><ha-icon icon="mdi:close-circle-outline"></ha-icon></button>
            </div>
          </div>
        </div>

        <!-- 1-to-1 HA Native Circular Slider Geometry (320x320, cx=160, cy=160, r=145, stroke=24) -->
        <div class="gauge-container" id="gauge-container">
          <svg class="dial-svg" id="dial-svg" viewBox="0 0 320 320">
            <defs>
              <filter id="heating-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#f97316" flood-opacity="0.7"/>
              </filter>
              <filter id="cooling-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#38bdf8" flood-opacity="0.7"/>
              </filter>
              <filter id="standby-glow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="0" stdDeviation="3" flood-color="#e2e8f0" flood-opacity="0.35"/>
              </filter>
            </defs>
            <!-- 270deg background track: cx=160, cy=160, r=145, stroke-width=24 -->
            <path class="dial-track" id="dial-track" d="M 57.47 262.53 A 145 145 0 1 1 262.53 262.53"></path>
            <!-- Active arc -->
            <path class="dial-meter" id="dial-meter" d="M 57.47 262.53 A 145 145 0 0 1 160 15"></path>
            <!-- Current temperature marker dot on track -->
            <circle id="curr-temp-dot" cx="160" cy="15" r="4" fill="#cbd5e1" opacity="0.85"></circle>
            <!-- Visible Knob inside 24px track -->
            <circle class="dial-knob" id="dial-knob" cx="160" cy="15" r="9" stroke="#ffffff" stroke-width="3"></circle>
            <!-- Transparent Enlarged Hit Area for Touch & Click -->
            <circle id="dial-knob-hit" cx="160" cy="15" r="28" fill="transparent" style="cursor: grab; touch-action: none;"></circle>
          </svg>

          <div class="gauge-center">
            <div class="dial-sub-text standby-text" id="dial-sub-text">Spento</div>
            <div class="target-temp-val">
              <span class="displayed-value">
                <span id="target-temp-int">20</span>
                <span class="addon">
                  <span class="decimal" id="target-temp-dec">,0</span>
                  <span class="unit">°C</span>
                </span>
              </span>
            </div>
            <div class="current-temp-badge">
              <ha-icon icon="mdi:thermometer" style="--mdc-icon-size: 16px; color: ${isClassic ? 'currentColor' : '#38bdf8'};"></ha-icon>
              <span id="current-temp">20,0 °C</span>
            </div>
          </div>

          <div class="step-buttons">
            <button class="step-btn" id="btn-temp-down" title="Diminuisci target (-0.5°C)">
              <ha-icon icon="mdi:minus"></ha-icon>
            </button>
            <button class="step-btn" id="btn-temp-up" title="Aumenta target (+0.5°C)">
              <ha-icon icon="mdi:plus"></ha-icon>
            </button>
          </div>
        </div>
      </ha-card>
    `;

    this.setupLuxuryEventListeners();
  }

  setupClassicEventListeners() {
    const segPrimary = this.shadowRoot.querySelector('#seg-primary');
    const segSecondary = this.shadowRoot.querySelector('#seg-secondary');
    const segBypass = this.shadowRoot.querySelector('#seg-bypass');
    const reEnableBtn = this.shadowRoot.querySelector('#re-enable-btn');

    if (segPrimary) segPrimary.addEventListener('click', (e) => { e.stopPropagation(); this.setZoneMode('primary'); });
    if (segSecondary) segSecondary.addEventListener('click', (e) => { e.stopPropagation(); this.setZoneMode('secondary'); });
    if (segBypass) segBypass.addEventListener('click', (e) => { e.stopPropagation(); this.setZoneMode('bypass'); });
    if (reEnableBtn) reEnableBtn.addEventListener('click', (e) => { e.stopPropagation(); this.setZoneMode('primary'); });

    const btnSplitToggle = this.shadowRoot.querySelector('#btn-split-toggle');
    if (btnSplitToggle) {
      btnSplitToggle.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleLocalSplit();
      });
    }
    const btnSplitClassic = this.shadowRoot.querySelector('#btn-split-toggle-classic');
    if (btnSplitClassic) {
      btnSplitClassic.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleLocalSplit();
      });
    }
  }

  setupLuxuryEventListeners() {
    this.setupClassicEventListeners();

    // Step buttons [-] and [+]
    const btnDown = this.shadowRoot.querySelector('#btn-temp-down');
    const btnUp = this.shadowRoot.querySelector('#btn-temp-up');
    if (btnDown) btnDown.addEventListener('click', (e) => { e.stopPropagation(); this.stepTemperature(-this.getStep()); });
    if (btnUp) btnUp.addEventListener('click', (e) => { e.stopPropagation(); this.stepTemperature(this.getStep()); });

    // Click/tap directly on SVG track
    const svgDial = this.shadowRoot.querySelector('#dial-svg');
    if (svgDial) {
      svgDial.addEventListener('click', (e) => {
        if (e.target && (e.target.id === 'btn-temp-down' || e.target.id === 'btn-temp-up')) return;
        this.setTempFromPointer(e);
      });
    }

    const knobHit = this.shadowRoot.querySelector('#dial-knob-hit');
    if (knobHit) {
      let startX = 0, startY = 0;
      let isPointerDown = false;

      const onWindowPointerUp = (e) => {
        if (this._onWindowPointerUp) {
          window.removeEventListener('pointerup', this._onWindowPointerUp);
          window.removeEventListener('pointercancel', this._onWindowPointerUp);
          this._onWindowPointerUp = null;
        }
        onPointerEnd(e);
      };

      const onPointerEnd = (e) => {
        if (this._onWindowPointerUp) {
          window.removeEventListener('pointerup', this._onWindowPointerUp);
          window.removeEventListener('pointercancel', this._onWindowPointerUp);
          this._onWindowPointerUp = null;
        }
        if (!isPointerDown && !this._isDragging) return;
        isPointerDown = false;
        if (this._isDragging) {
          this._isDragging = false;
          try { knobHit.releasePointerCapture(e.pointerId); } catch(err) {}
          if (this._dragTargetTemp !== undefined && this._hass && this._config.entity) {
            this._hass.callService("climate", "set_temperature", {
              entity_id: this._config.entity,
              temperature: this._dragTargetTemp
            });
          }
        }
      };

      knobHit.addEventListener('pointerdown', (e) => {
        isPointerDown = true;
        startX = e.clientX;
        startY = e.clientY;
        this._isDragging = false;
      });

      knobHit.addEventListener('pointermove', (e) => {
        if (!isPointerDown) return;
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (!this._isDragging) {
          // If vertical gesture exceeds threshold, abort drag so mobile page scrolls freely
          if (Math.abs(dy) > 8 && Math.abs(dy) > Math.abs(dx)) {
            isPointerDown = false;
            return;
          }
          if (dist > 5) {
            this._isDragging = true;
            try { knobHit.setPointerCapture(e.pointerId); } catch(err) {}
            this._onWindowPointerUp = onWindowPointerUp;
            window.addEventListener('pointerup', onWindowPointerUp);
            window.addEventListener('pointercancel', onWindowPointerUp);
          }
        }

        if (this._isDragging) {
          e.preventDefault();
          this.handlePointerDrag(e);
        }
      });

      knobHit.addEventListener('pointerup', onPointerEnd);
      knobHit.addEventListener('pointercancel', onPointerEnd);
      knobHit.addEventListener('lostpointercapture', onPointerEnd);
    }
  }

  stepTemperature(delta) {
    if (!this._hass || !this._config) return;
    const climateEntity = this._config.entity;
    const climateState = this._hass.states[climateEntity];
    if (!climateState) return;

    const step = this.getStep();
    const decimals = (step.toString().split('.')[1] || '').length;
    const effectiveDelta = (delta === 1 || delta === -1) ? delta * step : (delta || step);
    const minTemp = this._minTemp || 10;
    const maxTemp = this._maxTemp || 30;
    const currentTarget = typeof climateState.attributes.temperature === 'number'
      ? climateState.attributes.temperature
      : (this._targetTemp || 20.0);
    const stepped = parseFloat((Math.round((currentTarget + effectiveDelta) / step) * step).toFixed(decimals));
    const newTarget = Math.min(maxTemp, Math.max(minTemp, stepped));

    this._targetTemp = newTarget;
    this.updateTargetTempDisplay(newTarget);
    this.renderDialArc(newTarget);

    this._hass.callService("climate", "set_temperature", {
      entity_id: climateEntity,
      temperature: newTarget
    });
  }

  setTempFromPointer(e) {
    if (!this._hass || !this._config) return;
    const climateEntity = this._config.entity;
    const svg = this.shadowRoot.querySelector('#dial-svg');
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const scaleX = 320 / rect.width;
    const scaleY = 320 / rect.height;
    const px = (e.clientX - rect.left) * scaleX;
    const py = (e.clientY - rect.top) * scaleY;
    const dx = px - 160.0;
    const dy = py - 160.0;

    let angle = Math.atan2(dx, -dy) * (180 / Math.PI);
    if (angle > 135) {
      if (angle > 157.5) angle = -135;
      else angle = 135;
    } else if (angle < -135) {
      if (angle < -157.5) angle = 135;
      else angle = -135;
    }

    const minTemp = this._minTemp || 10;
    const maxTemp = this._maxTemp || 30;
    const step = this.getStep();
    const decimals = (step.toString().split('.')[1] || '').length;
    const pct = Math.max(0, Math.min(1, (angle + 135) / 270));
    let temp = minTemp + pct * (maxTemp - minTemp);
    const stepped = parseFloat((Math.round(temp / step) * step).toFixed(decimals));
    temp = Math.max(minTemp, Math.min(maxTemp, stepped));

    this._targetTemp = temp;
    this.renderDialArc(temp);
    this.updateTargetTempDisplay(temp);

    this._hass.callService("climate", "set_temperature", {
      entity_id: climateEntity,
      temperature: temp
    });
  }

  handlePointerDrag(e) {
    const svg = this.shadowRoot.querySelector('#dial-svg');
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const scaleX = 320 / rect.width;
    const scaleY = 320 / rect.height;
    const px = (e.clientX - rect.left) * scaleX;
    const py = (e.clientY - rect.top) * scaleY;

    const dx = px - 160.0;
    const dy = py - 160.0;

    // Clockwise angle where 0 = 12 o'clock (dy < 0)
    let angle = Math.atan2(dx, -dy) * (180 / Math.PI);

    // Bottom gap is from +135 to +180 and -180 to -135
    if (angle > 135) {
      if (angle > 157.5) angle = -135;
      else angle = 135;
    } else if (angle < -135) {
      if (angle < -157.5) angle = 135;
      else angle = -135;
    }

    const minTemp = this._minTemp || 10;
    const maxTemp = this._maxTemp || 30;
    const step = this.getStep();
    const decimals = (step.toString().split('.')[1] || '').length;
    const pct = Math.max(0, Math.min(1, (angle + 135) / 270));
    let temp = minTemp + pct * (maxTemp - minTemp);
    const stepped = parseFloat((Math.round(temp / step) * step).toFixed(decimals));
    temp = Math.max(minTemp, Math.min(maxTemp, stepped));

    this._dragTargetTemp = temp;
    this.renderDialArc(temp);

    this.updateTargetTempDisplay(temp);
  }

  renderDialArc(targetTemp) {
    const minTemp = this._minTemp || 10;
    const maxTemp = this._maxTemp || 30;
    const range = Math.max(maxTemp - minTemp, 1);
    const pct = Math.max(0, Math.min(1, (targetTemp - minTemp) / range));
    const delta = pct * 270.0;
    const alpha = -135.0 + delta;
    const rad = alpha * (Math.PI / 180);

    const cx = 160.0;
    const cy = 160.0;
    const r = 145.0;

    const xt = cx + r * Math.sin(rad);
    const yt = cy - r * Math.cos(rad);

    const meter = this.shadowRoot.querySelector('#dial-meter');
    const knob = this.shadowRoot.querySelector('#dial-knob');
    const knobHit = this.shadowRoot.querySelector('#dial-knob-hit');

    let activeColor = '#e2e8f0'; // Default Standby warm white
    let filterId = 'url(#standby-glow)';

    if (this._isOff) {
      activeColor = '#475569';
      filterId = 'none';
    } else if (this._isCooling) {
      activeColor = '#38bdf8'; // Cooling ice blue
      filterId = 'url(#cooling-glow)';
    } else if (this._isHeating) {
      activeColor = '#f97316'; // Heating flame orange
      filterId = 'url(#heating-glow)';
    }

    if (meter) {
      if (this._isOff) {
        meter.setAttribute('d', '');
      } else if (this._isCooling) {
        // In cooling: sweep counter-clockwise from right (+135deg) to target
        const sweepAngle = (1.0 - pct) * 270.0;
        if (sweepAngle <= 0.5) {
          meter.setAttribute('d', '');
        } else {
          const largeArc = sweepAngle > 180 ? 1 : 0;
          meter.setAttribute('d', `M 262.53 262.53 A 145 145 0 ${largeArc} 0 ${xt.toFixed(2)} ${yt.toFixed(2)}`);
        }
      } else {
        // In heating/standby: sweep clockwise from left (-135deg) to target
        if (delta <= 0.5) {
          meter.setAttribute('d', '');
        } else {
          const largeArc = delta > 180 ? 1 : 0;
          meter.setAttribute('d', `M 57.47 262.53 A 145 145 0 ${largeArc} 1 ${xt.toFixed(2)} ${yt.toFixed(2)}`);
        }
      }
      meter.setAttribute('stroke', activeColor);
      meter.style.filter = (this.getEffectiveStyle() === 'classic') ? 'none' : filterId;
    }

    if (knob) {
      knob.setAttribute('cx', xt.toFixed(2));
      knob.setAttribute('cy', yt.toFixed(2));
      knob.setAttribute('stroke', activeColor);
      if (this._isOff) {
        knob.setAttribute('fill', '#1e293b');
      } else {
        knob.setAttribute('fill', '#ffffff');
      }
    }

    if (knobHit) {
      knobHit.setAttribute('cx', xt.toFixed(2));
      knobHit.setAttribute('cy', yt.toFixed(2));
    }
  }

  renderCurrentTempMarker(currentTemp) {
    const minTemp = this._minTemp || 10;
    const maxTemp = this._maxTemp || 30;
    const range = Math.max(maxTemp - minTemp, 1);
    const pct = Math.max(0, Math.min(1, (currentTemp - minTemp) / range));
    const delta = pct * 270.0;
    const alpha = -135.0 + delta;
    const rad = alpha * (Math.PI / 180);

    const cx = 160.0;
    const cy = 160.0;
    const r = 145.0;

    const xc = cx + r * Math.sin(rad);
    const yc = cy - r * Math.cos(rad);

    const dot = this.shadowRoot.querySelector('#curr-temp-dot');
    if (dot) {
      dot.setAttribute('cx', xc.toFixed(2));
      dot.setAttribute('cy', yc.toFixed(2));
    }
  }

  toggleLocalSplit() {
    if (!this._hass || !this._config) return;
    const climateEntity = this._config.entity;
    const climateState = this._hass.states[climateEntity];
    if (!climateState) return;
    const splitEntity = climateState.attributes.split_climate_entity;
    if (!splitEntity) return;

    const masterEntity = typeof findMasterEntity === 'function' ? findMasterEntity(this._hass) : null;
    const isMasterOn = Boolean(masterEntity && this._hass.states[masterEntity] && this._hass.states[masterEntity].state === 'on');
    if (isMasterOn) {
      // Guard: when master is active, individual manual split override is disabled
      return;
    }

    const masterMode = typeof getMasterHVACMode === 'function' ? getMasterHVACMode(this._hass) : 'heat';
    const splitState = this._hass.states[splitEntity];
    const isSplitOn = (splitState && splitState.state !== 'off') || Boolean(climateState.attributes.split_active) || Boolean(climateState.attributes.split_manual_on);
    const targetHvac = isSplitOn ? 'off' : (masterMode === 'cool' ? 'cool' : 'heat');

    // Turn both the virtual thermostat zone and the split entity to target HVAC mode
    this._hass.callService("climate", "set_hvac_mode", {
      entity_id: climateEntity,
      hvac_mode: targetHvac
    });
    this._hass.callService("climate", "set_hvac_mode", {
      entity_id: splitEntity,
      hvac_mode: targetHvac
    });
  }

  setHvacMode(mode) {
    if (!this._hass) return;
    const climateEntity = this._config.entity;
    if (!climateEntity) return;
    this._hass.callService("climate", "set_hvac_mode", {
      entity_id: climateEntity,
      hvac_mode: mode
    });
  }

  renderMinimizedView(title, currentTemp) {
    const curStr = (typeof currentTemp === 'number') ? `${this.formatTemperature(currentTemp)} °C` : '--°C';
    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          padding: 12px 16px;
          border-radius: var(--ha-card-border-radius, 14px);
          background: rgba(30, 41, 59, 0.6);
          border: 1px dashed rgba(255, 255, 255, 0.12);
          display: flex;
          align-items: center;
          justify-content: space-between;
          color: #94a3b8;
          font-size: 12px;
          box-sizing: border-box;
        }
        .min-left { display: flex; align-items: center; gap: 8px; }
        .min-tag {
          font-size: 10px;
          text-transform: uppercase;
          background: rgba(148, 163, 184, 0.15);
          color: #94a3b8;
          padding: 2px 6px;
          border-radius: 4px;
          font-weight: 700;
        }
        .min-temp { font-size: 14px; font-weight: 700; color: #cbd5e1; }
      </style>
      <ha-card>
        <div class="min-left">
          <ha-icon icon="mdi:snowflake-off" style="--mdc-icon-size: 18px; color: #64748b;"></ha-icon>
          <span style="font-weight: 600;">${title}</span>
          <span class="min-tag">${getTranslation(this._hass, 'winter_only') || 'Solo Inverno'}</span>
        </div>
        <div class="min-temp">${curStr}</div>
      </ha-card>
    `;
    this._rendered = false;
  }

  setZoneMode(mode) {
    if (!this._hass) return;
    const climateEntity = this._config.entity;
    let switchEntity = this._config.switch;
    if (!switchEntity || !this._hass.states[switchEntity]) {
      const discovered = autoDiscoverSwitch(this._hass, climateEntity);
      if (discovered) switchEntity = discovered;
    }
    if (!switchEntity || !this._hass.states[switchEntity]) return;

    this._tempSwitchState = mode;
    this.updateCard();

    if (this._switchTimeout) clearTimeout(this._switchTimeout);
    this._switchTimeout = setTimeout(() => {
      this._tempSwitchState = undefined;
      this.updateCard();
    }, 1000);

    if (switchEntity.startsWith('select.')) {
      this._hass.callService("select", "select_option", {
        entity_id: switchEntity,
        option: mode
      });
    } else if (switchEntity.startsWith('switch.')) {
      if (mode === "bypass" || mode === "off") {
        this._hass.callService("switch", "turn_off", { entity_id: switchEntity });
      } else {
        this._hass.callService("switch", "turn_on", { entity_id: switchEntity });
      }
    }
  }

  updateCard() {
    if (!this._hass || !this._hass.states) return;
    if (!this._config) return;

    const climateEntity = this._config.entity;
    let switchEntity = this._config.switch;

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
      return;
    }

    let displayTitle = this._config.title || climateState.attributes.friendly_name || climateEntity;
    if (displayTitle) {
      displayTitle = displayTitle.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
    }

    const canCool = (climateState.attributes.can_cool !== false);
    const masterMode = typeof getMasterHVACMode === 'function' ? getMasterHVACMode(this._hass) : 'heat';
    const isSummer = (masterMode === 'cool');
    const curTempVal = typeof climateState.attributes.current_temperature === 'number' ? climateState.attributes.current_temperature : climateState.attributes.temperature;

    // Conditional visibility in summer mode if room cannot cool
    if (isSummer && !canCool) {
      if (this._config.hide_if_cannot_cool) {
        this.style.display = 'none';
        return;
      }
      if (this._config.minimize_if_cannot_cool) {
        this.style.display = '';
        this.renderMinimizedView(displayTitle, curTempVal);
        return;
      }
    }
    this.style.display = '';

    if (!this._rendered) {
      this.renderStructure();
    }

    const titleEl = this.shadowRoot.querySelector('#zone-title');
    if (titleEl) {
      titleEl.textContent = displayTitle;
    }

    let actualSwitchState = "primary";
    if (this._tempSwitchState !== undefined) {
      actualSwitchState = this._tempSwitchState;
    } else if (switchState && switchState.state) {
      actualSwitchState = switchState.state;
    } else if (climateState.attributes && climateState.attributes.zone_mode) {
      actualSwitchState = climateState.attributes.zone_mode;
    }

    // Local Split Toggle Button (In Header next to Title)
    const btnSplitToggle = this.shadowRoot.querySelector('#btn-split-toggle');
    const splitToggleIcon = this.shadowRoot.querySelector('#split-toggle-icon');
    const splitEntity = climateState.attributes.split_climate_entity;

    const masterEntity = typeof findMasterEntity === 'function' ? findMasterEntity(this._hass) : null;
    const isMasterOn = Boolean(masterEntity && this._hass.states[masterEntity] && this._hass.states[masterEntity].state === 'on');

    if (btnSplitToggle) {
      if (!splitEntity) {
        btnSplitToggle.style.display = 'none';
      } else {
        btnSplitToggle.style.display = 'inline-flex';
        const splitState = this._hass.states[splitEntity];
        const isSplitOn = (splitState && splitState.state !== 'off') || Boolean(climateState.attributes.split_active) || Boolean(climateState.attributes.split_manual_on);
        const iconName = isSummer ? 'mdi:snowflake' : 'mdi:fire';
        if (splitToggleIcon) splitToggleIcon.setAttribute('icon', iconName);

        if (isMasterOn) {
          btnSplitToggle.disabled = true;
          btnSplitToggle.style.pointerEvents = 'none';
          btnSplitToggle.style.opacity = '0.45';
          btnSplitToggle.style.cursor = 'not-allowed';
          btnSplitToggle.setAttribute('title', 'Gestito da Impianto Master (Controllo manuale disabilitato)');
          btnSplitToggle.className = isSplitOn ? (isSummer ? 'split-pill-btn active cool disabled' : 'split-pill-btn active heat disabled') : 'split-pill-btn disabled';
        } else {
          btnSplitToggle.disabled = false;
          btnSplitToggle.style.pointerEvents = 'auto';
          btnSplitToggle.style.opacity = '1';
          btnSplitToggle.style.cursor = 'pointer';
          if (isSplitOn) {
            btnSplitToggle.className = isSummer ? 'split-pill-btn active cool' : 'split-pill-btn active heat';
            btnSplitToggle.setAttribute('title', isSummer ? 'Split Acceso (Clicca per spegnere)' : 'Split Acceso (Clicca per spegnere)');
          } else {
            btnSplitToggle.className = 'split-pill-btn';
            btnSplitToggle.setAttribute('title', isSummer ? 'Accendi Split Climatizzazione' : 'Accendi Split Riscaldamento');
          }
        }
      }
    }

    // Classic Header Split Toggle
    const btnSplitClassic = this.shadowRoot.querySelector('#btn-split-toggle-classic');
    const splitIconClassic = this.shadowRoot.querySelector('#split-toggle-icon-classic');
    if (btnSplitClassic) {
      if (!splitEntity) {
        btnSplitClassic.style.display = 'none';
      } else {
        btnSplitClassic.style.display = 'inline-flex';
        const splitState = this._hass.states[splitEntity];
        const isSplitOn = (splitState && splitState.state !== 'off') || Boolean(climateState.attributes.split_active) || Boolean(climateState.attributes.split_manual_on);
        const iconName = isSummer ? 'mdi:snowflake' : 'mdi:fire';
        if (splitIconClassic) splitIconClassic.setAttribute('icon', iconName);

        if (isMasterOn) {
          btnSplitClassic.disabled = true;
          btnSplitClassic.style.pointerEvents = 'none';
          btnSplitClassic.style.opacity = '0.45';
          btnSplitClassic.style.cursor = 'not-allowed';
          btnSplitClassic.setAttribute('title', 'Gestito da Impianto Master (Controllo manuale disabilitato)');
          btnSplitClassic.className = isSplitOn ? (isSummer ? 'split-pill-btn active cool disabled' : 'split-pill-btn active heat disabled') : 'split-pill-btn disabled';
        } else {
          btnSplitClassic.disabled = false;
          btnSplitClassic.style.pointerEvents = 'auto';
          btnSplitClassic.style.opacity = '1';
          btnSplitClassic.style.cursor = 'pointer';
          if (isSplitOn) {
            btnSplitClassic.className = isSummer ? 'split-pill-btn active cool' : 'split-pill-btn active heat';
            btnSplitClassic.setAttribute('title', isSummer ? 'Split Acceso (Clicca per spegnere)' : 'Split Acceso (Clicca per spegnere)');
          } else {
            btnSplitClassic.className = 'split-pill-btn';
            btnSplitClassic.setAttribute('title', isSummer ? 'Accendi Split Climatizzazione' : 'Accendi Split Riscaldamento');
          }
        }
      }
    }

    // Segmented buttons
    const segPrimary = this.shadowRoot.querySelector('#seg-primary');
    const segSecondary = this.shadowRoot.querySelector('#seg-secondary');
    const segBypass = this.shadowRoot.querySelector('#seg-bypass');
    if (segPrimary) segPrimary.className = (actualSwitchState === "primary" || actualSwitchState === "on") ? "seg-btn active" : "seg-btn";
    if (segSecondary) segSecondary.className = (actualSwitchState === "secondary") ? "seg-btn active" : "seg-btn";
    if (segBypass) segBypass.className = (actualSwitchState === "bypass" || actualSwitchState === "off") ? "seg-btn active" : "seg-btn";

    // Mode Pill
    const modePill = this.shadowRoot.querySelector('#mode-pill');
    const modeText = this.shadowRoot.querySelector('#mode-text');
    if (modePill && modeText) {
      if (actualSwitchState === "secondary") {
        modePill.className = "luxury-pill pill-gray";
        modeText.textContent = getTranslation(this._hass, 'secondary');
      } else if (actualSwitchState === "bypass" || actualSwitchState === "off") {
        modePill.className = "luxury-pill pill-gray";
        modeText.textContent = "Bypass";
      } else {
        modePill.className = "luxury-pill pill-cyan";
        modeText.textContent = getTranslation(this._hass, 'primary');
      }
    }

    // Disabled overlay
    const overlay = this.shadowRoot.querySelector('#disabled-overlay');
    if (overlay) {
      overlay.style.display = (actualSwitchState === "bypass" || actualSwitchState === "off") ? "flex" : "none";
    }

    // Evaluate active heating source for both Classic and Luxury styles
    let heatSource = climateState.attributes.active_heating_source;
    const isHeatingActive = (climateState.attributes.hvac_action === "heating" || Boolean(climateState.attributes.split_active));
    if (!heatSource && isHeatingActive) {
      const splitActive = Boolean(climateState.attributes.split_active);
      const hydronicSuppressed = Boolean(climateState.attributes.split_hydronic_suppressed);
      if (splitActive && !hydronicSuppressed) {
        heatSource = "dual";
      } else if (splitActive) {
        heatSource = "electric";
      } else if (climateState.attributes.hvac_action === "heating") {
        heatSource = "gas";
      } else {
        heatSource = "none";
      }
    }

    const sourcePill = this.shadowRoot.querySelector('#heat-source-pill');
    const sourceIcon = this.shadowRoot.querySelector('#heat-source-icon');
    const sourceText = this.shadowRoot.querySelector('#heat-source-text');

    if (sourcePill && sourceIcon && sourceText) {
      const isCardDisabled = (actualSwitchState === "bypass" || actualSwitchState === "off" || climateState.state === "off");
      if (!isCardDisabled && isHeatingActive && heatSource && heatSource !== "none") {
        sourcePill.style.display = "inline-flex";
        sourcePill.classList.remove('pill-gas', 'pill-electric', 'pill-dual');
        if (heatSource === "electric") {
          sourcePill.classList.add('pill-electric');
          sourceIcon.icon = "mdi:lightning-bolt";
          sourceIcon.style.color = "#38bdf8";
          sourceText.textContent = getTranslation(this._hass, 'heat_source_electric');
        } else if (heatSource === "dual") {
          sourcePill.classList.add('pill-dual');
          sourceIcon.icon = "mdi:lightning-bolt-circle";
          sourceIcon.style.color = "#fcd34d";
          sourceText.textContent = getTranslation(this._hass, 'heat_source_dual');
        } else {
          sourcePill.classList.add('pill-gas');
          sourceIcon.icon = "mdi:fire";
          sourceIcon.style.color = "#fb923c";
          sourceText.textContent = getTranslation(this._hass, 'heat_source_gas');
        }
      } else {
        sourcePill.style.display = "none";
      }
    }

    const isClassic = (this.getEffectiveStyle() === 'classic');

    // Luxury Mode: State Evaluations
    const hvacAction = climateState.attributes.hvac_action;
    const hvacMode = climateState.state;

    this._isOff = (actualSwitchState === "bypass" || actualSwitchState === "off" || hvacMode === "off");
    this._isCooling = !this._isOff && (hvacAction === "cooling" || hvacMode === "cool");
    this._isHeating = !this._isOff && !this._isCooling && (hvacAction === "heating");
    this._isStandby = !this._isOff && !this._isHeating && !this._isCooling;

    this._minTemp = climateState.attributes.min_temp !== undefined ? climateState.attributes.min_temp : 10;
    this._maxTemp = climateState.attributes.max_temp !== undefined ? climateState.attributes.max_temp : 30;

    const targetTemp = typeof climateState.attributes.temperature === 'number' ? climateState.attributes.temperature : 20.0;
    const currentTemp = typeof climateState.attributes.current_temperature === 'number' ? climateState.attributes.current_temperature : targetTemp;

    this._targetTemp = targetTemp;
    this._currentTemp = currentTemp;

    // Only update dial visually from HA state if user is NOT currently dragging
    if (!this._isDragging) {
      this.updateTargetTempDisplay(targetTemp);
      this.renderDialArc(targetTemp);
    }

    const currentEl = this.shadowRoot.querySelector('#current-temp');
    if (currentEl) currentEl.textContent = this.formatTemperature(currentTemp) + " °C";

    this.renderCurrentTempMarker(currentTemp);

    const card = this.shadowRoot.querySelector('#zone-card');
    if (card) {
      card.classList.remove('heating-aura', 'cooling-aura', 'idle-aura');
      if (this._isHeating) {
        card.classList.add('heating-aura');
      } else if (this._isCooling) {
        card.classList.add('cooling-aura');
      } else if (this._isStandby) {
        card.classList.add('idle-aura');
      }
    }

    const subText = this.shadowRoot.querySelector('#dial-sub-text');
    if (subText) {
      if (this._isOff) {
        subText.className = "dial-sub-text off-text";
        subText.textContent = getTranslation(this._hass, 'off') || "Spento";
      } else if (this._isCooling) {
        subText.className = "dial-sub-text cooling-text";
        subText.textContent = "In Raffrescamento";
      } else if (this._isHeating) {
        subText.className = "dial-sub-text heating-text";
        if (heatSource === "electric") {
          subText.textContent = "Riscaldamento (" + (getTranslation(this._hass, 'heat_source_electric') || "Split") + ")";
        } else if (heatSource === "dual") {
          subText.textContent = "Riscaldamento (" + (getTranslation(this._hass, 'heat_source_dual') || "Gas + Split") + ")";
        } else {
          subText.textContent = "Riscaldamento (" + (getTranslation(this._hass, 'heat_source_gas') || "Gas") + ")";
        }
      } else {
        subText.className = "dial-sub-text standby-text";
        subText.textContent = getTranslation(this._hass, 'idle') || "In attesa";
      }
    }

    // Humidity
    const humEl = this.shadowRoot.querySelector('#humidity-val');
    const humBox = this.shadowRoot.querySelector('#humidity-metric');
    if (typeof climateState.attributes.current_humidity === 'number') {
      if (humEl) humEl.textContent = climateState.attributes.current_humidity + "%";
      if (humBox) humBox.style.display = "inline-flex";
    }

    // Valve Telemetry
    const valveEl = this.shadowRoot.querySelector('#valve-val');
    if (valveEl) {
      if (typeof climateState.attributes.valve_position === 'number') {
        valveEl.textContent = "Valvola " + Math.round(climateState.attributes.valve_position) + "%";
        valveEl.style.color = "#38bdf8";
      } else if (this._isHeating) {
        if (heatSource === "electric") {
          valveEl.textContent = "Attivo (Split/PDC)";
          valveEl.style.color = "#38bdf8";
        } else if (heatSource === "dual") {
          valveEl.textContent = "Attivo (Gas + Split)";
          valveEl.style.color = "#fcd34d";
        } else {
          valveEl.textContent = "Attivo (Gas)";
          valveEl.style.color = "#f97316";
        }
      } else if (this._isCooling) {
        valveEl.textContent = "Raffrescamento";
        valveEl.style.color = "#38bdf8";
      } else {
        valveEl.textContent = "Standby";
        valveEl.style.color = "#94a3b8";
      }
    }
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

    // Card Style Picker Row
    const styleRow = document.createElement('div');
    styleRow.className = 'form-row';
    const styleLabel = document.createElement('label');
    styleLabel.id = 'style-label';
    styleLabel.textContent = 'Stile Grafico Card';
    const styleSelect = document.createElement('select');
    styleSelect.id = 'card-style-select';
    styleSelect.style.padding = '10px';
    styleSelect.style.borderRadius = '4px';
    styleSelect.style.border = '1px solid var(--divider-color)';
    styleSelect.style.background = 'var(--card-background-color)';
    styleSelect.style.color = 'var(--primary-text-color)';
    styleSelect.style.fontSize = '14px';
    styleSelect.innerHTML = `
      <option value="luxury">Luxury Vector Arc (Nuovo)</option>
      <option value="classic">Standard Home Assistant (Classico)</option>
    `;
    styleSelect.value = this._config.card_style || this._config.style || 'luxury';
    styleSelect.addEventListener('change', (e) => {
      this._updateConfig('card_style', e.target.value);
    });
    styleRow.appendChild(styleLabel);
    styleRow.appendChild(styleSelect);
    container.appendChild(styleRow);

    // Summer Non-Cooling Visibility Options
    const summerRow = document.createElement('div');
    summerRow.className = 'form-row';
    summerRow.innerHTML = `
      <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; margin-bottom: 8px;">
        <input type="checkbox" id="chk-hide-non-cooling" ${this._config.hide_if_cannot_cool ? 'checked' : ''}>
        <span>${getTranslation(this._hass, 'hide_non_cooling') || 'Nascondi card in modalità Raffrescamento se non climatizzata'}</span>
      </label>
      <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
        <input type="checkbox" id="chk-min-non-cooling" ${this._config.minimize_if_cannot_cool ? 'checked' : ''}>
        <span>${getTranslation(this._hass, 'minimize_non_cooling') || 'Minimizza card in modalità Raffrescamento se non climatizzata'}</span>
      </label>
    `;
    summerRow.querySelector('#chk-hide-non-cooling').addEventListener('change', (e) => {
      this._updateConfig('hide_if_cannot_cool', e.target.checked);
    });
    summerRow.querySelector('#chk-min-non-cooling').addEventListener('change', (e) => {
      this._updateConfig('minimize_if_cannot_cool', e.target.checked);
    });
    container.appendChild(summerRow);

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

function getActiveMzCardStyle() {
  return localStorage.getItem('mz_card_style') || 'luxury';
}

/* ==================== STATUS (BUTTON-STYLE MASTER SWITCH) CARD CLASS ==================== */
/* ==================== MULTIZONE STATUS CARD ==================== */
class MultizoneThermostatStatusCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this._styleListener = () => {
      this.renderStructure();
      this.updateCard();
    };
    window.addEventListener('mz-style-changed', this._styleListener);
  }

  disconnectedCallback() {
    if (this._styleListener) {
      window.removeEventListener('mz-style-changed', this._styleListener);
    }
  }

  getEffectiveStyle() {
    return getActiveMzCardStyle();
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  setConfig(config) {
    this._config = Object.assign({}, config);
    if (!this._rendered) {
      this.renderStructure();
    }
    this.updateCard();
  }

  getCardSize() {
    return 1;
  }

  renderStructure() {
    const card = document.createElement('ha-card');
    const style = document.createElement('style');

    const radius = (this._config && this._config.border_radius) ? this._config.border_radius : '20px';
    const isClassic = (this.getEffectiveStyle() === 'classic');

    if (isClassic) {
      style.textContent = `
        :host {
          display: block;
          height: 100%;
          box-sizing: border-box;
        }
        ha-card {
          padding: 18px 20px;
          border-radius: ${radius} !important;
          overflow: hidden !important;
          color: var(--primary-text-color, white);
          background: var(--ha-card-background, var(--card-background-color, #1c1c1e)) !important;
          border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, rgba(255, 255, 255, 0.12))) !important;
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0, 0, 0, 0.2)) !important;
          backdrop-filter: none !important;
          -webkit-backdrop-filter: none !important;
          transition: all 0.3s ease;
          cursor: pointer;
          display: flex;
          align-items: center;
          height: 100%;
          min-height: 96px;
          position: relative;
          box-sizing: border-box;
        }
        ha-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
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
        .icon-wrap {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 54px;
          height: 54px;
          border-radius: 12px;
          background: var(--secondary-background-color, rgba(255, 255, 255, 0.05));
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.12));
          flex-shrink: 0;
          transition: transform 0.2s ease;
        }
        ha-card:hover .icon-wrap {
          transform: scale(1.05);
        }
        .icon-wrap ha-icon {
          --mdc-icon-size: 28px;
          color: var(--primary-color, #0284c7);
        }
        .info-container {
          display: flex;
          flex-direction: column;
          justify-content: center;
          flex-grow: 1;
          overflow: hidden;
          gap: 3px;
        }
        .sub-title {
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.8px;
          color: var(--secondary-text-color, #94a3b8);
        }
        .name {
          font-size: 16px;
          font-weight: 700;
          margin: 0;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          color: var(--primary-text-color, #ffffff);
        }
        .status-pill {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 2px 8px;
          border-radius: 6px;
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.3px;
          align-self: flex-start;
          margin-top: 2px;
          background: rgba(255, 255, 255, 0.06);
          color: var(--primary-text-color, #ffffff);
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
        }
        .status-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: currentColor;
        }
        .telemetry {
          font-size: 11px;
          color: var(--secondary-text-color, #94a3b8);
          font-weight: 500;
          margin-top: 2px;
        }
      `;
    } else {
      style.textContent = `
        :host {
          display: block;
          height: 100%;
          box-sizing: border-box;
        }
        ha-card {
          padding: 18px 20px;
          border-radius: ${radius} !important;
          overflow: hidden !important;
          color: white;
          background: linear-gradient(135deg, rgba(20, 27, 41, 0.88) 0%, rgba(15, 23, 42, 0.94) 100%) !important;
          backdrop-filter: blur(20px) !important;
          -webkit-backdrop-filter: blur(20px) !important;
          border: 1px solid rgba(255, 255, 255, 0.08) !important;
          box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
          transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
          cursor: pointer;
          display: flex;
          align-items: center;
          height: 100%;
          min-height: 96px;
          position: relative;
          box-sizing: border-box;
        }
        ha-card:hover {
          transform: translateY(-2px);
          border-color: rgba(255, 255, 255, 0.16) !important;
          box-shadow: 0 16px 40px -10px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
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
        .icon-wrap {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 58px;
          height: 58px;
          border-radius: 18px;
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.1);
          flex-shrink: 0;
          transition: transform 0.2s ease, background 0.3s ease, box-shadow 0.3s ease;
        }
        ha-card:hover .icon-wrap {
          transform: scale(1.08);
        }
        .icon-wrap ha-icon {
          --mdc-icon-size: 30px;
          color: inherit;
        }
        .info-container {
          display: flex;
          flex-direction: column;
          justify-content: center;
          flex-grow: 1;
          overflow: hidden;
          gap: 3px;
        }
        .sub-title {
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.8px;
          color: #94a3b8;
        }
        .name {
          font-size: 17px;
          font-weight: 800;
          margin: 0;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          color: #ffffff;
          letter-spacing: -0.3px;
        }
        .status-pill {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 3px 10px;
          border-radius: 9999px;
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.3px;
          text-transform: uppercase;
          align-self: flex-start;
          margin-top: 2px;
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
        }
        .status-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: currentColor;
          box-shadow: 0 0 6px currentColor;
        }
        .telemetry {
          font-size: 11px;
          color: #94a3b8;
          font-weight: 600;
          margin-top: 2px;
        }
        .heating-aura {
          background: radial-gradient(circle at 30% 50%, rgba(249, 115, 22, 0.28) 0%, rgba(239, 68, 68, 0.10) 50%, rgba(20, 27, 41, 0.92) 85%) !important;
          border-color: rgba(249, 115, 22, 0.35) !important;
        }
        .cooling-aura {
          background: radial-gradient(circle at 30% 50%, rgba(56, 189, 248, 0.28) 0%, rgba(14, 165, 233, 0.10) 50%, rgba(20, 27, 41, 0.92) 85%) !important;
          border-color: rgba(56, 189, 248, 0.35) !important;
        }
        .idle-aura {
          background: radial-gradient(circle at 30% 50%, rgba(245, 158, 11, 0.18) 0%, rgba(20, 27, 41, 0.92) 80%) !important;
          border-color: rgba(245, 158, 11, 0.25) !important;
        }
        .cool-idle-aura {
          background: radial-gradient(circle at 30% 50%, rgba(14, 165, 233, 0.15) 0%, rgba(20, 27, 41, 0.92) 80%) !important;
          border-color: rgba(56, 189, 248, 0.2) !important;
        }
      `;
    }

    card.id = 'status-card';
    card.innerHTML = `
      <div class="card-content">
        <div class="icon-wrap" id="master-icon-wrap">
          <ha-icon id="master-icon" icon="mdi:power"></ha-icon>
        </div>
        <div class="info-container">
          <div class="sub-title">Impianto Centrale</div>
          <div class="name" id="master-name">Riscaldamento</div>
          <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            <div class="status-pill" id="master-pill">
              <span class="status-dot"></span>
              <span id="master-state-text">Caricamento...</span>
            </div>
            <div class="telemetry" id="master-telemetry">Caldaia: OFF</div>
          </div>
        </div>
      </div>
    `;

    card.addEventListener('click', () => {
      this.toggleMaster();
    });

    this.shadowRoot.innerHTML = '';
    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._rendered = true;
  }

  toggleMaster() {
    if (!this._hass) return;
    const masterEntity = findMasterEntity(this._hass);
    if (!masterEntity) return;

    this._hass.callService("switch", "toggle", {
      entity_id: masterEntity
    });
  }

  updateCard() {
    if (!this._hass || !this._hass.states) return;
    if (!this._rendered) return;

    const masterEntity = findMasterEntity(this._hass);
    let isMasterOn = false;
    let boilerEntity = null;

    if (masterEntity) {
      const masterState = this._hass.states[masterEntity];
      if (masterState) {
        isMasterOn = masterState.state === "on";
      }
    }

    const masterMode = typeof getMasterHVACMode === 'function' ? getMasterHVACMode(this._hass) : 'heat';
    const isCoolMode = (masterMode === 'cool');

    boilerEntity = this._config.entity || this._config.boiler_entity;
    if (!boilerEntity && typeof findBoilerEntity === 'function') {
      boilerEntity = findBoilerEntity(this._hass);
    }

    let isBoilerActive = false;
    let boilerText = "OFF";

    if (boilerEntity) {
      const bState = this._hass.states[boilerEntity];
      if (bState) {
        if (boilerEntity.startsWith("switch.")) {
          isBoilerActive = bState.state === "on";
          boilerText = isBoilerActive ? "ON" : "OFF";
        } else if (boilerEntity.startsWith("sensor.")) {
          const val = parseFloat(bState.state);
          isBoilerActive = !isNaN(val) && val > 0;
          boilerText = `${bState.state} ${bState.attributes.unit_of_measurement || ''}`.trim();
        }
      }
    }

    // Central Heat Pump (PDC) detection
    let hpEntity = this._config.heat_pump_entity || this._config.hp_entity || null;
    const masterStateObj = (masterEntity && this._hass.states[masterEntity]) ? this._hass.states[masterEntity] : null;
    if (!hpEntity && masterStateObj && masterStateObj.attributes) {
      hpEntity = masterStateObj.attributes.heat_pump_ch_switch || masterStateObj.attributes.heat_pump_switch || masterStateObj.attributes.heat_pump_entity;
    }
    if (!hpEntity) {
      hpEntity = Object.keys(this._hass.states).find(k =>
        (k.startsWith("switch.") || k.startsWith("climate.")) &&
        (k.includes("heat_pump") || k.includes("pompa_di_calore") || k.includes("_pdc"))
      ) || null;
    }

    let isHpSwitchActive = false;
    if (hpEntity && this._hass.states[hpEntity]) {
      const hpSt = this._hass.states[hpEntity];
      isHpSwitchActive = (hpSt.state === "on" || hpSt.state === "heat" || hpSt.attributes?.hvac_action === "heating" || hpSt.attributes?.hvac_action === "cooling");
    }

    // Also inspect all multizone climate zones for active heating or cooling (including splits/PDC)
    let activeHeatingZones = 0;
    let activeCoolingZones = 0;
    let activeSplits = 0;
    let activePdcZones = 0;

    for (const key of Object.keys(this._hass.states)) {
      if (key.startsWith("climate.")) {
        const st = this._hass.states[key];
        const attrs = st ? st.attributes || {} : {};
        if (attrs.hybrid_zone || key.includes("multizone_thermostat_")) {
          const isZoneHeating = (attrs.hvac_action === "heating" || (st.state === "heat" && attrs.split_active));
          if (isZoneHeating) {
            activeHeatingZones++;
            if (attrs.pdc_active || attrs.hp_active || attrs.heat_pump_active || (attrs.active_heating_source === "electric" && !attrs.split_active)) {
              activePdcZones++;
            }
          }
          if (attrs.hvac_action === "cooling" || attrs.split_cooling || (st.state === "cool" && attrs.split_active)) {
            activeCoolingZones++;
            if (attrs.pdc_active || attrs.hp_active || attrs.heat_pump_active) {
              activePdcZones++;
            }
          }
          if (attrs.split_active) {
            activeSplits++;
          }
        }
      }
    }

    const isCentralHpActive = isHpSwitchActive || activePdcZones > 0 || (activeHeatingZones > 0 && !boilerEntity && Boolean(hpEntity));
    const hasCentralHp = Boolean(hpEntity || activePdcZones > 0);
    const hasBoiler = Boolean(boilerEntity);

    const isHeatingSystemActive = isBoilerActive || isCentralHpActive || activeHeatingZones > 0;
    const isCoolingSystemActive = activeCoolingZones > 0;

    const card = this.shadowRoot.getElementById('status-card');
    const iconWrap = this.shadowRoot.getElementById('master-icon-wrap');
    const icon = this.shadowRoot.getElementById('master-icon');
    const nameEl = this.shadowRoot.getElementById('master-name');
    const pill = this.shadowRoot.getElementById('master-pill');
    const stateText = this.shadowRoot.getElementById('master-state-text');
    const telemetry = this.shadowRoot.getElementById('master-telemetry');

    if (nameEl) {
      nameEl.textContent = isCoolMode
        ? (getTranslation(this._hass, 'cooling_active') ? 'Raffrescamento' : 'Raffrescamento')
        : 'Riscaldamento';
    }

    if (telemetry) {
      if (isCoolMode) {
        telemetry.textContent = activeCoolingZones > 0
          ? `Zone attive: ${activeCoolingZones}`
          : `Split / PDC: Standby`;
      } else if (activeSplits > 0 && !isBoilerActive && !isCentralHpActive) {
        telemetry.textContent = `Split Elettrico: ON`;
      } else if (activeSplits > 0 && isBoilerActive && !isCentralHpActive) {
        telemetry.textContent = `Caldaia: ON + Split`;
      } else if (activeSplits > 0 && isCentralHpActive && !isBoilerActive) {
        telemetry.textContent = `PDC: ON + Split`;
      } else if (activeSplits > 0 && isCentralHpActive && isBoilerActive) {
        telemetry.textContent = `Caldaia + PDC: ON + Split`;
      } else if (isCentralHpActive && isBoilerActive) {
        telemetry.textContent = `Caldaia + PDC: ON`;
      } else if (isCentralHpActive) {
        telemetry.textContent = `PDC: ON`;
      } else if (isBoilerActive) {
        telemetry.textContent = `Caldaia: ${boilerText}`;
      } else if (hasCentralHp && hasBoiler) {
        telemetry.textContent = `Caldaia / PDC: OFF`;
      } else if (hasCentralHp && !hasBoiler) {
        telemetry.textContent = `PDC: OFF`;
      } else if (activeHeatingZones > 0 && !isBoilerActive) {
        // Heating is active across zones without boiler switch: PDC or integrated central heating
        telemetry.textContent = hasCentralHp ? `PDC: ON` : `Caldaia / PDC: ON`;
      } else {
        telemetry.textContent = `Caldaia: ${boilerText}`;
      }
    }

    const isClassic = (this.getEffectiveStyle() === 'classic');

    if (!isMasterOn) {
      if (card && !isClassic) card.className = "";
      if (icon) {
        icon.icon = "mdi:power";
        icon.style.color = "var(--secondary-text-color, #94a3b8)";
      }
      if (iconWrap) {
        iconWrap.style.background = isClassic ? "var(--secondary-background-color, rgba(255, 255, 255, 0.05))" : "rgba(255, 255, 255, 0.04)";
        iconWrap.style.borderColor = "var(--divider-color, rgba(255, 255, 255, 0.1))";
        iconWrap.style.boxShadow = "none";
      }
      if (pill) {
        pill.style.background = isClassic ? "rgba(255, 255, 255, 0.06)" : "rgba(148, 163, 184, 0.12)";
        pill.style.color = "var(--secondary-text-color, #94a3b8)";
        pill.style.borderColor = "var(--divider-color, rgba(148, 163, 184, 0.25))";
      }
      if (stateText) stateText.textContent = "SPENTO";
    } else if (isCoolMode) {
      if (isCoolingSystemActive) {
        if (card && !isClassic) card.className = "cooling-aura";
        if (icon) {
          icon.icon = "mdi:snowflake";
          icon.style.color = "#38bdf8";
        }
        if (iconWrap) {
          iconWrap.style.background = "rgba(56, 189, 248, 0.22)";
          iconWrap.style.borderColor = "#38bdf8";
          iconWrap.style.boxShadow = isClassic ? "none" : "0 0 18px rgba(56, 189, 248, 0.45)";
        }
        if (pill) {
          pill.style.background = "rgba(56, 189, 248, 0.18)";
          pill.style.color = "#38bdf8";
          pill.style.borderColor = "rgba(56, 189, 248, 0.45)";
        }
        if (stateText) stateText.textContent = "RAFFRESCAMENTO ATTIVO";
      } else {
        if (card && !isClassic) card.className = "cool-idle-aura";
        if (icon) {
          icon.icon = "mdi:snowflake";
          icon.style.color = "#38bdf8";
        }
        if (iconWrap) {
          iconWrap.style.background = "rgba(56, 189, 248, 0.12)";
          iconWrap.style.borderColor = "rgba(56, 189, 248, 0.35)";
          iconWrap.style.boxShadow = isClassic ? "none" : "0 0 12px rgba(56, 189, 248, 0.2)";
        }
        if (pill) {
          pill.style.background = "rgba(56, 189, 248, 0.12)";
          pill.style.color = "#7dd3fc";
          pill.style.borderColor = "rgba(56, 189, 248, 0.3)";
        }
        if (stateText) stateText.textContent = "STANDBY (FREDDO)";
      }
    } else {
      if (isHeatingSystemActive) {
        if (card && !isClassic) card.className = "heating-aura";
        if (icon) {
          icon.icon = "mdi:fire";
          icon.style.color = "#f97316";
        }
        if (iconWrap) {
          iconWrap.style.background = "rgba(249, 115, 22, 0.22)";
          iconWrap.style.borderColor = "#f97316";
          iconWrap.style.boxShadow = isClassic ? "none" : "0 0 18px rgba(249, 115, 22, 0.45)";
        }
        if (pill) {
          pill.style.background = "rgba(249, 115, 22, 0.18)";
          pill.style.color = "#f97316";
          pill.style.borderColor = "rgba(249, 115, 22, 0.45)";
        }
        if (stateText) stateText.textContent = "RISCALDAMENTO ATTIVO";
      } else {
        if (card && !isClassic) card.className = "idle-aura";
        if (icon) {
          icon.icon = "mdi:power";
          icon.style.color = "#f59e0b";
        }
        if (iconWrap) {
          iconWrap.style.background = "rgba(245, 158, 11, 0.15)";
          iconWrap.style.borderColor = "#f59e0b";
          iconWrap.style.boxShadow = isClassic ? "none" : "0 0 15px rgba(245, 158, 11, 0.25)";
        }
        if (pill) {
          pill.style.background = "rgba(245, 158, 11, 0.15)";
          pill.style.color = "#f59e0b";
          pill.style.borderColor = "rgba(245, 158, 11, 0.35)";
        }
        if (stateText) stateText.textContent = "STANDBY (ACCESO)";
      }
    }
  }
}

/* ==================== MULTIZONE PRESET CARD ==================== */
class MultizoneThermostatPresetCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this._styleListener = () => {
      this.renderStructure();
      this.updateCard();
    };
    window.addEventListener('mz-style-changed', this._styleListener);
    this.renderStructure();
  }

  disconnectedCallback() {
    if (this._styleListener) {
      window.removeEventListener('mz-style-changed', this._styleListener);
    }
  }

  getEffectiveStyle() {
    return getActiveMzCardStyle();
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  setConfig(config) {
    this._config = Object.assign({}, config || {});
    this.renderStructure();
    this.updateCard();
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
    const radius = (this._config && this._config.border_radius) ? this._config.border_radius : '20px';
    const isClassic = (this.getEffectiveStyle() === 'classic');

    const styleContent = isClassic ? `
      :host {
        display: block;
        height: 100%;
        box-sizing: border-box;
      }
      ha-card {
        padding: 18px 16px;
        border-radius: ${radius} !important;
        overflow: hidden !important;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        gap: 12px;
        background: var(--ha-card-background, var(--card-background-color, #1c1c1e)) !important;
        border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, rgba(255, 255, 255, 0.12))) !important;
        box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0, 0, 0, 0.2)) !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
        box-sizing: border-box;
        height: 100%;
        min-height: 96px;
      }
      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: var(--secondary-text-color, #94a3b8);
      }
      .header-left {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .mode-switch-wrap {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
        user-select: none;
      }
      .mode-switch-label {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        transition: color 0.25s ease;
      }
      .mode-switch-wrap.heat .mode-switch-label { color: #fb923c; }
      .mode-switch-wrap.cool .mode-switch-label { color: #38bdf8; }
      .mode-switch-track {
        position: relative;
        width: 56px;
        height: 28px;
        border-radius: 9999px;
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.18);
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 6px;
        box-sizing: border-box;
        transition: all 0.25s ease;
      }
      .mode-switch-wrap.heat .mode-switch-track {
        border-color: rgba(249, 115, 22, 0.5);
        background: rgba(249, 115, 22, 0.15);
      }
      .mode-switch-wrap.cool .mode-switch-track {
        border-color: rgba(56, 189, 248, 0.5);
        background: rgba(56, 189, 248, 0.15);
      }
      .track-icon {
        --mdc-icon-size: 14px;
        z-index: 1;
        transition: opacity 0.25s ease, color 0.25s ease;
      }
      .track-icon.fire { color: #fb923c; opacity: 0.45; }
      .track-icon.snow { color: #38bdf8; opacity: 0.45; }
      .mode-switch-thumb {
        position: absolute;
        top: 2px;
        left: 2px;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.28s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.25s ease, box-shadow 0.25s ease;
        z-index: 2;
      }
      .mode-switch-thumb ha-icon {
        --mdc-icon-size: 14px;
        color: #ffffff;
      }
      .mode-switch-wrap.heat .mode-switch-thumb {
        transform: translateX(0px);
        background: linear-gradient(135deg, #f97316, #ea580c);
        box-shadow: 0 2px 8px rgba(249, 115, 22, 0.6);
      }
      .mode-switch-wrap.cool .mode-switch-thumb {
        transform: translateX(28px);
        background: linear-gradient(135deg, #38bdf8, #0284c7);
        box-shadow: 0 2px 8px rgba(56, 189, 248, 0.6);
      }
      .preset-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
        width: 100%;
        box-sizing: border-box;
        align-items: stretch;
      }
      .preset-btn {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 10px 4px;
        border-radius: 12px;
        background: var(--card-background-color, #202b38);
        border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.12));
        color: var(--secondary-text-color, #94a3b8);
        cursor: pointer;
        transition: all 0.2s ease;
        gap: 6px;
        min-height: 52px;
        box-sizing: border-box;
      }
      .preset-btn:hover {
        background: rgba(255, 255, 255, 0.08);
        color: var(--primary-text-color, white);
      }
      .preset-btn.active {
        background: var(--primary-color, #0284c7) !important;
        border-color: var(--primary-color, #0284c7) !important;
        color: #ffffff !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
      }
      .preset-btn ha-icon {
        --mdc-icon-size: 22px;
        color: inherit;
      }
      .preset-label {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.2px;
      }
      .priority-segmented {
        display: flex;
        align-items: center;
        gap: 3px;
        background: var(--card-background-color, #202b38);
        padding: 3px;
        border-radius: 9999px;
        border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.15));
        flex: 1;
        justify-content: space-between;
      }
      .priority-btn {
        background: transparent;
        border: none;
        color: var(--secondary-text-color, #94a3b8);
        font-size: 11px;
        font-weight: 600;
        padding: 4px 8px;
        border-radius: 9999px;
        cursor: pointer;
        transition: all 0.2s ease;
        text-align: center;
        flex: 1;
        white-space: nowrap;
      }
      .priority-btn:hover {
        color: var(--primary-text-color, #ffffff);
        background: rgba(255, 255, 255, 0.08);
      }
      .priority-btn.active {
        color: #ffffff;
        background: #f97316;
        box-shadow: 0 2px 6px rgba(249, 115, 22, 0.4);
      }
      .priority-btn.active.electric {
        background: #38bdf8;
        box-shadow: 0 2px 6px rgba(56, 189, 248, 0.4);
      }
      .priority-btn.active.combined {
        background: #fcd34d;
        color: #0f172a;
        box-shadow: 0 2px 6px rgba(252, 211, 77, 0.4);
      }
      .priority-btn.active.hybrid {
        background: #10b981;
        box-shadow: 0 2px 6px rgba(16, 185, 129, 0.4);
      }
      .summer-indicator {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(56, 189, 248, 0.12);
        border: 1px solid rgba(56, 189, 248, 0.25);
        color: #38bdf8;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.3px;
        height: 28px;
        box-sizing: border-box;
      }
    ` : `
      :host {
        display: block;
        height: 100%;
        box-sizing: border-box;
      }
      ha-card {
        padding: 18px 16px;
        border-radius: ${radius} !important;
        overflow: hidden !important;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        gap: 12px;
        background: linear-gradient(135deg, rgba(20, 27, 41, 0.88) 0%, rgba(15, 23, 42, 0.94) 100%) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
        box-sizing: border-box;
        height: 100%;
        min-height: 96px;
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
      }
      ha-card.cooling-mode {
        border-color: rgba(56, 189, 248, 0.25) !important;
        box-shadow: 0 10px 30px -10px rgba(14, 165, 233, 0.2), inset 0 1px 0 rgba(56, 189, 248, 0.15) !important;
      }
      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #94a3b8;
      }
      .header-left {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .mode-switch-wrap {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
        user-select: none;
        padding: 2px 4px;
        border-radius: 9999px;
        transition: transform 0.2s ease;
      }
      .mode-switch-wrap:hover {
        transform: scale(1.03);
      }
      .mode-switch-wrap:active {
        transform: scale(0.97);
      }
      .mode-switch-label {
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        transition: color 0.25s ease;
      }
      .mode-switch-wrap.heat .mode-switch-label {
        color: #fb923c;
        text-shadow: 0 0 10px rgba(249, 115, 22, 0.35);
      }
      .mode-switch-wrap.cool .mode-switch-label {
        color: #38bdf8;
        text-shadow: 0 0 10px rgba(56, 189, 248, 0.35);
      }
      .mode-switch-track {
        position: relative;
        width: 58px;
        height: 28px;
        border-radius: 9999px;
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.14);
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 7px;
        box-sizing: border-box;
        transition: all 0.3s ease;
        box-shadow: inset 0 2px 5px rgba(0, 0, 0, 0.5);
      }
      .mode-switch-wrap.heat .mode-switch-track {
        border-color: rgba(249, 115, 22, 0.45);
        background: linear-gradient(90deg, rgba(249, 115, 22, 0.2) 0%, rgba(15, 23, 42, 0.9) 100%);
        box-shadow: 0 0 12px rgba(249, 115, 22, 0.2), inset 0 1px 3px rgba(0, 0, 0, 0.5);
      }
      .mode-switch-wrap.cool .mode-switch-track {
        border-color: rgba(56, 189, 248, 0.45);
        background: linear-gradient(90deg, rgba(15, 23, 42, 0.9) 0%, rgba(56, 189, 248, 0.2) 100%);
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.2), inset 0 1px 3px rgba(0, 0, 0, 0.5);
      }
      .track-icon {
        --mdc-icon-size: 14px;
        z-index: 1;
        transition: opacity 0.25s ease, transform 0.25s ease;
      }
      .track-icon.fire { color: #fb923c; opacity: 0.45; }
      .track-icon.snow { color: #38bdf8; opacity: 0.45; }
      .mode-switch-thumb {
        position: absolute;
        top: 2px;
        left: 2px;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.25s ease, box-shadow 0.25s ease;
        z-index: 2;
      }
      .mode-switch-thumb ha-icon {
        --mdc-icon-size: 14px;
        color: #ffffff;
      }
      .mode-switch-wrap.heat .mode-switch-thumb {
        transform: translateX(0px);
        background: linear-gradient(135deg, #fb923c 0%, #ea580c 100%);
        box-shadow: 0 0 10px rgba(249, 115, 22, 0.8), 0 2px 4px rgba(0, 0, 0, 0.4);
      }
      .mode-switch-wrap.cool .mode-switch-thumb {
        transform: translateX(30px);
        background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.8), 0 2px 4px rgba(0, 0, 0, 0.4);
      }
      .preset-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
        width: 100%;
        box-sizing: border-box;
        align-items: stretch;
      }
      .preset-btn {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 10px 4px;
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: #94a3b8;
        cursor: pointer;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        gap: 6px;
        min-height: 52px;
        box-sizing: border-box;
      }
      .preset-btn:hover {
        background: rgba(255, 255, 255, 0.08);
        color: #ffffff;
        transform: translateY(-2px);
      }
      .preset-btn.active.manual {
        background: rgba(14, 165, 233, 0.2) !important;
        border-color: #38bdf8 !important;
        color: #38bdf8 !important;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.35) !important;
      }
      .preset-btn.active.eco {
        background: rgba(16, 185, 129, 0.2) !important;
        border-color: #10b981 !important;
        color: #34d399 !important;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.35) !important;
      }
      .preset-btn.active.comfort {
        background: rgba(245, 158, 11, 0.2) !important;
        border-color: #f59e0b !important;
        color: #fbbf24 !important;
        box-shadow: 0 0 15px rgba(245, 158, 11, 0.35) !important;
      }
      .cooling-mode .preset-btn.active.comfort {
        background: rgba(14, 165, 233, 0.2) !important;
        border-color: #38bdf8 !important;
        color: #38bdf8 !important;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.35) !important;
      }
      .preset-btn.active.sleep {
        background: rgba(99, 102, 241, 0.2) !important;
        border-color: #6366f1 !important;
        color: #818cf8 !important;
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.35) !important;
      }
      .preset-btn.active.away {
        background: rgba(239, 68, 68, 0.2) !important;
        border-color: #ef4444 !important;
        color: #f87171 !important;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.35) !important;
      }
      .cooling-mode .preset-btn.active.away {
        background: rgba(100, 116, 139, 0.2) !important;
        border-color: #94a3b8 !important;
        color: #cbd5e1 !important;
        box-shadow: 0 0 15px rgba(100, 116, 139, 0.35) !important;
      }
      .preset-btn ha-icon {
        --mdc-icon-size: 22px;
        color: inherit;
      }
      .preset-label {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.3px;
      }
      .priority-wrap {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 6px;
        padding-top: 8px;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
      }
      .priority-label {
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #94a3b8;
        white-space: nowrap;
      }
      
      .summer-indicator {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(56, 189, 248, 0.12);
        border: 1px solid rgba(56, 189, 248, 0.25);
        color: #38bdf8;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.3px;
        height: 28px;
        box-sizing: border-box;
      }

      .priority-segmented {
        display: flex;
        align-items: center;
        gap: 3px;
        background: rgba(15, 23, 42, 0.7);
        padding: 3px;
        border-radius: 9999px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        flex: 1;
        justify-content: space-between;
      }
      .priority-btn {
        background: transparent;
        border: none;
        color: #94a3b8;
        font-size: 10px;
        font-weight: 700;
        padding: 4px 8px;
        border-radius: 9999px;
        cursor: pointer;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        text-align: center;
        flex: 1;
        white-space: nowrap;
      }
      .priority-btn:hover {
        color: #ffffff;
        background: rgba(255, 255, 255, 0.08);
      }
      .priority-btn.active {
        color: #ffffff;
        background: #f97316;
        box-shadow: 0 2px 8px rgba(249, 115, 22, 0.4);
      }
      .priority-btn.active.electric {
        background: #38bdf8;
        box-shadow: 0 2px 8px rgba(56, 189, 248, 0.4);
      }
      .priority-btn.active.combined {
        background: #fcd34d;
        color: #0f172a;
        box-shadow: 0 2px 8px rgba(252, 211, 77, 0.4);
      }
      .priority-btn.active.hybrid {
        background: #10b981;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.4);
      }

    `;

    this.shadowRoot.innerHTML = `
      <style>${styleContent}</style>
      <ha-card id="preset-card-container">
        <div class="header">
          <div class="header-left">
            <div class="priority-segmented" id="priority-segmented">
              <button class="priority-btn" data-priority="auto" id="pbtn-auto" title="Automatica (Solare + Gas)">Auto</button>
              <button class="priority-btn" data-priority="hybrid" id="pbtn-hybrid" title="Ibrido (Split solo se surplus solare)">Ibrido</button>
              <button class="priority-btn" data-priority="combined" id="pbtn-combined" title="Combinato (Caldaia + Split insieme)">Combinato</button>
              <button class="priority-btn" data-priority="electric_only" id="pbtn-electric" title="Solo Elettrico (Blocca Caldaia)">Elettrico</button>
              <button class="priority-btn" data-priority="gas_only" id="pbtn-gas" title="Solo Gas (Split spenti in caldo)">Gas</button>
            </div>
            <div class="summer-indicator" id="summer-indicator" style="display: none;">
              <ha-icon icon="mdi:snowflake" style="--mdc-icon-size: 15px; color: #38bdf8;"></ha-icon>
              <span>Raffrescamento Elettrico</span>
            </div>
          </div>
          <div class="mode-switch-wrap heat" id="btn-mode-toggle" role="switch" aria-checked="false" title="Commuta Riscaldamento / Raffrescamento">
            <span class="mode-switch-label" id="mode-toggle-label">${getTranslation(this._hass, 'master_mode_heat') || 'Caldo'}</span>
            <div class="mode-switch-track">
              <ha-icon class="track-icon fire" icon="mdi:fire"></ha-icon>
              <ha-icon class="track-icon snow" icon="mdi:snowflake"></ha-icon>
              <div class="mode-switch-thumb">
                <ha-icon id="mode-toggle-icon" icon="mdi:fire"></ha-icon>
              </div>
            </div>
          </div>
        </div>
        <div class="preset-grid">
          <div class="preset-btn" data-preset="manual" id="btn-manual">
            <ha-icon icon="mdi:power"></ha-icon>
            <span class="preset-label">${getTranslation(this._hass, 'preset_manual') || 'Manuale'}</span>
          </div>
          <div class="preset-btn" data-preset="eco" id="btn-eco">
            <ha-icon icon="mdi:leaf"></ha-icon>
            <span class="preset-label">${getTranslation(this._hass, 'preset_eco') || 'Eco'}</span>
          </div>
          <div class="preset-btn" data-preset="comfort" id="btn-comfort">
            <ha-icon icon="mdi:sofa"></ha-icon>
            <span class="preset-label">${getTranslation(this._hass, 'preset_comfort') || 'Comfort'}</span>
          </div>
          <div class="preset-btn" data-preset="sleep" id="btn-sleep">
            <ha-icon icon="mdi:bed"></ha-icon>
            <span class="preset-label">${getTranslation(this._hass, 'preset_sleep') || 'Notte'}</span>
          </div>
          <div class="preset-btn" data-preset="away" id="btn-away">
            <ha-icon icon="mdi:car"></ha-icon>
            <span class="preset-label">${getTranslation(this._hass, 'preset_away') || 'Fuori Casa'}</span>
          </div>
        </div>
      </ha-card>
    `;

    const modeBtn = this.shadowRoot.querySelector('#btn-mode-toggle');
    if (modeBtn) {
      modeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleMasterMode();
      });
    }

    const buttons = this.shadowRoot.querySelectorAll('.preset-btn');
    buttons.forEach(btn => {
      btn.addEventListener('click', () => {
        const preset = btn.getAttribute('data-preset');
        this.selectPreset(preset);
      });
    });

    const pBtns = this.shadowRoot.querySelectorAll('.priority-btn');
    pBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const prio = btn.getAttribute('data-priority');
        this.selectHeatPriority(prio);
      });
    });
  }

  toggleMasterMode() {
    if (!this._hass) return;
    const currentMode = getMasterHVACMode(this._hass);
    const newMode = (currentMode === 'cool') ? 'heat' : 'cool';

    const modeEntity = findMasterOperationModeEntity(this._hass);
    if (modeEntity) {
      this._hass.callService("select", "select_option", {
        entity_id: modeEntity,
        option: newMode
      });
    } else {
      this._hass.callService("multizone_thermostat", "set_master_operation_mode", {
        operation_mode: newMode
      });
    }
  }

  selectHeatPriority(priority) {
    if (!this._hass) return;
    const priorityEntity = typeof findHeatSourcePriorityEntity === 'function' ? findHeatSourcePriorityEntity(this._hass) : null;
    if (!priorityEntity) return;

    this._hass.callService("select", "select_option", {
      entity_id: priorityEntity,
      option: priority
    });
  }

  selectPreset(preset) {
    if (!this._hass) return;
    const entityId = this.presetEntity;
    if (!entityId) return;

    let targetOption = preset;
    if (targetOption === 'none') targetOption = 'manual';

    this._hass.callService("select", "select_option", {
      entity_id: entityId,
      option: targetOption
    });
  }

  updateCard() {
    if (!this._hass || !this._hass.states) return;

    // 1. Update Master Mode Toggle (Heat vs Cool)
    const masterMode = getMasterHVACMode(this._hass);
    const isCool = (masterMode === 'cool');

    const card = this.shadowRoot.querySelector('#preset-card-container');
    const modeBtn = this.shadowRoot.querySelector('#btn-mode-toggle');
    const modeIcon = this.shadowRoot.querySelector('#mode-toggle-icon');
    const modeLabel = this.shadowRoot.querySelector('#mode-toggle-label');

    if (card) {
      if (isCool) {
        card.classList.add('cooling-mode');
      } else {
        card.classList.remove('cooling-mode');
      }
    }

    if (modeBtn) {
      modeBtn.setAttribute('aria-checked', isCool ? 'true' : 'false');
      if (isCool) {
        modeBtn.classList.remove('heat');
        modeBtn.classList.add('cool');
        if (modeIcon) {
          modeIcon.icon = "mdi:snowflake";
          modeIcon.style.color = "#38bdf8";
        }
        if (modeLabel) modeLabel.textContent = getTranslation(this._hass, 'master_mode_cool') || 'Freddo';
      } else {
        modeBtn.classList.remove('cool');
        modeBtn.classList.add('heat');
        if (modeIcon) {
          modeIcon.icon = "mdi:fire";
          modeIcon.style.color = "#fb923c";
        }
        if (modeLabel) modeLabel.textContent = getTranslation(this._hass, 'master_mode_heat') || 'Caldo';
      }
    }

    // 2. Update Heat Source Priority Selector in Header
    const prioritySegmented = this.shadowRoot.querySelector('#priority-segmented');
    const summerIndicator = this.shadowRoot.querySelector('#summer-indicator');
    if (prioritySegmented && summerIndicator) {
      if (isCool) {
        prioritySegmented.style.display = 'none';
        summerIndicator.style.display = 'inline-flex';
      } else {
        prioritySegmented.style.display = 'flex';
        summerIndicator.style.display = 'none';

        const priorityEntity = typeof findHeatSourcePriorityEntity === 'function' ? findHeatSourcePriorityEntity(this._hass) : null;
        let currentPriority = 'auto';
        if (priorityEntity && this._hass.states[priorityEntity]) {
          currentPriority = this._hass.states[priorityEntity].state;
        }

        const pBtns = this.shadowRoot.querySelectorAll('.priority-btn');
        pBtns.forEach(btn => {
          const prio = btn.getAttribute('data-priority');
          btn.classList.remove('active', 'electric', 'combined', 'hybrid');
          if (prio === currentPriority) {
            btn.classList.add('active');
            if (prio === 'electric_only') btn.classList.add('electric');
            else if (prio === 'combined') btn.classList.add('combined');
            else if (prio === 'hybrid') btn.classList.add('hybrid');
          }
        });
      }
    }

    // 2. Update Active Preset
    const entityId = this.presetEntity;
    if (!entityId) return;

    const stateObj = this._hass.states[entityId];
    if (!stateObj) return;

    const currentPreset = stateObj.state;
    const buttons = this.shadowRoot.querySelectorAll('.preset-btn');
    buttons.forEach(btn => {
      const preset = btn.getAttribute('data-preset');
      const isActive = (preset === currentPreset) || (preset === 'manual' && (currentPreset === 'none' || currentPreset === 'manual'));
      if (isActive) {
        btn.classList.add('active');
        btn.classList.add(preset);
      } else {
        btn.classList.remove('active');
        btn.classList.remove(preset);
      }
    });
  }
}

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

function closeMzStandaloneModal() {
  const existing = document.getElementById('mz-standalone-nav-overlay');
  if (existing) {
    existing.remove();
  }
}

function getGlobalHass() {
  if (window.hass) return window.hass;
  try {
    const ha = document.querySelector('home-assistant');
    if (ha && ha.hass) return ha.hass;
  } catch (e) {}
  try {
    const grid = document.querySelector('multizone-thermostat-responsive-grid') || document.querySelector('multizone-thermostat-nav-card');
    if (grid && grid._hass) return grid._hass;
  } catch (e) {}
  return null;
}

function openMzStandaloneModal(type, hass) {
  closeMzStandaloneModal();
  const effectiveHass = hass || getGlobalHass();

  const overlay = document.createElement('div');
  overlay.id = 'mz-standalone-nav-overlay';
  overlay.style.cssText = [
    'position: fixed',
    'inset: 0',
    'z-index: 999999',
    'background: rgba(10, 15, 29, 0.90)',
    'backdrop-filter: blur(12px)',
    '-webkit-backdrop-filter: blur(12px)',
    'overflow-y: auto',
    'padding: 24px 16px',
    'box-sizing: border-box',
    'display: flex',
    'flex-direction: column',
    'align-items: center'
  ].join(';');

  const wrapper = document.createElement('div');
  wrapper.style.cssText = 'width: 100%; max-width: 1200px; margin: 0 auto; box-sizing: border-box;';

  const topBar = document.createElement('div');
  topBar.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding: 0 4px;';

  const titleEl = document.createElement('div');
  titleEl.style.cssText = 'font-size: 1.2rem; font-weight: 700; color: #ffffff; display: flex; align-items: center; gap: 10px;';
  titleEl.innerHTML = type === 'scheduler'
    ? '<ha-icon icon="mdi:calendar-clock" style="color:#38bdf8;"></ha-icon> <span>Programmazione Fasce Orarie</span>'
    : '<ha-icon icon="mdi:chart-box-outline" style="color:#10b981;"></ha-icon> <span>Diagnostica & Impianto</span>';

  const closeBtn = document.createElement('button');
  closeBtn.innerHTML = '✕ Chiudi';
  closeBtn.style.cssText = [
    'background: rgba(255, 255, 255, 0.14)',
    'color: #ffffff',
    'border: 1px solid rgba(255, 255, 255, 0.25)',
    'border-radius: 10px',
    'padding: 8px 18px',
    'font-size: 0.95rem',
    'font-weight: 600',
    'cursor: pointer',
    'transition: background 0.2s ease'
  ].join(';');
  closeBtn.onmouseover = () => { closeBtn.style.background = 'rgba(255, 255, 255, 0.25)'; };
  closeBtn.onmouseout = () => { closeBtn.style.background = 'rgba(255, 255, 255, 0.14)'; };

  const dismissModal = () => {
    closeMzStandaloneModal();
    window.removeEventListener('keydown', keyHandler);
  };

  const keyHandler = (e) => {
    if (e.key === 'Escape') dismissModal();
  };
  window.addEventListener('keydown', keyHandler);
  closeBtn.addEventListener('click', dismissModal);

  topBar.appendChild(titleEl);
  topBar.appendChild(closeBtn);
  wrapper.appendChild(topBar);

  let innerCard;
  if (type === 'scheduler') {
    innerCard = document.createElement('multizone-thermostat-scheduler-card');
  } else {
    innerCard = document.createElement('multizone-thermostat-plant-card');
  }
  if (typeof innerCard.setConfig === 'function') {
    innerCard.setConfig({ border_radius: '16px' });
  }
  if (effectiveHass) {
    innerCard.hass = effectiveHass;
  }
  wrapper.appendChild(innerCard);
  overlay.appendChild(wrapper);

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) dismissModal();
  });

  document.body.appendChild(overlay);
}

function findLovelaceConfig(el) {
  let node = el;
  while (node) {
    if (node.lovelace && node.lovelace.config && Array.isArray(node.lovelace.config.views)) {
      return node.lovelace.config;
    }
    if (node.config && Array.isArray(node.config.views)) {
      return node.config;
    }
    node = node.parentNode || node.host || null;
  }
  try {
    const ha = document.querySelector('home-assistant');
    const main = ha && ha.shadowRoot && ha.shadowRoot.querySelector('home-assistant-main');
    const resolver = main && main.shadowRoot && main.shadowRoot.querySelector('partial-panel-resolver, ha-panel-lovelace');
    const panel = resolver && (resolver.tagName === 'HA-PANEL-LOVELACE' ? resolver : (resolver.shadowRoot && resolver.shadowRoot.querySelector('ha-panel-lovelace')));
    if (panel && panel.lovelace && panel.lovelace.config && Array.isArray(panel.lovelace.config.views)) {
      return panel.lovelace.config;
    }
  } catch (e) {}
  return null;
}

function haNavigate(node, path) {
  if (!path) return;
  // 1. Dispatch hass-action (official Lovelace action handler)
  try {
    const actionEv = new CustomEvent('hass-action', {
      detail: {
        config: {
          tap_action: {
            action: 'navigate',
            navigation_path: path
          }
        },
        action: 'tap'
      },
      bubbles: true,
      composed: true
    });
    (node || document.body).dispatchEvent(actionEv);
  } catch (e) {}

  // 2. Dispatch hass-navigate (Lovelace router event)
  try {
    const navEv = new CustomEvent('hass-navigate', {
      detail: { path: path },
      bubbles: true,
      composed: true
    });
    (node || document.body).dispatchEvent(navEv);
  } catch (e) {}

  // 3. Low-level history API and location-changed event (standard HA navigate.ts)
  try {
    if (window.location.pathname !== path) {
      window.history.pushState(null, '', path);
      const locEv = new CustomEvent('location-changed', {
        detail: { replace: false },
        bubbles: true,
        composed: true
      });
      (node || window).dispatchEvent(locEv);
      window.dispatchEvent(new CustomEvent('location-changed'));
    }
  } catch (e) {}
}

function navigateOrFallbackModal(hostEl, targetPath, onFallback) {
  let normalizedPath = targetPath || 'programmazione';
  if (normalizedPath === 'schedulatore') normalizedPath = 'programmazione';

  // 1. Resolve dashboard base and target fullPath
  const parts = window.location.pathname.split('/').filter(Boolean);
  const dashboardBase = parts.length > 0 ? `/${parts[0]}` : '/lovelace';
  let fullPath = normalizedPath.startsWith('/') 
    ? normalizedPath 
    : `${dashboardBase}/${normalizedPath}`;

  const llConfig = findLovelaceConfig(hostEl);
  let hasMatchingView = false;

  if (llConfig && Array.isArray(llConfig.views)) {
    const matchedView = llConfig.views.find((v, idx) => {
      const p = (v.path !== undefined && v.path !== null && v.path !== '') ? String(v.path) : String(idx);
      if (p.toLowerCase() === normalizedPath.toLowerCase() || (normalizedPath === 'programmazione' && p.toLowerCase() === 'schedulatore')) {
        fullPath = `${dashboardBase}/${p}`;
        return true;
      }
      const stratType = (v.strategy && v.strategy.type) ? String(v.strategy.type) : '';
      if ((normalizedPath === 'programmazione' || normalizedPath === 'schedulatore') && stratType.includes('multizone-thermostat-scheduler')) {
        fullPath = `${dashboardBase}/${p}`;
        return true;
      }
      if (normalizedPath === 'diagnostica' && stratType.includes('multizone-thermostat-diagnostics')) {
        fullPath = `${dashboardBase}/${p}`;
        return true;
      }
      return false;
    });

    if (matchedView) {
      hasMatchingView = true;
    } else {
      // Lovelace config exists but does not contain target view: open fallback modal immediately
      if (typeof onFallback === 'function') {
        onFallback();
        return;
      }
    }
  }

  // 2. Perform navigation
  const initialPath = window.location.pathname;
  haNavigate(hostEl, fullPath);

  // 3. Fallback verification: if path hasn't changed after 150ms and fallback is provided
  setTimeout(() => {
    if (window.location.pathname === initialPath && window.location.pathname !== fullPath) {
      if (typeof onFallback === 'function') {
        onFallback();
      }
    }
  }, 150);
}

function navigateToLovelaceView(viewSlug) {
  const type = (viewSlug === 'programmazione' || viewSlug === 'schedulatore') ? 'scheduler' : 'diagnostics';
  navigateOrFallbackModal(document.body, viewSlug, () => openMzStandaloneModal(type, null));
}

/* ==================== SUMMARY NAVIGATION CARDS ==================== */
class MultizoneThermostatScheduleSummaryCard extends HTMLElement {
  getCardSize() { return 3; }
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback() {
    this._styleListener = () => {
      this.renderStructure();
      this.updateCard();
    };
    window.addEventListener('mz-style-changed', this._styleListener);
  }

  disconnectedCallback() {
    if (this._styleListener) {
      window.removeEventListener('mz-style-changed', this._styleListener);
    }
  }

  getEffectiveStyle() {
    return getActiveMzCardStyle();
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  setConfig(config) {
    this._config = config || {};
    if (!this._rendered) this.renderStructure();
    this.updateCard();
  }

  renderStructure() {
    const radius = (this._config && this._config.border_radius) ? this._config.border_radius : '20px';
    const isClassic = (this.getEffectiveStyle() === 'classic');

    const styleContent = isClassic ? `
      :host {
        display: block;
        height: 100%;
        box-sizing: border-box;
      }
      ha-card {
        padding: 14px 10px;
        border-radius: ${radius} !important;
        overflow: hidden !important;
        background: var(--ha-card-background, var(--card-background-color, #1c1c1e)) !important;
        border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, rgba(255, 255, 255, 0.12))) !important;
        box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0, 0, 0, 0.2)) !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
        color: var(--primary-text-color, white);
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        min-height: 96px;
        cursor: pointer;
        transition: all 0.2s ease;
        box-sizing: border-box;
      }
      ha-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
      }
      .badge-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        gap: 4px;
        width: 100%;
      }
      .icon-box {
        width: 36px;
        height: 36px;
        border-radius: 10px;
        background: var(--secondary-background-color, rgba(255, 255, 255, 0.06));
        border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.12));
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--primary-color, #0284c7);
      }
      .icon-box ha-icon { --mdc-icon-size: 20px; }
      .badge-title {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.2px;
        color: var(--primary-text-color, #ffffff);
      }
      .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 6px;
        border-radius: 6px;
        font-size: 9px;
        font-weight: 600;
        background: rgba(255, 255, 255, 0.06);
        color: var(--secondary-text-color, #94a3b8);
        border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
      }
      .badge-dot {
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background: currentColor;
      }
    ` : `
      :host {
        display: block;
        height: 100%;
        box-sizing: border-box;
      }
      ha-card {
        padding: 14px 10px;
        border-radius: ${radius} !important;
        overflow: hidden !important;
        background: linear-gradient(135deg, rgba(20, 27, 41, 0.88) 0%, rgba(15, 23, 42, 0.94) 100%) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        min-height: 96px;
        cursor: pointer;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        box-sizing: border-box;
      }
      ha-card:hover {
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.16) !important;
        box-shadow: 0 16px 40px -10px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
      }
      .badge-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        gap: 5px;
        width: 100%;
      }
      .icon-box {
        width: 38px;
        height: 38px;
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.1);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #94a3b8;
        transition: transform 0.2s ease;
      }
      ha-card:hover .icon-box {
        transform: scale(1.08);
      }
      .icon-box ha-icon { --mdc-icon-size: 20px; }
      .badge-title {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.2px;
        color: #ffffff;
      }
      .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 7px;
        border-radius: 9999px;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 0.2px;
        text-transform: uppercase;
        background: rgba(148, 163, 184, 0.12);
        color: #94a3b8;
        border: 1px solid rgba(148, 163, 184, 0.25);
      }
      .badge-dot {
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background: currentColor;
        box-shadow: 0 0 4px currentColor;
      }
    `;

    this.shadowRoot.innerHTML = `
      <style>${styleContent}</style>
      <ha-card id="card">
        <div class="badge-content">
          <div class="icon-box" id="icon-box">
            <ha-icon icon="mdi:calendar-clock"></ha-icon>
          </div>
          <div class="badge-title">Programmazione</div>
          <div class="badge-pill" id="pill">
            <span class="badge-dot" id="dot"></span>
            <span id="label">In Pausa</span>
          </div>
        </div>
      </ha-card>
    `;

    const card = this.shadowRoot.getElementById('card');
    const handleSchedClick = (e) => {
      if (e) e.stopPropagation();
      const targetPath = (this._config && this._config.navigation_path) ? this._config.navigation_path : 'programmazione';
      navigateOrFallbackModal(this, targetPath, () => openMzStandaloneModal('scheduler', this._hass));
    };

    if (card) {
      card.addEventListener('click', handleSchedClick);
    }
    this.style.cursor = 'pointer';
    this.onclick = handleSchedClick;

    this._rendered = true;
  }

  updateCard() {
    if (!this._hass || !this._rendered) return;
    const pill = this.shadowRoot.getElementById('pill');
    const label = this.shadowRoot.getElementById('label');
    const dot = this.shadowRoot.getElementById('dot');

    const profileEntityId = Object.keys(this._hass.states).find(k =>
      k.startsWith('select.') && (
        k.includes('schedule_profile') ||
        k.includes('active_profile') ||
        k.includes('profilo_programmazione')
      )
    );
    const profileState = profileEntityId ? this._hass.states[profileEntityId] : null;
    const activeProfile = profileState ? profileState.state : 'standard';

    if (activeProfile && activeProfile !== 'none') {
      const name = activeProfile.charAt(0).toUpperCase() + activeProfile.slice(1);
      label.textContent = name;
      pill.style.background = 'rgba(56, 189, 248, 0.15)';
      pill.style.color = '#38bdf8';
      pill.style.borderColor = 'rgba(56, 189, 248, 0.35)';
      if (dot) dot.style.background = '#38bdf8';
    } else {
      label.textContent = 'In Pausa';
      pill.style.background = 'rgba(148, 163, 184, 0.12)';
      pill.style.color = '#94a3b8';
      pill.style.borderColor = 'rgba(148, 163, 184, 0.25)';
      if (dot) dot.style.background = '#94a3b8';
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

  connectedCallback() {
    this._styleListener = () => {
      this.renderStructure();
      this.updateCard();
    };
    window.addEventListener('mz-style-changed', this._styleListener);
  }

  disconnectedCallback() {
    if (this._styleListener) {
      window.removeEventListener('mz-style-changed', this._styleListener);
    }
  }

  getEffectiveStyle() {
    return getActiveMzCardStyle();
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  setConfig(config) {
    this._config = config || {};
    if (!this._rendered) this.renderStructure();
    this.updateCard();
  }

  renderStructure() {
    const radius = (this._config && this._config.border_radius) ? this._config.border_radius : '20px';
    const isClassic = (this.getEffectiveStyle() === 'classic');

    const styleContent = isClassic ? `
      :host {
        display: block;
        height: 100%;
        box-sizing: border-box;
      }
      ha-card {
        padding: 14px 10px;
        border-radius: ${radius} !important;
        overflow: hidden !important;
        background: var(--ha-card-background, var(--card-background-color, #1c1c1e)) !important;
        border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, rgba(255, 255, 255, 0.12))) !important;
        box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0, 0, 0, 0.2)) !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
        color: var(--primary-text-color, white);
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        min-height: 96px;
        cursor: pointer;
        transition: all 0.2s ease;
        box-sizing: border-box;
      }
      ha-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
      }
      .badge-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        gap: 4px;
        width: 100%;
      }
      .icon-box {
        width: 36px;
        height: 36px;
        border-radius: 10px;
        background: var(--secondary-background-color, rgba(255, 255, 255, 0.06));
        border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.12));
        display: flex;
        align-items: center;
        justify-content: center;
        color: #10b981;
      }
      .icon-box ha-icon { --mdc-icon-size: 20px; }
      .badge-title {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.2px;
        color: var(--primary-text-color, #ffffff);
      }
      .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 6px;
        border-radius: 6px;
        font-size: 9px;
        font-weight: 600;
        background: rgba(16, 185, 129, 0.12);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.25);
      }
      .badge-dot {
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background: currentColor;
      }
    ` : `
      :host {
        display: block;
        height: 100%;
        box-sizing: border-box;
      }
      ha-card {
        padding: 14px 10px;
        border-radius: ${radius} !important;
        overflow: hidden !important;
        background: linear-gradient(135deg, rgba(20, 27, 41, 0.88) 0%, rgba(15, 23, 42, 0.94) 100%) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        min-height: 96px;
        cursor: pointer;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        box-sizing: border-box;
      }
      ha-card:hover {
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.16) !important;
        box-shadow: 0 16px 40px -10px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
      }
      .badge-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        gap: 5px;
        width: 100%;
      }
      .icon-box {
        width: 38px;
        height: 38px;
        border-radius: 12px;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.25);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #10b981;
        transition: transform 0.2s ease;
      }
      ha-card:hover .icon-box {
        transform: scale(1.08);
      }
      .icon-box ha-icon { --mdc-icon-size: 20px; }
      .badge-title {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.2px;
        color: #ffffff;
      }
      .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 7px;
        border-radius: 9999px;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 0.2px;
        text-transform: uppercase;
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.35);
      }
      .badge-dot {
        width: 4px;
        height: 4px;
        border-radius: 50%;
        background: currentColor;
        box-shadow: 0 0 4px currentColor;
      }
    `;

    this.shadowRoot.innerHTML = `
      <style>${styleContent}</style>
      <ha-card id="card">
        <div class="badge-content">
          <div class="icon-box" id="icon-box">
            <ha-icon icon="mdi:shield-check"></ha-icon>
          </div>
          <div class="badge-title">Diagnostica</div>
          <div class="badge-pill" id="pill">
            <span class="badge-dot" id="dot"></span>
            <span id="label">Sistema OK</span>
          </div>
        </div>
      </ha-card>
    `;

    const card = this.shadowRoot.getElementById('card');
    const handleHealthClick = (e) => {
      if (e) e.stopPropagation();
      const targetPath = (this._config && this._config.navigation_path) ? this._config.navigation_path : 'diagnostica';
      navigateOrFallbackModal(this, targetPath, () => openMzStandaloneModal('diagnostics', this._hass));
    };

    if (card) {
      card.addEventListener('click', handleHealthClick);
    }
    this.style.cursor = 'pointer';
    this.onclick = handleHealthClick;

    this._rendered = true;
  }

  updateCard() {
    if (!this._hass || !this._rendered) return;
    const pill = this.shadowRoot.getElementById('pill');
    const label = this.shadowRoot.getElementById('label');
    const dot = this.shadowRoot.getElementById('dot');
    const iconBox = this.shadowRoot.getElementById('icon-box');

    const errSensors = Object.keys(this._hass.states).filter(k =>
      k.startsWith('binary_sensor.') && (
        k.includes('plant_anomaly') ||
        k.includes('anomaly_detected') ||
        k.includes('anomalia_impianto')
      )
    );
    let hasAnomaly = false;
    for (const sid of errSensors) {
      if (this._hass.states[sid]?.state === 'on') {
        hasAnomaly = true;
        break;
      }
    }

    if (hasAnomaly) {
      label.textContent = 'Allarme';
      pill.style.background = 'rgba(239, 68, 68, 0.18)';
      pill.style.color = '#ef4444';
      pill.style.borderColor = 'rgba(239, 68, 68, 0.4)';
      if (dot) dot.style.background = '#ef4444';
      if (iconBox) iconBox.style.color = '#ef4444';
    } else {
      label.textContent = 'Sistema Ok';
      pill.style.background = 'rgba(16, 185, 129, 0.15)';
      pill.style.color = '#10b981';
      pill.style.borderColor = 'rgba(16, 185, 129, 0.35)';
      if (dot) dot.style.background = '#10b981';
      if (iconBox) iconBox.style.color = '#10b981';
    }
  }
}

if (!customElements.get("multizone-thermostat-health-summary-card")) {
  customElements.define("multizone-thermostat-health-summary-card", MultizoneThermostatHealthSummaryCard);
}

class MultizoneThermostatNavCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._schedCard = null;
    this._healthCard = null;
    this._rendered = false;
  }

  setConfig(config) {
    this._config = Object.assign({}, config || {});
    if (!this._rendered) {
      this.render();
    }
  }

  getCardSize() {
    return 3;
  }

  set hass(hass) {
    this._hass = hass;
    if (this._schedCard) {
      this._schedCard.hass = hass;
    }
    if (this._healthCard) {
      this._healthCard.hass = hass;
    }
  }

  render() {
    const radius = (this._config && this._config.border_radius) ? this._config.border_radius : '20px';
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          height: 100%;
          box-sizing: border-box;
        }
        .nav-container {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          height: 100%;
          box-sizing: border-box;
        }
        .nav-container > * {
          min-width: 0;
          height: 100%;
        }
      </style>
      <div class="nav-container" id="nav-container"></div>
    `;

    const container = this.shadowRoot.getElementById('nav-container');

    this._schedCard = document.createElement('multizone-thermostat-schedule-summary-card');
    if (typeof this._schedCard.setConfig === 'function') {
      this._schedCard.setConfig({
        border_radius: radius,
        navigation_path: (this._config && (this._config.scheduler_path || this._config.navigation_path)) || 'programmazione'
      });
    }
    if (this._hass) {
      this._schedCard.hass = this._hass;
    }
    this._schedCard.style.cursor = 'pointer';
    this._schedCard.addEventListener('click', (e) => {
      e.stopPropagation();
      navigateOrFallbackModal(this._schedCard, 'programmazione', () => openMzStandaloneModal('scheduler', this._hass));
    });

    this._healthCard = document.createElement('multizone-thermostat-health-summary-card');
    if (typeof this._healthCard.setConfig === 'function') {
      this._healthCard.setConfig({
        border_radius: radius,
        navigation_path: (this._config && (this._config.diagnostics_path || this._config.navigation_path)) || 'diagnostica'
      });
    }
    if (this._hass) {
      this._healthCard.hass = this._hass;
    }
    this._healthCard.style.cursor = 'pointer';
    this._healthCard.addEventListener('click', (e) => {
      e.stopPropagation();
      navigateOrFallbackModal(this._healthCard, 'diagnostica', () => openMzStandaloneModal('diagnostics', this._hass));
    });

    container.appendChild(this._schedCard);
    container.appendChild(this._healthCard);
    this._rendered = true;
  }
}

if (!customElements.get("multizone-thermostat-nav-card")) {
  customElements.define("multizone-thermostat-nav-card", MultizoneThermostatNavCard);
}


/* ==================== RESPONSIVE GRID CARD ==================== */
class MultizoneThermostatResponsiveGrid extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._cardElements = [];
    this._rendered = false;
  }

  setConfig(config) {
    this._config = Object.assign({}, config || {});
    this.render();
  }

  getCardSize() {
    return 6;
  }

  set hass(hass) {
    this._hass = hass;
    const switcher = this.shadowRoot.querySelector('multizone-thermostat-style-switcher');
    if (switcher) {
      try { switcher.hass = hass; } catch (e) {}
    }
    if (this._cardElements && this._cardElements.length > 0) {
      for (const el of this._cardElements) {
        try {
          el.hass = hass;
        } catch (e) {}
      }
    }
  }

  async render() {
    const columns = parseInt(this._config.columns, 10) || 3;
    const cards = this._config.cards || [];

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          width: 100%;
          box-sizing: border-box;
          position: relative;
        }
        .responsive-grid {
          display: grid;
          grid-template-columns: repeat(${columns}, minmax(0, 1fr));
          gap: 12px;
          width: 100%;
          box-sizing: border-box;
          margin-bottom: 12px;
        }
        @media (max-width: 1024px) and (min-width: 769px) {
          .responsive-grid {
            grid-template-columns: repeat(${Math.min(columns, 2)}, minmax(0, 1fr));
          }
        }
        @media (max-width: 768px) {
          .responsive-grid {
            grid-template-columns: 1fr !important;
            gap: 12px;
          }
        }
      </style>
      <div class="responsive-grid" id="grid"></div>
      <multizone-thermostat-style-switcher></multizone-thermostat-style-switcher>
    `;

    const grid = this.shadowRoot.getElementById('grid');
    this._cardElements = [];

    let helpers = window.cardHelpers;
    if (!helpers && window.loadCardHelpers) {
      try {
        helpers = await window.loadCardHelpers();
        window.cardHelpers = helpers;
      } catch (e) {
        console.warn("Could not load Lovelace card helpers:", e);
      }
    }

    for (const cardConfig of cards) {
      if (!cardConfig) continue;
      let cardEl = null;
      if (helpers && typeof helpers.createCardElement === 'function') {
        try {
          cardEl = helpers.createCardElement(cardConfig);
        } catch (e) {
          console.warn("Error creating card element with helpers:", e);
        }
      }
      if (!cardEl) {
        const type = cardConfig.type || '';
        const tag = type.startsWith('custom:') ? type.replace('custom:', '') : `hui-${type}-card`;
        cardEl = document.createElement(tag);
        if (typeof cardEl.setConfig === 'function') {
          try {
            cardEl.setConfig(cardConfig);
          } catch (e) {}
        }
      }
      if (this._hass) {
        try {
          cardEl.hass = this._hass;
        } catch (e) {}
      }
      this._cardElements.push(cardEl);
      grid.appendChild(cardEl);
    }

    this._rendered = true;
  }
}

if (!customElements.get("multizone-thermostat-responsive-grid")) {
  customElements.define("multizone-thermostat-responsive-grid", MultizoneThermostatResponsiveGrid);
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
      .status-neutral {
        background: rgba(148, 163, 184, 0.15);
        color: #94a3b8;
        border: 1px solid rgba(148, 163, 184, 0.3);
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
      @media (max-width: 640px) {
        ha-card {
          padding: 16px 14px;
        }
        .header-row {
          flex-direction: column;
          align-items: flex-start;
          gap: 12px;
        }
        .title-text {
          font-size: 18px;
        }
        .kpi-grid {
          grid-template-columns: 1fr;
          gap: 10px;
        }
        .ot-grid {
          padding: 10px 12px !important;
        }
        .ot-grid > div:last-child {
          grid-template-columns: repeat(2, 1fr) !important;
          gap: 8px !important;
        }
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

      const isHealthUnavailable = !healthState || ['unavailable', 'unknown'].includes(healthState.state);
      const statusVal = isHealthUnavailable ? null : healthState.state;
      const isCritical = statusVal === "Critical" || statusVal === "Critico";
      const isWarning = statusVal === "Warning" || statusVal === "Attenzione";
      const isOptimal = statusVal === "Optimal" || statusVal === "Ottimale";
      if (healthBadge && healthText) {
        if (isHealthUnavailable) {
          healthText.innerText = "--";
          healthBadge.className = "status-badge status-neutral";
        } else if (isCritical) {
          healthText.innerText = t('critical');
          healthBadge.className = "status-badge status-critical";
        } else if (isWarning) {
          healthText.innerText = t('warning');
          healthBadge.className = "status-badge status-warning";
        } else if (isOptimal) {
          healthText.innerText = t('optimal');
          healthBadge.className = "status-badge status-optimal";
        } else {
          healthText.innerText = statusVal;
          healthBadge.className = "status-badge status-neutral";
        }
      }

      if (cyclesVal) {
        if (cyclesState && !['unavailable', 'unknown'].includes(cyclesState.state)) {
          const c = parseFloat(cyclesState.state);
          if (!isNaN(c)) {
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
          } else {
            cyclesVal.innerText = "--";
            if (cyclesSub) {
              cyclesSub.innerText = "--";
              cyclesSub.style.color = "#94a3b8";
            }
          }
        } else {
          cyclesVal.innerText = "--";
          if (cyclesSub) {
            cyclesSub.innerText = "--";
            cyclesSub.style.color = "#94a3b8";
          }
        }
      }

      if (runtimeVal) {
        if (runtimeState && !['unavailable', 'unknown'].includes(runtimeState.state)) {
          const r = parseFloat(runtimeState.state);
          runtimeVal.innerText = !isNaN(r) ? r.toFixed(1) : "--";
        } else {
          runtimeVal.innerText = "--";
        }
      }

      if (alertBox && alertDesc) {
        const hasAnomaly = anomalyState ? anomalyState.state === "on" : (!isHealthUnavailable && !isOptimal);
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
      @media (max-width: 640px) {
        ha-card {
          padding: 16px 14px;
        }
        .top-row {
          flex-wrap: wrap;
          gap: 10px;
        }
        .zone-name {
          font-size: 17px;
          flex-wrap: wrap;
        }
        .stats-grid {
          grid-template-columns: 1fr;
          gap: 10px;
        }
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
      .pid-panel {
        margin-top: 10px;
        margin-bottom: 10px;
        background: rgba(15, 23, 42, 0.38);
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 12px;
        padding: 10px 12px;
      }
      .pid-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        gap: 8px;
      }
      .pid-title-row {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.78em;
        font-weight: 600;
        color: var(--secondary-text-color, #94a3b8);
      }
      .pid-state-pill {
        font-size: 0.78em;
        padding: 2px 7px;
        border-radius: 999px;
        background: rgba(148, 163, 184, 0.16);
        color: #cbd5e1;
      }
      .pid-reset-btn {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 0.75em;
        font-weight: 600;
        padding: 4px 8px;
        border-radius: 8px;
        border: 1px solid rgba(239, 68, 68, 0.35);
        background: rgba(239, 68, 68, 0.12);
        color: #fca5a5;
        cursor: pointer;
        transition: background 0.15s ease;
      }
      .pid-reset-btn:hover {
        background: rgba(239, 68, 68, 0.24);
      }
      .pid-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
      }
      .pid-box {
        background: rgba(148, 163, 184, 0.14);
        border: 1px solid rgba(148, 163, 184, 0.28);
        border-radius: 10px;
        padding: 8px 6px;
        text-align: center;
        cursor: pointer;
        color: #94a3b8;
        transition: border-color 0.15s ease, transform 0.12s ease;
      }
      .pid-box:hover {
        border-color: rgba(148, 163, 184, 0.55);
        transform: translateY(-1px);
      }
      .pid-box.manual-override {
        background: rgba(245, 158, 11, 0.14);
        border-color: rgba(245, 158, 11, 0.55);
        color: #fde68a;
      }
      .pid-box-top {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 4px;
        font-size: 0.72em;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        margin-bottom: 3px;
      }
      .pid-box-val {
        font-size: 0.95em;
        font-weight: 700;
        font-variant-numeric: tabular-nums;
      }
      .pid-modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(2, 6, 23, 0.72);
        backdrop-filter: blur(4px);
        display: none;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        padding: 16px;
      }
      .pid-modal-backdrop.open {
        display: flex;
      }
      .pid-modal {
        width: 100%;
        max-width: 360px;
        background: var(--card-background-color, #1e293b);
        color: var(--primary-text-color, #f1f5f9);
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 16px;
        padding: 18px;
        box-shadow: 0 20px 45px rgba(0, 0, 0, 0.45);
      }
      .pid-modal-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.02em;
        font-weight: 700;
        margin-bottom: 10px;
        color: #fbbf24;
      }
      .pid-modal-warn {
        font-size: 0.84em;
        line-height: 1.45;
        color: var(--secondary-text-color, #cbd5e1);
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.28);
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 12px;
      }
      .pid-modal-input-wrap {
        margin-bottom: 14px;
      }
      .pid-modal-input-wrap label {
        display: block;
        font-size: 0.8em;
        color: var(--secondary-text-color, #94a3b8);
        margin-bottom: 4px;
      }
      .pid-modal-input-wrap input {
        width: 100%;
        box-sizing: border-box;
        padding: 8px 10px;
        border-radius: 8px;
        border: 1px solid rgba(148, 163, 184, 0.35);
        background: rgba(15, 23, 42, 0.55);
        color: var(--primary-text-color, #f8fafc);
        font-size: 1em;
        font-weight: 600;
      }
      .pid-modal-actions {
        display: flex;
        justify-content: flex-end;
        flex-wrap: wrap;
        gap: 8px;
      }
      .pid-btn {
        border: none;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 0.82em;
        font-weight: 600;
        cursor: pointer;
      }
      .pid-btn-cancel {
        background: rgba(148, 163, 184, 0.18);
        color: #cbd5e1;
      }
      .pid-btn-restore {
        background: rgba(56, 189, 248, 0.18);
        color: #7dd3fc;
      }
      .pid-btn-save {
        background: #f59e0b;
        color: #0f172a;
      }
      .pid-btn-danger {
        background: #ef4444;
        color: #ffffff;
      }
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

      <div class="pid-panel">
        <div class="pid-header">
          <div class="pid-title-row">
            <span id="pid-section-title">${t('pid_section_title')}</span>
            <span class="pid-state-pill" id="pid-state-pill">--</span>
          </div>
          <button type="button" class="pid-reset-btn" id="pid-reset-btn" title="${t('pid_reset_btn')}">
            <ha-icon icon="mdi:restart-alert" style="--mdc-icon-size: 14px;"></ha-icon>
            <span id="pid-reset-label">${t('pid_reset_btn')}</span>
          </button>
        </div>
        <div class="pid-grid">
          <div class="pid-box" id="pid-box-kp" data-param="Kp" title="${t('pid_click_to_edit')}">
            <div class="pid-box-top"><span id="pid-lock-kp">🔒</span><span>Kp</span></div>
            <div class="pid-box-val" id="pid-val-kp">--</div>
          </div>
          <div class="pid-box" id="pid-box-ki" data-param="Ki" title="${t('pid_click_to_edit')}">
            <div class="pid-box-top"><span id="pid-lock-ki">🔒</span><span>Ki</span></div>
            <div class="pid-box-val" id="pid-val-ki">--</div>
          </div>
          <div class="pid-box" id="pid-box-kd" data-param="Kd" title="${t('pid_click_to_edit')}">
            <div class="pid-box-top"><span id="pid-lock-kd">🔒</span><span>Kd</span></div>
            <div class="pid-box-val" id="pid-val-kd">--</div>
          </div>
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

      <div class="pid-modal-backdrop" id="pid-modal-backdrop">
        <div class="pid-modal">
          <div class="pid-modal-title" id="pid-modal-title"></div>
          <div class="pid-modal-warn" id="pid-modal-warn"></div>
          <div class="pid-modal-input-wrap" id="pid-modal-input-wrap">
            <label for="pid-modal-input" id="pid-modal-input-label"></label>
            <input type="number" id="pid-modal-input" />
          </div>
          <div class="pid-modal-actions">
            <button type="button" class="pid-btn pid-btn-cancel" id="pid-modal-cancel">${t('pid_modal_cancel')}</button>
            <button type="button" class="pid-btn pid-btn-restore" id="pid-modal-restore">${t('pid_modal_restore')}</button>
            <button type="button" class="pid-btn pid-btn-save" id="pid-modal-confirm">${t('pid_modal_save')}</button>
          </div>
        </div>
      </div>
    `;

    this.shadowRoot.appendChild(style);
    this.shadowRoot.appendChild(card);
    this._bindPidEvents();
    this._rendered = true;
  }

  _bindPidEvents() {
    this._activePidParam = null;
    this._modalMode = null;

    const closeModal = () => {
      const backdrop = this.shadowRoot.getElementById('pid-modal-backdrop');
      if (backdrop) backdrop.classList.remove('open');
      this._activePidParam = null;
      this._modalMode = null;
    };

    ['kp', 'ki', 'kd'].forEach((paramLower) => {
      const box = this.shadowRoot.getElementById(`pid-box-${paramLower}`);
      if (!box) return;
      box.addEventListener('click', () => {
        if (!this._hass || !this._config || !this._config.entity) return;
        const param = box.dataset.param;
        this._openPidEditModal(param);
      });
    });

    const resetBtn = this.shadowRoot.getElementById('pid-reset-btn');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        if (!this._hass || !this._config || !this._config.entity) return;
        this._openResetModal();
      });
    }

    const cancelBtn = this.shadowRoot.getElementById('pid-modal-cancel');
    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

    const backdrop = this.shadowRoot.getElementById('pid-modal-backdrop');
    if (backdrop) {
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) closeModal();
      });
    }

    const restoreBtn = this.shadowRoot.getElementById('pid-modal-restore');
    if (restoreBtn) {
      restoreBtn.addEventListener('click', async () => {
        if (!this._hass || !this._config || !this._activePidParam) return;
        await this._hass.callService('multizone_thermostat', 'set_pid_parameters', {
          climate_entity: this._config.entity,
          lock_parameter: this._activePidParam,
          unlock: false,
        });
        closeModal();
      });
    }

    const confirmBtn = this.shadowRoot.getElementById('pid-modal-confirm');
    if (confirmBtn) {
      confirmBtn.addEventListener('click', async () => {
        if (!this._hass || !this._config || !this._config.entity) return;
        if (this._modalMode === 'reset') {
          await this._hass.callService('multizone_thermostat', 'reset_autotune', {
            climate_entity: this._config.entity,
          });
          closeModal();
          return;
        }
        if (this._modalMode === 'edit' && this._activePidParam) {
          const inputEl = this.shadowRoot.getElementById('pid-modal-input');
          const parsed = inputEl ? parseFloat(inputEl.value) : NaN;
          if (!isNaN(parsed)) {
            await this._hass.callService('multizone_thermostat', 'set_pid_parameters', {
              climate_entity: this._config.entity,
              [this._activePidParam.toLowerCase()]: parsed,
              unlock: true,
            });
          }
          closeModal();
        }
      });
    }
  }

  _openPidEditModal(param) {
    const t = (k) => getTranslation(this._hass, k);
    this._modalMode = 'edit';
    this._activePidParam = param;

    const specs = {
      Kp: { min: 0.1, max: 500, step: 0.1 },
      Ki: { min: 0, max: 1, step: 0.0001 },
      Kd: { min: 0, max: 50000, step: 1 },
    }[param];

    const titleEl = this.shadowRoot.getElementById('pid-modal-title');
    const warnEl = this.shadowRoot.getElementById('pid-modal-warn');
    const inputWrap = this.shadowRoot.getElementById('pid-modal-input-wrap');
    const labelEl = this.shadowRoot.getElementById('pid-modal-input-label');
    const inputEl = this.shadowRoot.getElementById('pid-modal-input');
    const restoreBtn = this.shadowRoot.getElementById('pid-modal-restore');
    const confirmBtn = this.shadowRoot.getElementById('pid-modal-confirm');
    const valEl = this.shadowRoot.getElementById(`pid-val-${param.toLowerCase()}`);
    const backdrop = this.shadowRoot.getElementById('pid-modal-backdrop');

    if (titleEl) titleEl.innerText = `⚠️ ${t('pid_modal_title')} (${param})`;
    if (warnEl) warnEl.innerText = t('pid_modal_warn');
    if (inputWrap) inputWrap.style.display = 'block';
    if (labelEl) labelEl.innerText = `${t('pid_modal_value')} (${param})`;
    if (inputEl && specs) {
      inputEl.min = String(specs.min);
      inputEl.max = String(specs.max);
      inputEl.step = String(specs.step);
      const curNum = valEl ? parseFloat(valEl.innerText) : NaN;
      inputEl.value = isNaN(curNum) ? '0' : String(curNum);
    }
    if (restoreBtn) {
      const overrides = (this._latestPidInfo && this._latestPidInfo.overrides) || [];
      restoreBtn.style.display = overrides.includes(param) ? 'inline-block' : 'none';
      restoreBtn.innerText = t('pid_modal_restore');
    }
    if (confirmBtn) {
      confirmBtn.className = 'pid-btn pid-btn-save';
      confirmBtn.innerText = t('pid_modal_save');
    }
    if (backdrop) backdrop.classList.add('open');
  }

  _openResetModal() {
    const t = (k) => getTranslation(this._hass, k);
    this._modalMode = 'reset';
    this._activePidParam = null;

    const titleEl = this.shadowRoot.getElementById('pid-modal-title');
    const warnEl = this.shadowRoot.getElementById('pid-modal-warn');
    const inputWrap = this.shadowRoot.getElementById('pid-modal-input-wrap');
    const restoreBtn = this.shadowRoot.getElementById('pid-modal-restore');
    const confirmBtn = this.shadowRoot.getElementById('pid-modal-confirm');
    const backdrop = this.shadowRoot.getElementById('pid-modal-backdrop');

    if (titleEl) titleEl.innerText = `🔄 ${t('pid_reset_title')}`;
    if (warnEl) warnEl.innerText = t('pid_reset_confirm_msg');
    if (inputWrap) inputWrap.style.display = 'none';
    if (restoreBtn) restoreBtn.style.display = 'none';
    if (confirmBtn) {
      confirmBtn.className = 'pid-btn pid-btn-danger';
      confirmBtn.innerText = t('pid_reset_confirm_btn');
    }
    if (backdrop) backdrop.classList.add('open');
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
      const cleanSlug = slug.replace(/^zona_/, "");
      const isSlugMatch = (id) => {
        if (typeof isZoneEntityMatch === 'function') return isZoneEntityMatch(id, cleanSlug);
        const objId = (id.includes('.') ? id.split('.')[1] : id).toLowerCase();
        const cSlug = cleanSlug.toLowerCase();
        let stripped = objId.replace(/^(multizone_thermostat_|zona_|zone_)/, '');
        if (stripped === cSlug) return true;
        const sfxs = ['_energy_class', '_classe_energetica', '_thermal_retention', '_tempo_ritenzione_termica', '_tempo_di_ritenzione_termica', '_radiator_sizing', '_dimensionamento_radiatore', '_anomaly', '_anomalia', '_passive_heat', '_apporto_passivo', '_battery', '_batteria', '_heating_rate', '_cooling_rate', '_thermal_loss', '_duty_cycle', '_mode', '_modalita_zona'];
        for (const sfx of sfxs) {
          if (stripped.endsWith(sfx) && stripped.slice(0, -sfx.length) === cSlug) return true;
        }
        return objId.endsWith('_' + cSlug) || objId.endsWith('_zona_' + cSlug);
      };

      const energyEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
        k.startsWith('sensor.') && (k.includes('energy_class') || k.includes('classe_energetica')) && isSlugMatch(k)
      );
      const retentionEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
        k.startsWith('sensor.') && (k.includes('thermal_retention') || k.includes('tempo_ritenzione_termica') || k.includes('tempo_di_ritenzione_termica')) && isSlugMatch(k)
      );
      const sizingEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
        k.startsWith('sensor.') && (k.includes('radiator_sizing') || k.includes('dimensionamento_radiatore')) && isSlugMatch(k)
      );
      const anomalyEntity = this._hass && this._hass.states && Object.keys(this._hass.states).find(k => k.startsWith('binary_sensor.') && (k.includes('anomaly') || k.includes('anomalia')) && isSlugMatch(k));

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
          s.entity_id && (s.entity_id.startsWith('select.') || s.entity_id.startsWith('switch.')) && (
            (s.attributes && s.attributes.climate_entity === climateId) ||
            (isSlugMatch(s.entity_id) && (s.entity_id.includes('mode') || s.entity_id.includes('zone') || s.entity_id.includes('modalita')))
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
      const energyClass = (eState && !['unavailable', 'unknown'].includes(eState.state)) ? eState.state : "--";
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
      if (retentionVal) {
        if (rState && !['unavailable', 'unknown'].includes(rState.state)) {
          const r = parseFloat(rState.state);
          retentionVal.innerText = isNaN(r) ? "--" : r.toFixed(1);
          if (retentionEval) {
            if (isNaN(r)) retentionEval.innerText = t('learning');
            else if (r >= 6.0) retentionEval.innerText = t('opt_insulation');
            else if (r >= 3.5) retentionEval.innerText = t('med_insulation');
            else retentionEval.innerText = t('fast_dispersion');
          }
        } else {
          retentionVal.innerText = "--";
          if (retentionEval) retentionEval.innerText = "--";
        }
      }

      const sState = sizingEntity ? this._hass.states[sizingEntity] : null;
      if (sizingVal) {
        if (sState && !['unavailable', 'unknown'].includes(sState.state)) {
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
        } else {
          sizingVal.innerText = "--";
          if (sizingEval) {
            sizingEval.innerText = "--";
            sizingEval.style.color = "#94a3b8";
          }
        }
      }

      const aState = anomalyEntity ? this._hass.states[anomalyEntity] : null;
      const passiveHeatSwitch = this._hass && this._hass.states && Object.keys(this._hass.states).find(k => 
        k.startsWith('switch.') && (k.includes('passive_heat') || k.includes('apporto_passivo')) && isSlugMatch(k)
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
              k.startsWith('switch.') && (k.includes('passive_heat') || k.includes('apporto_passivo')) && isSlugMatch(k)
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
              isSlugMatch(k) &&
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

      // PID & Autotuner Display
      const attrs = climateState.attributes || {};
      const autotuneSensorKey = this._hass && this._hass.states && Object.keys(this._hass.states).find(k =>
        k.startsWith('sensor.') && k.includes('autotun') && (isSlugMatch(k) || k.includes(slug))
      );
      const autotuneStateObj = autotuneSensorKey ? this._hass.states[autotuneSensorKey] : null;
      const autoAttrs = (autotuneStateObj && autotuneStateObj.attributes) || {};

      const readNumFallback = (paramLower) => {
        const numKey = Object.keys(this._hass.states).find(k =>
          k.startsWith('number.') && k.includes(`pid_${paramLower}`) && (isSlugMatch(k) || k.includes(slug))
        );
        if (numKey && this._hass.states[numKey]) {
          const parsed = parseFloat(this._hass.states[numKey].state);
          if (!isNaN(parsed)) return parsed;
        }
        return null;
      };

      const kpVal = attrs.pid_kp !== undefined ? attrs.pid_kp : (autoAttrs.Kp !== undefined ? autoAttrs.Kp : readNumFallback('kp'));
      const kiVal = attrs.pid_ki !== undefined ? attrs.pid_ki : (autoAttrs.Ki !== undefined ? autoAttrs.Ki : readNumFallback('ki'));
      const kdVal = attrs.pid_kd !== undefined ? attrs.pid_kd : (autoAttrs.Kd !== undefined ? autoAttrs.Kd : readNumFallback('kd'));
      const overrides = Array.isArray(attrs.pid_manual_overrides)
        ? attrs.pid_manual_overrides
        : (Array.isArray(autoAttrs.manual_overrides) ? autoAttrs.manual_overrides : []);
      const autotuneState = attrs.autotune_state || (autotuneStateObj ? autotuneStateObj.state : null);

      this._latestPidInfo = { kp: kpVal, ki: kiVal, kd: kdVal, overrides };

      const pidTitleEl = this.shadowRoot.getElementById('pid-section-title');
      if (pidTitleEl) pidTitleEl.innerText = t('pid_section_title');
      const resetLabelEl = this.shadowRoot.getElementById('pid-reset-label');
      if (resetLabelEl) resetLabelEl.innerText = t('pid_reset_btn');

      const pillEl = this.shadowRoot.getElementById('pid-state-pill');
      if (pillEl) {
        if (overrides.length > 0) {
          pillEl.innerText = t('pid_manual_badge');
        } else if (
          autotuneState === 'completed'
          || (typeof autotuneState === 'string' && (autotuneState.includes('Smart PID Attivo') || autotuneState.includes('Smart PID Active')))
        ) {
          pillEl.innerText = t('pid_auto_badge');
        } else {
          const cyc = attrs.autotune_cycles !== undefined ? attrs.autotune_cycles : 0;
          const req = attrs.autotune_required_cycles !== undefined ? attrs.autotune_required_cycles : 3;
          pillEl.innerText = `${t('pid_learning_status')} (${cyc}/${req})`;
        }
      }

      const fmtMap = {
        Kp: kpVal !== null && kpVal !== undefined ? Number(kpVal).toFixed(1) : '--',
        Ki: kiVal !== null && kiVal !== undefined ? Number(kiVal).toFixed(4) : '--',
        Kd: kdVal !== null && kdVal !== undefined ? Number(kdVal).toFixed(1) : '--',
      };
      ['Kp', 'Ki', 'Kd'].forEach((param) => {
        const lower = param.toLowerCase();
        const box = this.shadowRoot.getElementById(`pid-box-${lower}`);
        const valEl = this.shadowRoot.getElementById(`pid-val-${lower}`);
        const lockEl = this.shadowRoot.getElementById(`pid-lock-${lower}`);
        const isOverride = overrides.includes(param);
        if (valEl) valEl.innerText = fmtMap[param];
        if (box) {
          box.classList.toggle('manual-override', isOverride);
          box.title = t('pid_click_to_edit');
        }
        if (lockEl) lockEl.innerText = isOverride ? '✏️' : '🔒';
      });
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
    const currentMasterMode = typeof getMasterHVACMode === 'function' ? getMasterHVACMode(hass) : 'heat';
    if (!this._rendered) {
      this.render();
      this._rendered = true;
      this._lastMasterHvacMode = currentMasterMode;
      const raw = this._extractHaScheduleStatus();
      this._lastHaScheduleJson = raw ? JSON.stringify(raw) : "";
    } else {
      let masterModeChanged = false;
      if (this._lastMasterHvacMode && currentMasterMode !== this._lastMasterHvacMode) {
        masterModeChanged = true;
      }
      this._lastMasterHvacMode = currentMasterMode;

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
        if (masterModeChanged) {
          this.renderPresetMatrixTable();
          this.renderLiveZones();
        }
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

    const getRates = (climateId, cState) => {
      let heatingRate = (cState.attributes && typeof cState.attributes.heating_rate === 'number') ? cState.attributes.heating_rate : null;
      let coolingRate = (cState.attributes && typeof cState.attributes.cooling_rate === 'number') ? cState.attributes.cooling_rate : null;

      if ((heatingRate === null || coolingRate === null) && this._hass && this._hass.states) {
        const slug = climateId.replace("climate.multizone_thermostat_", "").replace("climate.", "");
        const cleanSlug = slug.replace(/^zona_/, "");
        const isSlugMatch = (id) => {
          if (typeof isZoneEntityMatch === 'function') return isZoneEntityMatch(id, cleanSlug);
          const objId = (id.includes('.') ? id.split('.')[1] : id).toLowerCase();
          const cSlug = cleanSlug.toLowerCase();
          let stripped = objId.replace(/^(multizone_thermostat_|zona_|zone_)/, '');
          if (stripped === cSlug) return true;
          const sfxs = ['_heating_rate', '_velocita_riscaldamento', '_cooling_rate', '_velocita_raffrescamento'];
          for (const sfx of sfxs) {
            if (stripped.endsWith(sfx) && stripped.slice(0, -sfx.length) === cSlug) return true;
          }
          return objId.endsWith('_' + cSlug) || objId.endsWith('_zona_' + cSlug);
        };

        if (coolingRate === null) {
          const cRateEntity = Object.keys(this._hass.states).find(k =>
            k.startsWith('sensor.') && k.includes('cooling_rate') && isSlugMatch(k) &&
            !['unavailable', 'unknown'].includes(this._hass.states[k].state)
          );
          if (cRateEntity) {
            const parsed = parseFloat(this._hass.states[cRateEntity].state);
            if (!isNaN(parsed)) coolingRate = parsed;
          }
        }

        if (heatingRate === null) {
          const hRateEntity = Object.keys(this._hass.states).find(k =>
            k.startsWith('sensor.') && k.includes('heating_rate') && isSlugMatch(k) &&
            !['unavailable', 'unknown'].includes(this._hass.states[k].state)
          );
          if (hRateEntity) {
            const parsed = parseFloat(this._hass.states[hRateEntity].state);
            if (!isNaN(parsed)) heatingRate = parsed;
          }
        }
      }

      return {
        heatingRate: heatingRate !== null ? heatingRate : 1.0,
        coolingRate: coolingRate
      };
    };

    for (const eid of Object.keys(this._hass.states)) {
      const s = this._hass.states[eid];
      const climateId = s.attributes ? s.attributes.climate_entity : null;
      if (climateId && this._hass.states[climateId] && !seenClimates.has(climateId)) {
        seenClimates.add(climateId);
        const cState = this._hass.states[climateId];
        let name = cState.attributes.friendly_name || climateId;
        name = name.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
        const { heatingRate, coolingRate } = getRates(climateId, cState);
        zones.push({
          id: climateId,
          climate: climateId,
          switch: eid,
          name: name,
          current_temp: typeof cState.attributes.current_temperature === 'number' ? cState.attributes.current_temperature : 20.0,
          target_temp: typeof cState.attributes.temperature === 'number' ? cState.attributes.temperature : 20.0,
          hvac_mode: cState.state,
          heating_rate: heatingRate,
          cooling_rate: coolingRate,
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
          const { heatingRate, coolingRate } = getRates(eid, cState);
          zones.push({
            id: eid,
            climate: eid,
            switch: null,
            name: name,
            current_temp: typeof cState.attributes.current_temperature === 'number' ? cState.attributes.current_temperature : 20.0,
            target_temp: typeof cState.attributes.temperature === 'number' ? cState.attributes.temperature : 20.0,
            hvac_mode: cState.state,
            heating_rate: heatingRate,
            cooling_rate: coolingRate,
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
    const isCoolMode = (typeof getMasterHVACMode === 'function' && getMasterHVACMode(this._hass) === 'cool');
    const sched = this._getScheduleStatus();
    if (sched.preset_matrix && sched.preset_matrix[preset]) {
      if (typeof sched.preset_matrix[preset][zoneId] === 'number') {
        return sched.preset_matrix[preset][zoneId];
      }
    }
    if (this._hass && zoneId && this._hass.states[zoneId]) {
      const zState = this._hass.states[zoneId];
      if (isCoolMode && zState.attributes && zState.attributes.presets_cool && typeof zState.attributes.presets_cool[preset] === 'number') {
        return zState.attributes.presets_cool[preset];
      }
      if (zState.attributes && zState.attributes.presets && typeof zState.attributes.presets[preset] === 'number') {
        return zState.attributes.presets[preset];
      }
    }
    const defaults = isCoolMode
      ? { comfort: 24.5, eco: 26.5, sleep: 25.5, away: 28.0 }
      : { comfort: 21.0, eco: 19.0, sleep: 17.0, away: 15.0 };
    return defaults[preset] || (isCoolMode ? 25.0 : 20.0);
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
          flex-wrap: wrap;
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
          grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
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
          flex-wrap: wrap;
        }
        .zone-card-title {
          font-weight: 700;
          font-size: 1.02rem;
          line-height: 1.25;
          word-break: break-word;
        }
        .zone-card-mid {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          flex-wrap: wrap;
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
          font-size: 0.75rem;
          opacity: 0.75;
          border-top: 1px solid rgba(255, 255, 255, 0.08);
          padding-top: 8px;
          margin-top: 4px;
          gap: 8px;
          line-height: 1.4;
          overflow: hidden;
        }
        .zone-card-bottom span {
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
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
          align-items: center;
          gap: 10px;
          margin-bottom: 8px;
        }
        .ruler-spacer {
          width: 170px;
          flex-shrink: 0;
        }
        .ruler-track {
          flex: 1;
          position: relative;
          height: 20px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
          border-left: 1px solid transparent;
          border-right: 1px solid transparent;
          box-sizing: border-box;
        }
        .ruler-hour {
          position: absolute;
          top: 0;
          transform: translateX(-50%);
          font-size: 0.75rem;
          color: rgba(255, 255, 255, 0.6);
          white-space: nowrap;
          user-select: none;
        }
        .ruler-hour.ruler-start {
          transform: translateX(0);
        }
        .ruler-hour.ruler-end {
          transform: translateX(-100%);
        }
        .matrix-row {
          display: flex;
          align-items: center;
          margin-bottom: 8px;
          gap: 10px;
        }
        .room-label-box {
          width: 170px;
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
        .time-block.baseline-block {
          opacity: 0.36;
          border: 1px dashed rgba(255, 255, 255, 0.35);
          box-shadow: none;
          font-weight: 500;
          font-size: 0.68rem;
          z-index: 1;
          pointer-events: none;
        }
        .time-block.manual-override-block {
          background: linear-gradient(135deg, rgba(245, 158, 11, 0.92), rgba(217, 119, 6, 0.92));
          border: 1px solid #fde68a;
          z-index: 6;
          box-shadow: 0 0 8px rgba(245, 158, 11, 0.45);
        }
        .matrix-row.general-master-row {
          padding-bottom: 8px;
          margin-bottom: 10px;
          border-bottom: 1px dashed rgba(56, 189, 248, 0.35);
        }
        .matrix-row.general-master-row .room-title {
          color: #38bdf8;
          font-weight: 700;
        }
        .matrix-row.general-master-row .timeline-track {
          border-color: rgba(56, 189, 248, 0.35);
          background: rgba(56, 189, 248, 0.06);
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

        /* Responsive Mobile Layout Fixes for Scheduler Panel */
        @media (max-width: 768px) {
          ha-card {
            padding: 14px 10px;
          }
          .header-bar {
            flex-direction: column;
            align-items: flex-start;
            gap: 12px;
          }
          .header-title-box {
            width: 100%;
            justify-content: space-between;
          }
          .header-title {
            font-size: 1.15rem;
          }
          .header-badges {
            width: 100%;
          }
          .header-actions {
            width: 100%;
            display: grid;
            grid-template-columns: 1fr;
            gap: 8px;
          }
          .header-actions .btn {
            width: 100%;
            text-align: center;
            padding: 10px;
          }
          .live-zones-grid {
            grid-template-columns: 1fr;
            gap: 10px;
          }
          .editor-header-bar {
            flex-direction: column;
            align-items: stretch;
            gap: 10px;
          }
          .profile-tabs {
            display: flex;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            width: 100%;
            padding-bottom: 4px;
          }
          .editor-controls {
            justify-content: space-between;
            width: 100%;
          }
          .toolbar-bar {
            flex-direction: column;
            align-items: stretch;
            gap: 10px;
            padding: 10px 8px;
          }
          .day-pills {
            display: flex;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
            padding-bottom: 4px;
            width: 100%;
          }
          .day-pills::-webkit-scrollbar { display: none; }
          .matrix-container {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            width: 100%;
          }
          .time-ruler, .matrix-row {
            min-width: 680px;
          }
          .room-label-box {
            position: sticky;
            left: 0;
            background: #1e293b;
            z-index: 10;
            padding-right: 6px;
          }
          .matrix-table-container table {
            min-width: 520px;
          }
          .preset-summary-grid {
            grid-template-columns: 1fr;
          }
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
    const currentMasterMode = typeof getMasterHVACMode === 'function' ? getMasterHVACMode(this._hass) : 'heat';
    if (this._lastMasterHvacMode && currentMasterMode !== this._lastMasterHvacMode) {
      this.renderPresetMatrixTable();
      this.renderLiveZones();
    }
    this._lastMasterHvacMode = currentMasterMode;
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

    const isCoolMode = (typeof getMasterHVACMode === 'function' && getMasterHVACMode(this._hass) === 'cool');
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
            badgeHtml = `<span class="badge badge-orange">${isCoolMode ? '❄️' : '🔥'} Smart Start ${z.smart_start_detail || ''}</span>`;
          } else {
            badgeHtml = `<span class="badge badge-green">🌿 ${z.target_temp.toFixed(1)}°C</span>`;
          }

          const isOff = z.hvac_mode === 'off';
          const zoneRate = (isCoolMode && typeof z.cooling_rate === 'number') ? z.cooling_rate : z.heating_rate;
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
                <span>⚡ Inerzia: ${(typeof zoneRate === 'number' && !isNaN(zoneRate)) ? zoneRate.toFixed(1) : '--'} °C/h</span>
                <span title="${z.climate}">${z.climate.replace('climate.', '')}</span>
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
          const nextMode = z.hvac_mode === 'off' ? (isCoolMode ? 'cool' : 'heat') : 'off';
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

    const isCoolMode = (typeof getMasterHVACMode === 'function' && getMasterHVACMode(this._hass) === 'cool');
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
                <option value="comfort" ${currentBaseline === 'comfort' ? 'selected' : ''}>${isCoolMode ? '❄️' : '🔥'} Comfort</option>
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
            <div class="ruler-spacer"></div>
            <div class="ruler-track">
              ${Array.from({ length: 13 }).map((_, i) => {
                const h = String(i * 2).padStart(2, '0');
                const leftPct = (i * 100) / 12;
                const edgeCls = i === 0 ? 'ruler-start' : (i === 12 ? 'ruler-end' : '');
                return `<div class="ruler-hour ${edgeCls}" style="left: ${leftPct}%;">${h}:00</div>`;
              }).join('')}
            </div>
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
    this.renderMatrixRows();
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

  _computeBaselineGaps(blocks, baselinePreset) {
    const base = baselinePreset || 'eco';
    const sorted = (blocks || [])
      .map(b => {
        const s = this._toMinutes(b.start);
        const e = (b.end === '23:59' || b.end === '24:00') ? 1440 : this._toMinutes(b.end);
        return { s, e };
      })
      .filter(b => b.e > b.s)
      .sort((a, b) => a.s - b.s);

    const gaps = [];
    let cursor = 0;
    for (const seg of sorted) {
      if (seg.s > cursor) {
        gaps.push({
          startMin: cursor,
          endMin: seg.s,
          start: this._toTimeStr(cursor),
          end: seg.s >= 1440 ? '24:00' : this._toTimeStr(seg.s),
          preset: base,
        });
      }
      cursor = Math.max(cursor, seg.e);
    }
    if (cursor < 1440) {
      gaps.push({
        startMin: cursor,
        endMin: 1440,
        start: this._toTimeStr(cursor),
        end: '24:00',
        preset: base,
      });
    }
    return gaps;
  }

  _computeGeneralDayBlocks(zones, daySchedule) {
    if (!zones || zones.length === 0) return [];
    const points = new Set([0, 1440]);
    const zoneIntervals = zones.map(z => {
      const zBlocks = daySchedule[z.climate] || daySchedule[z.id] || [];
      return zBlocks.map(b => {
        const s = this._toMinutes(b.start);
        const e = (b.end === '23:59' || b.end === '24:00') ? 1440 : this._toMinutes(b.end);
        if (e > s) {
          points.add(s);
          points.add(e);
        }
        return { s, e, preset: b.preset || 'comfort' };
      }).filter(b => b.e > b.s);
    });

    const sortedPoints = Array.from(points).sort((a, b) => a - b);
    const priority = { comfort: 0, eco: 1, sleep: 2, away: 3 };
    const slices = [];

    for (let i = 0; i < sortedPoints.length - 1; i++) {
      const t1 = sortedPoints[i];
      const t2 = sortedPoints[i + 1];
      if (t2 <= t1) continue;
      const mid = (t1 + t2) / 2;
      const counts = {};
      let covered = 0;

      for (const intervals of zoneIntervals) {
        const hit = intervals.find(iv => iv.s <= mid && iv.e > mid);
        if (hit) {
          covered += 1;
          counts[hit.preset] = (counts[hit.preset] || 0) + 1;
        }
      }
      if (covered === 0) continue;

      const topPreset = Object.keys(counts).sort((a, b) => {
        if (counts[b] !== counts[a]) return counts[b] - counts[a];
        return (priority[a] ?? 99) - (priority[b] ?? 99);
      })[0];
      const mixed = counts[topPreset] < zones.length;
      slices.push({ startMin: t1, endMin: t2, preset: topPreset, mixed });
    }

    const merged = [];
    for (const sl of slices) {
      const prev = merged[merged.length - 1];
      if (prev && prev.endMin === sl.startMin && prev.preset === sl.preset && prev.mixed === sl.mixed) {
        prev.endMin = sl.endMin;
      } else {
        merged.push({ ...sl });
      }
    }

    return merged.map(m => ({
      start: this._toTimeStr(m.startMin),
      end: m.endMin >= 1440 ? '24:00' : this._toTimeStr(m.endMin),
      startMin: m.startMin,
      endMin: m.endMin,
      preset: m.preset,
      mixed: m.mixed,
    }));
  }

  renderMatrixRows() {
    const rowsContainer = this.shadowRoot.querySelector('#matrix-rows-container');
    if (!rowsContainer) return;

    const zones = this._getZones();
    const sched = this._getScheduleStatus();
    const prof = sched.profiles?.[this._editorProfileId] || {};
    const daySchedule = prof.days?.[this._selectedDay] || {};
    const currentBaseline = prof.baseline_preset || 'eco';
    const manualOverrides = sched.manual_overrides || {};

    const dayMap = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
    const isToday = dayMap[new Date().getDay()] === this._selectedDay;
    const now = new Date();
    const nowMinutes = now.getHours() * 60 + now.getMinutes();
    const nowPercent = (nowMinutes / 1440) * 100;

    const gridAndLine = `
      ${Array.from({ length: 12 }).map((_, i) => `
        <div class="grid-line" style="left: ${(i + 1) * (100 / 12)}%;"></div>
      `).join('')}
      ${isToday ? `<div class="current-time-line" style="left: ${nowPercent}%;"></div>` : ''}
    `;

    const renderBaselineGapsHtml = (blocks) => {
      const gaps = this._computeBaselineGaps(blocks, currentBaseline);
      return gaps.map(g => {
        const left = (g.startMin / 1440) * 100;
        const width = ((g.endMin - g.startMin) / 1440) * 100;
        if (width < 2) return '';
        const presetClass = 'block-' + g.preset;
        const baseWord = this._t('sched_base_tag');
        return `
          <div class="time-block baseline-block ${presetClass}" style="left: ${left}%; width: ${width}%;"
               title="${g.preset.toUpperCase()} (${baseWord}): ${g.start} - ${g.end}">
            ${g.preset.substring(0, 3).toUpperCase()} (${baseWord})
          </div>
        `;
      }).join('');
    };

    const generalBlocks = this._computeGeneralDayBlocks(zones, daySchedule);
    const generalRowHtml = zones.length > 0 ? `
      <div class="matrix-row general-master-row" data-zone="__all__">
        <div class="room-label-box">
          <span class="room-title" title="${this._t('sched_all_zones_row')}">🏠 ${this._t('sched_all_zones_row')}</span>
        </div>
        <div class="timeline-track" data-zone="__all__">
          ${gridAndLine}
          ${renderBaselineGapsHtml(generalBlocks)}
          ${generalBlocks.map(b => {
            const left = (b.startMin / 1440) * 100;
            const width = Math.max(1.5, ((b.endMin - b.startMin) / 1440) * 100);
            const presetClass = 'block-' + b.preset;
            const prefix = b.mixed ? '⚡ ' : '';
            return `
              <div class="time-block ${presetClass}" style="left: ${left}%; width: ${width}%;"
                   data-zone="__all__" data-start="${b.start}" data-end="${b.end}" data-preset="${b.preset}"
                   title="${b.preset.toUpperCase()}: ${b.start} - ${b.end}${b.mixed ? ' (Mixed)' : ''}">
                ${prefix}${b.preset.substring(0, 3).toUpperCase()} ${b.start}-${b.end}
              </div>
            `;
          }).join('')}
        </div>
      </div>
    ` : '';

    const zonesRowsHtml = zones.map(z => {
      const blocks = daySchedule[z.climate] || daySchedule[z.id] || [];
      let overrideBlockHtml = '';
      if (isToday && manualOverrides[z.climate]) {
        const ov = manualOverrides[z.climate];
        const untilDt = ov.until ? new Date(ov.until) : null;
        if (untilDt && !isNaN(untilDt.getTime()) && untilDt > now && nowMinutes < 1440) {
          const sameDay = untilDt.getDate() === now.getDate()
            && untilDt.getMonth() === now.getMonth()
            && untilDt.getFullYear() === now.getFullYear();
          const untilMin = sameDay ? (untilDt.getHours() * 60 + untilDt.getMinutes()) : 1440;
          const ovEnd = Math.min(1440, Math.max(nowMinutes + 15, untilMin));
          const left = (nowMinutes / 1440) * 100;
          const width = Math.max(2.0, ((ovEnd - nowMinutes) / 1440) * 100);
          overrideBlockHtml = `
            <div class="time-block manual-override-block" style="left: ${left}%; width: ${width}%;"
                 data-zone="${z.climate}" data-override="1"
                 title="Override manuale attivo: ${Number(ov.target_temp).toFixed(1)}°C">
              ✋ ${Number(ov.target_temp).toFixed(1)}°C
            </div>
          `;
        }
      }

      return `
        <div class="matrix-row" data-zone="${z.climate}">
          <div class="room-label-box">
            <span class="room-title" title="${z.name}">${z.name}</span>
            <button class="room-copy-btn btn-copy-room" data-zone="${z.climate}" title="Copia/Incolla programmazione stanza">
              📋
            </button>
          </div>
          <div class="timeline-track" data-zone="${z.climate}">
            ${gridAndLine}
            ${renderBaselineGapsHtml(blocks)}
            ${blocks.map((b, idx) => {
              const startMin = this._toMinutes(b.start);
              const endMin = (b.end === '23:59' || b.end === '24:00') ? 1440 : this._toMinutes(b.end);
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
            ${overrideBlockHtml}
          </div>
        </div>
      `;
    }).join('');

    rowsContainer.innerHTML = generalRowHtml + zonesRowsHtml;

    rowsContainer.querySelectorAll('.btn-copy-room').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const cid = btn.getAttribute('data-zone');
        this._handleRoomCopyPaste(cid);
      });
    });

    rowsContainer.querySelectorAll('.timeline-track').forEach(track => {
      track.addEventListener('click', (e) => {
        if (e.target.closest('.time-block:not(.baseline-block)')) return;
        const cid = track.getAttribute('data-zone');
        const rect = track.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const ratio = Math.max(0, Math.min(1, clickX / rect.width));
        const clickMin = Math.floor(ratio * 1440);
        const startMin = Math.floor(clickMin / 30) * 30;
        const endMin = Math.min(1440, startMin + 120);

        this.openSlotModal({
          isEdit: false,
          zoneId: cid === '__all__' ? undefined : cid,
          day: this._selectedDay,
          start: this._toTimeStr(startMin),
          end: this._toTimeStr(endMin),
          selectedDays: [this._selectedDay]
        });
      });
    });

    rowsContainer.querySelectorAll('.time-block:not(.baseline-block)').forEach(block => {
      block.addEventListener('click', (e) => {
        e.stopPropagation();
        const cid = block.getAttribute('data-zone');
        if (block.hasAttribute('data-override')) {
          if (this._hass && confirm("Rimuovere l'override manuale temporaneo per questa stanza?")) {
            this._hass.callService('multizone_thermostat', 'clear_zone_override', {
              entity_id: cid
            });
          }
          return;
        }
        if (cid === '__all__') {
          this.openSlotModal({
            isEdit: true,
            day: this._selectedDay,
            preset: block.getAttribute('data-preset') || 'comfort',
            start: block.getAttribute('data-start'),
            end: block.getAttribute('data-end'),
            selectedDays: [this._selectedDay]
          });
          return;
        }
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

  async _saveProfileToServer(profileId, profObj) {
    if (!this._hass) return;
    await this._hass.callService('multizone_thermostat', 'save_schedule_profile', {
      profile_id: profileId,
      name: profObj.name || profileId,
      baseline_preset: profObj.baseline_preset || 'eco',
      days: profObj.days || {},
      profile: profObj
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

    const isCoolMode = (typeof getMasterHVACMode === 'function' && getMasterHVACMode(this._hass) === 'cool');
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
              <div style="font-size:0.75rem; opacity:0.65;">Valori di riferimento sincronizzati dai Preset Standard dell'impianto (${isCoolMode ? 'Raffrescamento ❄️' : 'Riscaldamento 🔥'})</div>
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
                  <span class="preset-badge badge-comfort ${isCoolMode ? 'cool' : ''}" style="${isCoolMode ? 'background:rgba(56,189,248,0.15); color:#38bdf8; border:1px solid rgba(56,189,248,0.3);' : ''} cursor:pointer;" data-zone="${z.climate}" data-preset="comfort" data-temp="${cVal}" title="Comfort">${isCoolMode ? '❄️' : '🔥'} ${cVal.toFixed(1)}°C</span>
                  <span class="preset-badge badge-eco" style="cursor:pointer;" data-zone="${z.climate}" data-preset="eco" data-temp="${eVal}" title="Eco">🌿 ${eVal.toFixed(1)}°C</span>
                  <span class="preset-badge badge-sleep" style="cursor:pointer;" data-zone="${z.climate}" data-preset="sleep" data-temp="${sVal}" title="Notte">🌙 ${sVal.toFixed(1)}°C</span>
                  <span class="preset-badge badge-away" style="cursor:pointer;" data-zone="${z.climate}" data-preset="away" data-temp="${aVal}" title="Away">🚶 ${aVal.toFixed(1)}°C</span>
                </div>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;

    container.querySelectorAll('.preset-badge').forEach(badge => {
      badge.addEventListener('click', (e) => {
        e.stopPropagation();
        const zoneId = badge.getAttribute('data-zone');
        const preset = badge.getAttribute('data-preset');
        const temp = parseFloat(badge.getAttribute('data-temp'));
        const zone = zones.find(z => z.climate === zoneId);
        this.openPresetModal(zone || { climate: zoneId, name: zoneId }, preset, temp);
      });
    });
  }

  openPresetModal(zone, preset, currentTemp) {
    this._activeModal = 'preset';
    const isCoolMode = (typeof getMasterHVACMode === 'function' && getMasterHVACMode(this._hass) === 'cool');
    const safeTemp = (typeof currentTemp === 'number' && !isNaN(currentTemp)) ? currentTemp : (isCoolMode ? 24.5 : 20.0);
    const modalContainer = this.shadowRoot.querySelector('#modal-container');
    if (!modalContainer) return;

    const presetLabels = {
      comfort: { label: 'Comfort', icon: isCoolMode ? '❄️' : '🔥', color: isCoolMode ? '#38bdf8' : '#f87171' },
      eco: { label: 'Eco', icon: '🌿', color: '#4ade80' },
      sleep: { label: 'Notte', icon: '🌙', color: '#60a5fa' },
      away: { label: 'Away', icon: '🚶', color: '#cbd5e1' }
    };
    const pInfo = presetLabels[preset] || { label: preset, icon: '🌡️', color: '#38bdf8' };

    modalContainer.innerHTML = `
      <div class="modal-backdrop" id="modal-backdrop">
        <div class="modal-card" style="max-width: 400px;">
          <div class="modal-header">
            <div class="modal-title" style="display:flex; align-items:center; gap:8px;">
              <span>${pInfo.icon}</span>
              <span>Preset ${pInfo.label} - ${zone.name}</span>
            </div>
            <button class="modal-close" id="btn-close-modal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-row">
              <label class="form-label">Modalità Impianto:</label>
              <div style="font-weight:600; color: ${isCoolMode ? '#38bdf8' : '#fb923c'}; margin-bottom: 8px;">
                ${isCoolMode ? '❄️ Raffrescamento (Cool)' : '🔥 Riscaldamento (Heat)'}
              </div>
            </div>
            <div class="form-row">
              <label class="form-label">Temperatura Obiettivo (°C):</label>
              <input type="number" id="input-preset-temp" class="form-control" step="0.5" min="10" max="35" value="${safeTemp.toFixed(1)}" style="font-size:1.2rem; font-weight:700; text-align:center; padding:8px;">
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn" id="btn-cancel-modal">Annulla</button>
            <button class="btn btn-primary" id="btn-save-preset">Salva</button>
          </div>
        </div>
      </div>
    `;

    modalContainer.querySelector('#btn-close-modal')?.addEventListener('click', () => this.closeModal());
    modalContainer.querySelector('#btn-cancel-modal')?.addEventListener('click', () => this.closeModal());
    modalContainer.querySelector('#modal-backdrop')?.addEventListener('click', (e) => {
      if (e.target.id === 'modal-backdrop') this.closeModal();
    });

    modalContainer.querySelector('#btn-save-preset')?.addEventListener('click', () => {
      const input = modalContainer.querySelector('#input-preset-temp');
      const val = parseFloat(input?.value);
      if (!isNaN(val) && this._hass) {
        this._hass.callService('multizone_thermostat', 'set_preset_temperature', {
          entity_id: zone.climate,
          preset: preset,
          temperature: val,
          hvac_mode: isCoolMode ? 'cool' : 'heat'
        });
      }
      this.closeModal();
      setTimeout(() => this.renderPresetMatrixTable(), 300);
    });
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

    const isCoolMode = (typeof getMasterHVACMode === 'function' && getMasterHVACMode(this._hass) === 'cool');
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
                <div class="preset-card-icon">${isCoolMode ? '❄️' : '🔥'}</div>
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
                        <option value="comfort" ${initialVal === 'comfort' ? 'selected' : ''}>${isCoolMode ? '❄️' : '🔥'} Comfort (${cTemp.toFixed(1)}°C)</option>
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
        comfort: { label: 'Comfort', icon: isCoolMode ? '❄️' : '🔥' },
        eco: { label: 'Eco', icon: '🌿' },
        sleep: { label: 'Notte', icon: '🌙' },
        away: { label: 'Away', icon: '🚶' }
      }[genPreset] || { label: 'Comfort', icon: isCoolMode ? '❄️' : '🔥' };

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

    const isCoolMode = (typeof getMasterHVACMode === 'function' && getMasterHVACMode(this._hass) === 'cool');
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
                <option value="comfort" selected>${isCoolMode ? '❄️' : '🔥'} Comfort</option>
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
            <button class="btn btn-amber" id="btn-confirm-sr">${isCoolMode ? '❄️' : '🔥'} Pianifica Rientro</button>
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
        const delta = isCoolMode ? Math.max(0, curTemp - targetTemp) : Math.max(0, targetTemp - curTemp);
        const rate = (isCoolMode && typeof z.cooling_rate === 'number' && z.cooling_rate > 0.05)
          ? z.cooling_rate
          : (z.heating_rate > 0.05 ? z.heating_rate : 1.0);
        const reqMin = Math.min(360, Math.round((delta / rate) * 60));
        const ignDate = new Date(arrDate.getTime() - reqMin * 60000);
        const now = new Date();
        const ignStr = ignDate <= now
          ? ' Subito (Immediata)'
          : String(ignDate.getHours()).padStart(2, '0') + ':' + String(ignDate.getMinutes()).padStart(2, '0');
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
                <span style="font-size:0.75rem; font-weight:700; color:#fcd34d;">Accensione: ${item.ignStr.trim()}</span>
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

      const sched = JSON.parse(JSON.stringify(this._getScheduleStatus()));
      if (!sched.profiles) sched.profiles = {};
      const srcProf = sched.profiles[this._editorProfileId] || { name: this._editorProfileId, baseline_preset: 'eco', days: {} };
      const clonedProf = JSON.parse(JSON.stringify(srcProf));
      clonedProf.name = targetName;
      sched.profiles[targetId] = clonedProf;
      this._localScheduleCache = sched;

      this._editorProfileId = targetId;
      this.closeModal();
      this.renderEditor();
    });
  }
}

if (!customElements.get("multizone-thermostat-scheduler-card")) {
  customElements.define("multizone-thermostat-scheduler-card", MultizoneThermostatSchedulerCard);
}

/* ==================== FLOATING STYLE SWITCHER WITH POPUP MODAL ==================== */
function setHeaderVisibility(hide, retryCount = 0) {
  try {
    // 1. Document head global fallback
    let docStyle = document.getElementById('mz-header-hide-style-global');
    if (hide) {
      if (!docStyle) {
        docStyle = document.createElement('style');
        docStyle.id = 'mz-header-hide-style-global';
        docStyle.textContent = `
          app-header, .header, ha-top-app-bar, ha-top-app-bar-fixed, ha-tabs {
            display: none !important;
          }
          #view, #columns, hui-root {
            padding-top: 0 !important;
            margin-top: 0 !important;
          }
        `;
        document.head.appendChild(docStyle);
      }
    } else {
      if (docStyle) docStyle.remove();
    }

    // 2. Piercing Lovelace hui-root Shadow DOM
    const ha = document.querySelector('home-assistant');
    const main = ha?.shadowRoot?.querySelector('home-assistant-main');
    const lovelace = main?.shadowRoot?.querySelector('ha-panel-lovelace');
    const huiRoot = lovelace?.shadowRoot?.querySelector('hui-root');
    
    if (!huiRoot || !huiRoot.shadowRoot) {
      if (retryCount < 10) {
        setTimeout(() => setHeaderVisibility(hide, retryCount + 1), 300);
      }
      return;
    }

    let style = huiRoot.shadowRoot.querySelector('#mz-header-hide-style');
    if (hide) {
      if (!style) {
        style = document.createElement('style');
        style.id = 'mz-header-hide-style';
        style.textContent = `
          .header, app-header, ha-top-app-bar, ha-top-app-bar-fixed, ha-tabs {
            display: none !important;
          }
          #view, #columns {
            padding-top: 0 !important;
            margin-top: 0 !important;
          }
        `;
        huiRoot.shadowRoot.appendChild(style);
      }
    } else {
      if (style) {
        style.remove();
      }
    }
  } catch (e) {
    console.warn("Could not toggle header visibility:", e);
  }
}

class MultizoneThermostatStyleSwitcher extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._isOpen = false;
  }

  setConfig(config) {
    this._config = Object.assign({}, config || {});
    this.render();
  }

  getCardSize() {
    return 0;
  }

  connectedCallback() {
    const shouldHide = localStorage.getItem('mz_hide_header') === 'true';
    setHeaderVisibility(shouldHide);

    this._styleListener = (e) => {
      this.render();
    };
    window.addEventListener('mz-style-changed', this._styleListener);
    this.render();
  }

  disconnectedCallback() {
    if (this._styleListener) {
      window.removeEventListener('mz-style-changed', this._styleListener);
    }
  }

  getCurrentStyle() {
    return localStorage.getItem('mz_card_style') || 'luxury';
  }

  isHeaderHidden() {
    return localStorage.getItem('mz_hide_header') === 'true';
  }

  setStyle(style) {
    localStorage.setItem('mz_card_style', style);
    window.dispatchEvent(new CustomEvent('mz-style-changed', { detail: { style } }));
    this.render();
  }

  toggleHeader(hide) {
    localStorage.setItem('mz_hide_header', hide ? 'true' : 'false');
    setHeaderVisibility(hide);
    this.render();
  }

  openModal() {
    this._isOpen = true;
    this.render();
  }

  closeModal() {
    this._isOpen = false;
    this.render();
  }

  render() {
    const currentStyle = this.getCurrentStyle();
    const isClassic = currentStyle === 'classic';
    const hideHeader = this.isHeaderHidden();
    const bottom = this._config?.bottom || '2.5vh';
    const right = this._config?.right || '2.5vh';
    const icon = this._config?.icon || 'mdi:palette-outline';

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
        }
        .fab-btn {
          position: fixed !important;
          bottom: ${bottom} !important;
          right: ${right} !important;
          width: 52px !important;
          height: 52px !important;
          border-radius: 50% !important;
          z-index: 9999 !important;
          display: flex !important;
          justify-content: center !important;
          align-items: center !important;
          cursor: pointer !important;
          transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }
        
        /* Responsive styling: Luxury vs Classic */
        .fab-luxury {
          background: rgba(20, 27, 41, 0.85) !important;
          backdrop-filter: blur(16px) !important;
          -webkit-backdrop-filter: blur(16px) !important;
          border: 1.5px solid rgba(56, 189, 248, 0.4) !important;
          box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6), 0 0 15px rgba(56, 189, 248, 0.25) !important;
          color: #38bdf8 !important;
        }
        .fab-luxury:hover {
          transform: scale(1.1) !important;
          background: rgba(30, 41, 59, 0.95) !important;
          border-color: rgba(56, 189, 248, 0.7) !important;
          box-shadow: 0 12px 35px rgba(0, 0, 0, 0.8), 0 0 25px rgba(56, 189, 248, 0.5) !important;
        }
        
        .fab-classic {
          background: var(--card-background-color, #202b38) !important;
          border: 1.5px solid var(--divider-color, rgba(255, 255, 255, 0.2)) !important;
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5) !important;
          color: var(--primary-text-color, #ffffff) !important;
        }
        .fab-classic:hover {
          transform: scale(1.1) !important;
          background: var(--primary-color, #0284c7) !important;
          color: #ffffff !important;
        }

        .fab-btn:active {
          transform: scale(0.95) !important;
        }
        .fab-btn ha-icon {
          --mdc-icon-size: 26px;
          color: inherit;
        }

        /* Modal Overlay */
        .modal-overlay {
          position: fixed;
          inset: 0;
          z-index: 10000;
          background: rgba(0, 0, 0, 0.75);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          display: ${this._isOpen ? 'flex' : 'none'};
          align-items: center;
          justify-content: center;
          padding: 16px;
          box-sizing: border-box;
          animation: fadeIn 0.2s ease;
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        .modal-card {
          border-radius: 24px;
          width: 100%;
          max-width: 440px;
          overflow: hidden;
          animation: popIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .modal-card.modal-luxury {
          background: linear-gradient(135deg, rgba(20, 27, 41, 0.96) 0%, rgba(15, 23, 42, 0.99) 100%);
          border: 1px solid rgba(255, 255, 255, 0.12);
          box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.9), 0 0 30px rgba(56, 189, 248, 0.2);
        }
        .modal-card.modal-classic {
          background: var(--ha-card-background, var(--card-background-color, #1c1c1e)) !important;
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.15)) !important;
          box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6) !important;
        }
        .modal-classic .modal-header {
          border-bottom: 1px solid var(--divider-color, rgba(255, 255, 255, 0.12)) !important;
        }
        .modal-classic .modal-title {
          color: var(--primary-text-color, #ffffff) !important;
        }
        .modal-classic .section-label {
          color: var(--secondary-text-color, #94a3b8) !important;
        }
        .modal-classic .option-card {
          background: var(--card-background-color, #202b38) !important;
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.12)) !important;
        }
        .modal-classic .option-card:hover {
          background: rgba(255, 255, 255, 0.05) !important;
        }
        .modal-classic .option-card.active {
          background: rgba(var(--rgb-primary-color, 2, 132, 199), 0.15) !important;
          border-color: var(--primary-color, #0284c7) !important;
          box-shadow: 0 0 16px rgba(var(--rgb-primary-color, 2, 132, 199), 0.25) !important;
        }
        .modal-classic .option-card.active .option-icon {
          background: rgba(var(--rgb-primary-color, 2, 132, 199), 0.25) !important;
          color: var(--primary-color, #0284c7) !important;
        }
        .modal-classic .option-card.active .radio-dot {
          border-color: var(--primary-color, #0284c7) !important;
          background: var(--primary-color, #0284c7) !important;
        }
        .modal-classic .toggle-box {
          background: var(--card-background-color, #202b38) !important;
          border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.12)) !important;
        }
        .modal-classic .toggle-title {
          color: var(--primary-text-color, #ffffff) !important;
        }
        .modal-classic .toggle-desc {
          color: var(--secondary-text-color, #94a3b8) !important;
        }
        .modal-classic input:checked + .slider {
          background-color: var(--primary-color, #0284c7) !important;
        }
        @keyframes popIn {
          from { transform: scale(0.92); opacity: 0; }
          to { transform: scale(1); opacity: 1; }
        }
        .modal-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 18px 20px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }
        .modal-title {
          font-size: 16px;
          font-weight: 800;
          color: #ffffff;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .close-btn {
          background: rgba(255, 255, 255, 0.06);
          border: none;
          color: #94a3b8;
          width: 30px;
          height: 30px;
          border-radius: 50%;
          cursor: pointer;
          font-size: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s ease;
        }
        .close-btn:hover {
          background: rgba(255, 255, 255, 0.15);
          color: #ffffff;
        }
        .modal-body {
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .section-label {
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1px;
          color: #94a3b8;
          margin-bottom: 2px;
        }
        .options-group {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .option-card {
          display: flex;
          align-items: center;
          padding: 14px 16px;
          border-radius: 16px;
          background: rgba(255, 255, 255, 0.03);
          border: 1.5px solid rgba(255, 255, 255, 0.08);
          cursor: pointer;
          gap: 14px;
          transition: all 0.2s ease;
        }
        .option-card:hover {
          background: rgba(255, 255, 255, 0.06);
          border-color: rgba(255, 255, 255, 0.18);
          transform: translateY(-1px);
        }
        .option-card.active {
          background: rgba(14, 165, 233, 0.15);
          border-color: #38bdf8;
          box-shadow: 0 0 20px rgba(14, 165, 233, 0.25);
        }
        .option-icon {
          width: 44px;
          height: 44px;
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.06);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 22px;
          flex-shrink: 0;
        }
        .option-card.active .option-icon {
          background: rgba(14, 165, 233, 0.25);
          color: #38bdf8;
        }
        .option-details {
          flex: 1;
        }
        .option-name {
          font-size: 14px;
          font-weight: 700;
          color: #ffffff;
          margin-bottom: 2px;
        }
        .option-desc {
          font-size: 11px;
          color: #94a3b8;
          line-height: 1.3;
        }
        .radio-dot {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          border: 2px solid rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .option-card.active .radio-dot {
          border-color: #38bdf8;
          background: #38bdf8;
        }
        .radio-dot::after {
          content: '';
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #ffffff;
          display: none;
        }
        .option-card.active .radio-dot::after {
          display: block;
        }

        /* Toggle Header Row */
        .toggle-box {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 14px 16px;
          border-radius: 16px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          gap: 12px;
        }
        .toggle-info {
          flex: 1;
        }
        .toggle-title {
          font-size: 14px;
          font-weight: 700;
          color: #ffffff;
          margin-bottom: 2px;
        }
        .toggle-desc {
          font-size: 11px;
          color: #94a3b8;
          line-height: 1.3;
        }
        .switch {
          position: relative;
          display: inline-block;
          width: 48px;
          height: 26px;
          flex-shrink: 0;
        }
        .switch input {
          opacity: 0;
          width: 0;
          height: 0;
        }
        .slider {
          position: absolute;
          cursor: pointer;
          top: 0; left: 0; right: 0; bottom: 0;
          background-color: rgba(255, 255, 255, 0.15);
          transition: .3s;
          border-radius: 26px;
        }
        .slider:before {
          position: absolute;
          content: "";
          height: 20px;
          width: 20px;
          left: 3px;
          bottom: 3px;
          background-color: white;
          transition: .3s;
          border-radius: 50%;
        }
        input:checked + .slider {
          background-color: #38bdf8;
        }
        input:checked + .slider:before {
          transform: translateX(22px);
        }
      </style>

      <div class="fab-btn ${isClassic ? 'fab-classic' : 'fab-luxury'}" id="fab-btn" title="Personalizza Grafica">
        <ha-icon icon="${icon}"></ha-icon>
      </div>

      <div class="modal-overlay" id="modal-overlay">
        <div class="modal-card ${isClassic ? 'modal-classic' : 'modal-luxury'}">
          <div class="modal-header">
            <div class="modal-title">
              <span>🎨</span> Personalizzazione Dashboard
            </div>
            <button class="close-btn" id="close-btn">✕</button>
          </div>
          <div class="modal-body">
            <div>
              <div class="section-label">Stile Schede Termostati</div>
              <div class="options-group">
                <div class="option-card ${currentStyle === 'luxury' ? 'active' : ''}" id="opt-luxury">
                  <div class="option-icon">💎</div>
                  <div class="option-details">
                    <div class="option-name">Luxury Vector Arc (Nuovo)</div>
                    <div class="option-desc">Design moderno con arco vettoriale a 270°, regolazione touch e tema glassmorphic.</div>
                  </div>
                  <div class="radio-dot"></div>
                </div>

                <div class="option-card ${currentStyle === 'classic' ? 'active' : ''}" id="opt-classic">
                  <div class="option-icon">🏛️</div>
                  <div class="option-details">
                    <div class="option-name">Standard Home Assistant (Classico)</div>
                    <div class="option-desc">Manopola circolare standard originale di Home Assistant.</div>
                  </div>
                  <div class="radio-dot"></div>
                </div>
              </div>
            </div>

            <div>
              <div class="section-label">Visualizzazione Interfaccia</div>
              <div class="toggle-box">
                <div class="toggle-info">
                  <div class="toggle-title">Nascondi Barra Superiore</div>
                  <div class="toggle-desc">Nasconde la barra in alto per una vista pulita. Disattiva per far riapparire la matita di modifica e i menu.</div>
                </div>
                <label class="switch">
                  <input type="checkbox" id="header-toggle" ${hideHeader ? 'checked' : ''}>
                  <span class="slider"></span>
                </label>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    const fab = this.shadowRoot.querySelector('#fab-btn');
    if (fab) fab.addEventListener('click', () => this.openModal());

    const closeBtn = this.shadowRoot.querySelector('#close-btn');
    if (closeBtn) closeBtn.addEventListener('click', () => this.closeModal());

    const overlay = this.shadowRoot.querySelector('#modal-overlay');
    if (overlay) overlay.addEventListener('click', (e) => {
      if (e.target === overlay) this.closeModal();
    });

    const optLuxury = this.shadowRoot.querySelector('#opt-luxury');
    if (optLuxury) optLuxury.addEventListener('click', () => this.setStyle('luxury'));

    const optClassic = this.shadowRoot.querySelector('#opt-classic');
    if (optClassic) optClassic.addEventListener('click', () => this.setStyle('classic'));

    const headerToggle = this.shadowRoot.querySelector('#header-toggle');
    if (headerToggle) {
      headerToggle.addEventListener('change', (e) => {
        this.toggleHeader(e.target.checked);
      });
    }
  }
}

if (!customElements.get("multizone-thermostat-style-switcher")) {
  customElements.define("multizone-thermostat-style-switcher", MultizoneThermostatStyleSwitcher);
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

    // Fallback: discover climate.multizone_thermostat_* not yet found
    for (const entityId of Object.keys(hass.states)) {
      const isFallbackMatch = entityId.startsWith("climate.multizone_thermostat_") ||
        (entityId.startsWith("climate.") && (hass.states[entityId]?.attributes?.hybrid_zone === true || this._hass?.states?.[entityId]?.attributes?.hybrid_zone === true));
      if (isFallbackMatch && !zones.some(z => z.climate === entityId)) {
        const climateState = hass.states[entityId];
        if (climateState) {
          let title = climateState.attributes.friendly_name || entityId;
          title = title.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
          zones.push({
            climate: entityId,
            title: title,
          });
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
        if (climateId && !zones.some(z => z.climate === climateId)) {
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

    // Fallback: discover climate.multizone_thermostat_* not yet found
    for (const entityId of Object.keys(hass.states)) {
      const isFallbackMatch = entityId.startsWith("climate.multizone_thermostat_") ||
        (entityId.startsWith("climate.") && (hass.states[entityId]?.attributes?.hybrid_zone === true || this._hass?.states?.[entityId]?.attributes?.hybrid_zone === true));
      if (isFallbackMatch && !zones.some(z => z.climate === entityId)) {
        const climateState = hass.states[entityId];
        if (climateState) {
          let title = climateState.attributes.friendly_name || entityId;
          title = title.replace(/^Virtual Thermostats VT /i, '').replace(/^Heating Zones(?: Zone)? /i, '');
          const discoveredSwitch = typeof autoDiscoverSwitch === 'function' ? autoDiscoverSwitch(hass, entityId) : "";
          zones.push({
            climate: entityId,
            switch: discoveredSwitch || null,
            title: title,
          });
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

