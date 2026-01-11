# ===============================================================
# utils_geotraitement.py – Version consolidée et épurée
# ===============================================================
from lxml import etree
import os
import pandas as pd
import zipfile
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union
import matplotlib.pyplot as plt
import gpxpy
import xml.etree.ElementTree as ET
from lxml import etree
from numba import njit
import streamlit as st
from utils.lang_helper import get_text

# ---------------------------------------------------------------
# 🧠 1. Filtrage GPX
# ---------------------------------------------------------------
@njit
def filter_points_numba(elevations, x_retenu):
    result = []
    n = len(elevations)
    for i in range(1, n-1):
        if elevations[i] >= (elevations[i-1] + x_retenu) and elevations[i] >= (elevations[i+1] + x_retenu):
            result.append(i)
    return result

def filter_gpx(df):
    x_values = [1, 0.75, 0.5, 0.25]
    elevations = df['elevation'].values
    x_retenu = None
    for x in x_values:
        indices = filter_points_numba(elevations, x)
        result = df.iloc[indices]
        if len(result) >= len(df) / 500:
            x_retenu = x
            break
    return result, x_retenu

# ---------------------------------------------------------------
# 🧠 2. Lecture GPX
# ---------------------------------------------------------------
def read_gpx_files(folder_path):
    all_data = []
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".gpx"):
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                    gpx_content = file.read()
                gpx_end_tag_index = gpx_content.rfind("</gpx>")
                if gpx_end_tag_index != -1:
                    gpx_content = gpx_content[:gpx_end_tag_index + len("</gpx>")]
                root = ET.fromstring(gpx_content)
                namespace = {'default': 'http://www.topografix.com/GPX/1/1'}
                for wpt in root.findall(".//default:wpt", namespace):
                    lat = float(wpt.get("lat"))
                    lon = float(wpt.get("lon"))
                    ele_element = wpt.find("default:ele", namespace)
                    ele = float(ele_element.text) if ele_element is not None else 0.0
                    all_data.append({"latitude": lat, "longitude": lon, "elevation": ele})
            except Exception:
                continue
    return all_data

# ---------------------------------------------------------------
# 🧠 3. Traitement GPX et génération shapefiles
# ---------------------------------------------------------------
def process_and_plot_gpx(folder_path, output_folder, display_in_streamlit=False):
    gpx_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.gpx')]
    if not gpx_files:
        if display_in_streamlit:
            st.warning(f"Aucun fichier GPX trouvé dans {folder_path}")
        return None

    gpx_data = read_gpx_files(folder_path)
    if not gpx_data:
        if display_in_streamlit:
            st.warning(f"Aucun GPX valide trouvé dans {folder_path}")
        return None

    points_df = pd.DataFrame(gpx_data)
    filtered_result, x_retenu = filter_gpx(points_df)

    geo_df = gpd.GeoDataFrame(
        filtered_result,
        geometry=gpd.points_from_xy(filtered_result.longitude, filtered_result.latitude),
        crs="EPSG:4326"
    )

    # Polygone Dolines
    lower_quartile = np.percentile(points_df['elevation'], 25)
    filtered_points_lower_quartile = points_df[points_df['elevation'] < lower_quartile]
    points = filtered_points_lower_quartile[['longitude', 'latitude']].to_numpy()
    if len(points) < 3:
        gdf_dolines = gpd.GeoDataFrame(columns=['geometry'], crs="EPSG:4326")
    else:
        polygon = Polygon(points)
        gdf_dolines = gpd.GeoDataFrame(geometry=[polygon], crs="EPSG:4326")

    # Points alignés
    coords = np.array([[p.x, p.y] for p in geo_df.geometry])
    n = len(coords)
    ANGLE_TOL = np.radians(2)
    aligned_points = set()
    for i in range(n):
        xi, yi = coords[i]
        angles = [(np.arctan2(coords[j][1]-yi, coords[j][0]-xi), j) for j in range(n) if j!=i]
        angles.sort(key=lambda x: x[0])
        current_group = [angles[0][1]]
        current_angle = angles[0][0]
        for k in range(1, len(angles)):
            angle_k, idx_k = angles[k]
            if abs(angle_k - current_angle) <= ANGLE_TOL:
                current_group.append(idx_k)
            else:
                if len(current_group) >= 2:
                    aligned_points.update([i] + current_group)
                current_group = [idx_k]
                current_angle = angle_k
        if len(current_group) >= 2:
            aligned_points.update([i] + current_group)

    aligned_points = list(aligned_points)
    lignes_geometry = [LineString([tuple(coords[i]), tuple(coords[i+1]), tuple(coords[i+2])])
                       for i in range(len(aligned_points)-2)]
    lignes_gdf = gpd.GeoDataFrame(geometry=lignes_geometry, crs="EPSG:4326")
    lignes_gdf = lignes_gdf[~lignes_gdf.geometry.is_empty & lignes_gdf.geometry.notna()]

    # Points d'intersection
    intersection_points = []
    for i, l1 in enumerate(lignes_gdf.geometry):
        for j, l2 in enumerate(lignes_gdf.geometry):
            if i != j:
                inter = l1.intersection(l2)
                if not inter.is_empty:
                    if inter.geom_type == 'Point':
                        intersection_points.append(inter)
                    elif inter.geom_type == 'MultiPoint':
                        intersection_points.extend(inter.geoms)
    intersection_gdf = gpd.GeoDataFrame(geometry=intersection_points, crs=lignes_gdf.crs)

    # Visualisation
    fig, ax = plt.subplots(figsize=(10,8))
    if not gdf_dolines.empty: gdf_dolines.plot(ax=ax)
    if not lignes_gdf.empty: lignes_gdf.plot(ax=ax, color='red')
    if not intersection_gdf.empty: intersection_gdf.plot(ax=ax, color='blue', markersize=40)
    plt.title("Contour, lignes alignées et intersections")
    plt.xlabel("Longitude"); plt.ylabel("Latitude")
    plt.grid(True)
    output_fig_path = os.path.join(output_folder, "visualisation_gpx.png")
    plt.savefig(output_fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    if display_in_streamlit:
        st.image(output_fig_path, caption="Visualisation GPX", width=700)

    # Sauvegarde shapefiles
    for gdf, name in zip([gdf_dolines, lignes_gdf, intersection_gdf],
                         ['output_dolines', 'output_lines', 'output_intersection_points']):
        if not gdf.empty:
            if gdf.crs is None:
                gdf.set_crs(epsg=4326, inplace=True)
            gdf.to_file(os.path.join(output_folder, f"{name}.shp"))

    return {
        "doline": gdf_dolines,
        "lines": lignes_gdf,
        "intersections": intersection_gdf
    }

# ---------------------------------------------------------------
# 🔹 Charger contour GPX/KML/KMZ
# ---------------------------------------------------------------
def load_contour_from_file(file_path):
    ext = file_path.split('.')[-1].lower()
    if ext=='gpx':
        with open(file_path,'r',encoding='utf-8') as f:
            gpx = gpxpy.parse(f)
        points=[(pt.longitude,pt.latitude)
                for track in gpx.tracks
                for segment in track.segments
                for pt in segment.points]
        if len(points)<3:
            raise ValueError("Pas assez de points pour créer un polygone")
        return Polygon(points)
    elif ext in ['kml','kmz']:
        if ext=='kmz':
            with zipfile.ZipFile(file_path,'r') as z:
                kml_bytes=None
                for name in z.namelist():
                    if name.endswith('.kml'):
                        kml_bytes=z.read(name)
                        break
                if kml_bytes is None:
                    raise ValueError("Aucun KML trouvé dans le KMZ.")
        else:
            with open(file_path,'rb') as f:
                kml_bytes=f.read()
        root=etree.fromstring(kml_bytes)
        ns={'kml':'http://www.opengis.net/kml/2.2'}
        polygons=[]
        for placemark in root.xpath('.//kml:Placemark',namespaces=ns):
            for polygon_elem in placemark.xpath('.//kml:Polygon',namespaces=ns):
                coords_text=polygon_elem.xpath('.//kml:coordinates/text()',namespaces=ns)
                for c in coords_text:
                    coords=[(float(lon),float(lat)) for lon,lat,*_ in (p.split(',') for p in c.strip().split())]
                    if len(coords)>=3:
                        polygons.append(Polygon(coords))
            for ring_elem in placemark.xpath('.//kml:LinearRing',namespaces=ns):
                coords_text=ring_elem.xpath('.//kml:coordinates/text()',namespaces=ns)
                for c in coords_text:
                    coords=[(float(lon),float(lat)) for lon,lat,*_ in (p.split(',') for p in c.strip().split())]
                    if len(coords)>=3:
                        polygons.append(Polygon(coords))
        if not polygons:
            raise ValueError(f"Aucun polygone trouvé dans {file_path}")
        return unary_union(polygons) if len(polygons)>1 else polygons[0]
    else:
        raise ValueError("Format non supporté (GPX/KML/KMZ)")

# ---------------------------------------------------------------
# 🔹 Filtrer points d'intersection selon doline et parcelle
# ---------------------------------------------------------------
def filter_intersection_points(intersection_gdf, doline_gdf, parcelle_polygon):
    if doline_gdf.empty or intersection_gdf.empty:
        return gpd.GeoDataFrame(columns=["geometry"], crs=intersection_gdf.crs), \
               gpd.GeoDataFrame(columns=["geometry"], crs=intersection_gdf.crs)

    doline_contour = doline_gdf.unary_union.convex_hull

    pts_inside_both = []
    pts_inside_parcelle_only = []

    for _, row in intersection_gdf.iterrows():
        geom = row.geometry
        if geom.within(doline_contour) and geom.within(parcelle_polygon):
            pts_inside_both.append(geom)
        elif geom.within(parcelle_polygon):
            pts_inside_parcelle_only.append(geom)

    def create_geodf(points, crs):
        if not points:
            return gpd.GeoDataFrame(columns=["geometry"], crs=crs)
        df = pd.DataFrame(points, columns=["geometry"])
        gdf = gpd.GeoDataFrame(df, geometry="geometry", crs=crs)
        return gdf[gdf.geometry.notna() & gdf.geometry.is_valid]

    gdf_both = create_geodf(pts_inside_both, intersection_gdf.crs)
    gdf_parcelle = create_geodf(pts_inside_parcelle_only, intersection_gdf.crs)

    return gdf_both, gdf_parcelle
