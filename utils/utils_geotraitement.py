# ===============================================================
# utils_geotraitement.py
# TRAITEMENT GPX + LECTURE CONTOUR
# ===============================================================

import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import os
import zipfile
import geopandas as gpd
import gpxpy
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
import numpy as np
from numba import njit
from lxml import etree
import pandas as pd

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
# CALCULS LIGNES / INTERSECTIONS / DOLINES
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
    seuils=[1,0.75,0.5,0.25]
    elev=df["ele"].values
    for s in seuils:
        idx=filter_points_numba(elev,s)
        if len(idx)>=len(df)/500: return df.iloc[idx],s
    return df.iloc[filter_points_numba(elev,seuils[-1])],seuils[-1]

def extraire_lignes_alignees(coords):
    if len(coords)<3: return [],[]
    ANGLE_TOL=np.radians(2)
    aligns=set()
    for i,(xi,yi) in enumerate(coords):
        angles=[]
        for j,(xj,yj) in enumerate(coords):
            if i!=j: angles.append((np.arctan2(yj-yi,xj-xi),j))
        angles.sort()
        groupe=[angles[0][1]]
        ref=angles[0][0]
        for a,j in angles[1:]:
            if abs(a-ref)<=ANGLE_TOL:
                groupe.append(j)
            else:
                if len(groupe)>=2: aligns.update([i]+groupe)
                groupe=[j]
                ref=a
        if len(groupe)>=2: aligns.update([i]+groupe)
    idx=sorted(list(aligns))
    lignes=[]
    for i in range(len(idx)-2):
        lignes.append(LineString([coords[idx[i]],coords[idx[i+1]],coords[idx[i+2]]]))
    return lignes,idx

def calculer_intersections(lignes):
    inters=[]
    for i in range(len(lignes)):
        for j in range(i+1,len(lignes)):
            inter=lignes[i].intersection(lignes[j])
            if not inter.is_empty:
                if inter.geom_type=="Point": inters.append(inter)
                elif inter.geom_type=="MultiPoint": inters.extend(inter.geoms)
    return inters

def calculer_dolines(df):
    if len(df)<10: return None
    q=np.percentile(df["ele"],25)
    pts=df[df["ele"]<q]
    if len(pts)<3: return None
    coords=pts[["lon","lat"]].values
    return Polygon(coords).convex_hull

# ===============================================================
# TRAITEMENT COMPLET
# ===============================================================
def traiter_complet():
    contour=load_contour_from_input()
    fichiers_gpx=trouver_fichiers_gpx_convertir()
    if not fichiers_gpx: log_warning("Aucun GPX pour lignes/points")
    df_pts=[]
    for f in fichiers_gpx:
        df_pts.extend(lire_gpx_points(f))
    df=pd.DataFrame(df_pts)
    lignes, inters, dolines=[],[],None
    if not df.empty:
        filtres, seuil=filter_gpx(df)
        coords=filtres[["lon","lat"]].values
        lignes,_=extraire_lignes_alignees(coords)
        inters=calculer_intersections(lignes)
        dolines=calculer_dolines(df)
    return {"contour":contour,"lignes":lignes,"intersections":inters,"dolines":dolines}

# ===============================================================
# EXPORT SHAPEFILES
# ===============================================================
def exporter_resultats(resultats):
    DOSSIER_RENDU.mkdir(parents=True,exist_ok=True)
    gpd.GeoDataFrame(geometry=[resultats["contour"]],crs="EPSG:4326").to_file(DOSSIER_RENDU/"CONTOUR.shp")
    if resultats["lignes"]: gpd.GeoDataFrame(geometry=resultats["lignes"],crs="EPSG:4326").to_file(DOSSIER_RENDU/"LIGNES.shp")
    if resultats["intersections"]: gpd.GeoDataFrame(geometry=resultats["intersections"],crs="EPSG:4326").to_file(DOSSIER_RENDU/"INTERSECTIONS.shp")
    if resultats["dolines"]: gpd.GeoDataFrame(geometry=[resultats["dolines"]],crs="EPSG:4326").to_file(DOSSIER_RENDU/"DOLINES.shp")

# ===============================================================
# STREAMLIT – AUTOMATIQUE AU LANCEMENT
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
            resultats = traiter_complet()
            exporter_resultats(resultats)

        st.success("✅ Traitement terminé")
        st.json({
            "lignes": len(resultats["lignes"]),
            "intersections": len(resultats["intersections"]),
            "dolines": bool(resultats["dolines"])
        })

    except Exception as e:
        st.error(str(e))
