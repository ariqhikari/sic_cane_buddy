#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "esp_camera.h"
#include "base64.h"
#include <HardwareSerial.h>

HardwareSerial SerialMaster(1);

const char* ssid = "Rachel Ganteng";
const char* password = "ujangkeju";

String messageCapture = "";

#define PWDN_GPIO_NUM  32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM  0
#define SIOD_GPIO_NUM  26
#define SIOC_GPIO_NUM  27
#define Y9_GPIO_NUM    35
#define Y8_GPIO_NUM    34
#define Y7_GPIO_NUM    39
#define Y6_GPIO_NUM    36
#define Y5_GPIO_NUM    21
#define Y4_GPIO_NUM    19
#define Y3_GPIO_NUM    18
#define Y2_GPIO_NUM    5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM  23
#define PCLK_GPIO_NUM  22

void setup_wifi() {
    Serial.print("Menghubungkan ke WiFi...");
    
    WiFi.begin(ssid, password);
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    
    Serial.println("\nWiFi terhubung. IP: " + WiFi.localIP().toString());
}

void setup_camera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.frame_size = FRAMESIZE_SVGA;
    config.pixel_format = PIXFORMAT_JPEG;
    config.jpeg_quality = 10;
    config.fb_count = 1;

    esp_err_t err = esp_camera_init(&config);
    
    if (err != ESP_OK) {
        Serial.printf("Kamera gagal diinisialisasi: 0x%x", err);
        
        return;
    }
    
    Serial.println("Kamera berhasil diinisialisasi.");
}

void send_image() {
    Serial.println("Mengirim data ke API.");
  
    camera_fb_t *fb = esp_camera_fb_get();
    
    if (!fb) {
        Serial.println("Gagal mengambil gambar.");

        messageCapture = "Gagal mengambil gambar.";
        
        return;
    }

    String image_base64 = base64::encode(fb->buf, fb->len);
    
    HTTPClient http;
    
    http.begin("http://192.168.46.218:8000/api/camera");
    http.addHeader("Content-Type", "application/json");
    
    http.setTimeout(10000);

    StaticJsonDocument<200> jsonDoc;
    jsonDoc["image"] = image_base64.c_str();

    String jsonString;
    serializeJson(jsonDoc, jsonString);
    
    int httpResponseCode = http.POST(jsonString);

    if (httpResponseCode > 0) {
        String response = http.getString();
          
        Serial.println("Respon API:");
        Serial.println(response);

        messageCapture = "Berhasil mengirim gambar";
    } else {
        Serial.print("Error dalam koneksi: ");
        Serial.println(httpResponseCode);
        
        messageCapture = "Error koneksi";  
    }

    http.end();
    esp_camera_fb_return(fb);
}

void setup() {
    Serial.begin(115200);
    SerialMaster.begin(9600, SERIAL_8N1, 3, 1);
    
    setup_wifi();
    setup_camera();
}

void loop() {
    if(WiFi.status() == WL_CONNECTED) {     
        if (SerialMaster.available()) {
          String message = SerialMaster.readStringUntil('\n');

          if(message == "CAPTURE") {
            send_image();
            
            SerialMaster.println(messageCapture);
            messageCapture = "";
          }
        }  
    } else {
      Serial.println("Wifi tidak terkoneksi.");
    }
    
    delay(1000);
}
