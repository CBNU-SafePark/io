/**
 * @file camera.c
 * @brief H.264로 인코딩된 비디오 스트림을 루프백 IP에 UDP로 전송하는 GStreamer 파이프라인
 * @details 빌드 : sudo apt install libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev 필요
 * @details 실행 : ./camera [IP 주소] [포트] [디바이스경로]
 * @details 예시 : ./camera 127.0.1 /dev/video1
 * @details 기본 IP 주소는 루프백 (localhost)
 * @details 기본 포트는 5000번
 * @details 기본 디바이스 경로는 /dev/video0
 * 
 * @author Minseok Kim
 */

#include <gst/gst.h>
#include <sys/stat.h>
#include <string.h>

int main(int argc, char *argv[]) {
    char *ip_address = "127.0.0.1"; // 기본 IP 주소
    char *device_path = "/dev/video0"; // 기본 디바이스 경로
    int udp_port = 5000; // 기본 포트

    // Argument parsing
    if (argc == 2) {
        ip_address = argv[1];
    } else if (argc == 3) {
        ip_address = argv[1];
        udp_port = atoi(argv[2]);
    } else if (argc == 4) {
        ip_address = argv[1];
        udp_port = atoi(argv[2]);
        device_path = argv[3];
    } else if (argc > 4) {
        g_printerr("Check Input Variables\n");
    }

    /* 디바이스 검사 */
    struct stat st;
    if (stat(device_path, &st) != 0) {
        g_printerr("Device %s not found\n", device_path);
        return -1;
    }

    g_print("IP Address: %s\n", ip_address);
    g_print("UDP Port: %d\n", udp_port);
    g_print("Device Path: %s\n", device_path);

    GstElement *pipeline, *source, *convert, *encoder, *payloader, *sink;
    GstCaps *caps;

    gst_init(&argc, &argv);

    /* 요소 생성 */
    source = gst_element_factory_make("v4l2src", "source");
    convert = gst_element_factory_make("videoconvert", "convert");
    encoder = gst_element_factory_make("x264enc", "encoder");
    payloader = gst_element_factory_make("rtph264pay", "payloader");
    sink = gst_element_factory_make("udpsink", "sink");

    if (!source || !convert || !encoder || !payloader || !sink) {
        g_printerr("Fail to Create Element\n");
        return -1;
    }

    /* source 카메라 디바이스 설정 */
    g_object_set(source,
                 "device", device_path,
                 NULL);

    /* 파이프라인 생성 */
    pipeline = gst_pipeline_new("video-pipeline");
    if (!pipeline) {
        g_printerr("Fail to create pipeline\n");
        return -1;
    }

    /* 요소 추가 */
    gst_bin_add_many(GST_BIN(pipeline), source, convert, encoder, payloader, sink, NULL);

    /* 연결 */
    caps = gst_caps_new_simple("video/x-raw",
                               "width", G_TYPE_INT, 640,
                               "height", G_TYPE_INT, 480,
                               "framerate", GST_TYPE_FRACTION, 30, 1,
                               NULL);

    if (!gst_element_link_filtered(source, convert, caps)) {
        g_printerr("source -> convert link fail\n");
        gst_object_unref(pipeline);
        return -1;
    }
    gst_caps_unref(caps);

    if (!gst_element_link(convert, encoder)) {
        g_printerr("convert -> encoder link fail\n");
        gst_object_unref(pipeline);
        return -1;
    }

    /* encoder 설정 */
    g_object_set(encoder,
                 "tune", 0x00000004,   /* zerolatency */
                 "key-int-max", 15,
                 "bitrate", 1000,
                 "speed-preset", 1,    /* ultrafast */
                 NULL);

    if (!gst_element_link(encoder, payloader)) {
        g_printerr("encoder -> payloader link fail\n");
        gst_object_unref(pipeline);
        return -1;
    }

    /* payloader 설정 */
    g_object_set(payloader,
                 "config-interval", 1,
                 "pt", 96,
                 NULL);

    if (!gst_element_link(payloader, sink)) {
        g_printerr("payloader -> sink link fail\n");
        gst_object_unref(pipeline);
        return -1;
    }

    /* sink 설정 */
    g_object_set(sink,
                 "host", ip_address,
                 "port", udp_port,
                 NULL);

    /* 실행 */
    gst_element_set_state(pipeline, GST_STATE_PLAYING);

    /* main loop */
    g_print("Streaming Started!! SAFE PARK\n");
    g_print("Press Ctrl+C to terminate\n");
    g_main_loop_run(g_main_loop_new(NULL, FALSE));

    /* 종료 */
    gst_element_set_state(pipeline, GST_STATE_NULL);
    gst_object_unref(pipeline);

    return 0;
}
