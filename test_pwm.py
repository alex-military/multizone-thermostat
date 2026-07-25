import time
import sys
sys.path.insert(0, "custom_components/multizone_thermostat")
from pwm_engine import PWMEngine

def test_pwm():
    # 15 minutes cycle (900s)
    # min_on = 3 mins (180s)
    # min_off = 3 mins (180s)
    engine = PWMEngine(pwm_interval=900.0, min_on=180.0, min_off=180.0)
    
    # Fake time module to manipulate time
    class FakeTime:
        def __init__(self):
            self.current_time = 0.0
        def time(self):
            return self.current_time
            
    fake_time = FakeTime()
    import pwm_engine
    pwm_engine.time.time = fake_time.time
    
    engine.cycle_start_time = fake_time.time()
    
    # Test 1: Demand = 50%
    # time_on = 450, time_off = 450 (No dilatation)
    print("--- Test 1: 50% Demand ---")
    fake_time.current_time = 0.0
    state = engine.calculate(50.0)
    print(f"Time 0s, Expected: True, Got: {state}, time_on: {engine.time_on}, time_off: {engine.time_off}")
    assert state == True
    assert engine.time_on == 450.0
    
    fake_time.current_time = 451.0
    state = engine.calculate(50.0)
    print(f"Time 451s, Expected: False, Got: {state}")
    assert state == False
    
    # Test 2: Demand = 10% (Should dilate)
    # raw time_on = 90s, raw time_off = 810s
    # min_on = 180s
    # time_on becomes 180s
    # time_off becomes 810 * (180/90) = 1620s
    # Total cycle = 1800s
    print("\n--- Test 2: 10% Demand (Dilatation) ---")
    fake_time.current_time = 900.0 # start of new cycle
    engine.cycle_start_time = 900.0
    
    state = engine.calculate(10.0)
    print(f"Time 900s, Expected: True, Got: {state}, time_on: {engine.time_on}, time_off: {engine.time_off}")
    assert engine.time_on == 180.0
    assert engine.time_off == 1620.0
    
    # At 900 + 179 = 1079 it should be ON
    fake_time.current_time = 1079.0
    state = engine.calculate(10.0)
    assert state == True
    
    # At 900 + 181 = 1081 it should be OFF
    fake_time.current_time = 1081.0
    state = engine.calculate(10.0)
    assert state == False
    
    print("\n✅ PWM Engine tests passed!")

if __name__ == "__main__":
    test_pwm()
