# actuator.py
import RPi.GPIO as GPIO
import time
import smbus

CONSOLE_PREFIX = "Actuator: "


# LED ----------------------------------------------------------------
LED_I2C_ADDRESS = 0x08 # 아두이노 LED I2C 주소
MAX_LED_INDEX = 11  # 최대 LED 인덱스 (0부터 시작하므로 11은 12번째 LED)

bus = smbus.SMBus(1)  # 라즈베리파이 GPIO2(SDA), GPIO3(SCL) 를 연결

def turn_on_led(led_index):
    # 입력값 검증
    if not isinstance(led_index, int) or led_index < 0 or led_index > MAX_LED_INDEX:
        print(f"{CONSOLE_PREFIX}Invalid LED index: {led_index}. Must be between 0 and {MAX_LED_INDEX}.")
        return
    
    print(f"{CONSOLE_PREFIX}LED {led_index} ON")
    try:
        bus.write_byte(LED_I2C_ADDRESS, 0, [led_index, 1])
    except Exception as e:
        print(f"{CONSOLE_PREFIX}Error turning on LED {led_index}: {e}")

def turn_off_led(led_index):
    # 입력값 검증
    if not isinstance(led_index, int) or led_index < 0 or led_index > MAX_LED_INDEX:
        print(f"{CONSOLE_PREFIX}Invalid LED index: {led_index}. Must be between 0 and {MAX_LED_INDEX}.")
        return
    
    print(f"{CONSOLE_PREFIX}LED {led_index} OFF")
    try:
        bus.write_byte(LED_I2C_ADDRESS, 0, [led_index, 0])
    except Exception as e:
        print(f"{CONSOLE_PREFIX}Error turning off LED {led_index}: {e}")

# End of LED ------------------------------------------------------------
# GATE (Servo) ----------------------------------------------------------------

SERVO_PIN = 18  # GPIO 핀 번호
OPEN_ANGLE = 90  # 게이트 열기 각도
CLOSE_ANGLE = 0  # 게이트 닫기 각도

GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo = GPIO.PWM(SERVO_PIN, 50)  # 50Hz 주파수로 PWM 설정
servo.start(0)  # PWM 시작, 초기 듀티 사이클 0%

def open_gate():
    print("Gate opned")
    duty = 2.5 + ( OPEN_ANGLE / 180.0) * 10.0
    servo.ChangeDutyCycle(duty)

def close_gate():
    print("Gate closed")
    duty = 2.5 + ( CLOSE_ANGLE / 180.0) * 10.0
    servo.ChangeDutyCycle(duty)

# End of GATE (Servo) ------------------------------------------------------------

# BELL (Buzzer) ----------------------------------------------------------------

BUZZER_PIN = 23  # GPIO 핀 번호
GPIO.setup(BUZZER_PIN, GPIO.OUT)

def ring_bell():
    print("Bell ringing")
    GPIO.output(BUZZER_PIN, GPIO.HIGH)  # 버저 켜기

def stop_bell():
    print("Bell stopped")
    GPIO.output(BUZZER_PIN, GPIO.LOW)  # 버저 끄기

# End of BELL (Buzzer) ------------------------------------------------------------

# Cleanup GPIO settings
def cleanup():
    print("Cleaning up GPIO settings...")
    servo.stop()  # PWM 정지
    GPIO.cleanup()  # GPIO 설정 초기화


# 테스트 실시
if __name__ == "__main__":
    try:
        print(f"{CONSOLE_PREFIX}Starting actuator test...")

        print(f"{CONSOLE_PREFIX}Testing LEDs...")
        for i in range(0, MAX_LED_INDEX + 1):
            print(f"{CONSOLE_PREFIX}Turning on LED {i}")
            turn_on_led(i)
            time.sleep(1)
            print(f"{CONSOLE_PREFIX}Turning off LED {i}")
            turn_off_led(i)
            time.sleep(0.5)

        print(f"{CONSOLE_PREFIX}Testing gate...")
        print(f"{CONSOLE_PREFIX}Opening gate...")
        open_gate()
        time.sleep(2)
        print(f"{CONSOLE_PREFIX}Closing gate...")
        close_gate()
        time.sleep(2)

        print(f"{CONSOLE_PREFIX}Testing bell...")
        print(f"{CONSOLE_PREFIX}Ringing bell...")
        ring_bell()
        time.sleep(2)
        stop_bell()
        print(f"{CONSOLE_PREFIX}Bell stopped.")

    except KeyboardInterrupt:
        print("Program interrupted by user.")
    finally:
        cleanup()  # GPIO 설정 초기화