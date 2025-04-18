import streamlit as st
import cv2
import tempfile
from ultralytics import YOLO
from streamlit_option_menu import option_menu
import folium
from streamlit_folium import folium_static
import numpy as np 
import openai
   
def generate_location_description(nama, lat, lon, context):
    prompt = f"""
    Berikan penjelasan tentang lokasi {nama} dengan koordinat latitude {lat} dan longitude {lon}. 
    Jelaskan dalam konteks {context}. Berikan informasi mengenai:
    1. Posisi geografis (wilayah, kota)
    2. Bangunan Terkenal di sekitarnya
    3. Aksesibilitas untuk penyandang disabilitas
    Gunakan bahasa yang deskriptif namun mudah dipahami.
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=150
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        return f"Gagal menghasilkan deskripsi: {str(e)}"

# Konfigurasi halaman
st.set_page_config(page_title="Canebuddy", layout="wide")

# Navigasi sidebar
with st.sidebar:
    selected = option_menu(
        menu_title="Menu",
        options=["📷 Object Detection", "📍 Panic Button Tracker", "📍 History Tracking"],
        icons=["camera", "palette"],
        default_index=0,
    )
@st.cache_resource
def load_model():
    model = YOLO('best.pt')
    return model

if selected == "📷 Object Detection":
    st.title("Object Detection dengan YOLOv8")
    st.write("Upload gambar/video dan lihat hasil deteksi objek!")

    with st.sidebar:
        st.header("Pengaturan Model")
        input_type = st.radio("Pilih tipe input", ["Gambar", "Video"])
        
        # Sesuaikan file uploader berdasarkan tipe input
        if input_type == "Gambar":
            uploaded_file = st.file_uploader("Upload gambar...", 
                                            type=["jpg", "jpeg", "png"])
        else:
            uploaded_file = st.file_uploader("Upload video...", 
                                            type=["mp4", "avi", "mov"])
        
        confidence_threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.5, 0.01)

    model = load_model()

    # Fungsi deteksi objek (tetap sama)
    def run_detection(frame):
        results = model.predict(frame, imgsz=640, conf=0.5)
        return results[0].boxes.cpu().numpy()

    # Fungsi gambar bounding box (tetap sama)
    def draw_boxes(frame, detections):
        for detection in detections:
            x1, y1, x2, y2 = map(int, detection.xyxy[0])
            conf = detection.conf[0]
            cls_id = int(detection.cls[0])
            
            if conf > confidence_threshold:
                label = f"{model.names[cls_id]} {conf:.2f}"
                # Gambar bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3) 
                
                # Tambahkan label 
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.5 
                thickness = 1    
                
                # Hitung ukuran teks untuk penempatan yang tepat
                (text_width, text_height), _ = cv2.getTextSize(label, font, font_scale, thickness)
                
                # Gambar background label
                cv2.rectangle(
                    frame, 
                    (x1, y1 - text_height - 10), 
                    (x1 + text_width, y1), 
                    (0, 255, 0), 
                    -1  
                )
                
                # Tambahkan teks
                cv2.putText(
                    frame, 
                    label, 
                    (x1, y1 - 10),  
                    font, 
                    font_scale, 
                    (0, 0, 0),      
                    thickness, 
                    lineType=cv2.LINE_AA
                )
        return frame

    if uploaded_file is not None:
        if input_type == "Gambar":
            # Proses gambar
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, 1)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            with st.spinner('Memproses gambar...'):
                detections = run_detection(image)
                processed_image = draw_boxes(image, detections)
                
            st.success("Deteksi selesai!")
            st.image(processed_image, caption="Hasil Deteksi", use_container_width=True)
            
        else:  # Untuk video
            # Simpan video sementara
            tfile = tempfile.NamedTemporaryFile(delete=False) 
            tfile.write(uploaded_file.read())
            
            # Proses video
            cap = cv2.VideoCapture(tfile.name)
            st_frame = st.empty()
            
            # Kontrol video
            col1, col2 = st.columns(2)
            with col1:
                start_processing = st.button("Mulai Pemrosesan")
            with col2:
                stop_processing = st.button("Hentikan Pemrosesan")
            
            if start_processing:
                while cap.isOpened() and not stop_processing:
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    detections = run_detection(frame_rgb)
                    processed_frame = draw_boxes(frame_rgb, detections)
                    st_frame.image(processed_frame, channels="RGB", use_container_width=True)
                    
                cap.release()
                st.success("Pemrosesan video selesai!")
            
            tfile.close()
    else:
        st.warning("Silakan upload file terlebih dahulu")



# Halaman Tracking
elif selected == "📍 Panic Button Tracker":
    st.title("Panic Button Tracker")
    st.write("Visualisasi tunanetra jika terjadi keadaan darurat")

    # Koordinat titik (lat, lon)
    x = (-6.8871105,107.614373)  
    y = (-6.8898283,107.6149485)
    
    # Hitung titik tengah untuk posisi awal map
    center_lat = (x[0] + y[0])/2
    center_lon = (x[1] + y[1])/2
    
    # Buat peta Folium
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=14,
        tiles='OpenStreetMap'
    )
    
    # Tambahkan marker
    folium.Marker(
        location=x,
        popup="jl_DipatiUkur",
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)
    
    folium.Marker(
        location=y,
        popup="jl_Multatuli",
        icon=folium.Icon(color='blue', icon='info-sign')
    ).add_to(m)
    
    # Tambahkan garis penghubung
    folium.PolyLine(
        locations=[x, y],
        color='#FF0000',
        weight=5,
        opacity=0.7
    ).add_to(m)
    
    # Hitung jarak
    from math import radians, sin, cos, sqrt, atan2
    
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371  # Radius bumi dalam km
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c
    
    distance = haversine(*x, *y)
    
    # Tampilkan peta
    folium_static(m, width=1000, height=500)
    
    # Tampilkan informasi
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Koordinat")
        
        st.write(f"**jl_DipatiUkur:**")
        st.write(f"Latitude: {x[0]:.4f}")
        st.write(f"Longitude: {x[1]:.4f}")
        with st.expander("Penjelasan Lokasi 1 Dengan AI"):
            st.write("""
            **Jl. Dipati Ukur, Bandung**
            Kota Bandung, khususnya di area yang dekat dengan kampus Universitas Komputer Indonesia, memiliki trotoar cukup lebar dilengkapi guiding block untuk aksesibilitas.
            """)
        
        st.write("---")
        
        st.write(f"**jl_Multatuli:**")
        st.write(f"Latitude: {y[0]:.4f}")
        st.write(f"Longitude: {y[1]:.4f}") 
        with st.expander("Penjelasan Lokasi 2 Dengan AI"):
            st.write("""
            **Jl. Multatuli, Bandung**
            Kota Bandung, khususnya di area dekat Taman Lansia, memiliki akses jalan yang cukup ramah difabel.
            """)  
    with col2:
        st.subheader("Jarak")
        st.metric(label="Jarak Tempuh", value=f"{distance:.2f} km")
        st.write("Jarak garis lurus antara dua titik")

    st.markdown("---")
    st.write("**Fitur Interaktif:**")
    st.write("- Zoom in/out dengan scroll mouse")
    st.write("- Klik dan drag untuk menggeser peta")
    st.write("- Klik marker untuk melihat informasi")

elif selected == "📍 History Tracking":
    st.title("History Tracking")
    st.write("Visualisasi rute histori perjalanan tunanetra") 

    # Daftar titik dalam format (nama, latitude, longitude, warna)
    points = [
        {"name": "Jl_DipatiUkur", "lat": -6.8871105, "lon": 107.614373, "color": "red"},
        {"name": "jl_Multatuli", "lat": -6.8898283, "lon": 107.6149485, "color": "blue"},
        {"name": "jl_TeukuUmar", "lat": -6.8916916, "lon": 107.6161087, "color": "green"},
        {"name": "jl_TeukuUmar", "lat": -6.8917672, "lon": 107.6135823, "color": "purple"}
    ]

    # Hitung titik tengah peta
    avg_lat = sum(point['lat'] for point in points) / len(points)
    avg_lon = sum(point['lon'] for point in points) / len(points)
    
    # Buat peta Folium
    m = folium.Map(
        location=[avg_lat, avg_lon],
        zoom_start=12,
        tiles='OpenStreetMap'
    )
    
    # Tambahkan semua marker
    locations = []
    for idx, point in enumerate(points, 1):
        folium.Marker(
            location=[point['lat'], point['lon']],
            popup=f"{idx}. {point['name']}",
            icon=folium.Icon(color=point['color'], icon='info-sign')
        ).add_to(m)
        locations.append([point['lat'], point['lon']])
    
    # Tambahkan garis penghubung bertahap
    for i in range(len(locations)-1):
        folium.PolyLine(
            locations=locations[i:i+2],
            color='#FF0000',
            weight=3,
            opacity=0.7,
            tooltip=f"Rute {i+1}"
        ).add_to(m)
    
    # Hitung total jarak
    from math import radians, sin, cos, sqrt, atan2
    
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371  # Radius bumi dalam km
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c
    
    total_distance = 0
    distance_breakdown = []
    
    for i in range(len(points)-1):
        start = points[i]
        end = points[i+1]
        distance = haversine(start['lat'], start['lon'], end['lat'], end['lon'])
        total_distance += distance
        distance_breakdown.append({
            "segment": f"{start['name']} ke {end['name']}",
            "distance": distance
        })
    
    # Tampilkan peta
    folium_static(m, width=1000, height=500)
    
   # Tampilkan informasi
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Daftar Titik")
        for idx, point in enumerate(points, 1):
            st.write(f"{idx}. **{point['name']}**")
            st.write(f"Lat: {point['lat']:.4f}, Lon: {point['lon']:.4f}")
            
            with st.expander(f"Deskripsi {point['name']} Dengan AI"):
                if point['name'] == "Jl_DipatiUkur":
                    st.write("""
                    **Jl. Dipati Ukur**
                    Kota Bandung, khususnya di area yang dekat dengan kampus Universitas Komputer Indonesia, memiliki trotoar cukup lebar dilengkapi guiding block untuk aksesibilitas.
                    """)
                elif point['name'] == "jl_Multatuli":
                    st.write("""~
                    **Jl. Multatuli**
                    Kota Bandung, khususnya di area dekat Taman Lansia, memiliki akses jalan yang cukup ramah difabel.
                    """)
                elif point['name'] == "jl_TeukuUmar":
                    st.write("""
                    **Jl. Teuku Umar**
                    Kota Bandung, dengan banyaknya bank dan ATM, juga memiliki trotoar cukup luas untuk mendukung kenyamanan publik.
                    """)
            
            st.write("---")
    with col2:
        st.subheader("Analisis Jarak")
        st.metric(label="Total Jarak Tempuh", value=f"{total_distance:.2f} km")
        
        st.write("**Rincian Per Segmen:**")
        for segment in distance_breakdown:
            st.write(f"- {segment['segment']}: {segment['distance']:.2f} km")

    st.markdown("---")
    st.write("**Panduan Interaksi:**")
    st.write("- Klik marker untuk melihat nama lokasi")
    st.write("- Hover di atas garis untuk melihat info segmen")
    st.write("- Gunakan kontrol zoom di pojok kiri atas peta")