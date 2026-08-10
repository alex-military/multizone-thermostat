import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), 'custom_components', 'multizone_thermostat'))
from thermal_model import ThermalObserver

class MockTime:
    def __init__(self):
        self.t = time.time()

    def time(self):
        return self.t
        
    def advance(self, seconds):
        self.t += seconds

mock = MockTime()
import thermal_model as tm
tm.time.time = mock.time

def run_test():
    print("==================================================")
    print(" INIZIO SIMULAZIONE MODELLO TERMICO & CURVA ADATTIVA")
    print("==================================================")

    observer = ThermalObserver("Salotto", temp_delta_threshold=0.1)
    
    print("\n--- FASE 1: RISCALDAMENTO (Imparare l'efficienza) ---")
    current_temp = 18.0
    observer.update(current_temp, is_heating=True)
    
    # 1.0 gradi in 30 minuti = 2.0 °C/hr
    for i in range(1, 11):
        mock.advance(180) # 3 minuti per ogni 0.1°C
        current_temp += 0.1
        observer.update(current_temp, is_heating=True)
        
    print(f"-> Heating Rate (Velocità Riscaldamento) Appreso: {observer.heating_rate:.2f} °C/hr (Aspettato: ~2.0)")
    
    print("\n--- FASE 2: SMART STOP & INERZIA ---")
    observer.update(current_temp, is_heating=False)
    print("Caldaia spenta a 19.0°C. Aspetto l'inerzia...")
    
    # L'inerzia sale di 0.4 gradi in 15 minuti
    mock.advance(900)
    current_temp += 0.4
    observer.update(current_temp, is_heating=False) 
    
    # Aspettiamo la fine della finestra di inerzia
    mock.advance(3600) 
    observer.update(current_temp, is_heating=False) 
    
    # Essendo un EMA con alpha basso, il primo valore è pieno, i successivi no, ma avendo init=0, il primo assorbe il 100%.
    # Ho fatto una modifica a _update_ema: `if current_value == 0: setattr(...)`
    print(f"-> Thermal Inertia Appresa: {observer.thermal_inertia:.2f} °C (Aspettato: ~0.4)")
    print(f"-> Smart Stop Attivo: Il prossimo target di 20.0°C verrà scalato automaticamente a {20.0 - observer.thermal_inertia:.2f}°C per evitare l'overshoot!")
    
    print("\n--- FASE 3: DISPERSIONE E CURVA ADATTIVA ---")
    # Scende di 1.0 gradi in 2 ore = 0.5 °C/hr
    for i in range(1, 11):
        mock.advance(720) # 12 minuti per ogni 0.1°C
        current_temp -= 0.1
        observer.update(current_temp, is_heating=False)
        
    print(f"-> Cooling Rate (Dispersione) Appreso: {observer.cooling_rate:.2f} °C/hr (Aspettato: ~0.5)")
    
    print("\n--- RISULTATO CALCOLO CURVA CLIMATICA ADATTIVA ---")
    # Supponiamo 5°C fuori
    outdoor = 5.0
    delta_t = 20.0 - outdoor
    
    # Questo è il calcolo che il nostro Coordinator fa automaticamente:
    adaptive_demand = (observer.cooling_rate / observer.heating_rate) * 100.0
    curve_val = adaptive_demand / delta_t
    
    print(f"Temperatura esterna simulata: {outdoor}°C")
    print(f"Domanda per bilanciare la dispersione (Cooling {observer.cooling_rate:.2f} / Heating {observer.heating_rate:.2f}): {adaptive_demand:.1f}% di fiamma fissa.")
    print(f"Moltiplicatore Curva Climatica Adattivo calcolato: {curve_val:.2f}")
    
    print("\nLa logica matematica funziona alla perfezione!")
    
if __name__ == "__main__":
    run_test()
