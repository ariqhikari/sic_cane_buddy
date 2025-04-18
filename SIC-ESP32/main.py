from machine import Pin, SoftI2C, time_pulse_us, UART
import time
import _thread
from umqtt.simple import MQTTClient
import json
import ssd1306
import network

SSID = "Rachel Ganteng"
PASSWORD = "ujangkeju"

MQTT_SERVER = "broker.emqx.io"
MQTT_CLIENT_ID = "esp32_client"
MQTT_TOPICS = ["/SIC/SHENDOCK/MAP", "/SIC/SHENDOCK/EMERGENCY"]

mqtt_isconnected = False
wlan = None
gps_locking = True
client = None

UART_PROTOCOL = UART(1, baudrate=9600, tx=17, rx=16)
UART_GPS = UART(2, baudrate=9600, tx=14, rx=27, timeout=10)

TRIGGER = Pin(12, Pin.OUT)
ECHO = Pin(13, Pin.IN)

BUZZER = Pin(19, Pin.OUT)

BUTTON_DANGER = Pin(15, Pin.IN, Pin.PULL_UP)
last_press_time_danger = 0

distance = 0
last_capture = 0

def connect_wifi():
    global mqtt_isconnected
    global wlan
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    while True:
        if not wlan.isconnected():
            mqtt_isconnected = False
            
            print('Connecting to WiFi...')
            
            wlan.connect(SSID, PASSWORD)
            
            timeout = 10
            while not wlan.isconnected() and timeout > 0:
                time.sleep(1)
                timeout -= 1
                
                print("Trying to connect...")
        
        if wlan.isconnected():
            #print('Network config:', wlan.ifconfig())
            pass
        else:
            print('Failed to connect to WiFi, retrying...')
        
        time.sleep(5)
        
def display_oled() :
    I2C_MODULE = SoftI2C(sda=Pin(21), scl=Pin(22))
    DISPLAY = ssd1306.SSD1306_I2C(128, 64, I2C_MODULE)
    
    while True :
        DISPLAY.fill(0)
        
        DISPLAY.hline(0, 26, 128, 1)
        
        if(wlan.isconnected()) :
            DISPLAY.text(f"WiFi: Connect", 0, 0, 1)
        else :
            DISPLAY.text("WiFi: Offline", 0, 0, 1)
            
        if(mqtt_isconnected) :
            DISPLAY.text(f"Mqtt: Connect", 0, 13, 1)
        else :
            DISPLAY.text("Mqtt: Offline", 0, 12, 1)
            
        if(gps_locking) :
            DISPLAY.text(f"Gps: Locking", 0, 33, 1)
        else :
            DISPLAY.text("Gps: Locate", 0, 12, 1)
                
        DISPLAY.show()
        time.sleep(0.1)
        
def mqtt_callback(topic, msg):
    data = json.loads(msg.decode())
             
    print("====================================================")
    print(f"Received message on topic: {topic}")
    print(data)
    print("====================================================")
    
def connect_mqtt():
    global mqtt_isconnected, client
    
    while True :
        if(wlan.isconnected() and mqtt_isconnected == False) :
            client = MQTTClient(MQTT_CLIENT_ID, MQTT_SERVER)
            client.set_callback(mqtt_callback)
            
            client.connect()
            
            print("Connected to mqtt broker")
            mqtt_isconnected = True
            
            for topic in MQTT_TOPICS :
                client.subscribe(topic)
                
                print(f"Subscribe to topic: {topic}")
                
            while True:
                client.wait_msg()
                time.sleep(1)
                
        time.sleep(6)

def parse_gpgga(sentence):
    try:
        parts = sentence.split(',')

        if parts[0] == "$GPGGA" and len(parts) > 5:
            raw_lat = parts[2]
            raw_lat_dir = parts[3]
            raw_lon = parts[4]
            raw_lon_dir = parts[5]

            # Pastikan data tidak kosong
            if raw_lat == '' or raw_lon == '':
                return (None, None)

            # Konversi Latitude
            lat_deg = float(raw_lat[:2])
            lat_min = float(raw_lat[2:])
            latitude = lat_deg + (lat_min / 60.0)
            if raw_lat_dir == "S":
                latitude = -latitude

            # Konversi Longitude
            lon_deg = float(raw_lon[:3])
            lon_min = float(raw_lon[3:])
            longitude = lon_deg + (lon_min / 60.0)
            if raw_lon_dir == "W":
                longitude = -longitude

            return (latitude, longitude)
    except Exception as e:
        print("Error parsing GPGGA:", e)

    return (None, None)

def getDistance() :
    TRIGGER.off()
    time.sleep_us(2)
    TRIGGER.on()
    time.sleep_us(10)
    TRIGGER.off()
    
    duration = time_pulse_us(ECHO, 1, 30000)
    
    if duration < 0:
        return None
    
    distance = (duration * 0.0343) / 2
    
    return distance

def communication_uart() :
    global last_capture
    
    while True :
        if(distance != None) :
            if(distance < 100) :
                current_time = time.ticks_ms()
                
                if(time.ticks_diff(current_time, last_capture) > 2000) :
                    message = "CAPTURE\n"
                    
                    print("Jarak Objek:", distance, "CM")
        
                    UART_PROTOCOL.write(message)
                    
                    print("Dikirim:", message.strip())

                    time.sleep(1)
                    
                    print(UART_PROTOCOL.any())
                    
                    if UART_PROTOCOL.any():
                        response = UART_PROTOCOL.readline()
                        
                        print("Diterima:", response.decode().strip())
                    
                    last_capture = current_time
                
        time.sleep(0.5)
        
def connect_gps() :
    while True :
        if UART_GPS.any():
            line = UART_GPS.readline()
            
            if line:
                try:
                    decoded_line = line.decode('utf-8').strip()
                    if decoded_line.startswith('$GPGGA'):
                        lat, lon = parse_gpgga(decoded_line)
                        
                        if lat is not None and lon is not None:
                            gps_locking = False
                            
                            print("Latitude :", lat)
                            print("Longitude:", lon)
                            
                            if mqtt_isconnected and client:
                                payload = {
                                    "latitude": lat,
                                    "longitude": lon,
                                }
                                
                                try:
                                    topic = b"/SIC/SHENDOCK/MAP"
                                    client.publish(topic, json.dumps(payload))
                                    
                                    print("GPS data published:", payload)
                                except Exception as e:
                                    print("Failed to publish GPS:", e)
                        else:
                            print("Menunggu GPS lock...")
                            
                            gps_locking = True
                except UnicodeError:
                    pass  # Lewati jika ada karakter rusak
                
        time.sleep(1)
    
def button_danger_handler(pin) :
    global last_press_time_danger
    
    current_time = time.ticks_ms()
    
    if time.ticks_diff(current_time, last_press_time_danger) > 7000:
        payload = {
            "status": True
        }
                                
        try:
            print("EMERGENCY BUTTON DITEKAN!!!")
            
            topic = b"/SIC/SHENDOCK/EMERGENCY"
            client.publish(topic, json.dumps(payload))
            
            BUZZER.value(1)
            
            time.sleep(5)
            
            BUZZER.value(0)
                                    
            print("EMERGENCY data published:", payload)
        except Exception as e:
            print("Failed to publish EMERGENCY:", e)
        
        last_press_time_danger = current_time
        
BUTTON_DANGER.irq(trigger=Pin.IRQ_FALLING, handler=button_danger_handler)
    
_thread.start_new_thread(connect_wifi, ())
_thread.start_new_thread(connect_mqtt, ())
_thread.start_new_thread(display_oled, ())
_thread.start_new_thread(communication_uart, ())
_thread.start_new_thread(connect_gps, ())
    
while True :
    distance = getDistance()
    
    time.sleep(1)