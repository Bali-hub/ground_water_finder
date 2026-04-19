# ===============================================================
# utils_geotraitement.py – version complète avec filtrage strict
# ===============================================================

import warnings
warnings.filterwarnings("ignore")

# ===============================================================
# IMPORTS
# ===============================================================
from pathlib import Path
import os
import zipfile
import numpy as np
import pandas as pd
import geopandas as gpd
import gpxpy
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
from shapely import STRtree
from lxml import etree
from numba import njit
from sklearn.cluster import DBSCAN
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
import alphashape  # pip install alphashape

# ===============================================================
# BASE DU PROJET
# ===============================================================
BASE_DIR = Path(__file__).resolve().parents[1]

# ===============================================================
# VARIABLES CLIENT
# ===============================================================
CLIENT_NOM = None
DOSSIER_CLIENT = None
DOSSIER_RENDU = None

# ===============================================================
# LOGS
# ===============================================================
def log_info(msg): print(f"[INFO] {msg}")
def log_success(msg): print(f"[SUCCESS] {msg}")
def log_warning(msg): print(f"[WARNING] {msg}")
def log_error(msg): print(f"[ERROR] {msg}")

# ===============================================================
# INITIALISATION CLIENT
# ===============================================================
def initialiser_client(client_nom: str):
    global CLIENT_NOM, DOSSIER_CLIENT, DOSSIER_RENDU
    CLIENT_NOM = client_nom
    DOSSIER_CLIENT = BASE_DIR / "data" / "Dossier_clients" / CLIENT_NOM
    DOSSIER_RENDU = DOSSIER_CLIENT / "RENDU"

# ===============================================================
# DETECTION CLIENT UNIQUE
# ===============================================================
def detecter_client_unique():
    dossier_clients = BASE_DIR / "data" / "Dossier_clients"
    if not dossier_clients.exists():
        raise FileNotFoundError("Le dossier data/Dossier_clients est introuvable")
    sous_dossiers = [d for d in dossier_clients.iterdir() if d.is_dir() and not d.name.startswith(".")]
    if len(sous_dossiers) == 0:
        raise ValueError("Aucun dossier client trouvé")
    if len(sous_dossiers) > 1:
        noms = [d.name for d in sous_dossiers]
        raise ValueError(f"Plusieurs dossiers clients détectés {noms}, un seul autorisé")
    return sous_dossiers[0].name

# ===============================================================
# LECTURE DU CONTOUR (INPUT)
# ===============================================================
def load_contour_from_input():
    input_dir = DOSSIER_CLIENT / "INPUT"
    fichiers = [f for f in input_dir.iterdir() if f.suffix.lower() in [".gpx",".kml",".kmz"] and "surface" in f.name.lower()]
    if not fichiers:
        fichiers = [f for f in input_dir.iterdir() if f.suffix.lower() in [".gpx",".kml",".kmz"]]
    if not fichiers:
        raise FileNotFoundError("Aucun fichier de contour trouvé dans INPUT")
    file_path = fichiers[0]

    ext = file_path.suffix.lower()
    if ext == ".gpx":
        with open(file_path, "r", encoding="utf-8") as f:
            gpx = gpxpy.parse(f)
        points = [(pt.longitude, pt.latitude)
                  for track in gpx.tracks
                  for seg in track.segments
                  for pt in seg.points]
        if len(points) < 3:
            raise ValueError("Pas assez de points pour créer le polygone")
        return Polygon(points)
    elif ext in [".kml",".kmz"]:
        if ext == ".kmz":
            with zipfile.ZipFile(file_path,"r") as z:
                kml_bytes = None
                for name in z.namelist():
                    if name.endswith(".kml"):
                        kml_bytes = z.read(name)
                        break
                if kml_bytes is None:
                    raise ValueError("Aucun KML trouvé dans KMZ")
        else:
            with open(file_path,"rb") as f:
                kml_bytes = f.read()
        root = etree.fromstring(kml_bytes)
        ns = {"kml":"http://www.opengis.net/kml/2.2"}
        polygons = []
        for placemark in root.xpath(".//kml:Placemark",namespaces=ns):
            for poly_elem in placemark.xpath(".//kml:Polygon",namespaces=ns):
                coords_text = poly_elem.xpath(".//kml:coordinates/text()",namespaces=ns)
                for c in coords_text:
                    coords = [(float(lon),float(lat)) for lon,lat,*_ in (p.split(",") for p in c.strip().split())]
                    if len(coords)>=3:
                        polygons.append(Polygon(coords))
        if not polygons:
            raise ValueError("Aucun polygone trouvé dans le KML/KMZ")
        valid_polys = [p.buffer(0) if not p.is_valid else p for p in polygons]
        return unary_union(valid_polys) if len(valid_polys)>1 else valid_polys[0]
    else:
        raise ValueError("Format non supporté")

# ===============================================================
# LECTURE GPX POUR LIGNES ET POINTS
# ===============================================================
def lire_gpx_points(fichier):
    points=[]
    try:
        with open(fichier,"r",encoding="utf-8",errors="ignore") as f:
            gpx = gpxpy.parse(f)
        for wpt in gpx.waypoints:
            points.append({"lat":wpt.latitude,"lon":wpt.longitude,"ele":wpt.elevation or 0.0})
        for trk in gpx.tracks:
            for seg in trk.segments:
                for pt in seg.points:
                    points.append({"lat":pt.latitude,"lon":pt.longitude,"ele":pt.elevation or 0.0})
    except Exception as e:
        log_error(f"Erreur lecture {fichier.name}: {e}")
    return points

def trouver_fichiers_gpx_convertir():
    convert_dir = DOSSIER_CLIENT / "OUTPUT" / "Convertir"
    if not convert_dir.exists():
        log_warning("Dossier Convertir inexistant")
        return []
    return sorted(convert_dir.glob("*.gpx"))

# ===============================================================
# FILTRAGE DES POINTS
# ===============================================================
@njit
def filter_points_numba(elev,x):
    res=[]
    for i in range(1,len(elev)-1):
        if elev[i]>=elev[i-1]+x and elev[i]>=elev[i+1]+x:
            res.append(i)
    return res

def filter_gpx(df):
    if len(df)<3: return df,0
    seuils=[1,0.9,0.8,0.75,0.6,0.5,0.4,0.3,0.25]
    elev=df["ele"].values
    for s in seuils:
        idx=filter_points_numba(elev,s)
        if len(idx)>=len(df)/1000: return df.iloc[idx],s
    return df.iloc[filter_points_numba(elev,seuils[-1])],seuils[-1]

# ===============================================================
# EXTRACTION LIGNES ALIGNEES
# ===============================================================
def extraire_lignes_alignees(coords, angle_tol_deg=2, extension_length=None):
    if len(coords) < 2:
        return [], []
    angle_tol = np.radians(angle_tol_deg)
    lignes = []
    segment_actuel = [coords[0], coords[1]]
    def angle(p1, p2):
        return np.arctan2(p2[1] - p1[1], p2[0] - p1[0])
    for i in range(2, len(coords)):
        p1 = segment_actuel[-2]
        p2 = segment_actuel[-1]
        p3 = coords[i]
        a1 = angle(p1, p2)
        a2 = angle(p2, p3)
        if abs(a1 - a2) <= angle_tol:
            segment_actuel.append(p3)
        else:
            if len(segment_actuel) >= 2:
                lignes.append(LineString(segment_actuel))
            segment_actuel = [p2, p3]
    if len(segment_actuel) >= 2:
        lignes.append(LineString(segment_actuel))
    return lignes, []   # retourne deux éléments

# ===============================================================
# CALCUL DES INTERSECTIONS
# ===============================================================
def calculer_intersections_avance(lignes, tolerance=1e-8, angle_min=30,
                                  distance_min=1e-4, ignore_extremites=True,
                                  dist_extremite=1e-4, use_dbscan=False):
    lignes = [l for l in lignes if isinstance(l, LineString) and not l.is_empty]
    if len(lignes) < 2: return []
    tree = STRtree(lignes)
    intersections = []
    deja_vu = set()
    for i, ligne in enumerate(lignes):
        candidats = tree.query(ligne)
        for idx in candidats:
            if i == idx: continue
            paire = (min(i, idx), max(i, idx))
            if paire in deja_vu: continue
            deja_vu.add(paire)
            autre = lignes[idx]
            if angle_min > 0:
                coords_l = list(ligne.coords)
                coords_a = list(autre.coords)
                if len(coords_l) >= 2 and len(coords_a) >= 2:
                    v1 = np.array(coords_l[-1]) - np.array(coords_l[0])
                    v2 = np.array(coords_a[-1]) - np.array(coords_a[0])
                    norm1 = np.linalg.norm(v1)
                    norm2 = np.linalg.norm(v2)
                    if norm1 > 0 and norm2 > 0:
                        cos_angle = np.dot(v1, v2) / (norm1 * norm2)
                        angle = np.degrees(np.arccos(np.clip(cos_angle, -1, 1)))
                        if angle < angle_min: continue
            inter = ligne.intersection(autre)
            if inter.is_empty:
                inter = ligne.buffer(tolerance, cap_style=2).intersection(autre)
            if inter.is_empty: continue
            points_inter = []
            if inter.geom_type == 'Point':
                points_inter = [inter]
            elif inter.geom_type == 'MultiPoint':
                points_inter = list(inter.geoms)
            else:
                continue
            for pt in points_inter:
                if ignore_extremites:
                    dist_debut = pt.distance(Point(ligne.coords[0]))
                    dist_fin = pt.distance(Point(ligne.coords[-1]))
                    dist_debut2 = pt.distance(Point(autre.coords[0]))
                    dist_fin2 = pt.distance(Point(autre.coords[-1]))
                    if min(dist_debut, dist_fin, dist_debut2, dist_fin2) < dist_extremite: continue
                intersections.append(pt)
    if len(intersections) > 1:
        if use_dbscan and len(intersections) > 2:
            coords = np.array([(p.x, p.y) for p in intersections])
            clustering = DBSCAN(eps=distance_min, min_samples=1).fit(coords)
            labels = clustering.labels_
            intersections = [Point(np.mean([p.x for p, l in zip(intersections, labels) if l == label]),
                                   np.mean([p.y for p, l in zip(intersections, labels) if l == label]))
                             for label in set(labels)]
        else:
            intersections = fusionner_points_proches(intersections, distance_min)
    return intersections

def fusionner_points_proches(points, distance_min):
    if not points: return []
    buffers = [p.buffer(distance_min) for p in points]
    union = unary_union(buffers)
    if union.geom_type == 'Polygon':
        return [union.centroid]
    elif union.geom_type == 'MultiPolygon':
        return [poly.centroid for poly in union.geoms]
    else:
        return points

# ===============================================================
# CALCUL DES DOLINES
# ===============================================================
def detecter_dolines_contour(df, elev_col='ele', lon_col='lon', lat_col='lat',
                             resolution=200, niveau=None, percentile=25, min_area=1e-8,
                             check_depression=True, simplify_tolerance=None):
    if df.empty or len(df) < 10: return []
    lons = df[lon_col].values
    lats = df[lat_col].values
    elev = df[elev_col].values
    mask = ~(np.isnan(lons) | np.isnan(lats) | np.isnan(elev))
    lons, lats, elev = lons[mask], lats[mask], elev[mask]
    if len(lons) < 10: return []
    xi = np.linspace(lons.min(), lons.max(), resolution)
    yi = np.linspace(lats.min(), lats.max(), resolution)
    xi, yi = np.meshgrid(xi, yi)
    zi = griddata((lons, lats), elev, (xi, yi), method='cubic')
    if niveau is None: niveau = np.percentile(elev, percentile)
    fig, ax = plt.subplots()
    contours = ax.contour(xi, yi, zi, levels=[niveau])
    plt.close(fig)
    polygons = []
    for collection in contours.collections:
        for path in collection.get_paths():
            for poly in path.to_polygons():
                if len(poly) >= 3:
                    if not np.allclose(poly[0], poly[-1]):
                        poly = np.vstack([poly, poly[0]])
                    polygon = Polygon(poly)
                    if not polygon.is_valid:
                        polygon = polygon.buffer(0)
                        if polygon.is_empty or not polygon.is_valid:
                            continue
                    if polygon.area < min_area: continue
                    if check_depression:
                        interior = polygon.representative_point()
                        alt_int = griddata((lons, lats), elev, (interior.x, interior.y), method='linear')
                        if alt_int is not None and alt_int < niveau:
                            polygons.append(polygon)
                    else:
                        polygons.append(polygon)
    if simplify_tolerance:
        polygons = [p.simplify(simplify_tolerance, preserve_topology=True) for p in polygons]
    return [p for p in polygons if p.is_valid and not p.is_empty]

# ===============================================================
# TRAITEMENT COMPLET
# ===============================================================
def traiter_complet():
    contour = load_contour_from_input()
    fichiers_gpx = trouver_fichiers_gpx_convertir()
    if not fichiers_gpx: log_warning("Aucun GPX pour lignes/points")
    df_pts = []
    for f in fichiers_gpx:
        df_pts.extend(lire_gpx_points(f))
    df = pd.DataFrame(df_pts)
    lignes, inters, dolines = [], [], None
    if not df.empty:
        filtres, seuil = filter_gpx(df)
        coords = filtres[["lon","lat"]].values
        lignes, _ = extraire_lignes_alignees(coords, extension_length=10)
        inters = calculer_intersections_avance(lignes, angle_min=35, distance_min=1e-4)
        dolines = detecter_dolines_contour(df, resolution=200, percentile=25)
    return {"contour": contour, "lignes": lignes, "intersections": inters, "dolines": dolines}

# ===============================================================
# FILTRAGE STRICT AVANT EXPORT
# ===============================================================

def filtrer_lignes_intersections(contour, lignes, intersections, dolines, distance_min=30, tol=1e-6):
    if not intersections:
        return [], []

    tree_pts = STRtree(intersections)
    intersections_filtrees = []
    lignes_a_conserver = set()

    # Construction du mapping lignes -> points avec tolérance
    if lignes:
        ligne_to_pts = {l: [] for l in lignes}
        for pt in intersections:
            for l in lignes:
                if pt.distance(l) < tol:
                    ligne_to_pts[l].append(pt)
    else:
        ligne_to_pts = {}

    for pt in intersections:
        # Voisins dans un rayon de distance_min
        voisins = [v for v in tree_pts.query(pt.buffer(distance_min)) if v != pt]
        pas_d_autres = len(voisins) == 0

        # Le point est-il dans une doline ?
        dans_doline = any(d.contains(pt) for d in dolines) if dolines else False
        intersection_hors_doline = not dans_doline

        if lignes:
            # Lignes génératrices (avec tolérance)
            lignes_gen = [l for l in lignes if pt.distance(l) < tol]

            # Vérifier si au moins une de ces lignes traverse une doline
            lignes_dans_doline = False
            for l in lignes_gen:
                for d in dolines:
                    if any(d.contains(Point(c)) for c in l.coords):
                        lignes_dans_doline = True
                        break
                if lignes_dans_doline:
                    break
            lignes_hors_doline = not lignes_dans_doline

            # Condition de suppression : point isolé, point hors doline, et toutes les lignes hors doline
            if pas_d_autres and intersection_hors_doline and lignes_hors_doline:
                continue

            # Sinon on conserve le point
            intersections_filtrees.append(pt)
            for l in lignes_gen:
                lignes_a_conserver.add(l)

        else:
            # Pas de lignes : on conserve le point (il sera filtré plus tard par le contour)
            intersections_filtrees.append(pt)

    # Ajouter toutes les lignes qui ont généré au moins une intersection (même si cette intersection a été supprimée)
    if lignes:
        for l, pts in ligne_to_pts.items():
            if pts:
                lignes_a_conserver.add(l)
        # Filtrer les lignes : ne conserver que celles qui intersectent le contour
        lignes_filtrees = [l for l in lignes_a_conserver if contour.intersects(l)]
    else:
        lignes_filtrees = []

    # Dernier filtre : ne garder que les intersections à l'intérieur du contour
    intersections_filtrees = [pt for pt in intersections_filtrees if contour.contains(pt)]

    return lignes_filtrees, intersections_filtrees

# ===============================================================
# EXPORT SHAPEFILES
# ===============================================================
def exporter_resultats(resultats):
    DOSSIER_RENDU.mkdir(parents=True, exist_ok=True)
    gpd.GeoDataFrame(geometry=[resultats["contour"]], crs="EPSG:4326").to_file(DOSSIER_RENDU/"CONTOUR.shp")
    if resultats["lignes"]:
        gpd.GeoDataFrame(geometry=resultats["lignes"], crs="EPSG:4326").to_file(DOSSIER_RENDU/"LIGNES.shp")
    if resultats["intersections"]:
        gpd.GeoDataFrame(geometry=resultats["intersections"], crs="EPSG:4326").to_file(DOSSIER_RENDU/"INTERSECTIONS.shp")
    if resultats["dolines"]:
        geometries = [p.buffer(0) if not p.is_valid else p for p in resultats["dolines"] if p and not p.is_empty]
        if geometries:
            gpd.GeoDataFrame(geometry=geometries, crs="EPSG:4326").to_file(DOSSIER_RENDU/"DOLINES.shp")

# ===============================================================
# STREAMLIT
# ===============================================================
if __name__ == "__main__":
    import streamlit as st
    st.set_page_config(page_title="Ground Water Finder", layout="wide")
    st.title("💧 Ground Water Finder – Traitement GPX/Contour")

    try:
        client_nom = detecter_client_unique()
        st.info(f"📁 Client détecté automatiquement : **{client_nom}**")
        initialiser_client(client_nom)

        with st.spinner("Traitement automatique en cours..."):
            # 1️⃣ traitement complet
            resultats = traiter_complet()

            # 2️⃣ filtrage strict avant export
            lignes_filtrees, inters_filtrees = filtrer_lignes_intersections(
                contour=resultats["contour"],
                lignes=resultats["lignes"],
                intersections=resultats["intersections"],
                dolines=resultats["dolines"],
                distance_min=30
            )
            resultats["lignes"] = lignes_filtrees
            resultats["intersections"] = inters_filtrees

            # 3️⃣ exporter après filtrage
            exporter_resultats(resultats)

        st.success("✅ Traitement terminé")
        st.json({
            "lignes": len(resultats["lignes"]),
            "intersections": len(resultats["intersections"]),
            "dolines": bool(resultats["dolines"])
        })

    except Exception as e:
        st.error(str(e))