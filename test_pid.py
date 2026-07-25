import sys
sys.path.insert(0, "custom_components/multizone_thermostat")
import time
from pid_wrapper import MultizonePID

def test_pid():
    print("Initializing PID with Kp=100, Ki=0.5, Kd=0...")
    # Fast timeout for testing: 2 seconds
    pid = MultizonePID(kp=100.0, ki=0.5, kd=0.0, out_min=0.0, out_max=100.0, sensor_timeout=2.0)
    
    target = 20.0
    current = 18.0
    
    print(f"Target: {target}°C, Current: {current}°C")
    pid.update_sensor_timestamp()
    demand = pid.calc(current, target)
    print(f"Initial Demand: {demand:.1f}%")
    
    print("Waiting 1 second (simulating time passing)...")
    time.sleep(1)
    
    current = 19.0
    print(f"Target: {target}°C, Current: {current}°C")
    pid.update_sensor_timestamp()
    demand = pid.calc(current, target)
    print(f"Demand after 1s: {demand:.1f}%")
    
    print("Waiting 3 seconds (simulating Dead Sensor)...")
    time.sleep(3)
    
    # We don't call update_sensor_timestamp, but we call calc (as if the target temp changed or a timer triggered it)
    print("Triggering calc without sensor update...")
    demand = pid.calc(current, target)
    print(f"Demand (should be 0 due to timeout): {demand:.1f}%")
    
    if demand == 0.0:
        print("✅ Dead Sensor Timeout Test PASSED!")
    else:
        print("❌ Dead Sensor Timeout Test FAILED!")

if __name__ == "__main__":
    test_pid()
