# sensor.py

import RPi.GPIO as GPIO
import time
import threading

CONSOLE_PREFIX = "Sensor: "

from pinmap import TRIG_1, ECHO_1
from pinmap import TRIG_2, ECHO_2
from pinmap import TRIG_3, ECHO_3
from pinmap import TRIG_4, ECHO_4
from pinmap import TRIG_5, ECHO_5

trig_pins = []
trig_pins.append(TRIG_1)
trig_pins.append(TRIG_2)
trig_pins.append(TRIG_3)
trig_pins.append(TRIG_4)
trig_pins.append(TRIG_5)

echo_pins = []
echo_pins.append(ECHO_1)
echo_pins.append(ECHO_2)
echo_pins.append(ECHO_3)
echo_pins.append(ECHO_4)
echo_pins.append(ECHO_5)

# 센서 갯수 초기화
SENSOR_COUNT = len(trig_pins)

GPIO.setmode(GPIO.BCM)

# GPIO 핀 설정
for trig_pin, echo_pin in zip(trig_pins, echo_pins):
    GPIO.setup(trig_pin, GPIO.OUT)
    GPIO.setup(echo_pin, GPIO.IN)

# 한번 거리 측정
def measure_distance(trig_pin, echo_pin):
    # Pulse 생성
    GPIO.output(trig_pin, True)
    time.sleep(0.00001)
    GPIO.output(trig_pin, False)

    timeout = time.time() + 0.1

    # Echo HIGH 대기
    while GPIO.input(echo_pin) == 0 and time.time() < timeout:
        pass
    if time.time() >= timeout:
        return -1  # 타임아웃 오류

    pulse_start = time.time()

    # Echo LOW 대기
    while GPIO.input(echo_pin) == 1 and time.time() < timeout:
        pass
    if time.time() >= timeout:
        return -1  # 타임아웃 오류

    pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    distance = round(distance, 2)
    return distance

# 측정 돌리는 루프, interval(초)에 한번씩 해당 센서의 거리를 측정
# callback(pin)
def measure_thread(interval, callback):
    while True:
        
        index = 0
        
        for trig_pin, echo_pin in zip(trig_pins, echo_pins):
            distance = measure_distance(
                trig_pin, 
                echo_pin)
            
            callback(index, distance)
            
            index += 1

            time.sleep(interval)

# 테스트 실시
if __name__ == "__main__":
    test_index_pin = 0 # 테스트하려면 이 부분 수정
    interval = 0.5

    # 콜백 구현, (단순히 거리 측정)
    def callback(pin_index, distance):
        print(f"{CONSOLE_PREFIX}{pin_index}에서 측정된 거리 : {distance}")

    measure_thread(interval, callback)