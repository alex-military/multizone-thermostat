import sys
import os
import time
import asyncio
from unittest.mock import MagicMock

# Add integration to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'custom_components', 'multizone_thermostat'))

from autotune import PassiveAutotuneObserver
from pwm_engine import PWMEngine
from pid_wrapper import MultizonePID

def run_simulation():
    print("==================================================")
    print(" INIZIO SIMULAZIONE DI SISTEMA (3 CICLI VIRTUALI)")
    print("==================================================")

    # 1. Inizializza i componenti per una stanza
    room_name = "Salone"
    autotuner = PassiveAutotuneObserver(room_name, required_cycles=3)
    pid = MultizonePID(kp=100.0, ki=0.0, kd=0.0, out_min=0.0, out_max=100.0, sensor_timeout=7200.0)

    # Variabili di stato della stanza
    current_temp = 18.0
    target_temp = 20.0
    tolerance = 0.3
    room_valve_open = False
    boiler_on = False

    time_step = 10  # secondi per ogni iterazione (PWM tick rate)
    simulated_time = time.time()
    
    print(f"[{time.strftime('%H:%M:%S', time.localtime(simulated_time))}] Configurazione: Target {target_temp}°C, Tolerance {tolerance}°C")

    # Ciclo di simulazione: 8 ore per dare tempo di completare 3 cicli di riscaldamento naturale
    total_duration = 8 * 60 * 60
    
    for elapsed in range(0, total_duration, time_step):
        simulated_time += time_step
        
        # 1. Calcolo del Demand
        if autotuner.state != autotuner.STATE_COMPLETED:
            # Modalità Isteresi (Apprendimento)
            if current_temp <= target_temp - tolerance:
                demand = 100.0
            elif current_temp >= target_temp + tolerance:
                demand = 0.0
            else:
                demand = 100.0 if room_valve_open else 0.0 # Mantiene lo stato
        else:
            # Modalità PID
            demand = pid.calc(current_temp, target_temp)
            
        # 2. Aggiornamento Autotuner
        was_completed = (autotuner.state == autotuner.STATE_COMPLETED)
        autotuner.update(current_temp, demand > 0, now=simulated_time)
        is_completed = (autotuner.state == autotuner.STATE_COMPLETED)
        
        if is_completed and not was_completed:
            print(f"\n[{time.strftime('%H:%M:%S', time.localtime(simulated_time))}] *** AUTOTUNING COMPLETATO! ***")
            pid.set_pid_param(kp=autotuner.kp, ki=autotuner.ki, kd=autotuner.kd)
            print(f"Nuovi Parametri PID applicati: Kp={autotuner.kp:.1f}, Ki={autotuner.ki:.4f}, Kd={autotuner.kd:.1f}")
            print("Passaggio automatico da Isteresi a PID Attivo.\n")
            
        # 3. PWM Valvola Stanza
        # Inject simulated_time to PWM engine calculation logic
        # Since PWMEngine uses time.time(), we can't easily mock it without patching.
        # For simulation, we just use the demand.
        room_valve_open = (demand > 0)
        
        # 4. PWM Caldaia
        # In a real system, PWM engine is updated with real time.
        boiler_on = (demand > 0)
        
        # 5. Simulazione Termica (Fisica della Stanza)
        # Se la caldaia è accesa e la valvola è aperta, la temperatura sale
        # Se spenta, la temperatura scende per dispersione
        if boiler_on and room_valve_open:
            # Riscaldamento: 1 grado ogni 20 minuti (0.05 gradi al minuto = 0.00083 gradi al secondo)
            current_temp += 0.00083 * time_step
        else:
            # Dispersione: 1 grado ogni 60 minuti (0.016 gradi al minuto = 0.00027 gradi al secondo)
            current_temp -= 0.00027 * time_step
            
        # Logica di stampa ridotta per non inondare la console
        if elapsed % 600 == 0:  # Stampa ogni 10 minuti di simulazione
            mode_str = "PID" if is_completed else "ISTERESI"
            print(f"[{time.strftime('%H:%M:%S', time.localtime(simulated_time))}] Temp: {current_temp:.2f}°C | Mode: {mode_str} | Demand: {demand:.1f}% | Caldaia: {'ON' if boiler_on else 'OFF'}")

    print("==================================================")
    print(" SIMULAZIONE COMPLETATA CON SUCCESSO")
    print("==================================================")
    print(f"Temperatura finale: {current_temp:.2f}°C")
    print(f"Parametri PID attivi: Kp={autotuner.kp:.1f}, Ki={autotuner.ki:.4f}, Kd={autotuner.kd:.1f}")

if __name__ == "__main__":
    import logging
    logging.getLogger('autotune').setLevel(logging.INFO)
    logging.basicConfig(format='%(levelname)s: %(message)s')
    run_simulation()
