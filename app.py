import streamlit as st
import streamlit.components.v1 as components
import requests
import xml.etree.ElementTree as ET
import json
import zipfile
import io

st.set_page_config(
    page_title="WMS/WFS Vector Polygon KMZ Downloader",
    page_icon="🗺️",
    layout="wide"
)

if "layers" not in st.session_state:
    st.session_state.layers = []
if "wms_url" not in st.session_state:
    st.session_state.wms_url = "https://ksrec.in/geoserver/Kerala/wms"
if "available_layers" not in st.session_state:
    st.session_state.available_layers = {}

st.title("🗺️ വെക്റ്റർ പോളിഗോൺ KMZ എക്സ്പോർട്ടർ")

# WMS GetCapabilities ഫെച്ച് ചെയ്യൽ
def fetch_capabilities(url):
    clean_url = url.split("?")[0].strip()
    target_url = f"{clean_url}?service=WMS&version=1.1.1&request=GetCapabilities"
    domain = clean_url.split("//")[-1].split("/")[0]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": f"https://{domain}/",
        "Origin": f"https://{domain}"
    }
    try:
        res = requests.get(target_url, headers=headers, timeout=20)
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
        return None, f"Status: {res.status_code}"
    except Exception as e:
        return None, str(e)

# മുകളിലെ കൺട്രോളുകൾ
c1, c2 = st.columns([4, 1])
with c1:
    wms_input = st.text_input("WMS URL:", value=st.session_state.wms_url)
    st.session_state.wms_url = wms_input
with c2:
    st.write("##")
    if st.button("ലെയറുകൾ എടുക്കുക", use_container_width=True):
        with st.spinner("ശേഖരിക്കുന്നു..."):
            layers, err = fetch_capabilities(st.session_state.wms_url)
            if layers:
                st.session_state.available_layers = layers
                st.success(f"{len(layers)} ലെയറുകൾ കണ്ടെത്തി!")
            else:
                st.error(f"ലഭിച്ചില്ല: {err}")

# സെർച്ച് & ലെയർ ആഡിങ്
if st.session_state.available_layers:
    all_layers = st.session_state.available_layers
    s_col1, s_col2, s_col3 = st.columns([2, 3, 1])
    with s_col1:
        search_query = st.text_input("🔍 ലെയർ സെർച്ച്:", placeholder="പേര് ടൈപ്പ് ചെയ്യുക...").strip().lower()
    
    filtered_layers = {k: v for k, v in all_layers.items() if search_query in k.lower() or search_query in v.lower()} if search_query else all_layers

    with s_col2:
        if filtered_layers:
            selected_layer = st.selectbox("ലഭ്യമായ ലെയറുകൾ:", options=list(filtered_layers.keys()), format_func=lambda x: f"{filtered_layers[x]} ({x})")
        else:
            st.selectbox("ലഭ്യമായ ലെയറുകൾ:", ["ഫലങ്ങളില്ല"], disabled=True)
            selected_layer = None

    with s_col3:
        st.write("##")
        if st.button("മാപ്പിൽ ചേർക്കുക", use_container_width=True, disabled=(selected_layer is None)):
            if selected_layer and not any(l['name'] == selected_layer for l in st.session_state.layers):
                st.session_state.layers.append({
                    "name": selected_layer,
                    "title": all_layers[selected_layer],
                    "baseUrl": st.session_state.wms_url.split("?")[0].strip()
                })
                st.rerun()
else:
    col_manual, col_add = st.columns([4, 1])
    with col_manual:
        manual_name = st.text_input("ലെയറിന്റെ പേര് നൽകുക (Manual):", value="Cadastry_Kerala")
    with col_add:
        st.write("##")
        if st.button("നേരിട്ട് ചേർക്കുക", use_container_width=True):
            if not any(l['name'] == manual_name for l in st.session_state.layers):
                st.session_state.layers.append({
                    "name": manual_name,
                    "title": manual_name,
                    "baseUrl": st.session_state.wms_url.split("?")[0].strip()
                })
                st.rerun()

# ആക്ടീവ് ലെയറുകൾ
if st.session_state.layers:
    st.markdown("**മാപ്പിലുള്ള ലെയറുകൾ (ഡിലീറ്റ് ചെയ്യാൻ ക്ലിക്ക് ചെയ്യുക):**")
    cols = st.columns(min(len(st.session_state.layers), 6))
    to_delete = None
    for i, lyr in enumerate(st.session_state.layers):
        with cols[i % 6]:
            if st.button(f"🗑️ {lyr['name']}", key=f"del_{i}", use_container_width=True):
                to_delete = i
    if to_delete is not None:
        st.session_state.layers.pop(to_delete)
        st.rerun()

# മാപ്പും ലൈവ് സെലക്ഷനും
layers_payload = json.dumps(st.session_state.layers)

html_code = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js"></script>
  <style>
    body {{ margin: 0; padding: 0; font-family: sans-serif; }}
    #map {{ height: 500px; width: 100%; border-radius: 6px; border: 1px solid #cbd5e1; }}
    #status-bar {{ padding: 8px 12px; background: #0f172a; color: #38bdf8; font-size: 13px; font-weight: bold; }}
  </style>
</head>
<body>
  <div id="status-bar">മാപ്പിലെ Draw ടൂൾ ഉപയോഗിച്ച് ഏരിയ സെലക്ട് ചെയ്യുക (BBOX താഴെ ഓട്ടോമാറ്റിക് ആയി വരും).</div>
  <div id="map"></div>

  <script>
    const map = L.map('map', {{ center: [10.5471, 76.1295], zoom: 11 }});
    map.createPane('overlayPane');
    map.getPane('overlayPane').style.zIndex = 600;

    const roads = L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{ maxZoom: 22 }}).addTo(map);
    const hybrid = L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={{x}}&y={{y}}&z={{z}}', {{ maxZoom: 22 }});
    L.control.layers({{ "Google Roads": roads, "Google Hybrid": hybrid }}, null, {{ position: 'topright' }}).addTo(map);

    const activeLayers = {layers_payload};
    activeLayers.forEach(l => {{
      L.tileLayer.wms(l.baseUrl, {{
        layers: l.name,
        format: 'image/png',
        transparent: true,
        version: '1.1.1',
        maxZoom: 22,
        pane: 'overlayPane',
        opacity: 0.9
      }}).addTo(map);
    }});

    const drawnItems = new L.FeatureGroup().addTo(map);
    new L.Control.Draw({{
      draw: {{
        polyline: false, circle: false, marker: false, circlemarker: false,
        rectangle: {{ shapeOptions: {{ color: '#ef4444', weight: 2 }} }},
        polygon: {{ shapeOptions: {{ color: '#ef4444', weight: 2 }} }}
      }},
      edit: {{ featureGroup: drawnItems, remove: true }}
    }}).addTo(map);

    map.on(L.Draw.Event.CREATED, (e) => {{
      drawnItems.clearLayers();
      drawnItems.addLayer(e.layer);
      const b = e.layer.getBounds();
      const bboxStr = `${{b.getWest().toFixed(6)}},${{b.getSouth().toFixed(6)}},${{b.getEast().toFixed(6)}},${{b.getNorth().toFixed(6)}}`;
      document.getElementById('status-bar').innerText = `സെലക്ട് ചെയ്ത BBOX: ${{bboxStr}} (ഇത് താഴെയുള്ള ബോക്സിൽ നൽകുക)`;
      navigator.clipboard.writeText(bboxStr);
    }});
  </script>
</body>
</html>
"""

components.html(html_code, height=540)

# വെക്റ്റർ പോളിഗോൺ KMZ ഡൗൺലോഡർ സെക്ഷൻ
st.markdown("### 📥 യഥാർത്ഥ പോളിഗോൺ KMZ ഡൗൺലോഡ്")

col_b1, col_b2 = st.columns([3, 1])
with col_b1:
    bbox_input = st.text_input("സെലക്ട് ചെയ്ത BBOX (മാപ്പിൽ സെലക്ട് ചെയ്യുമ്പോൾ തനിയെ ക്ലിപ്പ്ബോർഡിലേക്ക് കോപ്പിയാകും - Paste ചെയ്യുക):", placeholder="minX,minY,maxX,maxY (ഉദാ: 76.10,10.50,76.15,10.55)")

# GeoJSON-ൽ നിന്ന് KML Polygon Placemark നിർമ്മിക്കുന്ന ഫംഗ്ഷൻ
def geojson_to_kml(geojson_data, layer_title):
    placemarks = ""
    for feat in geojson_data.get("features", []):
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        gtype = geom.get("type", "")
        coords = geom.get("coordinates", [])

        # പ്രോപ്പർട്ടീസ് HTML ടേബിൾ ആക്കുന്നു (സർവേ നമ്പർ, വിവരങ്ങൾ എന്നിവ)
        desc = "<table border='1' style='font-size:12px;border-collapse:collapse;'>"
        for k, v in props.items():
            desc += f"<tr><td><b>{k}</b></td><td>{v}</td></tr>"
        desc += "</table>"
        name = props.get("name") or props.get("SURVEY_NO") or props.get("LAND_NO") or layer_title

        geom_kml = ""
        if gtype == "Polygon":
            outer = " ".join([f"{c[0]},{c[1]},0" for c in coords[0]])
            geom_kml = f"<Polygon><outerBoundaryIs><LinearRing><coordinates>{outer}</coordinates></LinearRing></outerBoundaryIs></Polygon>"
        elif gtype == "MultiPolygon":
            geom_kml = "<MultiGeometry>"
            for poly in coords:
                outer = " ".join([f"{c[0]},{c[1]},0" for c in poly[0]])
                geom_kml += f"<Polygon><outerBoundaryIs><LinearRing><coordinates>{outer}</coordinates></LinearRing></outerBoundaryIs></Polygon>"
            geom_kml += "</MultiGeometry>"
        elif gtype == "LineString":
            line = " ".join([f"{c[0]},{c[1]},0" for c in coords])
            geom_kml = f"<LineString><coordinates>{line}</coordinates></LineString>"

        if geom_kml:
            placemarks += f"""
            <Placemark>
                <name><![CDATA[{name}]]></name>
                <description><![CDATA[{desc}]]></description>
                <styleUrl>#polyStyle</styleUrl>
                {geom_kml}
            </Placemark>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{layer_title} Full Polygons</name>
    <Style id="polyStyle">
      <LineStyle><color>ff0000ff</color><width>1.5</width></LineStyle>
      <PolyStyle><fill>0</fill></PolyStyle>
    </Style>
    {placemarks}
  </Document>
</kml>"""

with col_b2:
    st.write("##")
    if st.button("വെക്റ്റർ KMZ ഉണ്ടാക്കുക", use_container_width=True, disabled=len(st.session_state.layers) == 0 or not bbox_input):
        with st.spinner("സെർവറിൽ നിന്ന് പോളിഗോൺ വെക്റ്റർ ഡാറ്റ ശേഖരിക്കുന്നു..."):
            try:
                # WFS എൻഡ്‌പോയിന്റിലേക്ക് മാറ്റി വെക്റ്റർ GeoJSON ആവശ്യപ്പെടുന്നു
                layer = st.session_state.layers[0] # തിരഞ്ഞെടുത്ത ലെയർ
                wfs_base = layer["baseUrl"].replace("/wms", "/wfs")
                wfs_url = f"{wfs_base}?service=WFS&version=1.1.0&request=GetFeature&typeName={layer['name']}&outputFormat=application/json&srsname=EPSG:4326&bbox={bbox_input},EPSG:4326"

                headers = {
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://ksrec.in/",
                    "Origin": "https://ksrec.in"
                }

                res = requests.get(wfs_url, headers=headers, timeout=30)
                if res.status_code == 200:
                    geojson_res = res.json()
                    feat_count = len(geojson_res.get("features", []))

                    if feat_count == 0:
                        st.warning("സെലക്ട് ചെയ്ത ഭാഗത്ത് വെക്റ്റർ പോളിഗോണുകൾ കണ്ടെത്തിയില്ല.")
                    else:
                        # പൂർണ്ണ KML ഉണ്ടാക്കുന്നു
                        kml_text = geojson_to_kml(geojson_res, layer['name'])
                        
                        # KMZ ആയി സിപ്പ് ചെയ്യുന്നു
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                            zip_file.writestr("doc.kml", kml_text.encode('utf-8'))

                        st.success(f"{feat_count} യഥാർത്ഥ പോളിഗോണുകൾ ലഭിച്ചു!")
                        st.download_button(
                            label="⬇️ സമ്പൂർണ്ണ KMZ ഫയൽ ഡൗൺലോഡ് ചെയ്യുക",
                            data=zip_buffer.getvalue(),
                            file_name=f"{layer['name']}_full_polygons.kmz",
                            mime="application/vnd.google-earth.kmz",
                            use_container_width=True
                        )
                else:
                    st.error(f"വെക്റ്റർ ഡാറ്റ സെർവർ നൽകിയില്ല (Status {res.status_code}).")
            except Exception as e:
                st.error(f"ഡാറ്റ എടുക്കുന്നതിൽ തടസ്സം: {e}")
