import streamlit as st
import streamlit.components.v1 as components
import requests
import xml.etree.ElementTree as ET
import json
import base64

st.set_page_config(
    page_title="WMS Vector Polygon Exporter",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Streamlit-ന്റെ മുകളിലെയും താഴത്തെയും മാർജിനുകൾ പൂർണ്ണമായി ഒഴിവാക്കാൻ CSS
st.markdown("""
<style>
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

# സെഷൻ സ്റ്റേറ്റുകൾ
if "available_layers" not in st.session_state:
    st.session_state.available_layers = {}
if "selected_layers" not in st.session_state:
    st.session_state.selected_layers = []

# WMS GetCapabilities സെർവർ വഴി ഫെച്ച് ചെയ്യുന്നു (CORS തടസ്സങ്ങൾ ഒഴിവാക്കാൻ)
def get_capabilities_data(url):
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
            return layer_dict
    except:
        pass
    return {}

# ഡാറ്റ JSON ആക്കുന്നു
layers_json = json.dumps(st.session_state.selected_layers)

html_code = f"""
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
    html, body {{
      margin: 0;
      padding: 0;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      font-family: 'Segoe UI', sans-serif;
    }}
    #map {{
      width: 100vw;
      height: 100vh;
      position: absolute;
      top: 0;
      left: 0;
      z-index: 1;
    }}
    
    /* ഫ്ലോട്ടിംഗ് പാനൽ */
    #control-panel {{
      position: absolute;
      top: 15px;
      left: 60px;
      width: 360px;
      background: rgba(15, 23, 42, 0.95);
      backdrop-filter: blur(8px);
      border-radius: 8px;
      padding: 16px;
      color: #fff;
      z-index: 1000;
      box-shadow: 0 4px 20px rgba(0,0,0,0.4);
      border: 1px solid #334155;
      transition: all 0.3s ease;
    }}
    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      font-size: 15px;
      font-weight: bold;
      color: #38bdf8;
      cursor: pointer;
    }}
    .input-box {{
      width: 100%;
      padding: 8px 10px;
      margin-bottom: 10px;
      background: #1e293b;
      border: 1px solid #475569;
      border-radius: 4px;
      color: #fff;
      font-size: 13px;
      box-sizing: border-box;
    }}
    .input-box:focus {{
      outline: 2px solid #0284c7;
    }}
    .btn {{
      width: 100%;
      background: #0284c7;
      color: white;
      border: none;
      padding: 9px;
      border-radius: 4px;
      cursor: pointer;
      font-weight: 600;
      margin-bottom: 8px;
      transition: background 0.2s;
    }}
    .btn:hover:not(:disabled) {{ background: #0369a1; }}
    .btn:disabled {{ background: #475569; cursor: not-allowed; opacity: 0.6; }}
    
    #search-results {{
      max-height: 160px;
      overflow-y: auto;
      background: #1e293b;
      border: 1px solid #475569;
      border-radius: 4px;
      margin-bottom: 10px;
      display: none;
    }}
    .result-item {{
      padding: 8px 10px;
      font-size: 12px;
      cursor: pointer;
      border-bottom: 1px solid #334155;
    }}
    .result-item:hover {{
      background: #0284c7;
    }}
    
    #selected-badge {{
      display: none;
      background: #065f46;
      border: 1px solid #059669;
      padding: 6px 10px;
      border-radius: 4px;
      font-size: 12px;
      margin-bottom: 10px;
      justify-content: space-between;
      align-items: center;
    }}
    #status-msg {{
      font-size: 12px;
      color: #94a3b8;
      line-height: 1.4;
      margin-top: 5px;
    }}
  </style>
</head>
<body>

  <div id="map"></div>

  <!-- ഫുൾ സ്ക്രീൻ മാപ്പിന് മുകളിലുള്ള ഫ്ലോട്ടിംഗ് കൺട്രോളുകൾ -->
  <div id="control-panel">
    <div class="panel-header" onclick="togglePanel()">
      <span>🗺️ WMS ലെയർ & KMZ ടൂൾ</span>
      <span id="toggle-icon">➖</span>
    </div>

    <div id="panel-content">
      <input type="text" id="wmsUrl" class="input-box" value="https://ksrec.in/geoserver/Kerala/wms" placeholder="WMS URL നൽകുക" />
      <button id="btnFetch" class="btn" onclick="fetchLayers()">ലെയറുകൾ എടുക്കുക</button>

      <!-- ലൈവ് സെർച്ച് ബോക്സ് -->
      <input type="text" id="layerSearch" class="input-box" placeholder="🔍 ലെയർ പേര് സെർച്ച് ചെയ്യുക..." style="display:none;" onkeyup="filterLayers()" />
      <div id="search-results"></div>

      <div id="selected-badge">
        <span id="selected-layer-name"></span>
        <span style="cursor:pointer; color:#fca5a5; font-weight:bold;" onclick="removeLayer()">❌</span>
      </div>

      <button id="btnExportKmz" class="btn" style="background:#059669;" disabled onclick="exportVectorKMZ()">
        സെലക്ട് ചെയ്ത ഏരിയ വെക്റ്റർ KMZ ആക്കുക
      </button>

      <div id="status-msg">WMS URL നൽകി 'ലെയറുകൾ എടുക്കുക' ക്ലിക്ക് ചെയ്യുക.</div>
    </div>
  </div>

  <script>
    // 1. ഫുൾ സ്ക്രീൻ മാപ്പ് സെറ്റപ്പ്
    const map = L.map('map', { zoomControl: false }).setView([10.5471, 76.1295], 11);
    L.control.zoom({ position: 'bottomright' }).addTo(map);

    map.createPane('overlayPane');
    map.getPane('overlayPane').style.zIndex = 600;

    // Google Roads & Hybrid
    const roads = L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', { maxZoom: 22 }).addTo(map);
    const hybrid = L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', { maxZoom: 22 });
    L.control.layers({ "Google Roads": roads, "Google Hybrid": hybrid }, null, { position: 'topright' }).addTo(map);

    let allLayersList = [];
    let currentWmsLayer = null;
    let selectedLayerObj = null;
    let selectedBounds = null;

    // ഏരിയ സെലക്ഷൻ ടൂൾ
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
      checkDownloadReady();
    });

    map.on(L.Draw.Event.DELETED, () => {
      selectedBounds = null;
      checkDownloadReady();
    });

    // 2. പാനൽ ചുരുക്കാനും വലുതാക്കാനുമുള്ള ഫംഗ്ഷൻ
    function togglePanel() {
      const content = document.getElementById('panel-content');
      const icon = document.getElementById('toggle-icon');
      if (content.style.display === "none") {
        content.style.display = "block";
        icon.innerText = "➖";
      } else {
        content.style.display = "none";
        icon.innerText = "➕";
      }
    }

    // 3. WMS Capabilities വഴി ലെയറുകൾ എടുക്കൽ
    async function fetchLayers() {
      const url = document.getElementById('wmsUrl').value.trim();
      const status = document.getElementById('status-msg');
      status.innerText = "ലെയറുകൾ ഫെച്ച് ചെയ്യുന്നു...";
      
      const baseUrl = url.split("?")[0];
      const targetUrl = `${baseUrl}?service=WMS&version=1.1.1&request=GetCapabilities`;

      const proxies = [
        `https://api.allorigins.win/raw?url=${encodeURIComponent(targetUrl)}`,
        `https://corsproxy.io/?${encodeURIComponent(targetUrl)}`,
        `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(targetUrl)}`
      ];

      let xmlText = null;
      for (const p of proxies) {
        try {
          const res = await fetch(p);
          if (res.ok) {
            xmlText = await res.text();
            if (xmlText.includes("<Layer")) break;
          }
        } catch(e) {}
      }

      if (!xmlText) {
        status.innerText = "CORS തടസ്സപ്പെട്ടു. മാനുവൽ ആയി 'Cadastry_Kerala' തിരഞ്ഞെടുക്കുന്നു.";
        allLayersList = [{ name: 'Cadastry_Kerala', title: 'Cadastry_Kerala' }];
        enableSearch();
        return;
      }

      try {
        const parser = new DOMParser();
        const xml = parser.parseFromString(xmlText, "text/xml");
        const layers = xml.querySelectorAll("Layer > Layer");
        allLayersList = [];

        layers.forEach(l => {
          const n = l.querySelector("Name");
          const t = l.querySelector("Title");
          if (n) {
            allLayersList.push({
              name: n.textContent.trim(),
              title: t ? t.textContent.trim() : n.textContent.trim()
            });
          }
        });

        if (allLayersList.length > 0) {
          enableSearch();
          status.innerText = `${allLayersList.length} ലെയറുകൾ ലഭ്യമാണ്. പേര് സെർച്ച് ചെയ്യുക.`;
        }
      } catch (err) {
        status.innerText = "പാർസിങ് പിഴവ്.";
      }
    }

    function enableSearch() {
      document.getElementById('layerSearch').style.display = "block";
      filterLayers();
    }

    // 4. ലൈവ് സെർച്ച് ഫിൽട്ടർ
    function filterLayers() {
      const q = document.getElementById('layerSearch').value.toLowerCase();
      const resBox = document.getElementById('search-results');
      resBox.innerHTML = "";

      const filtered = allLayersList.filter(l => l.name.toLowerCase().includes(q) || l.title.toLowerCase().includes(q));

      if (filtered.length > 0) {
        resBox.style.display = "block";
        filtered.slice(0, 50).forEach(l => {
          const div = document.createElement('div');
          div.className = "result-item";
          div.innerText = `${l.title} (${l.name})`;
          div.onclick = () => selectLayer(l);
          resBox.appendChild(div);
        });
      } else {
        resBox.style.display = "none";
      }
    }

    // 5. ലെയർ സെലക്ഷനും ഫുൾ സ്ക്രീൻ മാപ്പ് ലോഡിംഗും
    function selectLayer(layer) {
      document.getElementById('search-results').style.display = "none";
      document.getElementById('layerSearch').value = layer.name;
      document.getElementById('selected-badge').style.display = "flex";
      document.getElementById('selected-layer-name').innerText = layer.name;

      selectedLayerObj = layer;
      const baseUrl = document.getElementById('wmsUrl').value.trim().split("?")[0];

      if (currentWmsLayer) map.removeLayer(currentWmsLayer);

      currentWmsLayer = L.tileLayer.wms(baseUrl, {
        layers: layer.name,
        format: 'image/png',
        transparent: true,
        version: '1.1.1',
        maxZoom: 22,
        pane: 'overlayPane',
        opacity: 0.9
      }).addTo(map);

      document.getElementById('status-msg').innerText = "ലെയർ ലോഡ് ചെയ്തു! മാപ്പിൽ ഏരിയ സെലക്ട് ചെയ്യുക.";
      checkDownloadReady();

      // സെലക്ട് ചെയ്തയുടൻ മാപ്പ് വ്യക്തമായി കാണാൻ പാനൽ തനിയെ ചെറുതാകുന്നു
      togglePanel();
    }

    function removeLayer() {
      if (currentWmsLayer) map.removeLayer(currentWmsLayer);
      currentWmsLayer = null;
      selectedLayerObj = null;
      document.getElementById('selected-badge').style.display = "none";
      checkDownloadReady();
    }

    function checkDownloadReady() {
      const btn = document.getElementById('btnExportKmz');
      btn.disabled = !(selectedLayerObj && selectedBounds);
    }

    // 6. NetworkLink ഇല്ലാതെ മുഴുവൻ വെക്റ്റർ പോളിഗോണുകളും KMZ ആയി മാറ്റുന്നു
    async function exportVectorKMZ() {
      if (!selectedLayerObj || !selectedBounds) return;
      const status = document.getElementById('status-msg');
      status.innerText = "യഥാർത്ഥ പോളിഗോൺ ഡാറ്റ ശേഖരിക്കുന്നു...";

      const baseUrl = document.getElementById('wmsUrl').value.trim().split("?")[0];
      const wfsUrl = baseUrl.replace("/wms", "/wfs");
      const minX = selectedBounds.getWest();
      const minY = selectedBounds.getSouth();
      const maxX = selectedBounds.getEast();
      const maxY = selectedBounds.getNorth();

      // WFS GetFeature വഴി പോളിഗോൺ GeoJSON ഫെച്ച് ചെയ്യുന്നു
      const featureUrl = `${wfsUrl}?service=WFS&version=1.1.0&request=GetFeature&typeName=${selectedLayerObj.name}&outputFormat=application/json&srsname=EPSG:4326&bbox=${minX},${minY},${maxX},${maxY},EPSG:4326`;
      const proxyUrl = `https://api.allorigins.win/raw?url=${encodeURIComponent(featureUrl)}`;

      try {
        const res = await fetch(proxyUrl);
        const geojson = await res.json();

        if (!geojson.features || geojson.features.length === 0) {
          alert("ഈ ഏരിയയിൽ പോളിഗോൺ ഫീച്ചറുകൾ ലഭ്യമല്ല.");
          status.innerText = "ഫീച്ചറുകൾ കണ്ടെത്തിയില്ല.";
          return;
        }

        // KML യഥാർത്ഥ പോളിഗോൺ സ്ട്രക്ചർ നിർമ്മിക്കുന്നു
        let placemarks = "";
        geojson.features.forEach((feat, i) => {
          const props = feat.properties || {};
          const geom = feat.geometry;
          const name = props.SURVEY_NO || props.LAND_NO || props.name || `Polygon_${i+1}`;

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
    <name>${selectedLayerObj.name} Export</name>
    <Style id="polyStyle">
      <LineStyle><color>ff0000ff</color><width>2</width></LineStyle>
      <PolyStyle><fill>0</fill></PolyStyle>
    </Style>
    ${placemarks}
  </Document>
</kml>`;

        // ZIP ആക്കി KMZ നിർമ്മിക്കുന്നു
        const zip = new JSZip();
        zip.file("doc.kml", kmlText);
        const kmzBlob = await zip.generateAsync({ type: "blob" });

        const dlLink = document.createElement("a");
        dlLink.href = URL.createObjectURL(kmzBlob);
        dlLink.download = `${selectedLayerObj.name}_polygons.kmz`;
        dlLink.click();

        status.innerText = "വെക്റ്റർ KMZ വിജയകരമായി ഡൗൺലോഡ് ചെയ്തു!";
      } catch (err) {
        console.error(err);
        alert("പോളിഗോൺ ഡാറ്റ എക്സ്ട്രാക്റ്റ് ചെയ്യുന്നതിൽ തടസ്സം നേരിട്ടു.");
        status.innerText = "എറർ സംഭവിച്ചു.";
      }
    }
  </script>
</body>
</html>
"""

components.html(html_code, height=920, scrolling=False)
