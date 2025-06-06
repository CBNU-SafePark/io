#!/usr/bin/env python3
import cv2
import numpy as np
import os
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("RPi.GPIO를 설치해라: pip3 install --break-system-packages RPi.GPIO")
    exit(1)
import time
import threading
from collections import deque
import math

class ParkingTracker:
    def __init__(self, headless=False):
        self.headless = headless  # 헤드리스 모드 설정
        
        # GPIO 설정
        self.LED_PIN = 18
        self.TRIG_PIN = 24
        self.ECHO_PIN = 23
        
        # GPIO 초기화
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.LED_PIN, GPIO.OUT)
        GPIO.setup(self.TRIG_PIN, GPIO.OUT)
        GPIO.setup(self.ECHO_PIN, GPIO.IN)
        GPIO.output(self.LED_PIN, GPIO.LOW)
        GPIO.output(self.TRIG_PIN, GPIO.LOW)
        
        # 카메라 설정
        self.cap = None
        self.initialize_camera()
        
        # 주차장 영역 좌표 (초기값, 마우스로 설정 가능)
        self.parking_area = []
        self.setting_area = False
        
        # 색상 범위 설정 (HSV)
        self.color_ranges = {
            'red': ([0, 50, 50], [10, 255, 255]),
            'red2': ([170, 50, 50], [180, 255, 255]),  # 빨간색 두 번째 범위
            'blue': ([100, 50, 50], [130, 255, 255]),
            'orange': ([10, 50, 50], [25, 255, 255]),   # 주황색 추가
            'yellow': ([25, 50, 50], [35, 255, 255])    # 노란색 범위 조정
        }
        
        # 탐지된 차량 추적
        self.tracked_cars = deque(maxlen=10)  # 최근 10프레임 저장
        
        # 경고 설정
        self.warning_distance = 100  # 픽셀 단위
        self.last_warning_time = 0
        self.warning_cooldown = 2.0  # 2초 쿨다운
        
        # 헤드리스 모드용 설정
        self.frame_count = 0
        self.save_interval = 30  # 30프레임마다 이미지 저장
        
        # 기본 주차장 영역 (헤드리스 모드용)
        if self.headless:
            self.setup_default_parking_area()
    
    def initialize_camera(self):
        """카메라 초기화 with 디버깅"""
        print("카메라 초기화 중...")
        
        # 여러 백엔드 시도
        backends = [
            (cv2.CAP_V4L2, "V4L2"),
            (cv2.CAP_GSTREAMER, "GStreamer"), 
            (cv2.CAP_ANY, "Any")
        ]
        
        # 여러 디바이스 번호 시도
        device_ids = [0, 1, 2]
        
        for device_id in device_ids:
            print(f"디바이스 {device_id} 시도 중...")
            
            for backend, backend_name in backends:
                print(f"  {backend_name} 백엔드로 시도 중...")
                
                try:
                    self.cap = cv2.VideoCapture(device_id, backend)
                    
                    if self.cap.isOpened():
                        # 테스트 프레임 읽기
                        ret, frame = self.cap.read()
                        if ret and frame is not None:
                            print(f"성공! 디바이스 {device_id}, {backend_name} 백엔드")
                            
                            # 해상도 설정
                            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                            self.cap.set(cv2.CAP_PROP_FPS, 15)
                            
                            # 실제 설정된 값 확인
                            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            fps = self.cap.get(cv2.CAP_PROP_FPS)
                            
                            print(f"해상도: {width}x{height}, FPS: {fps}")
                            return
                        else:
                            print(f"  프레임을 읽을 수 없음")
                            self.cap.release()
                    else:
                        print(f"  카메라를 열 수 없음")
                        
                except Exception as e:
                    print(f"  오류: {e}")
                    if self.cap:
                        self.cap.release()
        
        print("사용 가능한 카메라를 찾을 수 없다!")
        print("해결방법:")
        print("1. USB 카메라가 제대로 연결되었는지 확인")
        print("2. 'ls /dev/video*' 명령어로 디바이스 확인") 
        print("3. 다른 프로그램에서 카메라를 사용 중인지 확인")
        self.cap = None
    
    def setup_default_parking_area(self):
        """기본 주차장 영역 설정 (헤드리스 모드용)"""
        # 1280x720 해상도 기준 기본 영역
        # 중앙 부분을 주차장으로 설정
        width, height = 1280, 720
        margin_x = width // 4
        margin_y = height // 4
        
        self.parking_area = [
            (margin_x, margin_y),                    # 좌상단
            (width - margin_x, margin_y),            # 우상단  
            (width - margin_x, height - margin_y),   # 우하단
            (margin_x, height - margin_y)            # 좌하단
        ]
        
        print(f"기본 주차장 영역 설정: {self.parking_area}")
        print("더 정확한 설정을 원한다면 프로그램 실행 후 현재 프레임을 확인하고")
        print("코드에서 parking_area 좌표를 수정해라.")
        
    def mouse_callback(self, event, x, y, flags, param):
        """마우스 콜백으로 주차장 영역 설정"""
        if self.setting_area and event == cv2.EVENT_LBUTTONDOWN:
            self.parking_area.append((x, y))
            print(f"좌표 설정: ({x}, {y})")
            
            if len(self.parking_area) == 4:
                self.setting_area = False
                print("주차장 영역 설정 완료!")
    
    def setup_parking_area(self, frame):
        """주차장 영역 설정"""
        if self.headless:
            print("헤드리스 모드: 주차장 영역을 수동으로 설정한다.")
            print("4개 모서리 좌표를 순서대로 입력해라 (좌상단 -> 우상단 -> 우하단 -> 좌하단)")
            print(f"이미지 크기: {frame.shape[1]}x{frame.shape[0]} (가로x세로)")
            
            # 현재 프레임을 파일로 저장
            cv2.imwrite('current_frame.jpg', frame)
            print("현재 화면을 'current_frame.jpg'로 저장했다. 이를 참고해서 좌표를 입력해라.")
            
            try:
                for i in range(4):
                    corner_names = ["좌상단", "우상단", "우하단", "좌하단"]
                    print(f"{corner_names[i]} 좌표를 입력해라 (x,y 형식, 예: 100,50):")
                    coord_input = input().strip()
                    x, y = map(int, coord_input.split(','))
                    self.parking_area.append((x, y))
                    print(f"{corner_names[i]} 설정: ({x}, {y})")
                
                print("주차장 영역 설정 완료!")
                return
                
            except (ValueError, KeyboardInterrupt):
                print("좌표 입력이 취소되었거나 잘못되었다.")
                self.parking_area = []
                return
        
        # GUI 모드
        print("주차장 영역을 설정한다. 검은색 주차장의 4개 모서리를 순서대로 클릭해라.")
        print("순서: 좌상단 -> 우상단 -> 우하단 -> 좌하단")
        print("잘못 클릭했으면 'r'키로 리셋, 완료되면 자동으로 닫힌다.")
        
        self.setting_area = True
        cv2.namedWindow('Setup', cv2.WINDOW_NORMAL)
        cv2.setMouseCallback('Setup', self.mouse_callback)
        
        while self.setting_area:
            display_frame = frame.copy()
            
            # 설정된 점들 표시
            for i, point in enumerate(self.parking_area):
                cv2.circle(display_frame, point, 8, (0, 255, 0), -1)
                cv2.putText(display_frame, str(i+1), 
                           (point[0]+15, point[1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # 선분 연결
            if len(self.parking_area) > 1:
                for i in range(len(self.parking_area)-1):
                    cv2.line(display_frame, self.parking_area[i], 
                            self.parking_area[i+1], (0, 255, 0), 3)
                
                # 마지막 점과 첫 번째 점 연결 (4개 점이 모두 설정되었을 때)
                if len(self.parking_area) == 4:
                    cv2.line(display_frame, self.parking_area[3], 
                            self.parking_area[0], (0, 255, 0), 3)
                    # 반투명 영역 표시
                    pts = np.array(self.parking_area, np.int32)
                    overlay = display_frame.copy()
                    cv2.fillPoly(overlay, [pts], (0, 255, 0))
                    cv2.addWeighted(overlay, 0.2, display_frame, 0.8, 0, display_frame)
            
            # 안내 메시지
            cv2.rectangle(display_frame, (5, 5), (500, 80), (0, 0, 0), -1)
            cv2.putText(display_frame, f"Click point {len(self.parking_area)+1}/4", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(display_frame, "Press 'r' to reset, 'q' to quit", 
                       (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            cv2.imshow('Setup', display_frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.parking_area = []
                print("영역 설정 리셋!")
        
        if not self.headless:
            cv2.destroyWindow('Setup')
    
    def detect_cars_by_color(self, frame):
        """색상 기반 차량 탐지 (주차장 영역 내에서만)"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        detected_cars = []
        
        # 주차장 영역이 설정되지 않았으면 전체 화면에서 탐지
        if len(self.parking_area) == 4:
            # 주차장 영역 마스크 생성
            mask_polygon = np.zeros(hsv.shape[:2], dtype=np.uint8)
            pts = np.array(self.parking_area, np.int32)
            cv2.fillPoly(mask_polygon, [pts], 255)
        else:
            mask_polygon = np.ones(hsv.shape[:2], dtype=np.uint8) * 255
        
        for color_name, (lower, upper) in self.color_ranges.items():
            if color_name == 'red2':  # 빨간색 두 번째 범위는 첫 번째와 합침
                continue
                
            lower = np.array(lower)
            upper = np.array(upper)
            
            mask = cv2.inRange(hsv, lower, upper)
            
            # 빨간색의 경우 두 범위를 합침
            if color_name == 'red':
                lower2 = np.array(self.color_ranges['red2'][0])
                upper2 = np.array(self.color_ranges['red2'][1])
                mask2 = cv2.inRange(hsv, lower2, upper2)
                mask = cv2.bitwise_or(mask, mask2)
            
            # 주차장 영역과 교집합
            mask = cv2.bitwise_and(mask, mask_polygon)
            
            # 노이즈 제거 강화
            kernel = np.ones((7,7), np.uint8)  # 커널 크기 증가
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            # 컨투어 찾기
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # 면적 필터링 강화
                if area < 800:  # 최소 면적 증가
                    continue
                    
                # 형태 필터링 추가
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / float(h)
                
                # 너무 가늘거나 긴 형태 제외
                if aspect_ratio < 0.3 or aspect_ratio > 3.0:
                    continue
                
                # 컨투어의 면적과 바운딩 박스 면적 비율
                rect_area = w * h
                extent = area / rect_area
                
                # 너무 불규칙한 형태 제외 (면적 비율이 너무 작으면)
                if extent < 0.3:
                    continue
                
                center_x = x + w // 2
                center_y = y + h // 2
                
                # 중심점이 주차장 영역 내부에 있는지 확인
                if len(self.parking_area) == 4:
                    if not self.point_in_polygon((center_x, center_y), self.parking_area):
                        continue
                
                detected_cars.append({
                    'color': color_name,
                    'center': (center_x, center_y),
                    'bbox': (x, y, w, h),
                    'area': area,
                    'aspect_ratio': aspect_ratio,
                    'extent': extent
                })
        
        return detected_cars
    
    def point_in_polygon(self, point, polygon):
        """점이 다각형 내부에 있는지 확인"""
        x, y = point
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    def calculate_distance_to_boundary(self, point):
        """주차장 경계까지의 최단 거리 계산"""
        if len(self.parking_area) < 4:
            return float('inf')
        
        x, y = point
        min_distance = float('inf')
        
        # 각 변까지의 거리 계산
        for i in range(len(self.parking_area)):
            p1 = self.parking_area[i]
            p2 = self.parking_area[(i + 1) % len(self.parking_area)]
            
            # 점과 직선 사이의 거리 계산
            A = p2[1] - p1[1]
            B = p1[0] - p2[0]
            C = p2[0] * p1[1] - p1[0] * p2[1]
            
            distance = abs(A * x + B * y + C) / math.sqrt(A * A + B * B)
            min_distance = min(min_distance, distance)
        
        return min_distance
    
    def trigger_ultrasonic(self):
        """초음파 센서 트리거"""
        GPIO.output(self.TRIG_PIN, True)
        time.sleep(0.00001)
        GPIO.output(self.TRIG_PIN, False)
        
        pulse_start = time.time()
        pulse_end = time.time()
        
        # Echo 신호 대기
        timeout = time.time() + 0.1  # 100ms 타임아웃
        while GPIO.input(self.ECHO_PIN) == 0 and time.time() < timeout:
            pulse_start = time.time()
        
        while GPIO.input(self.ECHO_PIN) == 1 and time.time() < timeout:
            pulse_end = time.time()
        
        if pulse_end > pulse_start:
            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 17150  # cm 단위
            return round(distance, 2)
        else:
            return None
    
    def handle_warning(self, cars_near_boundary):
        """경고 처리"""
        current_time = time.time()
        
        if cars_near_boundary and (current_time - self.last_warning_time) > self.warning_cooldown:
            # LED 켜기
            GPIO.output(self.LED_PIN, GPIO.HIGH)
            
            # 초음파 센서 측정
            distance = self.trigger_ultrasonic()
            
            print(f"경고! 주차장 경계에 가까운 차량 감지")
            if distance:
                print(f"초음파 센서 거리: {distance}cm")
            
            self.last_warning_time = current_time
            
            # LED를 0.5초 후 끄기
            threading.Timer(0.5, lambda: GPIO.output(self.LED_PIN, GPIO.LOW)).start()
        
        elif not cars_near_boundary:
            GPIO.output(self.LED_PIN, GPIO.LOW)
    
    def draw_interface(self, frame, detected_cars):
        """인터페이스 그리기"""
        # 주차장 영역 그리기
        if len(self.parking_area) == 4:
            pts = np.array(self.parking_area, np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], True, (255, 255, 0), 3)  # 두꺼운 노란색 선
            
            # 반투명 오버레이 추가
            overlay = frame.copy()
            cv2.fillPoly(overlay, [pts], (255, 255, 0))
            cv2.addWeighted(overlay, 0.1, frame, 0.9, 0, frame)
        
        # 탐지된 차량 표시
        cars_near_boundary = []
        
        for car in detected_cars:
            center = car['center']
            bbox = car['bbox']
            color_name = car['color']
            area = car['area']
            
            # 바운딩 박스 그리기
            x, y, w, h = bbox
            color_map = {
                'red': (0, 0, 255), 
                'blue': (255, 0, 0), 
                'orange': (0, 165, 255),  # 주황색 추가
                'yellow': (0, 255, 255)
            }
            color = color_map.get(color_name, (0, 255, 0))
            
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 3)
            cv2.circle(frame, center, 8, color, -1)
            
            # 차량 정보 표시
            cv2.putText(frame, f"{color_name.upper()}", 
                       (x, y - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            # 좌표 표시
            cv2.putText(frame, f"({center[0]}, {center[1]})", 
                       (x, y - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # 면적 표시
            cv2.putText(frame, f"Area: {area}", 
                       (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # 경계까지의 거리 계산
            if len(self.parking_area) == 4:
                if self.point_in_polygon(center, self.parking_area):
                    distance_to_boundary = self.calculate_distance_to_boundary(center)
                    
                    cv2.putText(frame, f"Dist: {distance_to_boundary:.1f}px", 
                               (x, y + h + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                    
                    if distance_to_boundary < self.warning_distance:
                        cars_near_boundary.append(car)
                        # 경고 표시
                        cv2.putText(frame, "WARNING!", 
                                   (x, y - 55), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                        # 경고 박스
                        cv2.rectangle(frame, (x-5, y-5), (x + w + 5, y + h + 5), (0, 0, 255), 3)
        
        # 상태 정보 표시 (배경 추가)
        cv2.rectangle(frame, (5, 5), (400, 100), (0, 0, 0), -1)  # 검은 배경
        cv2.rectangle(frame, (5, 5), (400, 100), (255, 255, 255), 2)  # 흰 테두리
        
        cv2.putText(frame, f"Total cars detected: {len(detected_cars)}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Cars near boundary: {len(cars_near_boundary)}", 
                   (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Parking area: {'SET' if len(self.parking_area) == 4 else 'NOT SET'}", 
                   (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return cars_near_boundary
    
    def run(self):
        """메인 실행 루프"""
        print("미니카 주차장 추적 시스템 시작")
        
        if self.cap is None:
            print("카메라 초기화 실패. 프로그램을 종료한다.")
            return
            
        if self.headless:
            print("헤드리스 모드로 실행 중...")
            print("Ctrl+C로 종료")
            print("이미지는 30프레임마다 'output_XXXX.jpg'로 저장된다.")
        else:
            print("GUI 모드로 실행 중...")
            print("'s' - 주차장 영역 설정 (검은색 주차장 부분만 선택)")
            print("'r' - 주차장 영역 리셋")
            print("'q' - 종료")
            print("먼저 's'를 눌러서 주차장 영역을 설정해라!")
        
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("카메라에서 프레임을 읽을 수 없다")
                    break
                
                self.frame_count += 1
                
                # 차량 탐지
                detected_cars = self.detect_cars_by_color(frame)
                
                # 인터페이스 그리기 및 경고 확인
                cars_near_boundary = self.draw_interface(frame, detected_cars)
                
                # 경고 처리
                self.handle_warning(cars_near_boundary)
                
                # 콘솔 출력 (상태 정보)
                if self.frame_count % 30 == 0:  # 30프레임마다 출력
                    print(f"프레임 {self.frame_count}: 탐지된 차량 {len(detected_cars)}대, "
                          f"경계 근처 {len(cars_near_boundary)}대")
                    
                    for i, car in enumerate(detected_cars):
                        center = car['center']
                        color = car['color']
                        print(f"  차량 {i+1}: {color} 색상, 위치 ({center[0]}, {center[1]})")
                
                if self.headless:
                    # 헤드리스 모드: 주기적으로 이미지 저장
                    if self.frame_count % self.save_interval == 0:
                        filename = f"output_{self.frame_count:04d}.jpg"
                        cv2.imwrite(filename, frame)
                        print(f"이미지 저장: {filename}")
                    
                    # 짧은 딜레이
                    time.sleep(0.1)
                    
                else:
                    # GUI 모드: 화면 표시
                    cv2.imshow('Parking Tracker', frame)
                    
                    # 키 입력 처리
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                    elif key == ord('s'):
                        self.setup_parking_area(frame)
                    elif key == ord('r'):
                        self.parking_area = []
                        print("주차장 영역 리셋!")
                    elif key == ord('c'):
                        # 색상 범위 조정 모드 (추가 기능)
                        print("현재 색상 범위:")
                        for color, (lower, upper) in self.color_ranges.items():
                            if color != 'red2':
                                print(f"  {color}: {lower} ~ {upper}")
                
        except KeyboardInterrupt:
            print("프로그램 종료")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """정리 작업"""
        if self.cap:
            self.cap.release()
        if not self.headless:
            cv2.destroyAllWindows()
        GPIO.cleanup()
        print("정리 완료")

if __name__ == "__main__":
    import sys
    
    # GUI 모드로 실행 (사용자가 GUI로 하겠다고 했으므로)
    headless = False
    if len(sys.argv) > 1 and sys.argv[1] == '--headless':
        headless = True
    
    tracker = ParkingTracker(headless=headless)
    tracker.run()