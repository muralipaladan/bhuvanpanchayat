import streamlit as st
import streamlit.components.v1 as components
import requests
import xml.etree.ElementTree as ET
import zipfile
import io

st.set_page_config(
    page_title="WMS Vector/KMZ Exporter",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {
        padding-top: 8px !important;
        padding-bottom: 0px !important;
        padding-left: 12px !important;
        padding-right: 12px !important;
        max-width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

if "available_layers" not in st.session_state:
    st.session_state.available_layers = {}
if "selected_layer_name" not in st.session_state:
    st.session_state.selected_layer_name = "Cadastry_Kerala"
if "wms_url" not in st.session_state:
    st.session_state.wms_url = "https://ksrec.in/geoserver/Kerala/wms"

# 1. സെർവർ വഴി ലെയറുകൾ എടുക്കൽ
def fetch_layers_via_python(url):
    clean_url = url.split("?")[0].strip()
    target_url = f"{clean_url}?service=WMS&version=1.1.1&request=GetCapabilities"
    domain = clean_url.split("//")[-1].split("/")[0]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": f"https://{domain}/",
        "Origin": f"https://{domain}"
    }
    try:
        res = requests.get(target_url, headers=headers, timeout=25)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            layer_dict = {}
            for layer in root.iter("Layer"):
                name = layer.find("Name")
                title = layer.find("Title")
                if name is not None and name.text:
                    l_name = name.text.strip()
                    l_title = title.text.strip() if (title is not None and title.text) else l_name
                    layer_dict[l_name] = l_title
            return layer_dict, None
        return {}, f"Status: {res.status_code}"
    except Exception as e:
        return {}, str(e)

# Top Bar
with st.expander("⚙️ WMS ലെയർ സെർച്ച് & ക്രമീകരണങ്ങൾ", expanded=(len(st.session_state.available_layers) == 0)):
    c1, c2 = st.columns([3, 1])
    with c1:
        wms_input = st.text_input("WMS സെർവർ URL:", value=st.session_state.wms_url)
        st.session_state.wms_url = wms_input
    with c2:
        st.write("##")
        if st.button("ലെയറുകൾ ഫെച്ച് ചെയ്യുക", use_container_width=True):
            with st.spinner("ലെയറുകൾ ശേഖരിക്കുന്നു..."):
                layers, err = fetch_layers_via_python(st.session_state.wms_url)
                if layers:
                    st.session_state.available_layers = layers
                    st.success(f"{len(layers)} ലെയറുകൾ കണ്ടെത്തി!")
                else:
                    st.error(f"ലഭിച്ചില്ല: {err}")

    if st.session_state.available_layers:
        s_col1, s_col2 = st.columns([1, 2])
        with s_col1:
            query = st.text_input("🔍 ലെയർ പേര് സെർച്ച് ചെയ്യുക:", placeholder="ഉദാ: Cadastry...").strip().lower()
        all_l = st.session_state.available_layers
        filtered = {k: v for k, v in all_l.items() if query in k.lower() or query in v.lower()} if query else all_l
        with s_col2:
            if filtered:
                sel = st.selectbox(f"ലഭ്യമായ ലെയറുകൾ ({len(filtered)} എണ്ണം):", options=list(filtered.keys()), format_func=lambda x: f"{filtered[x]} ({x})")
                if st.button("ഈ ലെയർ മാപ്പിൽ ലോഡ് ചെയ്യുക"):
                    st.session_state.selected_layer_name = sel
                    st.rerun()
    else:
        m_col1, m_col2 = st.columns([3, 1])
        with m_col1:
            manual_layer = st.text_input("ലെയർ പേര് നേരിട്ട് നൽകുക:", value=st.session_state.selected_layer_name)
        with m_col2:
            st.write("##")
            if st.button("ലോഡ് ചെയ്യുക", use_container_width=True):
                st.session_state.selected_layer_name = manual_layer
                st.rerun()

# --- Full Canvas Map ---
active_base_url = st.session_state.wms_url.split("?")[0].strip()
active_layer_name = st.session_state.selected_layer_name

html_code = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js"></script>
  <style>
    body { margin: 0; padding: 0; font-family: sans-serif; overflow: hidden; }
    #map { width: 100vw; height: 68vh; border: 1px solid #cbd5e1; border-radius: 6px; }
    #status-bar {
      position: absolute; bottom: 15px; left: 15px; z-index: 1000;
      background: rgba(15, 23, 42, 0.9); color: #38bdf8;
      padding: 8px 14px; border-radius: 4px; font-size: 13px; font-weight: bold;
    }
  </style>
</head>
<body>
  <div id="map"></div>
  <div id="status-bar">മാപ്പിലെ Polygon/Rectangle ടൂൾ ഉപയോഗിച്ച് ഏരിയ സെലക്ട് ചെയ്യുക.</div>

  <script>
    const baseUrl = '""" + active_base_url + """';
    const layerName = '""" + active_layer_name + """';

    const map = L.map('map').setView([10.5471, 76.1295], 11);
    map.createPane('overlayPane');
    map.getPane('overlayPane').style.zIndex = 600;

    const roads = L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', { maxZoom: 22 }).addTo(map);
    const hybrid = L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', { maxZoom: 22 });
    L.control.layers({ "Google Roads": roads, "Google Hybrid": hybrid }, null, { position: 'topright' }).addTo(map);

    L.tileLayer.wms(baseUrl, {
      layers: layerName,
      format: 'image/png',
      transparent: true,
      version: '1.1.1',
      maxZoom: 22,
      pane: 'overlayPane',
      opacity: 0.9
    }).addTo(map);

    const drawnItems = new L.FeatureGroup().addTo(map);
    new L.Control.Draw({
      position: 'topleft',
      draw: {
        polyline: false, circle: false, marker: false, circlemarker: false,
        rectangle: { shapeOptions: { color: '#ef4444', weight: 2, fillOpacity: 0.2 } },
        polygon: { shapeOptions: { color: '#ef4444', weight: 2, fillOpacity: 0.2 } }
      },
      edit: { featureGroup: drawnItems, remove: true }
    }).addTo(map);

    map.on(L.Draw.Event.CREATED, (e) => {
      drawnItems.clearLayers();
      drawnItems.addLayer(e.layer);
      const b = e.layer.getBounds();
      const bboxStr = `${b.getWest().toFixed(6)},${b.getSouth().toFixed(6)},${b.getEast().toFixed(6)},${b.getNorth().toFixed(6)}`;
      document.getElementById('status-bar').innerText = "BBOX കോപ്പി ചെയ്തു: " + bboxStr;
      navigator.clipboard.writeText(bboxStr);
    });
  </script>
</body>
</html>
"""

components.html(html_code, height=520, scrolling=False)

# 2. ബാക്കെൻഡ് വഴി തടസ്സമില്ലാത്ത KMZ ജനറേഷൻ
st.markdown("### 📥 സെലക്ട് ചെയ്ത ഏരിയ KMZ ആയി ഡൗൺലോഡ് ചെയ്യുക")
b_col1, b_col2 = st.columns([3, 1])

with b_col1:
    bbox_val = st.text_input(
        "സെലക്ട് ചെയ്ത BBOX (മാപ്പിൽ സെലക്ട് ചെയ്യുമ്പോൾ ഓട്ടോമാറ്റിക് ആയി കോപ്പിയാകും - ഇവിടെ Paste ചെയ്യുക):",
        placeholder="minX,minY,maxX,maxY"
    )

with b_col2:
    st.write("##")
    if st.button("KMZ ഡൗൺലോഡ് ചെയ്യുക", use_container_width=True, disabled=not bbox_val):
        with st.spinner("സെർവറിൽ നിന്ന് മുഴുവൻ ഡാറ്റയും ശേഖരിക്കുന്നു..."):
            try:
                coords = bbox_val.split(",")
                minx, miny, maxx, maxy = coords[0], coords[1], coords[2], coords[3]
                
                # ഹൈ-റെസല്യൂഷൻ KML ഗ്രൗണ്ട് ഓവർലേ നിർമ്മിക്കുന്നു (ഓഫ്‌ലൈൻ ആയി പ്രവർത്തിക്കാൻ)
                img_url = f"{active_base_url}?service=WMS&request=GetMap&version=1.1.1&layers={active_layer_name}&styles=&format=image/png&transparent=true&srs=EPSG:4326&bbox={minx},{miny},{maxx},{maxy}&width=2048&height=2048"
                
                domain = active_base_url.split("//")[-1].split("/")[0]
                headers = {
                    "User-Agent": "Mozilla/5.0",
                    "Referer": f"https://{domain}/",
                    "Origin": f"https://{domain}"
                }
                
                img_res = requests.get(img_url, headers=headers, timeout=30)
                
                if img_res.status_code == 200:
                    kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Folder>
    <name>{active_layer_name}_Export</name>
    <GroundOverlay>
      <name>{active_layer_name} High-Res Overlay</name>
      <Icon>
        <href>overlay.png</href>
      </Icon>
      <LatLonBox>
        <north>{maxy}</north>
        <south>{miny}</south>
        <east>{maxx}</east>
        <west>{minx}</west>
      </LatLonBox>
    </GroundOverlay>
  </Folder>
</kml>"""

                    # ZIP ബഫറിലേക്ക് ചിത്രവും KML-ഉം ചേർത്ത് പൂർണ്ണ ഓഫ്‌ലൈൻ KMZ ആക്കുന്നു
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
                        z.writestr("doc.kml", kml_content.encode('utf-8'))
                        z.writestr("overlay.png", img_res.content)
                    
                    st.success("സമ്പൂർണ്ണ KMZ തയ്യാറായി!")
                    st.download_button(
                        label="⬇️ KMZ ഫയൽ സേവ് ചെയ്യുക",
                        data=zip_buffer.getvalue(),
                        file_name=f"{active_layer_name}_{minx}_{miny}.kmz",
                        mime="application/vnd.google-earth.kmz",
                        use_container_width=True
                    )
                else:
                    st.error(f"സെർവറിൽ നിന്ന് ഡാറ്റ ലഭിച്ചില്ല (Status {img_res.status_code}).")
            except Exception as ex:
                st.error(f"ഡൗൺലോഡിൽ പിഴവ്: {ex}")
