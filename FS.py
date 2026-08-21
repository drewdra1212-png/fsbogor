import io
import re
import zipfile
import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & CUSTOM STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Pencarian Homepass & Splitter ID - FS Bogor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for Modern, Premium UI
st.markdown(
    """
    <style>
    /* Metric Card Styling */
    .metric-container {
        background: linear-gradient(135deg, #f6f8fa 0%, #edf2f7 100%);
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 22px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 10px;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 700;
        color: #1a202c;
    }
    .metric-label {
        font-size: 13px;
        color: #718096;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }
    
    /* Search Box & Banner */
    .search-title {
        font-size: 28px;
        font-weight: 800;
        color: #2b6cb0;
        margin-bottom: 4px;
    }
    .search-subtitle {
        font-size: 14px;
        color: #4a5568;
        margin-bottom: 20px;
    }
    
    /* DataFrame custom table */
    .stDataFrame { border-radius: 8px; overflow: hidden; }
    </style>
""",
    unsafe_allow_html=True,
)

FILE_PATH = "HID FS Bogor.xlsx"


# -----------------------------------------------------------------------------
# 2. DATA LOADING & CACHING (WITH SMART INDEXING & BLOCK PARSING)
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner="Memuat database FS Bogor (129,000+ data)...")
def load_data(file_path):
    try:
        df = pd.read_excel(file_path, sheet_name="List HID")

        # Pastikan semua kolom bertipe string & hilangkan whitespace berlebih
        exclude_cols = [
            "search_text",
            "search_clean",
            "norm_house",
            "norm_road",
            "norm_area",
        ]
        cols_to_convert = [c for c in df.columns if c not in exclude_cols]
        for col in cols_to_convert:
            df[col] = df[col].fillna("").astype(str).str.strip()

        # Build normalized house number, road text, area text for exact block & house matching
        if "no_rumah_gedung" in df.columns:
            df["norm_house"] = (
                df["no_rumah_gedung"]
                .str.lower()
                .apply(lambda x: re.sub(r"[^\w\s]", "", x))
            )
        else:
            df["norm_house"] = ""

        if "nama_jalan_" in df.columns:
            df["norm_road"] = df["nama_jalan_"].str.lower().apply(
                lambda x: " "
                + " ".join(re.sub(r"[^\w\s]", " ", str(x)).split())
                + " "
            )
        else:
            df["norm_road"] = ""

        if "Area Name" in df.columns:
            df["norm_area"] = df["Area Name"].str.lower().apply(
                lambda x: " ".join(re.sub(r"[^\w\s]", " ", str(x)).split())
            )
        else:
            df["norm_area"] = ""

        # Vektoriasi pembuatan kolom search_clean serba-bisa
        search_cols = [
            c
            for c in [
                "homepass_id",
                "Area Name",
                "Distrrik",
                "nama_jalan_",
                "no_rumah_gedung",
                "resident_name",
                "splitter_id",
                "kelurahan",
                "kecamatan",
                "HUB",
                "NODE",
                "pop_id",
            ]
            if c in df.columns
        ]

        search_series = pd.Series("", index=df.index)
        for col in search_cols:
            search_series = search_series + " " + df[col]

        # Standardize punctuation and spaces for instant sub-second matching
        df["search_clean"] = search_series.str.lower().apply(
            lambda x: " ".join(re.sub(r"[^\w\s]", " ", x).split())
        )
        return df
    except Exception as e:
        st.error(f"❌ Gagal membaca file '{file_path}': {str(e)}")
        return pd.DataFrame()


df_raw = load_data(FILE_PATH)

if df_raw.empty:
    st.stop()

# -----------------------------------------------------------------------------
# 3. HEADER & TITLE
# -----------------------------------------------------------------------------
st.markdown(
    '<div class="search-title">🔎 Smart Search Homepass & Splitter ID — FS Bogor</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="search-subtitle">Ketik pencarian bebas secara lengkap (Contoh: Nama Jalan + Blok + No. Rumah, ID Homepass, ID Splitter, Area Name, dll.)</div>',
    unsafe_allow_html=True,
)

# Initialize Session State for Search Query
if "search_query" not in st.session_state:
    st.session_state.search_query = ""


def set_search(text):
    st.session_state.search_query = text


def clear_search():
    st.session_state.search_query = ""


# -----------------------------------------------------------------------------
# 4. MAIN SEARCH BAR (PROMINENT & CENTRED)
# -----------------------------------------------------------------------------
col_s1, col_s2 = st.columns([5, 1])
with col_s1:
    search_input = st.text_input(
        "🔍 Kolom Pencarian Cepat (Smart Search):",
        value=st.session_state.search_query,
        placeholder="Contoh: nuansa alam B 7 / Kintamani KA 10 / Bali Resort BLV 12 / 16310H / BGR-03...",
        help="Pencarian cerdas serba-bisa: Otomatis mendeteksi Nama Jalan, Kode Blok spesifik, dan Nomor Rumah.",
    )
with col_s2:
    st.write("&nbsp;")
    search_clicked = st.button("🔍 Cari", type="primary", use_container_width=True)

# Sync search widget with session state
if search_clicked or search_input != st.session_state.search_query:
    st.session_state.search_query = search_input

# Quick Search Shortcuts & Clear Button
col_shortcuts, col_reset = st.columns([5, 1])

with col_shortcuts:
    st.write("**Contoh Pencarian Cepat:**")
    btn_col1, btn_col2, btn_col3, btn_col4, _ = st.columns([1.2, 1.2, 1, 1, 1.6])
    with btn_col1:
        if st.button("💡 Nuansa Alam B 7", use_container_width=True):
            set_search("nuansa alam B 7")
            st.rerun()
    with btn_col2:
        if st.button("💡 Kintamani KA 10", use_container_width=True):
            set_search("Kintamani KA 10")
            st.rerun()
    with btn_col3:
        if st.button("💡 Bali Resort BLV 12", use_container_width=True):
            set_search("Bali Resort BLV 12")
            st.rerun()
    with btn_col4:
        if st.button("💡 BGR-03", use_container_width=True):
            set_search("BGR-03")
            st.rerun()

with col_reset:
    st.write("&nbsp;")
    if st.button("🔄 Reset / Hapus", type="secondary", use_container_width=True):
        clear_search()
        st.rerun()

st.markdown("<hr style='margin: 15px 0 20px 0;'>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. FILTER SPESIFIK NAMA JALAN / BLOK & NOMOR RUMAH
# -----------------------------------------------------------------------------
with st.expander("📌 Filter Spesifik Nama Jalan/Blok & Nomor Rumah (Opsional)", expanded=False):
    col_f1, col_f2 = st.columns(2)

    with col_f1:
        road_options = ["-- Semua Nama Jalan & Blok --"] + sorted(
            [r for r in df_raw["nama_jalan_"].unique() if r]
        )
        selected_road = st.selectbox("Filter Nama Jalan & Blok:", road_options)

    with col_f2:
        house_input = st.text_input(
            "Filter Nomor Rumah Spesifik:",
            value="",
            placeholder="Contoh: 7 / 10 / 12 / 24 / 3A...",
            help="Ketik nomor rumah untuk menyaring data secara presisi.",
        )

# -----------------------------------------------------------------------------
# 6. SMART FILTERING & BLOCK RANKING LOGIC
# -----------------------------------------------------------------------------
df_filtered = df_raw.copy()

# Apply Smart Multi-token Search Engine
query = st.session_state.search_query.strip()
if query:
    STOP_WORDS = {"jl", "jln", "jalan", "no", "nomor", "gg", "gang", "rt", "rw", "blok"}

    # 1. Clean query & strip noise address stop words
    q_clean = re.sub(r"[^\w\s]", " ", query.lower())
    raw_tokens = [t for t in q_clean.split() if t]
    tokens = [t for t in raw_tokens if t not in STOP_WORDS]
    if not tokens:
        tokens = raw_tokens

    # 2. Multi-token smart AND filtering with block specificity
    mask = pd.Series(True, index=df_filtered.index)
    numeric_tokens = [t for t in tokens if t.isdigit()]

    for token in tokens:
        if token.isdigit():
            mask = mask & df_filtered["search_clean"].str.contains(
                token, regex=False, na=False
            )
        elif len(token) <= 2:
            # Single or double letter block token (e.g. 'b', 'ka', 'jc', 'n') -> match block in nama_jalan_ or Area Name specifically!
            block_pattern = rf"\b{re.escape(token)}\b"
            road_match = df_filtered["norm_road"].str.contains(
                block_pattern, regex=True, na=False
            )
            area_match = df_filtered["norm_area"].str.contains(
                block_pattern, regex=True, na=False
            )
            mask = mask & (road_match | area_match)
        else:
            mask = mask & df_filtered["search_clean"].str.contains(
                token, regex=False, na=False
            )

    df_filtered = df_filtered[mask].copy()

    # 3. Smart House Number Ranking (prioritize exact house number match)
    if (
        numeric_tokens
        and not df_filtered.empty
        and "norm_house" in df_filtered.columns
    ):
        exact_house_mask = df_filtered["norm_house"].isin(numeric_tokens)
        if exact_house_mask.any():
            exact_matches = df_filtered[exact_house_mask]
            other_matches = df_filtered[~exact_house_mask]
            df_filtered = pd.concat([exact_matches, other_matches])

# Apply Specific Dropdown & Text Sub-Filters (Nama Jalan/Blok & Nomor Rumah)
if selected_road != "-- Semua Nama Jalan & Blok --":
    df_filtered = df_filtered[df_filtered["nama_jalan_"] == selected_road]

if house_input.strip():
    h_clean = re.sub(r"[^\w\s]", "", house_input.strip().lower())
    df_filtered = df_filtered[df_filtered["norm_house"] == h_clean]


# -----------------------------------------------------------------------------
# 7. SUMMARY METRICS
# -----------------------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(
        f"""
    <div class="metric-container">
        <div class="metric-label">Total Homepass Ditemukan</div>
        <div class="metric-value">{len(df_filtered):,}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with m2:
    unique_splitters = (
        df_filtered["splitter_id"].nunique() if not df_filtered.empty else 0
    )
    st.markdown(
        f"""
    <div class="metric-container">
        <div class="metric-label">Jumlah Splitter ID</div>
        <div class="metric-value">{unique_splitters:,}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with m3:
    unique_areas = (
        df_filtered["Area Name"].nunique() if not df_filtered.empty else 0
    )
    st.markdown(
        f"""
    <div class="metric-container">
        <div class="metric-label">Area Tercover</div>
        <div class="metric-value">{unique_areas:,}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with m4:
    unique_districts = (
        df_filtered["Distrrik"].nunique() if not df_filtered.empty else 0
    )
    st.markdown(
        f"""
    <div class="metric-container">
        <div class="metric-label">Jumlah Distrik</div>
        <div class="metric-value">{unique_districts:,}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

st.write("")

# -----------------------------------------------------------------------------
# 8. RESULTS DISPLAY TABLE & DOWNLOAD EXCEL
# -----------------------------------------------------------------------------
st.subheader("📋 Hasil Pencarian Detail")

if not df_filtered.empty:
    primary_cols = [
        "homepass_id",
        "splitter_id",
        "Area Name",
        "nama_jalan_",
        "no_rumah_gedung",
        "resident_name",
        "Distrrik",
        "HUB",
        "NODE",
        "pop_id",
        "rfs_status",
        "kelurahan",
        "kecamatan",
        "homepassed_koordinat",
        "spliter_distribusi_koordinat",
    ]

    display_cols = [c for c in primary_cols if c in df_filtered.columns]

    col_toggle, col_download = st.columns([3, 1])

    with col_toggle:
        show_all_cols = st.checkbox("Tampilkan seluruh 30+ kolom detail Excel")

    exclude_internal = [
        "search_text",
        "search_clean",
        "norm_house",
        "norm_road",
        "norm_area",
    ]
    final_cols = (
        [c for c in df_filtered.columns if c not in exclude_internal]
        if show_all_cols
        else display_cols
    )

    # Display Data Table (Dibatasi 100 baris agar sangat ringan dan smooth di HP)
    if len(df_filtered) > 100:
        st.info(f"⚠️ Menampilkan 100 data pertama dari total {len(df_filtered):,} data. Ketik pencarian yang lebih spesifik untuk mempersempit hasil.")
        
    st.dataframe(
        df_filtered[final_cols].head(100),
        use_container_width=True,
        height=500,
        hide_index=True,
    )

    # Export Excel (Fast in-memory buffer)
    @st.cache_data
    def get_excel_download(df_data):
        buffer = io.BytesIO()
        cols_export = [c for c in df_data.columns if c not in exclude_internal]
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_data[cols_export].to_excel(
                writer, index=False, sheet_name="Hasil Search"
            )
        return buffer.getvalue()

    # -------------------------------------------------------------------------
    # KMZ GENERATION — ultra-lightweight (no embedded images)
    # -------------------------------------------------------------------------
    def _parse_coord(coord_str):
        """Parse 'lat, lng' string → (lat, lng) floats or None."""
        try:
            parts = str(coord_str).split(",")
            if len(parts) == 2:
                lat = float(parts[0].strip())
                lng = float(parts[1].strip())
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return lat, lng
        except (ValueError, TypeError):
            pass
        return None

    def build_kmz(df_data):
        """Build a minimal KMZ with splitter + homepass points."""
        # Collect unique splitters
        splitter_points = {}  # splitter_id → (lat, lng)
        homepass_lines = []   # list of KML <Placemark> XML strings

        for _, row in df_data.iterrows():
            sid = str(row.get("splitter_id", "")).strip()
            hid = str(row.get("homepass_id", "")).strip()

            # Splitter coordinate (deduplicated)
            if sid and sid not in splitter_points:
                sc = _parse_coord(row.get("spliter_distribusi_koordinat", ""))
                if sc:
                    splitter_points[sid] = sc

            # Homepass coordinate
            hc = _parse_coord(row.get("homepassed_koordinat", ""))
            if hc and hid:
                area = str(row.get("Area Name", "")).strip()
                jalan = str(row.get("nama_jalan_", "")).strip()
                nomor = str(row.get("no_rumah_gedung", "")).strip()
                resident = str(row.get("resident_name", "")).strip()
                desc_parts = [p for p in [area, jalan, nomor, resident] if p]
                desc_text = ", ".join(desc_parts) if desc_parts else hid
                homepass_lines.append(
                    f'<Placemark><name>{hid}</name>'
                    f'<description>{desc_text}</description>'
                    f'<styleUrl>#hp</styleUrl>'
                    f'<Point><coordinates>{hc[1]},{hc[0]},0</coordinates></Point>'
                    f'</Placemark>'
                )

        # Splitter placemarks
        splitter_placemarks = []
        for sid, (lat, lng) in splitter_points.items():
            splitter_placemarks.append(
                f'<Placemark><name>{sid}</name>'
                f'<styleUrl>#sp</styleUrl>'
                f'<Point><coordinates>{lng},{lat},0</coordinates></Point>'
                f'</Placemark>'
            )

        # Minimal KML — standard Google Earth palette icons (no embedded files)
        kml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<kml xmlns="http://www.opengis.net/kml/2.2">'
            '<Document>'
            '<name>Hasil Pencarian FS</name>'
            '<Style id="sp">'
              '<IconStyle><color>ff0000ff</color><scale>1.0</scale>'
                '<Icon><href>http://maps.google.com/mapfiles/kml/paddle/red-circle.png</href></Icon>'
              '</IconStyle>'
              '<LabelStyle><scale>0.8</scale></LabelStyle>'
            '</Style>'
            '<Style id="hp">'
              '<IconStyle><color>ffff8800</color><scale>0.5</scale>'
                '<Icon><href>http://maps.google.com/mapfiles/kml/paddle/blu-blank-lv.png</href></Icon>'
              '</IconStyle>'
              '<LabelStyle><scale>0</scale></LabelStyle>'
            '</Style>'
            '<Folder><name>Splitter</name>'
            + "".join(splitter_placemarks)
            + '</Folder>'
            '<Folder><name>Homepass</name>'
            + "".join(homepass_lines)
            + '</Folder>'
            '</Document></kml>'
        )

        # Compress into KMZ (ZIP with max compression)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            zf.writestr("doc.kml", kml)
        return buf.getvalue()

    excel_data = get_excel_download(df_filtered)

    dl_col1, dl_col2 = st.columns(2)

    with dl_col1:
        st.download_button(
            label="📥 Download Hasil Pencarian (.xlsx)",
            data=excel_data,
            file_name="Hasil_Pencarian_HID_Bogor.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )

    with dl_col2:
        kmz_data = build_kmz(df_filtered)
        # Build a smart filename from the search query
        kmz_filename = "Hasil_Pencarian"
        if query:
            safe_name = re.sub(r'[^\w\s-]', '', query).strip().replace(' ', '_')[:50]
            if safe_name:
                kmz_filename = safe_name
        st.download_button(
            label=f"🗺️ Download KMZ — Google Earth ({len(kmz_data)/1024:.0f} KB)",
            data=kmz_data,
            file_name=f"{kmz_filename}.kmz",
            mime="application/vnd.google-earth.kmz",
            type="secondary",
            use_container_width=True,
        )

else:
    st.warning(
        "⚠️ Data tidak ditemukan untuk kata kunci tersebut. "
        "Cobalah untuk periksa kembali nama jalan, blok, atau nomor rumah yang Anda masukkan."
    )