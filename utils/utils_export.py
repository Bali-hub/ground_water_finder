import os
import zipfile
import io
import shutil
from datetime import datetime

import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
import gpxpy
from lxml import etree
import matplotlib.patches as mpatches
import simplekml

# ================== STREAMLIT CONFIG ==================
st.set_page_config(page_title="Carte de prospection", layout="wide")
st.title("🗺️ Carte de prospection – Affichage complet")

# ================== FONCTIONS ==================
BASE_CLIENTS = "./data/Dossier_clients"

def choisir_dossier_client():
    # Cette fonction n'est plus utilisée, mais on la garde intacte
    if not os.path.exists(BASE_CLIENTS):
        st.error(f"❌ Le dossier {BASE_CLIENTS} n'existe pas.")
        st.stop()
    dossiers = [d for d in os.listdir(BASE_CLIENTS)
               if os.path.isdir(os.path.join(BASE_CLIENTS, d))]
    if not dossiers:
        st.error(f"❌ Aucun dossier client trouvé dans {BASE_CLIENTS}")
        st.stop()
    nom_client = st.selectbox("Sélectionner un client", sorted(dossiers, reverse=True))
    dossier_client = os.path.join(BASE_CLIENTS, nom_client)
    st.success(f"📁 Client sélectionné : {nom_client}")
    return dossier_client, nom_client

def load_contour(file_path):
    ext = file_path.split('.')[-1].lower()
    if ext == 'gpx':
        with open(file_path, 'r', encoding='utf-8') as f:
            gpx = gpxpy.parse(f)
        points = [(pt.longitude, pt.latitude)
                  for track in gpx.tracks
                  for segment in track.segments
                  for pt in segment.points]
        if len(points) < 3:
            raise ValueError("Pas assez de points pour créer un polygone")
        return Polygon(points)
    elif ext in ['kml', 'kmz']:
        if ext == 'kmz':
            with zipfile.ZipFile(file_path, 'r') as z:
                kml_bytes = None
                for name in z.namelist():
                    if name.endswith('.kml'):
                        kml_bytes = z.read(name)
                        break
                if kml_bytes is None:
                    raise ValueError("Aucun KML trouvé dans le KMZ.")
        else:
            with open(file_path, 'rb') as f:
                kml_bytes = f.read()
        root = etree.fromstring(kml_bytes)
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        polygons = []
        for placemark in root.xpath('.//kml:Placemark', namespaces=ns):
            for polygon_elem in placemark.xpath('.//kml:Polygon', namespaces=ns):
                coords_text = polygon_elem.xpath('.//kml:coordinates/text()', namespaces=ns)
                for c in coords_text:
                    coords = [(float(lon), float(lat)) for lon, lat, *_ in (p.split(',') for p in c.strip().split())]
                    if len(coords) >= 3:
                        polygons.append(Polygon(coords))
            for ring_elem in placemark.xpath('.//kml:LinearRing', namespaces=ns):
                coords_text = ring_elem.xpath('.//kml:coordinates/text()', namespaces=ns)
                for c in coords_text:
                    coords = [(float(lon), float(lat)) for lon, lat, *_ in (p.split(',') for p in c.strip().split())]
                    if len(coords) >= 3:
                        polygons.append(Polygon(coords))
        if not polygons:
            raise ValueError(f"Aucun polygone trouvé dans {file_path}")
        return unary_union(polygons) if len(polygons) > 1 else polygons[0]
    else:
        raise ValueError("Format non supporté : GPX, KML ou KMZ uniquement")

def charger_couche(path):
    ext = path.lower().split(".")[-1]
    coords = []
    if ext == "shp":
        return gpd.read_file(path)
    elif ext == "gpx":
        with open(path, "r", encoding="utf-8") as f:
            gpx = gpxpy.parse(f)
        for trk in gpx.tracks:
            for seg in trk.segments:
                for pt in seg.points:
                    coords.append((pt.longitude, pt.latitude))
    elif ext in ["kml", "kmz"]:
        if ext == "kmz":
            with zipfile.ZipFile(path, "r") as z:
                kml_name = next(n for n in z.namelist() if n.endswith(".kml"))
                tree = etree.parse(io.BytesIO(z.read(kml_name)))
        else:
            tree = etree.parse(path)
        for elem in tree.iter("{http://www.opengis.net/kml/2.2}coordinates"):
            for c in elem.text.strip().split():
                lon, lat, *_ = c.split(",")
                coords.append((float(lon), float(lat)))
    if not coords and ext != "shp":
        return None
    if ext == "shp":
        return gpd.read_file(path)
    return gpd.GeoDataFrame(geometry=[Point(xy) for xy in coords], crs="EPSG:4326")

def generer_journal(couches, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("JOURNAL DE PROSPECTION\n")
        f.write("="*60 + "\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for nom, gdf in couches.items():
            f.write(f"{nom.upper():<15}: {len(gdf) if gdf is not None else 0} entités\n")
        f.write("="*60 + "\n")
        f.write("Remarques:\n")
        f.write("• Surface prospectée = Contour\n")
        f.write("• Fractures = Lines\n")
        f.write("• Dolines = Points rouges\n")
        f.write("• Points de forage = Intersections\n")
    return True

def shp_to_kml_gpx_kmz(gdf, basename, target_dirs):
    if gdf is None or gdf.empty:
        return
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    kml = simplekml.Kml()
    for i, geom in enumerate(gdf.geometry):
        name = f"{basename}_{i+1}"
        if geom.geom_type == "Point":
            kml.newpoint(name=name, coords=[(geom.x, geom.y)])
        elif geom.geom_type == "MultiPoint":
            for j, pt in enumerate(geom.geoms):
                kml.newpoint(name=f"{name}_pt{j+1}", coords=[(pt.x, pt.y)])
        elif geom.geom_type == "LineString":
            kml.newlinestring(name=name, coords=list(geom.coords))
        elif geom.geom_type == "MultiLineString":
            for j, line in enumerate(geom.geoms):
                kml.newlinestring(name=f"{name}_ln{j+1}", coords=list(line.coords))
        elif geom.geom_type == "Polygon":
            kml.newpolygon(name=name, outerboundaryis=list(geom.exterior.coords))
        elif geom.geom_type == "MultiPolygon":
            for j, poly in enumerate(geom.geoms):
                kml.newpolygon(name=f"{name}_pg{j+1}", outerboundaryis=list(poly.exterior.coords))

    kml_path = os.path.join(target_dirs["kml"], f"{basename}.kml")
    kml.save(kml_path)

    kmz_path = os.path.join(target_dirs["kmz"], f"{basename}.kmz")
    with zipfile.ZipFile(kmz_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(kml_path, arcname=f"{basename}.kml")

    gpx = gpxpy.gpx.GPX()
    for geom in gdf.geometry:
        if geom.geom_type == "Point":
            gpx.waypoints.append(gpxpy.gpx.GPXWaypoint(latitude=geom.y, longitude=geom.x))
        elif geom.geom_type == "MultiPoint":
            for pt in geom.geoms:
                gpx.waypoints.append(gpxpy.gpx.GPXWaypoint(latitude=pt.y, longitude=pt.x))
        elif geom.geom_type in ["LineString", "MultiLineString"]:
            lines = geom.geoms if geom.geom_type == "MultiLineString" else [geom]
            for line in lines:
                trk = gpxpy.gpx.GPXTrack()
                gpx.tracks.append(trk)
                seg = gpxpy.gpx.GPXTrackSegment()
                trk.segments.append(seg)
                for x, y in line.coords:
                    seg.points.append(gpxpy.gpx.GPXTrackPoint(y, x))

    gpx_path = os.path.join(target_dirs["gpx"], f"{basename}.gpx")
    with open(gpx_path, "w", encoding="utf-8") as f:
        f.write(gpx.to_xml())

# ================== MAIN AUTOMATIQUE ==================

# Détection automatique du dernier client
if not os.path.exists(BASE_CLIENTS):
    st.error(f"❌ Le dossier {BASE_CLIENTS} n'existe pas.")
    st.stop()

dossiers = [d for d in os.listdir(BASE_CLIENTS) if os.path.isdir(os.path.join(BASE_CLIENTS, d))]
if not dossiers:
    st.error(f"❌ Aucun dossier client trouvé dans {BASE_CLIENTS}")
    st.stop()

nom_client = sorted(dossiers, reverse=True)[0]
dossier_client = os.path.join(BASE_CLIENTS, nom_client)
st.success(f"📁 Client détecté automatiquement : {nom_client}")

input_files = os.listdir(os.path.join(dossier_client, "INPUT"))
contour_input_path = [f for f in input_files if "contour" in f.lower() and f.lower().endswith(('.kmz','.kml','.gpx'))][0]
contour_poly = load_contour(os.path.join(dossier_client, "INPUT", contour_input_path))
contour_gdf = gpd.GeoDataFrame(geometry=[contour_poly], crs="EPSG:4326").to_crs(epsg=3857)

dossier_RENDU = os.path.join(dossier_client, "RENDU")
couches = {"contour": contour_gdf, "lines": None, "dolines": None, "intersections": None}

for f in os.listdir(dossier_RENDU):
    lf = f.lower()
    path = os.path.join(dossier_RENDU, f)
    if lf.endswith((".shp", ".gpx", ".kml", ".kmz")):
        gdf = charger_couche(path)
        if gdf is None or gdf.empty:
            continue
        if "lignes" in lf:
            couches["lines"] = gdf.to_crs(epsg=3857)
        elif "dolines" in lf:
            couches["dolines"] = gdf.to_crs(epsg=3857)
        elif "intersections" in lf:
            couches["intersections"] = gdf.to_crs(epsg=3857)

# ================== AFFICHAGE ==================
fig, ax = plt.subplots(figsize=(14,12))
handles=[]

handles.append(mpatches.Patch(facecolor='orange', edgecolor='orange', label="Fractures identifiées"))
if couches.get("lines") is not None:
    couches["lines"].plot(ax=ax, color="orange", linewidth=3.0, linestyle="--", alpha=0.8, zorder=6)

handles.append(mpatches.Patch(facecolor='red', edgecolor='white', label="Dolines"))
if couches.get("dolines") is not None:
    couches["dolines"].plot(ax=ax, color="red", markersize=60, alpha=0.5, marker="o", edgecolor="white", linewidth=1.0, zorder=4)

handles.append(mpatches.Patch(facecolor='lime', edgecolor='black', label="Points de forage"))
if couches.get("intersections") is not None:
    couches["intersections"].plot(ax=ax, color="lime", markersize=100, marker="*", edgecolor="black", linewidth=1.5, alpha=0.9, zorder=5)

handles.append(mpatches.Patch(facecolor='none', edgecolor='darkblue', linewidth=3, label="Surface prospectée"))
couches["contour"].plot(ax=ax, facecolor='none', edgecolor='darkblue', linewidth=3, alpha=0.9, zorder=5)

try:
    ctx.add_basemap(ax, source="http://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", crs='EPSG:3857', zorder=0)
except:
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, crs='EPSG:3857', zorder=0)

ax.set_axis_off()
ax.set_title(f"🗺️ Carte de prospection – Projet {nom_client}", fontsize=18, weight='bold')
ax.legend(handles=handles, loc="lower left", fontsize=10, frameon=True, framealpha=0.95)
plt.tight_layout()

rapport_dir = os.path.join(dossier_RENDU, f"Rapport_{nom_client}")
os.makedirs(rapport_dir, exist_ok=True)
fig_path = os.path.join(rapport_dir, "carte_prospection.png")
fig.savefig(fig_path, dpi=150)
st.pyplot(fig)
plt.close(fig)

# ================== RAPPORT ET EXPORT ==================
data_dir = os.path.join(rapport_dir,"Data")
convertir_dir = os.path.join(rapport_dir,"Convertir")
shp_dir = os.path.join(data_dir,"SHP")
gpx_dir = os.path.join(data_dir,"GPX")
kml_dir = os.path.join(data_dir,"KML")
kmz_dir = os.path.join(data_dir,"KMZ")
for d in [data_dir, convertir_dir, shp_dir, gpx_dir, kml_dir, kmz_dir]:
    os.makedirs(d, exist_ok=True)

generer_journal(couches, os.path.join(rapport_dir,"journal.txt"))

mail_message="""ℹ️ Information importante

L’obtention du rapport complet est disponible sur demande
en écrivant à :

📧 m2techsecretariat@gmail.com
"""
with open(os.path.join(rapport_dir,"info_mail.txt"),'w',encoding='utf-8') as f: f.write(mail_message)
st.markdown(f"---\n**{mail_message}**")

convertir_src = os.path.join(dossier_client,"OUTPUT","Convertir")
if os.path.exists(convertir_src):
    shutil.copytree(convertir_src, convertir_dir, dirs_exist_ok=True)
else:
    st.warning(f"⚠️ Dossier source Convertir introuvable : {convertir_src}")

extensions_map={".shp":shp_dir,".gpx":gpx_dir,".kml":kml_dir,".kmz":kmz_dir}
for f in os.listdir(dossier_RENDU):
    src_path=os.path.join(dossier_RENDU,f)
    ext=os.path.splitext(f.lower())[1]
    if os.path.isfile(src_path) and ext in extensions_map:
        shutil.copy2(src_path,extensions_map[ext])

target_dirs={'kml':kml_dir,'kmz':kmz_dir,'gpx':gpx_dir}
for nom,gdf in couches.items():
    if gdf is not None:
        shp_to_kml_gpx_kmz(gdf,f"{nom_client}_{nom}",target_dirs)

zip_path=os.path.join(dossier_RENDU,f"{nom_client}.zip")
shutil.make_archive(base_name=zip_path.replace(".zip",""),format="zip",root_dir=rapport_dir)
st.info(f"📦 Archive ZIP générée : {os.path.basename(zip_path)}")


# utils_export.py

# … tous les imports et fonctions restent EXACTEMENT les mêmes …

def main():
    # ================== CODE PRINCIPAL ==================
    # Tout ce qui était en dehors des fonctions (choisir_dossier_client, chargement, affichage, export, zip, etc.)
    # On laisse inchangé, juste indenté dans cette fonction.
    dossier_client, nom_client = choisir_dossier_client()
    # ... tout le reste jusqu'à la fin ...
    zip_path=os.path.join(dossier_RENDU,f"{nom_client}.zip")
    shutil.make_archive(base_name=zip_path.replace(".zip",""),format="zip",root_dir=rapport_dir)
    st.info(f"📦 Archive ZIP générée : {os.path.basename(zip_path)}")

# Permet de garder l’exécution automatique si utils_export.py est lancé seul
if __name__ == "__main__":
    main()
