# utils_export.py - VERSION CORRIGÉE POUR utils_geotraitement
# ===============================================================

import os
import zipfile
import shutil
import tempfile
from pathlib import Path
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon, MultiPolygon
import gpxpy
import gpxpy.gpx
from datetime import datetime

# ===============================================================
# 1. FONCTIONS D'EXPORT
# ===============================================================

def export_shp(gdf, output_path):
    """Export SHP"""
    gdf.to_file(output_path, driver='ESRI Shapefile')

def export_kml(gdf, output_path, layer_name):
    """Export KML avec simplekml (driver fiable)"""
    try:
        import simplekml
        
        # S'assurer du CRS WGS84
        if gdf.crs is None:
            gdf = gdf.set_crs('EPSG:4326')
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs('EPSG:4326')
        
        # Créer KML
        kml = simplekml.Kml(name=layer_name)
        
        for idx, row in gdf.iterrows():
            geom = row.geometry
            if geom.is_empty:
                continue
                
            if geom.geom_type == 'Point':
                kml.newpoint(
                    name=f"{layer_name}_{idx}",
                    coords=[(geom.x, geom.y)]
                )
                
            elif geom.geom_type == 'LineString':
                kml.newlinestring(
                    name=f"{layer_name}_line_{idx}",
                    coords=list(geom.coords)
                )
                
            elif geom.geom_type == 'MultiLineString':
                for i, line in enumerate(geom.geoms):
                    kml.newlinestring(
                        name=f"{layer_name}_multiline_{idx}_{i}",
                        coords=list(line.coords)
                    )
                    
            elif geom.geom_type == 'Polygon':
                kml.newpolygon(
                    name=f"{layer_name}_poly_{idx}",
                    outerboundaryis=list(geom.exterior.coords)
                )
                
            elif geom.geom_type == 'MultiPolygon':
                for i, poly in enumerate(geom.geoms):
                    kml.newpolygon(
                        name=f"{layer_name}_multipoly_{idx}_{i}",
                        outerboundaryis=list(poly.exterior.coords)
                    )
        
        kml.save(output_path)
        return True
        
    except Exception as e:
        print(f"❌ Erreur KML {layer_name}: {e}")
        return False

def export_gpx(gdf, output_path, layer_name):
    """Export GPX - méthode éprouvée"""
    gpx = gpxpy.gpx.GPX()
    
    for geom in gdf.geometry:
        if geom.is_empty:
            continue
        
        # POINTS
        if geom.geom_type == 'Point':
            gpx.waypoints.append(gpxpy.gpx.GPXWaypoint(
                latitude=geom.y, 
                longitude=geom.x
            ))
        
        # LIGNES
        elif geom.geom_type in ['LineString', 'MultiLineString']:
            lines = [geom] if geom.geom_type == 'LineString' else list(geom.geoms)
            for line in lines:
                for lon, lat in line.coords:
                    gpx.waypoints.append(gpxpy.gpx.GPXTrackPoint(
                        latitude=lat, 
                        longitude=lon
                    ))
        
        # POLYGONES
        elif geom.geom_type in ['Polygon', 'MultiPolygon']:
            polygons = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
            for poly in polygons:
                for lon, lat in poly.exterior.coords:
                    gpx.waypoints.append(gpxpy.gpx.GPXWaypoint(
                        latitude=lat, 
                        longitude=lon
                    ))
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(gpx.to_xml())

def export_kmz(kml_path, kmz_path):
    """Export KMZ"""
    with zipfile.ZipFile(kmz_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(kml_path, arcname=Path(kml_path).name)

# ===============================================================
# 2. CRÉATION DE LA CARTE - VERSION CORRIGÉE
# ===============================================================

def create_carte_prospection(contour_gdf, lines_gdf, points_gdf, dolines_gdf, 
                           nom_prospecteur, output_path):
    """Crée carte_prospection.png avec fond satellite - VERSION CORRIGÉE"""
    try:
        import matplotlib.pyplot as plt
        import contextily as ctx
        
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # Couches à afficher - VÉRIFIER SI ELLES SONT NON VIDES
        layers_to_plot = []
        
        if contour_gdf is not None and not contour_gdf.empty:
            try:
                contour_gdf_3857 = contour_gdf.to_crs(epsg=3857)
                layers_to_plot.append(("Contour", contour_gdf_3857, 'red', 'surface prospectée'))
            except Exception as e:
                print(f"⚠️ Erreur conversion contour: {e}")
        
        if lines_gdf is not None and not lines_gdf.empty:
            try:
                lines_gdf_3857 = lines_gdf.to_crs(epsg=3857)
                layers_to_plot.append(("Lines", lines_gdf_3857, 'blue', 'fractures identifiées'))
            except Exception as e:
                print(f"⚠️ Erreur conversion lines: {e}")
        
        if points_gdf is not None and not points_gdf.empty:
            try:
                points_gdf_3857 = points_gdf.to_crs(epsg=3857)
                layers_to_plot.append(("Points_intersections", points_gdf_3857, 'green', 'points de forage'))
            except Exception as e:
                print(f"⚠️ Erreur conversion points: {e}")
        
        if dolines_gdf is not None and not dolines_gdf.empty:
            try:
                dolines_gdf_3857 = dolines_gdf.to_crs(epsg=3857)
                layers_to_plot.append(("Dolines", dolines_gdf_3857, 'orange', 'Dolines'))
            except Exception as e:
                print(f"⚠️ Erreur conversion dolines: {e}")
        
        print(f"📊 Couches à afficher: {len(layers_to_plot)}")
        for layer_name, gdf, color, label in layers_to_plot:
            print(f"   - {layer_name}: {len(gdf)} éléments")
        
        if not layers_to_plot:
            # Carte simple si pas de données
            ax.text(0.5, 0.5, f'Carte de prospection\n{nom_prospecteur}',
                   horizontalalignment='center', verticalalignment='center',
                   fontsize=16, weight='bold')
            ax.axis('off')
            plt.savefig(output_path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            print("ℹ️ Carte simple générée (pas de données)")
            return True
        
        # Tracer
        handles = []
        
        for layer_name, gdf, color, label in layers_to_plot:
            try:
                if layer_name == "Contour":
                    gdf.plot(ax=ax, alpha=0.35, edgecolor=color, linewidth=2, facecolor='none')
                    handles.append(plt.Line2D([0], [0], color=color, lw=2, label=f'Contour = {label}'))
                
                elif layer_name == "Lines":
                    gdf.plot(ax=ax, alpha=0.7, edgecolor=color, linewidth=1.5)
                    handles.append(plt.Line2D([0], [0], color=color, lw=1.5, label=f'Lines = {label}'))
                
                elif layer_name == "Points_intersections":
                    gdf.plot(ax=ax, color=color, markersize=50, marker='o', alpha=0.7)
                    handles.append(plt.Line2D([0], [0], color=color, marker='o', 
                                            lw=0, markersize=8, label=f'Points_intersections = {label}'))
                
                elif layer_name == "Dolines":
                    gdf.plot(ax=ax, color=color, markersize=40, marker='X', alpha=0.7)
                    handles.append(plt.Line2D([0], [0], color=color, marker='X', 
                                            lw=0, markersize=8, label=f'Dolines = {label}'))
                print(f"✅ Couche {layer_name} tracée")
            except Exception as e:
                print(f"❌ Erreur traçage {layer_name}: {e}")
        
        # Fond satellite
        try:
            # Essayer plusieurs sources
            try:
                google_satellite = "http://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
                ctx.add_basemap(ax, source=google_satellite, crs='EPSG:3857')
                print("✅ Fond Google Satellite")
            except:
                try:
                    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, crs='EPSG:3857')
                    print("✅ Fond OpenStreetMap")
                except:
                    ctx.add_basemap(ax, crs='EPSG:3857')
                    print("✅ Fond par défaut")
        except Exception as e:
            print(f"⚠️ Pas de fond carte: {e}")
        
        # Configuration
        ax.set_title(f"🗺️ Carte prospection - {nom_prospecteur}", 
                    fontsize=18, weight='bold')
        ax.axis('off')
        
        if handles:
            ax.legend(handles=handles, loc='lower left', fontsize=9, frameon=True)
            print(f"✅ Légende avec {len(handles)} éléments")
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"✅ Carte sauvegardée: {output_path}")
        return True
        
    except Exception as e:
        print(f"⚠️ Erreur création carte: {e}")
        import traceback
        traceback.print_exc()
        
        # Carte de secours
        try:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.text(0.5, 0.5, f'Carte de prospection\n{nom_prospecteur}',
                   horizontalalignment='center', verticalalignment='center',
                   fontsize=16, weight='bold')
            ax.axis('off')
            plt.savefig(output_path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            print("✅ Carte de secours générée")
            return True
        except:
            print("❌ Impossible de générer la carte de secours")
            return False

# ===============================================================
# 3. CLASSE PRINCIPALE - VERSION CORRIGÉE
# ===============================================================

class ExportProspection:
    def __init__(self, nom_prospecteur, telephone, 
                 contour_polygon=None,
                 lines_gdf=None,
                 points_gdf=None,
                 dolines_gdf=None):
        
        self.nom_prospecteur = nom_prospecteur
        self.telephone = telephone
        self.contour_polygon = contour_polygon
        self.lines_gdf = lines_gdf
        self.points_gdf = points_gdf
        self.dolines_gdf = dolines_gdf
        
        # Debug
        print(f"\n📦 Initialisation ExportProspection:")
        print(f"   - lines_gdf: {'OUI' if lines_gdf is not None else 'NON'} ({len(lines_gdf) if lines_gdf is not None else 0} éléments)")
        print(f"   - points_gdf: {'OUI' if points_gdf is not None else 'NON'} ({len(points_gdf) if points_gdf is not None else 0} éléments)")
        print(f"   - dolines_gdf: {'OUI' if dolines_gdf is not None else 'NON'} ({len(dolines_gdf) if dolines_gdf is not None else 0} éléments)")
        print(f"   - contour_polygon: {'OUI' if contour_polygon is not None else 'NON'}")
    
    def executer_export_complet(self, output_dir=None):
        """
        Exécute l'export complet avec structure EXACTE - VERSION CORRIGÉE
        """
        print(f"\n🚀 ExportProspection: {self.nom_prospecteur}")
        
        # 1. Préparation
        output_dir = output_dir or tempfile.gettempdir()
        
        safe_nom = "".join(c for c in self.nom_prospecteur if c.isalnum() or c in (' ', '-', '_'))
        safe_nom = safe_nom.replace(' ', '_')
        safe_tel = "".join(c for c in self.telephone if c.isdigit())
        
        project_folder = Path(output_dir) / f"{safe_nom}_{safe_tel}"
        if project_folder.exists():
            shutil.rmtree(project_folder)
        project_folder.mkdir(parents=True, exist_ok=True)
        
        # 2. Structure Data/
        data_dir = project_folder / "Data"
        shp_dir = data_dir / "SHP"
        gpx_dir = data_dir / "GPX"
        kml_dir = data_dir / "KML"
        kmz_dir = data_dir / "KMZ"
        
        for d in [shp_dir, gpx_dir, kml_dir, kmz_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # 3. Préparation couches - NOMS CORRIGÉS POUR CORRESPONDRE À LA LÉGENDE
        layers = {}
        
        # Contour - doit être "Contour" pour la légende
        if self.contour_polygon is not None:
            if isinstance(self.contour_polygon, (Polygon, MultiPolygon)):
                layers["Contour"] = gpd.GeoDataFrame(
                    geometry=[self.contour_polygon], 
                    crs='EPSG:4326'
                )
                print(f"✅ Contour ajouté: 1 polygone")
        
        # Lines - doit être "lines" (minuscule) pour l'export SHP mais "Lines" pour la carte
        if self.lines_gdf is not None and not self.lines_gdf.empty:
            layers["lines"] = self.lines_gdf
            print(f"✅ Lines ajouté: {len(self.lines_gdf)} éléments")
        else:
            print(f"⚠️ Lines: données vides ou None")
        
        # Points - doit être "points_intersections" (avec underscore)
        if self.points_gdf is not None and not self.points_gdf.empty:
            layers["points_intersections"] = self.points_gdf
            print(f"✅ Points_intersections ajouté: {len(self.points_gdf)} éléments")
        else:
            print(f"⚠️ Points_intersections: données vides ou None")
        
        # Dolines - doit être "Dolines" (avec D majuscule) pour la légende
        if self.dolines_gdf is not None and not self.dolines_gdf.empty:
            layers["Dolines"] = self.dolines_gdf
            print(f"✅ Dolines ajouté: {len(self.dolines_gdf)} éléments")
        else:
            print(f"⚠️ Dolines: données vides ou None")
        
        print(f"📊 Total couches: {len(layers)}")
        
        # 4. Export
        for layer_name, gdf in layers.items():
            print(f"\n  📤 Export {layer_name}: {len(gdf)} éléments")
            
            # S'assurer CRS
            if gdf.crs is None:
                gdf = gdf.set_crs('EPSG:4326')
                print(f"    ℹ️ CRS défini: EPSG:4326")
            elif gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs('EPSG:4326')
                print(f"    ℹ️ CRS converti: EPSG:4326")
            
            # SHP
            shp_path = shp_dir / f"{layer_name}.shp"
            try:
                export_shp(gdf, shp_path)
                print(f"    ✅ SHP: {shp_path.name}")
            except Exception as e:
                print(f"    ❌ SHP: {e}")
            
            # KML
            kml_path = kml_dir / f"{layer_name}.kml"
            try:
                if export_kml(gdf, kml_path, layer_name):
                    print(f"    ✅ KML: {kml_path.name}")
                else:
                    print(f"    ❌ KML échoué")
            except Exception as e:
                print(f"    ❌ KML: {e}")
            
            # KMZ
            kmz_path = kmz_dir / f"{layer_name}.kmz"
            if os.path.exists(kml_path):
                try:
                    export_kmz(kml_path, kmz_path)
                    print(f"    ✅ KMZ: {kmz_path.name}")
                except Exception as e:
                    print(f"    ❌ KMZ: {e}")
            
            # GPX
            gpx_path = gpx_dir / f"{layer_name}.gpx"
            try:
                export_gpx(gdf, gpx_path, layer_name)
                print(f"    ✅ GPX: {gpx_path.name}")
            except Exception as e:
                print(f"    ❌ GPX: {e}")
        
        # 5. Convertir/
        convertir_dir = project_folder / "Convertir"
        convertir_dir.mkdir(exist_ok=True)
        print(f"📁 Dossier Convertir créé")
        
        # 6. Carte
        carte_path = project_folder / "carte_prospection.png"
        print(f"\n🎨 Génération de la carte...")
        
        # Préparer les données pour la carte
        contour_for_carte = layers.get("Contour")
        lines_for_carte = layers.get("lines")
        points_for_carte = layers.get("points_intersections")
        dolines_for_carte = layers.get("Dolines")
        
        print(f"   Données pour carte:")
        print(f"   - Contour: {'OUI' if contour_for_carte is not None else 'NON'}")
        print(f"   - Lines: {'OUI' if lines_for_carte is not None else 'NON'} ({len(lines_for_carte) if lines_for_carte is not None else 0} éléments)")
        print(f"   - Points: {'OUI' if points_for_carte is not None else 'NON'} ({len(points_for_carte) if points_for_carte is not None else 0} éléments)")
        print(f"   - Dolines: {'OUI' if dolines_for_carte is not None else 'NON'} ({len(dolines_for_carte) if dolines_for_carte is not None else 0} éléments)")
        
        create_carte_prospection(
            contour_gdf=contour_for_carte,
            lines_gdf=lines_for_carte,
            points_gdf=points_for_carte,
            dolines_gdf=dolines_for_carte,
            nom_prospecteur=self.nom_prospecteur,
            output_path=carte_path
        )
        
        # 7. Journal.txt - VERSION CORRIGÉE
        journal_path = project_folder / "journal.txt"
        try:
            with open(journal_path, 'w', encoding='utf-8') as f:
                f.write(f"Nom prospecteur: {self.nom_prospecteur}\n")
                f.write(f"Téléphone: {self.telephone}\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                
                f.write("STATISTIQUES DES DONNÉES\n")
                f.write("-" * 30 + "\n\n")
                
                # Points de forage
                points_count = len(self.points_gdf) if self.points_gdf is not None else 0
                f.write(f"• Nombre de points de forage: {points_count}\n")
                print(f"📊 Points de forage dans journal: {points_count}")
                
                # Lignes de fractures
                lines_count = len(self.lines_gdf) if self.lines_gdf is not None else 0
                f.write(f"• Nombre de lignes de fractures: {lines_count}\n")
                print(f"📊 Lignes de fractures dans journal: {lines_count}")
                
                # Dolines
                dolines_count = len(self.dolines_gdf) if self.dolines_gdf is not None else 0
                f.write(f"• Nombre de dolines: {dolines_count}\n")
                print(f"📊 Dolines dans journal: {dolines_count}")
                
                # Surface prospectée
                if self.contour_polygon is not None:
                    area_deg2 = self.contour_polygon.area
                    area_ha = area_deg2 * 110.574 * 111.320 * 0.01
                    f.write(f"• Surface prospectée: {area_ha:.2f} hectares\n")
                else:
                    f.write("• Surface prospectée: Non définie\n")
                
                f.write("\n" + "=" * 50 + "\n")
                f.write("LÉGENDE DE LA CARTE\n")
                f.write("-" * 30 + "\n\n")
                f.write("• Dolines = Dolines\n")
                f.write("• Points_intersections = Points de forage\n")
                f.write("• Lines = Fractures identifiées\n")
                f.write("• Contour = Surface prospectée\n")
            
            print(f"\n📝 Journal créé: {journal_path}")
            
        except Exception as e:
            print(f"❌ Journal: {e}")
        
        # 8. Archive ZIP
        zip_path = Path(output_dir) / f"Rapport_{safe_nom}_{safe_tel}.zip"
        
        try:
            print(f"\n📦 Création archive ZIP...")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in project_folder.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(project_folder.parent)
                        zipf.write(file_path, arcname=arcname)
                        print(f"   + {arcname}")
            
            print(f"✅ Archive créée: {zip_path.name} ({os.path.getsize(zip_path)/1024:.1f} Ko)")
            
            # Vérification
            with zipfile.ZipFile(zip_path, 'r') as z:
                files = z.namelist()
                print(f"📊 {len(files)} fichiers dans l'archive")
                # Lister les shapefiles
                shp_files = [f for f in files if f.endswith('.shp')]
                print(f"📁 Shapefiles: {len(shp_files)}")
                for shp in shp_files[:10]:  # Afficher les 10 premiers
                    print(f"   - {shp}")
            
            return str(zip_path)
            
        except Exception as e:
            print(f"❌ Archive: {e}")
            import traceback
            traceback.print_exc()
            return None