# utils_setup.py
import os
import shutil
import io
import math
import zipfile
import numpy as np
import geopandas as gpd
import gpxpy
from shapely.geometry import Point
from itertools import combinations
from lxml import etree
from pathlib import Path
import streamlit as st
import time

# ===============================================================
# CONFIGURATION
# ===============================================================

# Chemin RELATIF pour Docker / Linux
BASE_PATH = Path("/app/data/Dossier_clients")

# Créer le dossier s'il n'existe pas
BASE_PATH.mkdir(parents=True, exist_ok=True)

# Debug
print(f"✅ BASE_PATH créé: {BASE_PATH}")
print(f"📂 Chemin absolu: {BASE_PATH.absolute()}")


# ===============================================================
# 1️⃣ CRÉATION DES DOSSIERS CLIENT
# ===============================================================


def setup_owner_folders(email, phone, surface):
    # Nettoyer les entrées
    email_clean = email.strip() if email else "sans_email"
    phone_clean = str(phone).strip().replace('+', '').replace(' ', '_').replace('-', '_') if phone else "sans_telephone"
    
    folder_name = f"{email_clean.replace('@','_at_').replace('.','_')}_{phone_clean}"
    owner_folder = BASE_PATH / folder_name

    input_folder = owner_folder / "INPUT"
    output_folder = owner_folder / "OUTPUT"
    a_convertir = output_folder / "A_convertir"
    convertir = output_folder / "Convertir"
    rendu = owner_folder / "RENDU"

    # Créer tous les dossiers
    for f in [owner_folder, input_folder, output_folder, a_convertir, convertir, rendu]:
        f.mkdir(parents=True, exist_ok=True)
        print(f"📁 Dossier créé: {f}")
        st.write(f"📁 Dossier créé: {f}")

    # surface.txt
    surface_file = input_folder / "surface.txt"
    with open(surface_file, "w", encoding="utf-8") as f:
        f.write(surface)
    print(f"✅ surface.txt créé: {surface_file}")
    st.write(f"✅ surface.txt créé: {input_folder}")

    return {
        "base": str(owner_folder),
        "input": str(input_folder),
        "output": str(output_folder),
        "a_convertir": str(a_convertir),
        "convertir": str(convertir),
        "rendu": str(rendu)
    }

# ===============================================================
# 2️⃣ EXTRACTION + POINTS ÉQUIDISTANTS
# ===============================================================
def extract_coordinates_and_generate_equidistant_points(file_path, folders, nombre_points=None):
    coords = []
    ext = file_path.rsplit(".", 1)[-1].lower()

    if ext == "gpx":
        with open(file_path, "r", encoding="utf-8") as f:
            gpx = gpxpy.parse(f)
            for trk in gpx.tracks:
                for seg in trk.segments:
                    for pt in seg.points:
                        coords.append((pt.longitude, pt.latitude))
    elif ext in ["kml", "kmz"]:
        if ext == "kmz":
            with zipfile.ZipFile(file_path, "r") as kmz:
                kml_name = next(n for n in kmz.namelist() if n.endswith(".kml"))
                tree = etree.parse(io.BytesIO(kmz.read(kml_name)))
        else:
            tree = etree.parse(file_path)
        for elem in tree.iter("{http://www.opengis.net/kml/2.2}coordinates"):
            for c in elem.text.strip().split():
                lon, lat, *_ = c.split(",")
                coords.append((float(lon), float(lat)))
    else:
        raise ValueError("Format non supporté")

    gdf = gpd.GeoDataFrame(
        geometry=[Point(xy) for xy in coords],
        crs="EPSG:4326"
    )

    centroid = gdf.geometry.unary_union.centroid
    zone = int((centroid.x + 180) / 6) + 1
    epsg = f"EPSG:{326 if centroid.y >= 0 else 327}{zone:02d}"
    gdf = gdf.to_crs(epsg)

    def longest_distance(g):
        return max(p1.distance(p2) for p1, p2 in combinations(g.geometry, 2))

    dmax = longest_distance(gdf)
    nombre_points = nombre_points or int(2 * math.pi * dmax)

    centre = gdf.geometry.unary_union.centroid
    cercle = centre.buffer(dmax)

    points_cercle = [
        cercle.boundary.interpolate(i / nombre_points, normalized=True)
        for i in range(nombre_points)
    ]

    eq_pts = []
    N = len(points_cercle)
    for i in range(N):
        p1 = points_cercle[i]
        p2 = points_cercle[(i + N // 2) % N]
        n = max(int(p1.distance(p2) / 10), 1)
        v = np.array([p1.x - p2.x, p1.y - p2.y]) / n
        for j in range(1, n + 1):
            eq_pts.append(Point(p2.x + j * v[0], p2.y + j * v[1]))

    gdf_eq = gpd.GeoDataFrame(geometry=eq_pts, crs=epsg)
    out = os.path.join(folders["output"], "equidistant_points.geojson")
    gdf_eq.to_file(out, driver="GeoJSON")

    print(f"✅ GeoJSON points équidistants créés : {out}")
    st.write(f"✅ GeoJSON points équidistants créés : {out}")

    return gdf_eq

# ===============================================================
# 3️⃣ DÉCOUPAGE EN CHUNKS
# ===============================================================
def process_geojson_files_auto(folders, max_points=400):
    src = folders["output"]
    dst = folders["a_convertir"]
    os.makedirs(dst, exist_ok=True)
    files = [f for f in os.listdir(src) if f.endswith(".geojson")]
    count = 1
    
    st.write(f"📂 Découpage de {len(files)} fichier(s) GeoJSON")
    
    for f in files:
        gdf = gpd.read_file(os.path.join(src, f))
        st.write(f"  📄 {f}: {len(gdf)} points")
        
        for i in range(0, len(gdf), max_points):
            chunk = gdf.iloc[i:i + max_points]
            out = os.path.join(dst, f"chunk_{count}.geojson")
            chunk.to_file(out, driver="GeoJSON")
            
            print(f"✅ Chunk {count} créé: {out}")
            st.write(f"    ✅ Chunk {count}: {os.path.basename(out)}")
            count += 1

# ===============================================================
# 4️⃣ GEOJSON → GPX - LES GPX RESTENT DANS A_convertir
# ===============================================================
def geojson_to_gpx_valid(geojson_path, output_path):
    gdf = gpd.read_file(geojson_path)
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")

    gpx = gpxpy.gpx.GPX()
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom:
            if geom.geom_type == "Point":
                gpx.waypoints.append(
                    gpxpy.gpx.GPXWaypoint(latitude=geom.y, longitude=geom.x)
                )
            elif geom.geom_type == "LineString":
                trk = gpxpy.gpx.GPXTrack()
                seg = gpxpy.gpx.GPXTrackSegment()
                for x, y in geom.coords:
                    seg.points.append(gpxpy.gpx.GPXTrackPoint(latitude=y, longitude=x))
                trk.segments.append(seg)
                gpx.tracks.append(trk)
            elif geom.geom_type == "Polygon":
                trk = gpxpy.gpx.GPXTrack()
                seg = gpxpy.gpx.GPXTrackSegment()
                for x, y in geom.exterior.coords:
                    seg.points.append(gpxpy.gpx.GPXTrackPoint(latitude=y, longitude=x))
                trk.segments.append(seg)
                gpx.tracks.append(trk)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(gpx.to_xml())
    print(f"✅ GPX créé: {output_path}")
    st.write(f"✅ GPX créé: {os.path.basename(output_path)}")

def convert_all_geojson_to_gpx(folders):
    geojson_folder = folders['a_convertir']
    geojson_files = [f for f in os.listdir(geojson_folder) if f.endswith(".geojson")]
    gpx_files = []
    
    st.write(f"🔄 Conversion de {len(geojson_files)} fichier(s) en GPX")
    
    for file in geojson_files:
        input_path = os.path.join(geojson_folder, file)
        # Les GPX sont créés directement dans A_convertir (même dossier que les GeoJSON)
        output_path = os.path.join(folders['a_convertir'], file.replace(".geojson", ".gpx"))
        
        st.write(f"  🔄 {file} → {os.path.basename(output_path)}")
        geojson_to_gpx_valid(input_path, output_path)
        
        gpx_files.append(output_path)
    
    return gpx_files

# ===============================================================
# STREAMLIT INTERFACE
# ===============================================================
def create_streamlit_app():
    st.set_page_config(page_title="🌍 Ground Water Finder", page_icon="🌍", layout="wide")
    st.title("🌍 GROUND WATER FINDER - SETUP")
    st.markdown("---")
    
    # Afficher le chemin
    st.info(f"📍 **Les fichiers seront sauvegardés dans :**")
    st.code(str(BASE_PATH.absolute()))

    uploaded_file = st.file_uploader("Téléchargez votre fichier de contour", type=['gpx', 'kml', 'kmz'])
    email = st.text_input("📧 Email")
    phone = st.text_input("📞 Téléphone")
    surface = st.text_input("📐 Surface")

    process_button = st.button("🚀 Lancer le traitement", type="primary", disabled=not uploaded_file)
    if not process_button:
        st.stop()

    progress = st.progress(0)
    status = st.empty()

    phone_clean = phone if phone else "Non_spécifié"
    surface_clean = surface if surface else "Non_spécifiée"

    # 1️⃣ Création dossiers
    progress.progress(10, text="Création des dossiers…")
    status.write("📁 Création des dossiers")
    folders = setup_owner_folders(email, phone_clean, surface_clean)

    # 2️⃣ Sauvegarde fichier uploadé
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    temp_file_path = temp_dir / uploaded_file.name
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    dest_contour = os.path.join(folders["input"], uploaded_file.name)
    shutil.copy2(temp_file_path, dest_contour)
    progress.progress(25, text="Fichier contour copié")
    status.write(f"📄 Fichier contour copié dans INPUT : {uploaded_file.name}")

    # 3️⃣ Extraction + points équidistants
    progress.progress(45, text="Génération des points…")
    status.write("📍 Génération des points équidistants")
    gdf = extract_coordinates_and_generate_equidistant_points(str(temp_file_path), folders)

    # 4️⃣ Découpage GeoJSON
    progress.progress(65, text="Découpage en chunks…")
    status.write("✂️ Découpage des fichiers GeoJSON")
    process_geojson_files_auto(folders)

    # 5️⃣ Conversion GeoJSON → GPX
    progress.progress(85, text="Conversion GPX…")
    status.write("🧭 Conversion en GPX")
    gpx_files = convert_all_geojson_to_gpx(folders)

    # 6️⃣ Nettoyage temporaire
    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)
    progress.progress(100, text="Terminé ✅")
    status.write("✅ Traitement terminé")

    # 7️⃣ Résultats
    st.success("✅ Traitement terminé avec succès !")
    
    # Métriques
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📍 Points générés", len(gdf))
    with col2:
        st.metric("📄 Fichiers GPX créés", len(gpx_files))
    with col3:
        # Compter tous les fichiers
        base_path = Path(folders['base'])
        total_files = sum(1 for _ in base_path.rglob("*") if _.is_file())
        st.metric("📊 Total fichiers", total_files)
    
    # Structure des fichiers
    st.subheader("📁 Structure des fichiers créés :")
    def show_tree(path, indent=0):
        path = Path(path)
        if path.exists():
            for item in sorted(path.iterdir()):
                if item.is_file():
                    size = item.stat().st_size
                    st.text(f"{'    ' * indent}📄 {item.name} ({size:,} octets)")
                elif item.is_dir():
                    st.text(f"{'    ' * indent}📁 {item.name}/")
                    show_tree(item, indent + 1)
    
    show_tree(folders['base'])
    
    # Informations sur A_convertir
    a_convertir_path = Path(folders['a_convertir'])
    if a_convertir_path.exists():
        gpx_count = sum(1 for f in a_convertir_path.iterdir() if f.suffix == '.gpx')
        geojson_count = sum(1 for f in a_convertir_path.iterdir() if f.suffix == '.geojson')
        st.info(f"📂 **A_convertir contient :** {gpx_count} fichier(s) GPX et {geojson_count} fichier(s) GeoJSON")
    
    # Bouton pour ouvrir l'explorateur
    if st.button("📂 Ouvrir le dossier dans l'explorateur"):
        try:
            os.startfile(folders["base"])
        except:
            st.info(f"Chemin: {folders['base']}")

# ===============================================================
# EXÉCUTION
# ===============================================================
if __name__ == "__main__":
    create_streamlit_app()
