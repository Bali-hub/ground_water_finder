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
import sys

# ===============================================================
# CONFIGURATION - HYBRIDE LINUX/WINDOWS
# ===============================================================

def get_base_path():
    """Retourne le chemin base compatible Linux/Docker mais fonctionnel sur Windows"""
    
    # Sur Windows, on va créer un équivalent du chemin /app/data/Dossier_clients
    if sys.platform == "win32":
        # Plusieurs stratégies pour trouver le bon chemin sur Windows:
        
        # 1. Essayer le dossier courant + data/Dossier_clients
        current_dir = Path.cwd()
        windows_path = current_dir / "data" / "Dossier_clients"
        
        # 2. Si on est dans utils/, remonter d'un niveau
        if "utils" in str(current_dir):
            windows_path = current_dir.parent / "data" / "Dossier_clients"
        
        # 3. Fallback: créer dans Documents
        if not windows_path.exists():
            windows_path = Path.home() / "Documents" / "ground_water_finder" / "data" / "Dossier_clients"
        
        # Créer le chemin et retourner sous forme Linux/Docker simulée
        windows_path.mkdir(parents=True, exist_ok=True)
        print(f"🔧 Windows: Chemin réel = {windows_path}")
        
        # Pour la compatibilité, on garde /app/data/Dossier_clients comme référence
        # mais on utilise le chemin Windows pour les opérations
        return windows_path
    
    else:
        # Sur Linux/Docker, utiliser le chemin standard
        linux_path = Path("/app/data/Dossier_clients")
        linux_path.mkdir(parents=True, exist_ok=True)
        return linux_path

# BASE_PATH contient maintenant le chemin réel adapté au système
BASE_PATH = get_base_path()

# Pour le debug, garder une variable avec le chemin Linux pour référence
LINUX_STYLE_PATH = Path("/app/data/Dossier_clients")

print("=" * 60)
print(f"🔧 SYSTÈME: {sys.platform}")
print(f"📁 CHEMIN RÉEL (adapté): {BASE_PATH}")
print(f"📁 CHEMIN LINUX (style): {LINUX_STYLE_PATH}")
print(f"📁 EXISTE: {BASE_PATH.exists()}")
print("=" * 60)

# ===============================================================
# 1️⃣ CRÉATION DES DOSSIERS CLIENT - VERSION PORTABLE
# ===============================================================

def setup_owner_folders(email, phone, surface):
    """Crée la structure de dossiers avec gestion de chemins cross-platform"""
    
    # Nettoyer les entrées
    email_clean = email.strip() if email else "sans_email"
    phone_clean = str(phone).strip().replace('+', '').replace(' ', '_').replace('-', '_') if phone else "sans_telephone"
    
    # Nom du dossier client
    folder_name = f"{email_clean.replace('@','_at_').replace('.','_')}_{phone_clean}"
    
    # IMPORTANT: Toujours utiliser BASE_PATH (déjà adapté au système)
    owner_folder = BASE_PATH / folder_name

    # Structure des sous-dossiers (identique pour tous les systèmes)
    input_folder = owner_folder / "INPUT"
    output_folder = owner_folder / "OUTPUT"
    a_convertir = output_folder / "A_convertir"
    convertir = output_folder / "Convertir"
    rendu = owner_folder / "RENDU"

    # Debug avant création
    st.write("🔧 **Debug création dossiers:**")
    st.write(f"- Système: {sys.platform}")
    st.write(f"- Base path: {BASE_PATH}")
    st.write(f"- Dossier client: {owner_folder}")

    # Créer tous les dossiers
    folders_to_create = [owner_folder, input_folder, output_folder, a_convertir, convertir, rendu]
    
    for folder in folders_to_create:
        try:
            # Utiliser mkdir avec parents=True pour créer toute l'arborescence
            folder.mkdir(parents=True, exist_ok=True)
            print(f"✅ Dossier créé: {folder}")
            
            # Vérifier immédiatement que le dossier existe
            if folder.exists():
                st.write(f"✅ {folder.name}/ créé")
            else:
                st.error(f"❌ {folder.name}/ non créé!")
                raise Exception(f"Échec création: {folder}")
                
        except Exception as e:
            error_msg = f"❌ Erreur création dossier {folder}: {e}"
            print(error_msg)
            st.error(error_msg)
            # Afficher plus de détails sur Windows
            if sys.platform == "win32":
                st.write(f"Permissions du parent {folder.parent}: {os.access(folder.parent, os.W_OK)}")
            raise

    # Créer surface.txt dans INPUT
    surface_file = input_folder / "surface.txt"
    try:
        with open(surface_file, "w", encoding="utf-8") as f:
            f.write(surface if surface else "Surface non spécifiée")
        print(f"✅ surface.txt créé: {surface_file}")
        st.success(f"✅ surface.txt créé dans INPUT")
        
        # Vérifier que le fichier existe
        if not surface_file.exists():
            st.error(f"❌ surface.txt n'a pas été créé!")
            
    except Exception as e:
        error_msg = f"❌ Erreur création surface.txt: {e}"
        print(error_msg)
        st.error(error_msg)
        raise

    # Vérification finale avec listing
    print(f"\n✅ STRUCTURE CRÉÉE À L'EMPLACEMENT:")
    print(f"   {owner_folder}")
    
    st.write(f"\n📁 **Structure créée dans:**")
    st.code(str(owner_folder))
    
    # Lister le contenu pour vérification
    if owner_folder.exists():
        st.write("📂 **Contenu du dossier client:**")
        for item in owner_folder.iterdir():
            if item.is_dir():
                st.write(f"  📁 {item.name}/")
                for subitem in item.iterdir():
                    st.write(f"    📁 {subitem.name}/")

    return {
        "base": str(owner_folder),
        "input": str(input_folder),
        "output": str(output_folder),
        "a_convertir": str(a_convertir),
        "convertir": str(convertir),
        "rendu": str(rendu)
    }

# ===============================================================
# 2️⃣ EXTRACTION + POINTS ÉQUIDISTANTS (inchangé)
# ===============================================================
def extract_coordinates_and_generate_equidistant_points(file_path, folders, nombre_points=None):
    """Extrait les coordonnées et génère des points équidistants"""
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

    # IMPORTANT: Utiliser Path() pour les chemins
    output_path = Path(folders["output"]) / "equidistant_points.geojson"
    
    gdf_eq = gpd.GeoDataFrame(geometry=eq_pts, crs=epsg)
    gdf_eq.to_file(str(output_path), driver="GeoJSON")

    print(f"✅ GeoJSON points équidistants créés : {output_path}")
    st.write(f"✅ GeoJSON points équidistants créés dans OUTPUT")

    return gdf_eq

# ===============================================================
# 3️⃣ DÉCOUPAGE EN CHUNKS (inchangé)
# ===============================================================
def process_geojson_files_auto(folders, max_points=400):
    src = Path(folders["output"])
    dst = Path(folders["a_convertir"])
    dst.mkdir(parents=True, exist_ok=True)
    files = [f for f in src.iterdir() if f.suffix == ".geojson"]
    count = 1
    
    st.write(f"📂 Découpage de {len(files)} fichier(s) GeoJSON")
    
    for f in files:
        gdf = gpd.read_file(str(f))
        st.write(f"  📄 {f.name}: {len(gdf)} points")
        
        for i in range(0, len(gdf), max_points):
            chunk = gdf.iloc[i:i + max_points]
            out = dst / f"chunk_{count}.geojson"
            chunk.to_file(str(out), driver="GeoJSON")
            
            print(f"✅ Chunk {count} créé: {out}")
            st.write(f"    ✅ Chunk {count}: {out.name}")
            count += 1

# ===============================================================
# 4️⃣ GEOJSON → GPX (inchangé)
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
    geojson_folder = Path(folders['a_convertir'])
    geojson_files = [f for f in geojson_folder.iterdir() if f.suffix == ".geojson"]
    gpx_files = []
    
    st.write(f"🔄 Conversion de {len(geojson_files)} fichier(s) en GPX")
    
    for file in geojson_files:
        input_path = str(file)
        output_path = str(geojson_folder / f"{file.stem}.gpx")
        
        st.write(f"  🔄 {file.name} → {os.path.basename(output_path)}")
        geojson_to_gpx_valid(input_path, output_path)
        
        gpx_files.append(output_path)
    
    return gpx_files

# ===============================================================
# STREAMLIT INTERFACE - VERSION AMÉLIORÉE
# ===============================================================
def create_streamlit_app():
    #st.set_page_config(page_title="🌍 Ground Water Finder", page_icon="🌍", layout="wide")
    st.title("🌍 GROUND WATER FINDER - SETUP")
    st.markdown("---")
    
    # Informations système
    st.info("🔧 **INFORMATIONS SYSTÈME:**")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Système:** {sys.platform}")
        st.write(f"**Python:** {sys.version.split()[0]}")
    with col2:
        st.write(f"**Chemin base:** {BASE_PATH}")
        st.write(f"**Accessible:** {'✅ Oui' if BASE_PATH.exists() else '❌ Non'}")
    
    # Vérifier les permissions
    try:
        test_file = BASE_PATH / "test_permission.txt"
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        st.success("✅ Permissions d'écriture OK sur le dossier base")
    except Exception as e:
        st.error(f"❌ Problème de permissions: {e}")
        st.info("💡 Essayez de lancer Streamlit en tant qu'administrateur")
    
    uploaded_file = st.file_uploader("Téléchargez votre fichier de contour", type=['gpx', 'kml', 'kmz'])
    email = st.text_input("📧 Email")
    phone = st.text_input("📞 Téléphone")
    surface = st.text_input("📐 Surface")

    # Afficher l'arborescence actuelle
    with st.expander("📁 Voir l'arborescence actuelle"):
        def list_directory(path, indent=0):
            path = Path(path)
            if path.exists():
                for item in sorted(path.iterdir()):
                    if item.is_file():
                        st.text(f"{'    ' * indent}📄 {item.name}")
                    elif item.is_dir():
                        st.text(f"{'    ' * indent}📁 {item.name}/")
                        list_directory(item, indent + 1)
        
        list_directory(BASE_PATH if BASE_PATH.exists() else Path.cwd())

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
    try:
        folders = setup_owner_folders(email, phone_clean, surface_clean)
        st.success(f"✅ Dossiers créés avec succès!")
    except Exception as e:
        st.error(f"❌ Échec création dossiers: {e}")
        st.info("💡 Vérifiez que vous avez les permissions d'écriture")
        return

    # 2️⃣ Sauvegarde fichier uploadé
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    temp_file_path = temp_dir / uploaded_file.name
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    dest_contour = Path(folders["input"]) / uploaded_file.name
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
    st.success("🎉 Traitement terminé avec succès !")
    
    # Afficher le résultat final
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Résumé")
        st.metric("📍 Points générés", len(gdf))
        st.metric("📄 Fichiers GPX créés", len(gpx_files))
        st.metric("📁 Dossier client", Path(folders['base']).name)
    
    with col2:
        st.subheader("📁 Emplacement")
        st.code(folders['base'])
        
        # Bouton pour ouvrir l'explorateur (Windows)
        if sys.platform == "win32":
            if st.button("📂 Ouvrir dans l'explorateur Windows"):
                try:
                    os.startfile(folders["base"])
                except:
                    st.info(f"Copiez ce chemin dans l'explorateur: {folders['base']}")
    
    # Afficher la structure
    st.subheader("🌳 Structure créée:")
    with st.expander("Voir l'arborescence complète"):
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
    
    # Message final
    st.balloons()
    st.info("""
    🎯 **Prochaine étape:** 
    Les fichiers GPX sont prêts dans `A_convertir/`. 
    Vous pouvez maintenant utiliser ces fichiers pour la prospection sur le terrain.
    """)

# ===============================================================
# EXÉCUTION
# ===============================================================
if __name__ == "__main__":
    create_streamlit_app()