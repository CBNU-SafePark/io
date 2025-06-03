# io_server.py

# FastAPI import
from fastapi import FastAPI, HTTPException

# 액추에이터와 센서
import actuator_server
import lib.sensor as sensor

# 포트 정보
from portmap import IO_SERVER_PORT


# FastAPI 빌드
app = FastAPI()

# 센서 ---------------------------------------
# 센서 거리 저장
distance_data = {i: -1 for i in range(sensor.SENSOR_COUNT)}
threshold_distance = 30  # 예시 거리 임계값

# 센서에서 감지될 때 켤 LED 맵
sensor_led_map = [
    [0],  # 센서 0에 대응하는 LED
    [1],  # 센서 1에 대응하는 LED
    [2],  # 센서 2에 대응하는 LED
    [3],  # 센서 3에 대응하는 LED
    [4],  # 센서 4에 대응하는 LED
    [5],  # 센서 5에 대응하는 LED
]

# 센서 거리 측정 시 호출 될 콜백 함수
def sensor_callback(sensor_index, distance):
    distance_data[sensor_index] = distance

    # 거리 임계값에 따라 LED 상태 변경
    if distance < threshold_distance:
        # 해당 센서에 대응하는 LED를 켭니다.
        for led_index in sensor_led_map[sensor_index]:
            actuator_server.turn_on_led(led_index)
    else:
        # 해당 센서에 대응하는 LED를 끕니다.
        for led_index in sensor_led_map[sensor_index]:
            actuator_server.turn_off_led(led_index)



# 센서 거리 측정 엔드포인트
@app.get("/sensor/{sensor_index}/distance")
def get_sensor_distance(sensor_index: int):
    """
    특정 센서의 거리를 조회합니다.
    :param sensor_index: 센서 인덱스 (0부터 시작)
    :return: 거리 값
    """
    if sensor_index < 0 or sensor_index >= sensor.SENSOR_COUNT:
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    # 현재 거리 데이터 반환
    return {"sensor_index": sensor_index, "distance": distance_data[sensor_index]}








# 액추에이터 --------------------------------------
# led 상태 저장
led_status = {i: False for i in range(12)}
# 게이트 상태 저장
gate_status = False
# 벨 상태 저장
bell_status = False

# 출력 상태 조회 엔드포인트
@app.get("/status")
def get_status():
    """
    현재 LED, 게이트, 벨의 상태를 조회합니다.
    """
    return {
        "led_status": led_status,
        "gate_status": gate_status,
        "bell_status": bell_status
    }

# led 제어 엔드포인트
# /led/{led_index}/on 또는 /led/{led_index}/off
@app.get("/led/{led_index}/{action}")
def control_led(led_index: int, action: str):
    if action == "on":
        actuator_server.turn_on_led(led_index)
        return {"message": f"LED {led_index} turned ON"}
    elif action == "off":
        actuator_server.turn_off_led(led_index)
        return {"message": f"LED {led_index} turned OFF"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'on' or 'off'.")


# 게이트 제어 엔드포인트
# /gate/open 또는 /gate/close
@app.get("/gate/{action}")
def control_gate(action: str):
    if action == "open":
        actuator_server.open_gate()
        return {"message": "Gate opened"}
    elif action == "close":
        actuator_server.close_gate()
        return {"message": "Gate closed"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'open' or 'close'.")
    
# 벨 제어 엔드포인트
# /bell/ring 또는 /bell/stop
@app.get("/bell/{action}")
def control_bell(action: str):
    if action == "ring":
        actuator_server.ring_bell()
        return {"message": "Bell ringing"}
    elif action == "stop":
        actuator_server.stop_bell()
        return {"message": "Bell stopped"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'ring' or 'stop'.")