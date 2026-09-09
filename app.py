import streamlit as st
import streamlit.components.v1 as components
import requests
import xml.etree.ElementTree as ET
import json

st.set_page_config(
    page_title="WMS Layer Manager & KMZ Tool",
    page_icon="🗺️",
    layout="wide"
)

# സ്റ്റേറ്റ് മാനേജ്‌മെന്റ്
if "layers" not in st.session_state:
    st.session_state.layers = []
if "wms_url" not in st.session_state:
    st.session_state.wms_url = "https://ksrec.in/geoserver/Kerala/wms"
if "available_layers" not in st.session_state:
    st.session_state.available_layers = {}

st.title("🗺️ WMS ലെയർ മാനേജർ & ഏരിയ KMZ ടൂൾ")

# WMS GetCapabilities ഫെച്ച് ചെയ്യാനുള്ള സെർവർ ഫംഗ്ഷൻ
def fetch_capabilities(url):
    clean_url = url.split("?")[0].strip()
    target_url = f"{clean_url}?service=WMS&version=1.1.1&request=GetCapabilities"
    
    domain = clean_url.split("//")[-1].split("/")[0]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": f"https://{domain}/",
        "Origin": f"https://{domain}",
        "Accept": "application/xml,text/xml,*/*"
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
        else:
            return None, f"സെർവർ സ്റ്റാറ്റസ് കോഡ്: {res.status_code}"
    except Exception as e:
        return None, str(e)

# WMS URL ഇൻപുട്ട്
c1, c2 = st.columns([4, 1])
with c1:
    wms_input = st.text_input("WMS URL നൽകുക:", value=st.session_state.wms_url)
    st.session_state.wms_url = wms_input
with c2:
    st.write("##")
    if st.button("ലെയറുകൾ എടുക്കുക", use_container_width=True):
        with st.spinner("ലെയർ വിവരങ്ങൾ പരിശോധിക്കുന്നു..."):
            layers, err = fetch_capabilities(st.session_state.wms_url)
            if layers:
                st.session_state.available_layers = layers
                st.success(f"{len(layers)} ലെയറുകൾ കണ്ടെത്തി!")
            else:
                st.error(f"ലെയർ ലിസ്റ്റ് ലഭിച്ചില്ല: {err}")

# ലെയർ സെർച്ച് & സെലക്ഷൻ ഏരിയ
if st.session_state.available_layers:
    all_layers = st.session_state.available_layers
    
    st.markdown("---")
    s_col1, s_col2, s_col3 = st.columns([2, 3, 1])
    
    with s_col1:
        search_query = st.text_input("🔍 ലെയർ സെർച്ച് ചെയ്യുക:", placeholder="പേര് ടൈപ്പ് ചെയ്യുക...").strip().lower()
    
    # സെർച്ച് അനുസരിച്ച് ലെയറുകൾ ഫിൽട്ടർ ചെയ്യുന്നു
    if search_query:
        filtered_layers = {
            k: v for k, v in all_layers.items() 
            if search_query in k.lower() or search_query in v.lower()
        }
    else:
        filtered_layers = all_layers

    with s_col2:
        if filtered_layers:
            selected_layer = st.selectbox(
                f"ലഭ്യമായ ലെയറുകൾ ({len(filtered_layers)} എണ്ണം):",
                options=list(filtered_layers.keys()),
                format_func=lambda x: f"{filtered_layers[x]} ({x})"
            )
        else:
            st.selectbox("ലഭ്യമായ ലെയറുകൾ:", ["ഫലങ്ങളൊന്നും കണ്ടെത്തിയില്ല"], disabled=True)
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
        manual_name = st.text_input("ലെയറിന്റെ പേര് നേരിട്ട് നൽകാം (Manual):", value="Cadastry_Kerala")
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

# നിലവിൽ ചേർത്ത ലെയറുകൾ മാനേജ് ചെയ്യാനുള്ള ചിപ്പുകൾ
if st.session_state.layers:
    st.markdown("**മാപ്പിൽ ഉൾപ്പെടുത്തിയ ലെയറുകൾ (നീക്കം ചെയ്യാൻ ക്ലിക്ക് ചെയ്യുക):**")
    to_delete = None
    cols = st.columns(min(len(st.session_state.layers), 6))
    for i, lyr in enumerate(st.session_state.layers):
        with cols[i % 6]:
            if st.button(f"🗑️ {lyr['name']}", key=f"del_{i}", use_container_width=True):
                to_delete = i
    if to_delete is not None:
        st.session_state.layers.pop(to_delete)
        st.rerun()

# മാപ്പും KMZ എക്സ്പോർട്ട് ഘടകവും
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
  <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>
  <style>
    body {{ margin: 0; padding: 0; font-family: sans-serif; }}
    #map {{ height: 540px; width: 100%; border-radius: 6px; border: 1px solid #cbd5e1; }}
    #action-bar {{
      padding: 10px 14px; background: #0f172a; color: white; display: flex; align-items: center; gap: 15px; border-radius: 6px 6px 0 0;
    }}
    .btn {{
      background: #0284c7; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold;
    }}
    .btn:disabled {{ background: #475569; cursor: not-allowed; }}
    #info-text {{ font-size: 13px; color: #38bdf8; }}
  </style>
</head>
<body>
  <div id="action-bar">
    <button id="dlBtn" class="btn" disabled>സെലക്ട് ചെയ്ത ഏരിയ KMZ ആയി ഡൗൺലോഡ് ചെയ്യുക</button>
    <span id="info-text">മാപ്പിൽ റെക്ടാങ്കിൾ അല്ലെങ്കിൽ പോളിഗോൺ വരച്ച് പ്രദേശം തിരഞ്ഞെടുക്കുക.</span>
  </div>
  <div id="map"></div>

  <script>
    const map = L.map('map', {{ center: [10.5471, 76.1295], zoom: 10 }});
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

    let selectedBounds = null;
    map.on(L.Draw.Event.CREATED, (e) => {{
      drawnItems.clearLayers();
      drawnItems.addLayer(e.layer);
      selectedBounds = e.layer.getBounds();
      document.getElementById('dlBtn').disabled = activeLayers.length === 0;
      document.getElementById('info-text').innerText = "ഏരിയ തയ്യാറാണ്. KMZ ഡൗൺലോഡ് ചെയ്യാം.";
    }});

    map.on(L.Draw.Event.DELETED, () => {{
      selectedBounds = null;
      document.getElementById('dlBtn').disabled = true;
      document.getElementById('info-text').innerText = "ഏരിയ വീണ്ടും തിരഞ്ഞെടുക്കുക.";
    }});

    document.getElementById('dlBtn').addEventListener('click', async () => {{
      if (!selectedBounds || activeLayers.length === 0) return;
      const minX = selectedBounds.getWest();
      const minY = selectedBounds.getSouth();
      const maxX = selectedBounds.getEast();
      const maxY = selectedBounds.getNorth();

      let links = "";
      activeLayers.forEach(l => {{
        links += `
        <NetworkLink>
          <name>${{l.name}}</name>
          <open>1</open>
          <Url>
            <href>${{l.baseUrl}}?service=wms&amp;request=GetMap&amp;version=1.1.1&amp;format=application/vnd.google-earth.kml+xml&amp;layers=${{l.name}}&amp;bbox=${{minX}},${{minY}},${{maxX}},${{maxY}}&amp;width=2048&amp;height=2048&amp;srs=EPSG:4326&amp;transparent=true</href>
            <viewRefreshMode>never</viewRefreshMode>
          </Url>
        </NetworkLink>`;
      }});

      const kml = `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>WMS_Exported_Area</name>
    <LookAt>
      <longitude>${{(minX + maxX) / 2}}</longitude>
      <latitude>${{(minY + maxY) / 2}}</latitude>
      <range>1500</range>
      <altitudeMode>clampToGround</altitudeMode>
    </LookAt>
    ${{links}}
  </Document>
</kml>`;

      const zip = new JSZip();
      zip.file("doc.kml", kml);
      const blob = await zip.generateAsync({{ type: "blob" }});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `WMS_Network_${{Date.now()}}.kmz`;
      a.click();
    }});
  </script>
</body>
</html>
"""

components.html(html_code, height=620)
