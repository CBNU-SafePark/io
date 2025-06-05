#!/bin/bash
#
# camera.sh
#
# MJPG-Streamer로 USB 웹캠 영상을 HTTP MJPEG 스트림으로 송출하는 스크립트
# - 설치: sudo apt install mjpg-streamer
# - 실행 권한 부여: chmod +x camera.sh
# - 실행 예시: ./camera.sh [디바이스] [포트]
# - 기본 디바이스: /dev/video0
# - 기본 포트: 5000
#
# 브라우저에서 http://localhost:8080/?action=stream 으로 접속

# 기본 설정
DEVICE="/dev/video0"
PORT=5000

# 입력값 파싱
if [ $# -ge 1 ]; then
    DEVICE="$1"
fi

if [ $# -ge 2 ]; then
    PORT="$2"
fi

echo "Starting MJPG-Streamer..."
echo "Device : $DEVICE"
echo "Port   : $PORT"

# 실행
mjpg_streamer \
    -i "input_uvc.so -d $DEVICE -r 640x480 -f 30" \
    -o "output_http.so -p $PORT -w /usr/share/mjpg-streamer/www"

# 참고:
# -r: 해상도 (ex. 640x480)
# -f: 프레임레이트 (ex. 30fps)
# -w: MJPG 웹 페이지 루트 디렉토리 (기본: /usr/share/mjpg-streamer/www)
