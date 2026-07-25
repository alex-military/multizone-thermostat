import sys
import os
import time
from unittest.mock import patch

sys.path.append(os.path.join(os.path.dirname(__file__), 'custom_components', 'multizone_thermostat'))

from autotune import PassiveAutotuneObserver
from pwm_engine import PWMEngine
from pid_wrapper import MultizonePID

def run_simulation():
    print("==================================================")
    print(" SIMULAZIONE AVANZATA (TIME-WARP + PWM ENGINE)")
    print("==================================================")

    # Inizializziamo i componenti reali
    room_name = "Salone"
    autotuner = PassiveAutotuneObserver(room_name, required_cycles=3)
    pid = MultizonePID(kp=100.0, ki=0.0, kd=0.0, out_min=0.0, out_max=100.0, sensor_timeout=7200.0)
    
    # Motore PWM con ciclo di 15 minuti, min_on 2 min, min_off 2 min
    pwm_engine = PWMEngine(pwm_interval=900.0, min_on=120.0, min_off=120.0)

    current_temp = 18.0
    target_temp = 20.0
    tolerance = 0.3
    time_step = 10  # 10 secondi per tick

    # Iniziamo da mezzanotte (time = 0 per semplificare i calcoli)
    virtual_time = 0.0
    
    total_duration = 8 * 3600 # 8 ore
    
    last_boiler_state = False
    
    # Patch di time.time() per fargli credere al virtual_time
    with patch('time.time', side_effect=lambda: virtual_time):
        for elapsed in range(0, total_duration, time_step):
            virtual_time += time_step
            
            # 1. Calcolo del Demand
            if autotuner.state != autotuner.STATE_COMPLETED:
                # Modalità Isteresi
                if current_temp <= target_temp - tolerance:
                    demand = 100.0
                elif current_temp >= target_temp + tolerance:
                    demand = 0.0
                else:
                    # Mantiene l'ultimo stato (se era acceso 100, se spento 0)
                    demand = 100.0 if pwm_engine.current_state else 0.0
            else:
                # Modalità PID
                demand = pid.calc(current_temp, target_temp)
                
            # 2. Aggiornamento Autotuner
            was_completed = (autotuner.state == autotuner.STATE_COMPLETED)
            autotuner.update(current_temp, pwm_engine.current_state, now=virtual_time)
            is_completed = (autotuner.state == autotuner.STATE_COMPLETED)
            
            if is_completed and not was_completed:
                print(f"\n[{elapsed//3600:02d}:{(elapsed%3600)//60:02d}:{elapsed%60:02d}] *** AUTOTUNING COMPLETATO! ***")
                pid.set_pid_param(kp=autotuner.kp, ki=autotuner.ki, kd=autotuner.kd)
                print(f"Nuovi Parametri PID applicati: Kp={autotuner.kp:.1f}, Ki={autotuner.ki:.4f}, Kd={autotuner.kd:.1f}")
                
            # 3. Motore PWM (Gestisce min_on e min_off reali!)
            boiler_on = pwm_engine.calculate(demand)
            
            # Log changes in boiler state explicitly
            if boiler_on != last_boiler_state:
                print(f"[{elapsed//3600:02d}:{(elapsed%3600)//60:02d}:{elapsed%60:02d}] CALDAIA -> {'ON' if boiler_on else 'OFF'} (Demand: {demand:.1f}%)")
                last_boiler_state = boiler_on
            
            # 4. Termodinamica Reale dipendente dalla caldaia
            if boiler_on:
                current_temp += 0.00083 * time_step  # Sale
            else:
                current_temp -= 0.00027 * time_step  # Scende
                
            # Stampe di log periodiche
            if elapsed % 1800 == 0:
                mode_str = "PID" if is_completed else "ISTERESI"
                print(f"[{elapsed//3600:02d}:{(elapsed%3600)//60:02d}:{elapsed%60:02d}] Temp: {current_temp:.2f}°C | Mode: {mode_str} | Demand: {demand:.1f}%")

if __name__ == "__main__":
    import logging
    logging.getLogger('autotune').setLevel(logging.INFO)
    logging.getLogger('pwm_engine').setLevel(logging.WARNING) # Evitiamo inondazioni, logga solo WARNING
    logging.basicConfig(format='%(levelname)s: %(message)s')
    run_simulation()
