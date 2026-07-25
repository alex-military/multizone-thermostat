import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'custom_components', 'multizone_thermostat'))

from autotune import PassiveAutotuneObserver
import time

def simulate_room(observer):
    current_time = time.time()
    temp = 18.0
    
    # Idle for 5 minutes
    for i in range(5):
        observer.update(temp, False, current_time)
        current_time += 60
        
    # Heater ON (State goes to HEATING)
    # Dead time of 2 minutes where temp stays 18.0
    observer.update(temp, True, current_time)
    for i in range(2):
        current_time += 60
        observer.update(temp, True, current_time)
        
    # Temperature rises at 0.05 °C/sec = 3 °C/min
    for i in range(5):
        current_time += 60
        temp += 1.0 # 1 degree per minute for this test
        observer.update(temp, True, current_time)
        
    # Heater OFF (State goes to COOLING)
    observer.update(temp, False, current_time)
    
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    observer = PassiveAutotuneObserver("TestRoom", required_cycles=3)
    print(f"Initial state: {observer.state}")
    
    # Cycle 1
    simulate_room(observer)
    print(f"After Cycle 1: state={observer.state}, cycles={len(observer.completed_cycles)}")
    
    # Cycle 2
    simulate_room(observer)
    
    # Cycle 3
    simulate_room(observer)
    print(f"After Cycle 3: state={observer.state}")
    print(f"Final PID: Kp={observer.kp}, Ki={observer.ki}, Kd={observer.kd}")
