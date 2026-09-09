with b_col2:
    st.write("##")
    if st.button("KMZ ഡൗൺലോഡ് ചെയ്യുക", use_container_width=True, disabled=not bbox_val):
        with st.spinner("സെർവറിൽ നിന്ന് ഹൈ-റെസല്യൂഷൻ ഡാറ്റ ശേഖരിക്കുന്നു..."):
            try:
                raw_coords = [c.strip() for c in bbox_val.split(",")]
                if len(raw_coords) != 4:
                    st.error("BBOX തെറ്റാണ്. 4 കോർഡിനേറ്റുകൾ ഉണ്ടായിരിക്കണം.")
                    st.stop()

                minx, miny, maxx, maxy = raw_coords[0], raw_coords[1], raw_coords[2], raw_coords[3]

                # WMS 1.1.1 സ്റ്റാൻഡേർഡ് അനുസരിച്ചുള്ള കൃത്യമായ പാരാമീറ്ററുകൾ
                params = {
                    "service": "WMS",
                    "request": "GetMap",
                    "version": "1.1.1",
                    "layers": active_layer_name,
                    "format": "image/png",
                    "transparent": "true",
                    "srs": "EPSG:4326",
                    "bbox": f"{minx},{miny},{maxx},{maxy}",
                    "width": "2048",
                    "height": "2048"
                }

                domain = active_base_url.split("//")[-1].split("/")[0]
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "Referer": f"https://{domain}/",
                    "Origin": f"https://{domain}"
                }

                # GetMap റിക്വസ്റ്റ് അയക്കുന്നു
                img_res = requests.get(active_base_url, params=params, headers=headers, timeout=30)

                # 400 എറർ വരികയാണെങ്കിൽ fallback ആയി transparent=false പരീക്ഷിക്കുന്നു
                if img_res.status_code == 400:
                    params["transparent"] = "false"
                    img_res = requests.get(active_base_url, params=params, headers=headers, timeout=30)

                if img_res.status_code == 200 and "image" in img_res.headers.get("content-type", ""):
                    # KML ഗ്രൗണ്ട് ഓവർലേ ഫയൽ നിർമ്മിക്കുന്നു
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

                    # ZIP ബഫറിലേക്ക് ചിത്രവും KML-ഉം ചേർത്ത് സമ്പൂർണ്ണ KMZ നിർമ്മിക്കുന്നു
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
                        z.writestr("doc.kml", kml_content.encode('utf-8'))
                        z.writestr("overlay.png", img_res.content)

                    st.success("സമ്പൂർണ്ണ KMZ വിജയകരമായി തയ്യാറായി!")
                    st.download_button(
                        label="⬇️ KMZ ഫയൽ സേവ് ചെയ്യുക",
                        data=zip_buffer.getvalue(),
                        file_name=f"{active_layer_name}_{minx}_{miny}.kmz",
                        mime="application/vnd.google-earth.kmz",
                        use_container_width=True
                    )
                else:
                    # സെർവറിൽ നിന്ന് വരുന്ന യഥാർത്ഥ XML എറർ കാണിക്കുന്നു
                    error_msg = img_res.text[:300] if img_res.text else "Unknown"
                    st.error(f"സെർവർ എറർ (Status {img_res.status_code}): {error_msg}")

            except Exception as ex:
                st.error(f"ഡൗൺലോഡിൽ തടസ്സം നേരിട്ടു: {ex}")