# utils_setup.py
import os
import shutil
import io
import math
import zipfile
import numpy as np
import geopandas as gpd
import gpxpy
import gpxpy.gpx
from shapely.geometry import Point
from itertools import combinations
from lxml import etree
from pathlib import Path
import streamlit as st
import time
import sys
import tempfile
import glob

# ===============================================================
# CONFIGURATION - HYBRIDE LINUX/WINDOWS
# ===============================================================

def get_base_path():
    """Retourne le chemin base compatible Linux/Docker mais fonctionnel sur Windows"""
    
    if sys.platform == "win32":
        current_dir = Path.cwd()
        windows_path = current_dir / "data" / "Dossier_clients"
        if "utils" in str(current_dir):
            windows_path = current_dir.parent / "data" / "Dossier_clients"
        if not windows_path.exists():
            windows_path = Path.home() / "Documents" / "ground_water_finder" / "data" / "Dossier_clients"
        windows_path.mkdir(parents=True, exist_ok=True)
        print(f"🔧 Windows: Chemin réel = {windows_path}")
        return windows_path
    else:
        linux_path = Path("/app/data/Dossier_clients")
        linux_path.mkdir(parents=True, exist_ok=True)
        return linux_path

BASE_PATH = get_base_path()
LINUX_STYLE_PATH = Path("/app/data/Dossier_clients")

print("="*60)
print(f"🔧 SYSTÈME: {sys.platform}")
print(f"📁 CHEMIN RÉEL (adapté): {BASE_PATH}")
print(f"📁 CHEMIN LINUX (style): {LINUX_STYLE_PATH}")
print(f"📁 EXISTE: {BASE_PATH.exists()}")
print("="*60)

# ===============================================================
# TEMP DIR GLOBAL POUR TOUT LE SCRIPT
# ===============================================================
TEMP_DIR = Path(tempfile.mkdtemp(prefix="gwf_"))
print(f"🔧 TEMP_DIR utilisé: {TEMP_DIR}")

# ===============================================================
# 1️⃣ CRÉATION DES DOSSIERS CLIENT - CORRIGÉE (basée sur le modèle fonctionnel)
# ===============================================================

def setup_owner_folders(email, phone, surface, uploaded_file):
    """Crée la structure de dossiers avec gestion de chemins cross-platform"""
    
    # Utiliser l'email comme nom de propriétaire (comme dans le modèle fonctionnel)
    owner_name = email.strip().replace("@", "_at_").replace(".", "_") if email else "sans_email"
    owner_folder = os.path.join(BASE_PATH, owner_name)
    
    # Structure des dossiers (identique au modèle fonctionnel)
    input_folder = os.path.join(owner_folder, "INPUT")
    output_folder = os.path.join(owner_folder, "OUTPUT")
    a_convertir = os.path.join(output_folder, "A_convertir")
    convertir = os.path.join(output_folder, "Convertir")
    rendu = os.path.join(owner_folder, "RENDU")

    # Création des dossiers
    folders_to_create = [owner_folder, input_folder, output_folder, a_convertir, convertir, rendu]
    for folder in folders_to_create:
        os.makedirs(folder, exist_ok=True)
        print(f"✅ Dossier créé: {folder}")

    # Fichier surface.txt
    surface_file = os.path.join(input_folder, "surface.txt")
    with open(surface_file, "w", encoding="utf-8") as f:
        f.write(surface if surface else "Surface non spécifiée")
    print(f"✅ surface.txt créé: {surface_file}")

    # Sauvegarde du fichier uploadé
    temp_file_path = os.path.join(TEMP_DIR, uploaded_file.name)
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Copie dans INPUT
    dest_path = os.path.join(input_folder, uploaded_file.name)
    shutil.copy2(temp_file_path, dest_path)
    print(f"✅ Fichier copié dans INPUT : {dest_path}")

    return {
        "input": input_folder,
        "output": output_folder,
        "a_convertir": a_convertir,
        "convertir": convertir,
        "rendu": rendu
    }

# ===============================================================
# 2️⃣ Extraction des points et génération équidistante - CORRIGÉE
# ===============================================================
def extract_coordinates_and_generate_equidistant_points(file_path, folders, nombre_points=None):
    # Utiliser output_folder au lieu de a_convertir (comme dans le modèle fonctionnel)
    output_folder = folders['output']
    ext = file_path.rsplit('.', 1)[-1].lower()
    coords = []

    if ext == 'gpx':
        with open(file_path, 'r') as f:
            gpx = gpxpy.parse(f)
            for trk in gpx.tracks:
                for seg in trk.segments:
                    for pt in seg.points:
                        coords.append((pt.longitude, pt.latitude))
    elif ext in ['kml', 'kmz']:
        if ext == 'kmz':
            with zipfile.ZipFile(file_path, 'r') as kmz:
                kml_file = next(n for n in kmz.namelist() if n.lower().endswith('.kml'))
                with kmz.open(kml_file) as kml_data:
                    tree = etree.parse(io.BytesIO(kml_data.read()))
        else:
            tree = etree.parse(file_path)
        for elem in tree.iter('{http://www.opengis.net/kml/2.2}coordinates'):
            for c in elem.text.strip().split():
               parts = c.split(',')
               if len(parts) >= 2:
                  lon = parts[0]
                  lat = parts[1]
                  coords.append((float(lon), float(lat)))
               else:
                   print(f"⚠️ Coordonnée ignorée (format invalide): {c}")
    else:
        raise ValueError("Format non pris en charge")

    gdf = gpd.GeoDataFrame(geometry=[Point(lon, lat) for lon, lat in coords], crs="EPSG:4326")
    centroid = gdf.geometry.unary_union.centroid
    utm_zone = int((centroid.x + 180) / 6) + 1
    hemisphere = '326' if centroid.y >= 0 else '327'
    projected_crs = f"EPSG:{hemisphere}{utm_zone:02d}"
    gdf = gdf.to_crs(projected_crs)

    def longest_distance(gdf):
        return max(p1.distance(p2) for p1, p2 in combinations(gdf.geometry, 2)) if len(gdf) > 1 else 0

    dmax = longest_distance(gdf)
    if nombre_points is None:
        nombre_points = int(2 * dmax * math.pi)

    centroide = gdf.geometry.unary_union.centroid
    cercle = centroide.buffer(dmax)
    points_cercle = [cercle.boundary.interpolate(i / nombre_points, normalized=True) for i in range(nombre_points)]
    points_gdf = gpd.GeoDataFrame(geometry=points_cercle, crs=projected_crs)

    eq_pts = []
    N = len(points_gdf)
    for i in range(N):
        p1 = points_gdf.geometry.iloc[i]
        p2 = points_gdf.geometry.iloc[(i + N // 2) % N]
        n = max(int(p1.distance(p2) / 10), 1)
        # Correction de la direction du vecteur (comme dans le modèle fonctionnel)
        v = (np.array([p2.x - p1.x, p2.y - p1.y]) / n)
        for j in range(1, n + 1):
            eq_pts.append(Point(p1.x + j * v[0], p1.y + j * v[1]))

    gdf_eq = gpd.GeoDataFrame(geometry=eq_pts, crs=projected_crs)
    # Sauvegarde dans output_folder (comme dans le modèle fonctionnel)
    output_path = os.path.join(output_folder, "equidistant_points.geojson")
    gdf_eq.to_file(output_path, driver="GeoJSON")
    print(f"✅ GeoJSON créé : {output_path}")
    return gdf_eq, points_gdf

# ===============================================================
# 3️⃣ Division en chunks - CORRIGÉE
# ===============================================================
def process_geojson_files_auto(folders, max_points=400):
    # Chercher les fichiers dans output_folder (comme dans le modèle fonctionnel)
    output_folder = folders['a_convertir']
    os.makedirs(output_folder, exist_ok=True)
    
    # Chercher dans output, pas dans a_convertir (comme dans le modèle fonctionnel)
    files = glob.glob(os.path.join(folders['output'], "*.geojson"))
    if not files:
        print("⚠️ Aucun fichier GeoJSON trouvé dans output")
        return
    
    count = 1
    for f in files:
        gdf = gpd.read_file(f)
        for start in range(0, len(gdf), max_points):
            chunk = gdf.iloc[start:start + max_points]
            out = os.path.join(output_folder, f"chunk_{count}.geojson")
            chunk.to_file(out, driver="GeoJSON")
            print(f"✅ Chunk sauvegardé : {out}")
            count += 1

# ===============================================================
# 4️⃣ Conversion GeoJSON → GPX (inchangée, fonctionne bien)
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
        if geom is None:
            continue
        if geom.geom_type == "Point":
            gpx.waypoints.append(gpxpy.gpx.GPXWaypoint(latitude=geom.y, longitude=geom.x))
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
    print(f"✅ {os.path.basename(geojson_path)} → {os.path.basename(output_path)} (GPX valide)")

def convert_all_geojson_to_gpx(folders):
    geojson_folder = folders['a_convertir']
    geojson_files = [f for f in os.listdir(geojson_folder) if f.lower().endswith(".geojson")]
    gpx_files = []
    for file in geojson_files:
        input_path = os.path.join(geojson_folder, file)
        output_path = os.path.join(geojson_folder, file.replace(".geojson", ".gpx"))
        geojson_to_gpx_valid(input_path, output_path)
        gpx_files.append(output_path)
    print(f"\n🎉 Tous les GeoJSON convertis en GPX dans {geojson_folder} !")
    return gpx_files

# ===============================================================
# 5️⃣ STREAMLIT INTERFACE - CORRIGÉE
# ===============================================================

def create_streamlit_app():
    st.title("🌍 GROUND WATER FINDER - SETUP")
    st.markdown("---")
    st.info(f"🔧 **INFORMATIONS SYSTÈME:** {sys.platform}")
    st.write(f"Chemin base: {BASE_PATH} (Accessible: {'✅' if BASE_PATH.exists() else '❌'})")

    uploaded_file = st.file_uploader("Téléchargez votre fichier de contour", type=['gpx','kml','kmz'])
    email = st.text_input("📧 Email")
    phone = st.text_input("📞 Téléphone")
    surface = st.text_input("📐 Surface")

    if st.button("🚀 Lancer le traitement"):
        if not uploaded_file:
            st.error("❌ Veuillez télécharger un fichier")
            return
        if not email:
            st.error("❌ Veuillez entrer un email")
            return

        # 1. Création des dossiers et copie du fichier
        with st.spinner("🔄 Création des dossiers..."):
            folders = setup_owner_folders(email, phone or "Non_spécifié", surface or "Non_spécifiée", uploaded_file)
            st.success("✅ Dossiers créés et fichier copié dans INPUT")

        # 2. Extraction des points équidistants
        with st.spinner("🔄 Génération des points équidistants..."):
            input_file = os.path.join(folders["input"], uploaded_file.name)
            gdf_eq, points_gdf = extract_coordinates_and_generate_equidistant_points(input_file, folders)
            st.success("✅ Points équidistants générés dans OUTPUT")

        # 3. Division en chunks
        with st.spinner("🔄 Division en chunks..."):
            process_geojson_files_auto(folders)
            st.success("✅ Chunks créés dans A_convertir")

        # 4. Conversion en GPX
        with st.spinner("🔄 Conversion en GPX..."):
            gpx_files = convert_all_geojson_to_gpx(folders)
            st.success(f"✅ {len(gpx_files)} fichiers GPX créés dans A_convertir")

        # 5. Affichage des résultats
        st.balloons()
        st.success("🎉 Traitement terminé avec succès !")
        
        # Afficher les fichiers générés
        a_convertir_folder = folders["a_convertir"]
        geojson_files = glob.glob(os.path.join(a_convertir_folder, "*.geojson"))
        gpx_files = glob.glob(os.path.join(a_convertir_folder, "*.gpx"))
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("📁 **Fichiers GeoJSON dans A_convertir :**")
            for f in geojson_files:
                st.write(f"  📄 {os.path.basename(f)}")
        with col2:
            st.write("📁 **Fichiers GPX dans A_convertir :**")
            for f in gpx_files:
                st.write(f"  📄 {os.path.basename(f)}")

# ===============================================================
# POINT D'ENTRÉE
# ===============================================================
if __name__ == "__main__":
    create_streamlit_app()