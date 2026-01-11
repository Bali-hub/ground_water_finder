# utils/utils_setup.py
from lxml import etree
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
from pathlib import Path  # <-- IMPORT AJOUTÉ
from utils.lang_helper import get_text


# ===============================================================
# CONFIGURATION - CHEMIN RELATIF POUR DÉPLOIEMENT WEB
# ===============================================================
# Ancien chemin ABSOLU (Windows) qui ne fonctionne pas sur le cloud :
# BASE_PATH = r"C:\Users\HP Elitebook\Documents\Ground_water_finder\data\Dossier_clients"

# Nouveau chemin RELATIF qui fonctionne partout (PC, Streamlit Cloud, etc.) :
# __file__ = chemin du fichier actuel (utils_setup.py)
# .parent.parent = remonte de 2 niveaux (utils → Ground_water_finder)
# / "data" / "Dossier_clients" = descend dans les sous-dossiers
BASE_PATH = Path(__file__).parent.parent / "data" / "Dossier_clients"

# ===============================================================
# 1️⃣ CRÉATION DES DOSSIERS CLIENT
# ===============================================================
def setup_owner_folders(email, phone, surface):
    folder_name = f"{email.replace('@','_at_').replace('.','_')}_{phone}"
    owner_folder = os.path.join(BASE_PATH, folder_name)

    input_folder = os.path.join(owner_folder, "INPUT")
    output_folder = os.path.join(owner_folder, "OUTPUT")
    a_convertir = os.path.join(output_folder, "A_convertir")
    convertir = os.path.join(output_folder, "Convertir")
    rendu = os.path.join(owner_folder, "RENDU")

    for f in [owner_folder, input_folder, output_folder, a_convertir, convertir, rendu]:
        os.makedirs(f, exist_ok=True)

    with open(os.path.join(input_folder, "surface.txt"), "w", encoding="utf-8") as f:
        f.write(surface)

    return {
        "base": owner_folder,
        "input": input_folder,
        "output": output_folder,
        "a_convertir": a_convertir,
        "convertir": convertir,
        "rendu": rendu
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

    for f in files:
        gdf = gpd.read_file(os.path.join(src, f))
        for i in range(0, len(gdf), max_points):
            chunk = gdf.iloc[i:i + max_points]
            out = os.path.join(dst, f"chunk_{count}.geojson")
            chunk.to_file(out, driver="GeoJSON")
            count += 1

# ===============================================================
# 4️⃣ GEOJSON → GPX (ORIGINAL)
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

