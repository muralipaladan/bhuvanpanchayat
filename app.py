import streamlit as st
import streamlit.components.v1 as components
import requests
import xml.etree.ElementTree as ET
import json
import io
import zipfile

st.set_page_config(
    page_title="WMS Vector Polygon Exporter",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# സ്ക്രീൻ പരമാവധി വലുതാക്കാനുള്ള സ്റ്റൈൽ
st.markdown("""
<style>
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {
        padding-top: 10px !important;
        padding-bottom: 0px !important;
        padding-left: 15px !important;
        padding-right: 15px !important;
        max-width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

# സെഷൻ സ്റ്റേറ്റുകൾ
if "available_layers" not in st.session_state:
    st.session_state.available_layers = {}
if "selected_layer_name" not in st.session_state:
    st.session_state.selected_layer_name = "Cadastry_Kerala"
if "wms_url" not in st.session_state:
    st.session_state.wms_url = "https://ksrec.in/geoserver/Kerala/wms"

# പൈത്തൺ സെർവർ വഴി ലെയറുകൾ എടുക്കൽ (CORS പൂർണ്ണമായി ബൈപാസ്സ് ചെയ്യുന്നു)
def fetch_layers_via_python(url):
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
        return {}, f"സെർവർ കോഡ്: {res.status_code}"
    except Exception as e:
        return {}, str(e)

# --- Top Navigation Bar ---
with st.expander("⚙️ WMS ലെയർ സെർച്ച് & ക്രമീകരണങ്ങൾ", expanded=(len(st.session_state.available_layers) == 0)):
    c1, c2 = st.columns([3, 1])
    with c1:
        wms_input = st.text_input("WMS സെർവർ URL:", value=st.session_state.wms_url)
        st.session_state.wms_url = wms_input
    with c2:
        st.write("##")
        if st.button("ലെയറുകൾ ഫെച്ച് ചെയ്യുക", use_container_width=True):
            with st.spinner("പൈത്തൺ വഴി സെർവർ പരിശോധിക്കുന്നു..."):
                layers, err = fetch_layers_via_python(st.session_state.wms_url)
                if layers:
                    st.session_state.available_layers = layers
                    st.success(f"{len(layers)} ലെയറുകൾ വിജയകരമായി കണ്ടെത്തി!")
                else:
                    st.error(f"ലെയറുകൾ ലഭിച്ചില്ല: {err}")

    # ലെയർ സെർച്ച് ഫിൽട്ടർ
    if st.session_state.available_layers:
        s_col1, s_col2 = st.columns([1, 2])
        with s_col1:
            query = st.text_input("🔍 ലെയർ പേര് സെർച്ച് ചെയ്യുക:", placeholder="ഉദാ: Cadastry, village...").strip().lower()
        
        all_l = st.session_state.available_layers
        filtered = {k: v for k, v in all_l.items() if query in k.lower() or query in v.lower()} if query else all_l
        
        with s_col2:
            if filtered:
                sel = st.selectbox(f"ലഭ്യമായ ലെയറുകൾ ({len(filtered)} എണ്ണം):", options=list(filtered.keys()), format_func=lambda x: f"{filtered[x]} ({x})")
                if st.button("ഈ ലെയർ മാപ്പിൽ ലോഡ് ചെയ്യുക"):
                    st.session_state.selected_layer_name = sel
                    st.rerun()
            else:
                st.warning("സെർച്ച് ഫലങ്ങൾ ലഭ്യമല്ല.")
    else:
        m_col1, m_col2 = st.columns([3, 1])
        with m_col1:
            manual_layer = st.text_input("ലെയർ പേര് നേരിട്ട് നൽകുക:", value=st.session_state.selected_layer_name)
        with m_col2:
            st.write("##")
            if st.button("ലോഡ് ചെയ്യുക", use_container_width=True):
                st.session_state.selected_layer_name = manual_layer
                st.rerun()

# നിലവിൽ ലോഡ് ചെയ്തിരിക്കുന്ന ലെയർ
st.info(f"നിലവിലെ ലെയർ: **{st.session_state.selected_layer_name}** | മാപ്പിൽ Polygon/Rectangle വരച്ച് സെലക്ട് ചെയ്ത ശേഷം താഴെയുള്ള ബട്ടൺ വഴി യഥാർത്ഥ പോളിഗോൺ KMZ ഡൗൺലോഡ് ചെയ്യാം.")

# --- Full Canvas Map Component ---
active_base_url = st.session_state.wms_url.split("?")[0].strip()
active_layer_name = st.session_state.selected_layer_name

html_code = """
<!DOCTYPE html>
<html lang="ml">
<head>
  <meta charset="UTF-8">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.draw/1.0.4/leaflet.draw.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>

  <style>
    html, body {
      margin: 0;
      padding: 0;
      width: 100vw;
      height: 78vh;
      font-family: 'Segoe UI', sans-serif;
      overflow: hidden;
    }
    #map {
      width: 100%;
      height: 100%;
      border-radius: 6px;
      border: 1px solid #cbd5e1;
    }
    #control-floating {
      position: absolute;
      bottom: 25px;
      left: 20px;
      background: rgba(15, 23, 42, 0.95);
      border-radius: 6px;
      padding: 10px 14px;
      color: #fff;
      z-index: 1000;
      box-shadow: 0 4px 15px rgba(0,0,0,0.3);
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .btn-action {
      background: #059669;
      color: white;
      border: none;
      padding: 8px 14px;
      border-radius: 4px;
      cursor: pointer;
      font-weight: bold;
      font-size: 13px;
    }
    .btn-action:disabled {
      background: #475569;
      cursor: not-allowed;
      opacity: 0.6;
    }
  </style>
</head>
<body>

  <div id="map"></div>

  <div id="control-floating">
    <button id="exportKmzBtn" class="btn-action" disabled onclick="downloadVectorKMZ()">
      സെലക്ട് ചെയ്ത ഏരിയ വെക്റ്റർ KMZ ആയി ഡൗൺലോഡ് ചെയ്യുക
    </button>
    <span id="map-msg" style="font-size:12px; color:#38bdf8;">മാപ്പിൽ ഏരിയ സെലക്ട് ചെയ്യുക...</span>
  </div>

  <script>
    const baseUrl = '""" + active_base_url + """';
    const layerName = '""" + active_layer_name + """';

    const map = L.map('map').setView([10.5471, 76.1295], 11);

    map.createPane('overlayPane');
    map.getPane('overlayPane').style.zIndex = 600;

    const googleRoads = L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', { maxZoom: 22 }).addTo(map);
    const googleHybrid = L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', { maxZoom: 22 });
    L.control.layers({ "Google Roads": googleRoads, "Google Hybrid": googleHybrid }, null, { position: 'topright' }).addTo(map);

    // തിരഞ്ഞെടുത്ത WMS ടൈലുകൾ മാപ്പിൽ ചേർക്കുന്നു
    L.tileLayer.wms(baseUrl, {
      layers: layerName,
      format: 'image/png',
      transparent: true,
      version: '1.1.1',
      maxZoom: 22,
      pane: 'overlayPane',
      opacity: 0.9
    }).addTo(map);

    let selectedBounds = null;
    const drawnItems = new L.FeatureGroup().addTo(map);
    const drawControl = new L.Control.Draw({
      position: 'topleft',
      draw: {
        polyline: false, circle: false, marker: false, circlemarker: false,
        rectangle: { shapeOptions: { color: '#ef4444', weight: 2, fillOpacity: 0.2 } },
        polygon: { shapeOptions: { color: '#ef4444', weight: 2, fillOpacity: 0.2 } }
      },
      edit: { featureGroup: drawnItems, remove: true }
    });
    map.addControl(drawControl);

    map.on(L.Draw.Event.CREATED, (e) => {
      drawnItems.clearLayers();
      drawnItems.addLayer(e.layer);
      selectedBounds = e.layer.getBounds();
      document.getElementById('exportKmzBtn').disabled = false;
      document.getElementById('map-msg').innerText = "ഏരിയ തയ്യാറാണ്. KMZ ഡൗൺലോഡ് ചെയ്യാം.";
    });

    map.on(L.Draw.Event.DELETED, () => {
      selectedBounds = null;
      document.getElementById('exportKmzBtn').disabled = true;
      document.getElementById('map-msg').innerText = "ഏരിയ വീണ്ടും തിരഞ്ഞെടുക്കുക.";
    });

    // വെക്റ്റർ പോളിഗോൺ KMZ എക്സ്പോർട്ട്
    async function downloadVectorKMZ() {
      if (!selectedBounds) return;
      const statusEl = document.getElementById('map-msg');
      statusEl.innerText = "ഡാറ്റ ശേഖരിക്കുന്നു...";

      const wfsUrl = baseUrl.replace('/wms', '/wfs');
      const minX = selectedBounds.getWest();
      const minY = selectedBounds.getSouth();
      const maxX = selectedBounds.getEast();
      const maxY = selectedBounds.getNorth();

      const featureUrl = `${wfsUrl}?service=WFS&version=1.1.0&request=GetFeature&typeName=${layerName}&outputFormat=application/json&srsname=EPSG:4326&bbox=${minX},${minY},${maxX},${maxY},EPSG:4326`;

      try {
        const res = await fetch(featureUrl);
        const geojson = await res.json();

        if (!geojson.features || geojson.features.length === 0) {
          alert("ഈ ഏരിയയിൽ വെക്റ്റർ പോളിഗോണുകൾ കണ്ടെത്തിയില്ല.");
          statusEl.innerText = "ഫീച്ചറുകൾ ലഭ്യമല്ല.";
          return;
        }

        let placemarks = "";
        geojson.features.forEach((feat, i) => {
          const props = feat.properties || {};
          const geom = feat.geometry;
          const name = props.SURVEY_NO || props.LAND_NO || props.name || `Survey_${i+1}`;

          let desc = "<table border='1' style='font-size:12px;'>";
          for (let k in props) desc += `<tr><td><b>${k}</b></td><td>${props[k]}</td></tr>`;
          desc += "</table>";

          let geomStr = "";
          if (geom.type === "Polygon") {
            const coords = geom.coordinates[0].map(c => `${c[0]},${c[1]},0`).join(" ");
            geomStr = `<Polygon><outerBoundaryIs><LinearRing><coordinates>${coords}</coordinates></LinearRing></outerBoundaryIs></Polygon>`;
          } else if (geom.type === "MultiPolygon") {
            geomStr = "<MultiGeometry>" + geom.coordinates.map(poly => {
              const coords = poly[0].map(c => `${c[0]},${c[1]},0`).join(" ");
              return `<Polygon><outerBoundaryIs><LinearRing><coordinates>${coords}</coordinates></LinearRing></outerBoundaryIs></Polygon>`;
            }).join("") + "</MultiGeometry>";
          }

          if (geomStr) {
            placemarks += `
            <Placemark>
              <name>${name}</name>
              <description><![CDATA[${desc}]]></description>
              <styleUrl>#polyStyle</styleUrl>
              ${geomStr}
            </Placemark>`;
          }
        });

        const kmlText = `<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>${layerName} Export</name>
    <Style id="polyStyle">
      <LineStyle><color>ff0000ff</color><width>2</width></LineStyle>
      <PolyStyle><fill>0</fill></PolyStyle>
    </Style>
    ${placemarks}
  </Document>
</kml>`;

        const zip = new JSZip();
        zip.file("doc.kml", kmlText);
        const kmzBlob = await zip.generateAsync({ type: "blob" });

        const dlLink = document.createElement("a");
        dlLink.href = URL.createObjectURL(kmzBlob);
        dlLink.download = `${layerName}_polygons.kmz`;
        dlLink.click();

        statusEl.innerText = "വെക്റ്റർ KMZ ഡൗൺലോഡ് പൂർത്തിയായി!";
      } catch (err) {
        console.error(err);
        alert("വെക്റ്റർ ഡാറ്റ ലഭ്യമാക്കുന്നതിൽ തടസ്സം നേരിട്ടു.");
        statusEl.innerText = "ഡൗൺലോഡ് പരാജയപ്പെട്ടു.";
      }
    }
  </script>
</body>
</html>
"""

components.html(html_code, height=650, scrolling=False)