# actuator_server.py
import socket
import lib.actuator as actuator
from portmap import ACTUATOR_SERVER_PORT

def turn_on_led(led_index):
    actuator.turn_on_led(led_index)

def turn_off_led(led_index):
    actuator.turn_off_led(led_index)

def open_gate():
    actuator.open_gate()

def close_gate():
    actuator.close_gate()

def ring_bell():
    actuator.ring_bell()

def stop_bell():
    actuator.stop_bell()

HOST = '127.0.0.1'
PORT = ACTUATOR_SERVER_PORT

# 소켓으로 들어온 command를 처리하는 함수
def handle_command(command):
    print(f"Received command: {command}")
    # LED 처리
    if command[0] == "LED":
        try:
            led_index = int(command[1])

            if led_index < 0 or actuator.MAX_LED_INDEX < led_index:
                print(f"Invalid LED index: {led_index}. Must be between 0 and {actuator.MAX_LED_INDEX}.")
                return
            if command[2] == "ON":
                print(f"Turning on LED {led_index}")
                turn_on_led(led_index)
            elif command[2] == "OFF":
                print(f"Turning off LED {led_index}")
                turn_off_led(led_index)
            else:
                print("Unknown command for LED")
        except ValueError:
            print("Invalid LED index")

    # GATE 처리
    elif command[0] == "GATE":
        if command[1] == "OPEN":
            print("Opening gate")
            open_gate()
        elif command[1] == "CLOSE":
            print("Closing gate")
            close_gate()
        else:
            print("Unknown command for gate")

    # BELL 처리
    elif command[0] == "BELL":
        if command[1] == "RING":
            print("Ringing bell")
            ring_bell()
        elif command[1] == "STOP":
            print("Stopping bell")
            stop_bell()
        else:
            print("Unknown command for bell")

    else:
        print("Invalid command format")

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Socket Listen 
        s.bind((HOST, PORT))
        s.listen()
        print("Actuator server waiting for connection...")
        conn, addr = s.accept()
        
        with conn:
            print(f"Connected by {addr}")
            buffer = ""
            while True:
                try:
                    data = conn.recv(1024)
                    if not data:
                        print("Controller disconnected.")
                        break

                    # 데이터 수신 처리, 첫 번쨰 줄만 처리하고 나머지 버림
                    buffer += data.decode('utf-8')
                    lines = buffer.split('\n')
                    buffer = lines[-1]  # 마지막 줄은 아직 안 끝났을 수도 있음
                    for message in lines[:-1]:
                        command = message.strip().split()
                        if len(command) >= 3:
                            handle_command(command)
                        else:
                            print("Invalid command format") 

                except KeyboardInterrupt:
                    print("LED program stopped manually.")
                    conn.close()
                    print("Connection closed.")
                    actuator.cleanup()
                    break
                except Exception as e:
                    print(f"Unexpected error: {e}")
                    conn.close()
                    print("Connection closed.")
                    actuator.cleanup()
                    break

if __name__ == "__main__":
    main()
