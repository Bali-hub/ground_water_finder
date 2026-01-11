# app.py – VERSION COMPLÈTE AVEC UPLOAD B2 ET MESSAGES CLARIFIÉS
# ===============================================================

import os
import sys
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
import streamlit as st

# ===============================================================
# CONFIGURATION INITIALE
# ===============================================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
utils_dir = os.path.join(os.path.dirname(__file__), "utils")
if os.path.exists(utils_dir):
    sys.path.append(utils_dir)

# ===============================================================
# IMPORTS AVEC GESTION D'ERREURS
# ===============================================================
EXPORT_AVAILABLE = True
UPLOAD_AVAILABLE = True

try:
    import geopandas as gpd
    from shapely.geometry import Polygon, MultiPolygon
    print("✅ geopandas importé")
except ImportError as e:
    st.error(f"❌ Erreur import geopandas: {e}")
    st.stop()

# Import utils_setup
try:
    from utils.utils_setup import (
        convert_all_geojson_to_gpx,
        extract_coordinates_and_generate_equidistant_points,
        process_geojson_files_auto,
        setup_owner_folders,
    )
    print("✅ utils_setup importé")
except ImportError as e:
    st.error(f"❌ Erreur import utils_setup: {e}")
    st.stop()

# Import utils_browser
try:
    from utils.utils_browser import process_with_fallback
    print("✅ utils_browser importé")
except ImportError as e:
    st.error(f"❌ Erreur import utils_browser: {e}")
    
    def process_with_fallback(folders):
        st.warning("⚠️ utils_browser non disponible - simulation")
        destination = folders.get("convertir", "converted")
        os.makedirs(destination, exist_ok=True)
        
        fallback_file = os.path.join(destination, "simulation.gpx")
        with open(fallback_file, 'w') as f:
            f.write('<?xml version="1.0"?><gpx version="1.1"><trk><name>Simulation</name></trk></gpx>')
        
        return {
            "success": [{"output": fallback_file, "size": 100}],
            "failed": [],
            "skipped": []
        }

# Import utils_geotraitement
try:
    from utils.utils_geotraitement import (
        filter_intersection_points,
        load_contour_from_file,
        process_and_plot_gpx,
    )
    print("✅ utils_geotraitement importé")
except ImportError as e:
    st.error(f"❌ Erreur import utils_geotraitement: {e}")
    st.stop()

# Import utils_export
try:
    from utils.utils_export import ExportProspection, create_carte_prospection
    print("✅ utils_export importé")
except ImportError as e:
    print(f"⚠️ utils_export non disponible: {e}")
    EXPORT_AVAILABLE = False
    
    class ExportProspection:
        def __init__(self, nom_prospecteur, telephone, **kwargs):
            self.nom_prospecteur = nom_prospecteur
            self.telephone = telephone
            self.kwargs = kwargs
            
        def executer_export_complet(self, output_dir=None):
            st.warning("⚠️ ExportProspection en mode simulation")
            return self._creer_zip_simple(output_dir)
            
        def _creer_zip_simple(self, output_dir):
            try:
                output_dir = output_dir or tempfile.gettempdir()
                safe_nom = "".join(c for c in self.nom_prospecteur if c.isalnum() or c in (' ', '-', '_'))
                safe_nom = safe_nom.replace(' ', '_')
                safe_tel = "".join(c for c in self.telephone if c.isdigit())
                
                zip_path = os.path.join(output_dir, f"Rapport_{safe_nom}_{safe_tel}.zip")
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    info_txt = f"Nom: {self.nom_prospecteur}\nTéléphone: {self.telephone}\nDate: {datetime.now()}\n\nMode simulation"
                    zipf.writestr("INFO.txt", info_txt)
                
                return zip_path
            except Exception as e:
                print(f"❌ Erreur création ZIP simple: {e}")
                return None

# Import utils_upload_b2
try:
    from utils.utils_upload_b2 import upload_zip_to_b2, test_b2_connection
    print("✅ utils_upload_b2 importé")
except ImportError as e:
    print(f"⚠️ utils_upload_b2 non disponible: {e}")
    UPLOAD_AVAILABLE = False
    
    def upload_zip_to_b2(zip_path):
        return {
            "success": False,
            "error": "Module B2 non disponible",
            "file_name": os.path.basename(zip_path),
            "local_path": zip_path
        }
    
    def test_b2_connection():
        return False

# ===============================================================
# FONCTION AMÉLIORÉE POUR GÉNÉRER ET AFFICHER LA CARTE
# ===============================================================
def generer_et_afficher_carte_amelioree(folders, email, donnees_geo, contour_polygon):
    """Génère et affiche la carte avec méthode robuste inspirée de votre code"""
    
    try:
        # 1. Préparer les chemins
        carte_path = os.path.join(folders["output"], "carte_prospection.png")
        os.makedirs(os.path.dirname(carte_path), exist_ok=True)
        
        print(f"🎨 Génération carte améliorée pour: {email}")
        print(f"📂 Chemin carte: {carte_path}")
        
        # 2. Préparer les données (inspiré de votre code)
        import matplotlib.pyplot as plt
        import contextily as ctx
        
        fig, ax = plt.subplots(figsize=(14, 10))
        handles = []
        
        # 3. Tracer le contour (inspiré de votre code de contour)
        if contour_polygon is not None:
            try:
                # Convertir en GeoDataFrame
                contour_gdf = gpd.GeoDataFrame(geometry=[contour_polygon], crs='EPSG:4326')
                contour_gdf_3857 = contour_gdf.to_crs(epsg=3857)
                
                # Tracer avec style similaire à votre code
                contour_gdf_3857.plot(
                    ax=ax, 
                    alpha=0.35, 
                    edgecolor='red', 
                    linewidth=2,
                    facecolor='none'
                )
                handles.append(plt.Line2D([0], [0], color='red', lw=2, label='Contour prospecté'))
                print("✅ Contour tracé")
                
            except Exception as e:
                print(f"⚠️ Erreur traçage contour: {e}")
        
        # 4. Tracer les fractures/lignes
        fractures_gdf = donnees_geo.get("fractures", gpd.GeoDataFrame())
        if not fractures_gdf.empty:
            try:
                fractures_gdf_3857 = fractures_gdf.to_crs(epsg=3857)
                fractures_gdf_3857.plot(
                    ax=ax,
                    alpha=0.7,
                    edgecolor='blue',
                    linewidth=1.5
                )
                handles.append(plt.Line2D([0], [0], color='blue', lw=1.5, label='Fractures'))
                print(f"✅ Fractures tracées: {len(fractures_gdf)} éléments")
            except Exception as e:
                print(f"⚠️ Erreur traçage fractures: {e}")
        
        # 5. Tracer les points de forage
        points_gdf = donnees_geo.get("points_forage", gpd.GeoDataFrame())
        if not points_gdf.empty:
            try:
                points_gdf_3857 = points_gdf.to_crs(epsg=3857)
                points_gdf_3857.plot(
                    ax=ax,
                    color='green',
                    markersize=80,  # Plus gros pour être visible
                    marker='o',
                    alpha=0.8,
                    edgecolor='black',
                    linewidth=1
                )
                handles.append(plt.Line2D([0], [0], color='green', marker='o', 
                                        lw=0, markersize=8, label='Points de forage'))
                print(f"✅ Points de forage tracés: {len(points_gdf)} éléments")
            except Exception as e:
                print(f"⚠️ Erreur traçage points: {e}")
        
        # 6. Tracer les dolines
        dolines_gdf = donnees_geo.get("dolines", gpd.GeoDataFrame())
        if not dolines_gdf.empty:
            try:
                dolines_gdf_3857 = dolines_gdf.to_crs(epsg=3857)
                dolines_gdf_3857.plot(
                    ax=ax,
                    color='orange',
                    markersize=70,
                    marker='X',
                    alpha=0.8,
                    edgecolor='black',
                    linewidth=1
                )
                handles.append(plt.Line2D([0], [0], color='orange', marker='X', 
                                        lw=0, markersize=8, label='Dolines'))
                print(f"✅ Dolines tracées: {len(dolines_gdf)} éléments")
            except Exception as e:
                print(f"⚠️ Erreur traçage dolines: {e}")
        
        # 7. Ajouter fond de carte (inspiré de votre code)
        try:
            # Essayer Google Satellite d'abord
            google_satellite = "http://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
            ctx.add_basemap(ax, source=google_satellite, crs='EPSG:3857')
            print("✅ Fond Google Satellite ajouté")
        except:
            try:
                # Fallback: OpenStreetMap
                ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, crs='EPSG:3857')
                print("✅ Fond OpenStreetMap ajouté")
            except:
                try:
                    # Fallback ultime: contexte par défaut
                    ctx.add_basemap(ax, crs='EPSG:3857')
                    print("✅ Fond par défaut ajouté")
                except Exception as e:
                    print(f"⚠️ Impossible d'ajouter fond carte: {e}")
        
        # 8. Configuration finale
        ax.set_title(f"🗺️ Carte prospection - {email}", fontsize=18, weight='bold')
        ax.axis('off')
        
        # Ajouter légende si des éléments existent
        if handles:
            ax.legend(handles=handles, loc='lower left', fontsize=9, frameon=True, fancybox=True)
            print(f"✅ Légende ajoutée avec {len(handles)} éléments")
        
        plt.tight_layout()
        
        # 9. Sauvegarder l'image avec haute qualité
        plt.savefig(carte_path, dpi=300, bbox_inches='tight', format='png')
        plt.close(fig)
        
        # 10. Vérifier que l'image a été créée
        if os.path.exists(carte_path):
            file_size = os.path.getsize(carte_path)
            print(f"✅ Carte sauvegardée: {carte_path} ({file_size} octets)")
            
            if file_size > 0:
                # Afficher avec PIL pour plus de robustesse
                try:
                    from PIL import Image
                    img = Image.open(carte_path)
                    
                    # Redimensionner pour Streamlit
                    max_width = 800
                    if img.width > max_width:
                        ratio = max_width / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Afficher
                    st.image(img, caption="Carte de prospection générée", use_container_width=True)
                    print("✅ Image affichée avec PIL")
                    
                except Exception as e:
                    print(f"⚠️ PIL non disponible, utilisation st.image: {e}")
                    st.image(carte_path, caption="Carte de prospection générée", use_container_width=True)
                
                # Bouton de téléchargement
                with open(carte_path, "rb") as img_file:
                    st.download_button(
                        label="📥 Télécharger la carte",
                        data=img_file,
                        file_name="carte_prospection.png",
                        mime="image/png",
                        use_container_width=True
                    )
                
                return True
            else:
                st.error("❌ La carte a été générée mais le fichier est vide")
                return False
        else:
            st.error("❌ La carte n'a pas pu être générée")
            return False
            
    except Exception as e:
        st.error(f"❌ Erreur génération carte: {str(e)[:100]}")
        print(f"💥 Erreur détaillée génération carte: {e}")
        import traceback
        traceback.print_exc()
        return False

# ===============================================================
# FONCTIONS UTILITAIRES
# ===============================================================
def charger_shapefiles_depuis_rendu(rendu_folder):
    """Charge les shapefiles générés"""
    resultats = {
        "fractures": gpd.GeoDataFrame(columns=["geometry"], crs="EPSG:4326"),
        "points_forage": gpd.GeoDataFrame(columns=["geometry"], crs="EPSG:4326"),
        "dolines": gpd.GeoDataFrame(columns=["geometry"], crs="EPSG:4326"),
        "contour": gpd.GeoDataFrame(columns=["geometry"], crs="EPSG:4326"),
    }
    
    shapefiles = {
        "output_dolines.shp": "dolines",
        "output_lines.shp": "fractures",
        "output_intersection_points.shp": "points_forage",
        "contour.shp": "contour",
    }
    
    for filename, key in shapefiles.items():
        filepath = os.path.join(rendu_folder, filename)
        if os.path.exists(filepath):
            try:
                resultats[key] = gpd.read_file(filepath)
                print(f"✅ {filename} chargé ({len(resultats[key])} éléments)")
            except Exception as e:
                print(f"⚠️ Erreur lecture {filename}: {e}")
    
    return resultats

# ===============================================================
# CONFIGURATION STREAMLIT
# ===============================================================
st.set_page_config(
    page_title="Ground Water Finder",
    page_icon="💧",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Initialisation session
if "language_selected" not in st.session_state:
    st.session_state.language_selected = False
    st.session_state.language = None

if not st.session_state.language_selected:
    st.title("💧 Ground Water Finder")
    st.subheader("Hydrogeological Prospecting Application")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🇫🇷 Français", use_container_width=True):
            st.session_state.language = "fr"
            st.session_state.language_selected = True
            st.rerun()
    with col2:
        if st.button("🇬🇧 English", use_container_width=True):
            st.session_state.language = "en"
            st.session_state.language_selected = True
            st.rerun()
    st.stop()

# ===============================================================
# INTERFACE PRINCIPALE
# ===============================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/water.png", width=80)
    lang_flag = "🇫🇷" if st.session_state.language == "fr" else "🇬🇧"
    st.info(f"{lang_flag} **{st.session_state.language}**")
    
    if st.button("Changer de langue", use_container_width=True):
        st.session_state.language_selected = False
        st.rerun()
    
    with st.expander("🔧 Statut des modules"):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Export", "✅" if EXPORT_AVAILABLE else "❌")
        with col2:
            st.metric("Upload B2", "✅" if UPLOAD_AVAILABLE else "❌")
        
        if UPLOAD_AVAILABLE:
            if st.button("Test connexion B2", use_container_width=True):
                if test_b2_connection():
                    st.success("✅ Connexion B2 OK")
                else:
                    st.error("❌ Connexion B2 échouée")
    
    st.markdown("---")
    st.markdown("""
    **📧 Support technique:**
    m2techsecretariat@gmail.com
    """)
    st.caption("💧 Ground Water Finder v2.0")

# ===============================================================
# FORMULAIRE PRINCIPAL
# ===============================================================
with st.form("prospection_form"):
    st.markdown("### 📋 Informations de prospection")
    
    col1, col2 = st.columns(2)
    with col1:
        email = st.text_input("📧 Email", placeholder="votre@email.com")
    with col2:
        phone = st.text_input("📞 Téléphone", placeholder="+33 1 23 45 67 89")
    
    surface = st.text_input("📐 Surface (hectares)", placeholder="10.5")
    
    uploaded_file = st.file_uploader(
        "🗺️ Fichier contour (GPX/KML/KMZ/Shapefile)",
        type=["gpx", "kml", "kmz", "shp", "zip"],
        help="Téléchargez le fichier de contour de votre zone d'étude"
    )
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        launch_btn = st.form_submit_button(
            "🚀 Lancer l'analyse complète",
            use_container_width=True,
            type="primary"
        )
    with col2:
        debug_mode = st.checkbox("Mode debug", help="Conserve les fichiers temporaires")
    with col3:
        test_mode = st.checkbox("Test mode", help="Génère le ZIP sans upload")

# ===============================================================
# PIPELINE DE TRAITEMENT
# ===============================================================
if launch_btn and uploaded_file:
    if not all([email, phone, surface, uploaded_file]):
        st.warning("⚠️ Tous les champs sont requis")
        st.stop()
    
    try:
        surface_float = float(surface)
    except ValueError:
        st.error("❌ La surface doit être un nombre (ex: 10.5)")
        st.stop()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # ÉTAPE 1: Création des dossiers
        status_text.text("📁 Création des dossiers...")
        folders = setup_owner_folders(email, phone, surface)
        print(f"📂 Dossiers créés: {folders}")
        progress_bar.progress(10)
        
        # Sauvegarder fichier uploadé
        uploaded_path = os.path.join(folders["input"], uploaded_file.name)
        with open(uploaded_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        print(f"✅ Fichier sauvegardé: {uploaded_path}")
        
        # ÉTAPE 2: Chargement du contour
        status_text.text("📍 Chargement du contour...")
        contour_polygon = load_contour_from_file(uploaded_path)
        progress_bar.progress(20)
        
        # ÉTAPE 3: Extraction des coordonnées
        status_text.text("📐 Extraction des coordonnées...")
        extract_coordinates_and_generate_equidistant_points(uploaded_path, folders)
        process_geojson_files_auto(folders)
        progress_bar.progress(30)
        
        # ÉTAPE 4: Conversion GeoJSON → GPX
        status_text.text("🔄 Conversion GeoJSON → GPX...")
        convert_all_geojson_to_gpx(folders)
        progress_bar.progress(40)
        
        # ÉTAPE 5: Traitement GPSVisualizer
        status_text.text("🔍 Scan...")
        gps_result = process_with_fallback(folders)
        if gps_result and "success" in gps_result:
            st.success(f"✅ {len(gps_result['success'])} fichier(s) traités")
        progress_bar.progress(55)
        
        # ÉTAPE 6: Préparation GPX final
        status_text.text("⚡ Préparation GPX final...")
        final_gpx_folder = os.path.join(folders["rendu"], "GPX_FINAL")
        os.makedirs(final_gpx_folder, exist_ok=True)
        
        convertir_folder = folders.get("convertir", "")
        if os.path.exists(convertir_folder):
            for f in os.listdir(convertir_folder):
                if f.lower().endswith(".gpx"):
                    src = os.path.join(convertir_folder, f)
                    dst = os.path.join(final_gpx_folder, f)
                    shutil.copy2(src, dst)
        progress_bar.progress(65)
        
        # ÉTAPE 7: Traitement géospatial
        status_text.text("🗺️ Traitement géospatial...")
        process_and_plot_gpx(final_gpx_folder, folders["rendu"], display_in_streamlit=False)
        progress_bar.progress(80)
        
        # ÉTAPE 8: Chargement des données
        status_text.text("📦 Chargement des données...")
        donnees_geo = charger_shapefiles_depuis_rendu(folders["rendu"])
        progress_bar.progress(85)
        
        # ÉTAPE 9: Génération et affichage de la carte AMÉLIORÉE
        status_text.text("🖼️ Génération de la carte...")
        
        # Utiliser la fonction améliorée
        carte_generee = generer_et_afficher_carte_amelioree(
            folders, email, donnees_geo, contour_polygon
        )
        
        if not carte_generee:
            # Fallback simple
            st.warning("⚠️ Carte non générée - mode fallback")
            st.info("La carte n'a pas pu être générée, mais l'analyse est terminée.")
        
        progress_bar.progress(92)
        
        # ===============================================================
        # ÉTAPE 10: ARCHIVAGE DU RAPPORT ET UPLOAD B2
        # ===============================================================
        status_text.text("📤 Archivage du rapport...")
        
        # Si mode test, on saute l'upload
        if test_mode:
            st.info("🧪 Mode test activé - pas d'upload B2")
            st.info("""
            **📧 Pour recevoir le rapport complet en mode test:**
            Envoyez un email à **m2techsecretariat@gmail.com** avec votre demande.
            """)
        else:
            # ÉTAPE 11: Export complet et upload B2
            if EXPORT_AVAILABLE:
                status_text.text("📦 Création du rapport ZIP complet...")
                
                try:
                    # Créer l'export complet avec ExportProspection
                    export = ExportProspection(
                        nom_prospecteur=email,
                        telephone=phone,
                        contour_polygon=contour_polygon,
                        lines_gdf=donnees_geo["fractures"],
                        points_gdf=donnees_geo["points_forage"],
                        dolines_gdf=donnees_geo["dolines"]
                    )
                    
                    # Créer le ZIP dans le dossier output
                    zip_path = export.executer_export_complet(folders["output"])
                    
                    if zip_path and os.path.exists(zip_path):
                        file_size = os.path.getsize(zip_path)
                        st.success(f"✅ Rapport ZIP créé: {os.path.basename(zip_path)} ({file_size/1024/1024:.1f} MB)")
                        
                        # Upload vers B2 si disponible
                        if UPLOAD_AVAILABLE:
                            status_text.text("☁️ Envoi du rapport vers le cloud...")
                            
                            # Test de la connexion B2 d'abord
                            if test_b2_connection():
                                result = upload_zip_to_b2(zip_path)
                                
                                if result["success"]:
                                    progress_bar.progress(100)
                                    
                                    # ============================================
                                    # MESSAGES PRINCIPAUX - RAPPORT ENVOYÉ
                                    # ============================================
                                    
                                    # Message principal en grand
                                    st.markdown("""
                                    <div style='background-color: #d4edda; padding: 20px; border-radius: 10px; border-left: 5px solid #155724;'>
                                    <h2 style='color: #155724;'>📤 Rapport envoyé avec succès!</h2>
                                    <p style='font-size: 16px;'>Votre rapport ZIP a été transféré sur notre serveur cloud sécurisé.</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    st.markdown("---")
                                    
                                    # Message pour recevoir le rapport complet
                                    st.markdown("""
                                    <div style='background-color: #d1ecf1; padding: 20px; border-radius: 10px; border-left: 5px solid #0c5460;'>
                                    <h3 style='color: #0c5460;'>📧 Recevoir votre rapport complet</h3>
                                    <p style='font-size: 16px;'><strong>Pour obtenir votre rapport d'analyse complet :</strong></p>
                                    <ul style='font-size: 16px;'>
                                        <li>Envoyez un email à <strong>m2techsecretariat@gmail.com</strong></li>
                                        <li>Indiquez votre nom et email</li>
                                        <li>Mentionnez la référence : <code>{}</code></li>
                                        <li>Date de l'analyse : {}</li>
                                    </ul>
                                    <p style='font-size: 14px; color: #0c5460;'>Notre équipe vous enverra le rapport complet sous 24h.</p>
                                    </div>
                                    """.format(result['file_name'], result['uploaded_at']), unsafe_allow_html=True)
                                    
                                    # Informations techniques
                                    with st.expander("📊 Détails techniques du transfert", expanded=False):
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.metric("📁 Fichier", result['file_name'])
                                            st.metric("📊 Taille", f"{result['file_size']/1024/1024:.2f} MB")
                                        with col2:
                                            st.metric("⏱️ Durée", f"{result['duration_seconds']}s")
                                            st.metric("📦 Serveur", "Backblaze B2 Cloud")
                                        
                                        # Liens de téléchargement
                                        st.markdown("**🔗 Liens d'accès (technique):**")
                                        st.code(result['download_url'], language="text")
                                        
                                        # QR Code pour le lien
                                        try:
                                            import qrcode
                                            from PIL import Image
                                            import io
                                            
                                            qr = qrcode.QRCode(
                                                version=1,
                                                error_correction=qrcode.constants.ERROR_CORRECT_L,
                                                box_size=10,
                                                border=4,
                                            )
                                            qr.add_data(result['download_url'])
                                            qr.make(fit=True)
                                            
                                            img = qr.make_image(fill_color="black", back_color="white")
                                            img_bytes = io.BytesIO()
                                            img.save(img_bytes, format="PNG")
                                            img_bytes.seek(0)
                                            
                                            st.image(img_bytes, caption="Scan pour accéder au rapport", width=200)
                                        except ImportError:
                                            pass
                                    
                                    # Téléchargement local comme backup
                                    st.markdown("---")
                                    st.markdown("**📥 Téléchargement local (backup):**")
                                    with open(zip_path, "rb") as f:
                                        st.download_button(
                                            label="💾 Télécharger une copie locale",
                                            data=f,
                                            file_name=os.path.basename(zip_path),
                                            mime="application/zip",
                                            use_container_width=True
                                        )
                                    
                                    # Animation de succès
                                    st.balloons()
                                        
                                else:
                                    # En cas d'échec d'upload
                                    st.error("""
                                    ❌ **L'envoi vers le cloud a échoué**
                                    
                                    **Solution alternative:**
                                    Envoyez le fichier ZIP local à **m2techsecretariat@gmail.com** avec votre demande.
                                    """)
                                    
                                    # Téléchargement local
                                    with open(zip_path, "rb") as f:
                                        st.download_button(
                                            label="📥 Télécharger le rapport (à envoyer manuellement)",
                                            data=f,
                                            file_name=os.path.basename(zip_path),
                                            mime="application/zip",
                                            use_container_width=True
                                        )
                            else:
                                st.warning("""
                                ⚠️ **Connexion cloud indisponible**
                                
                                **Pour obtenir votre rapport:**
                                Téléchargez le fichier ci-dessous et envoyez-le à **m2techsecretariat@gmail.com**
                                """)
                        else:
                            st.warning("""
                            ⚠️ **Module cloud désactivé**
                            
                            **Pour obtenir votre rapport complet:**
                            1. Téléchargez le fichier ci-dessous
                            2. Envoyez-le à **m2techsecretariat@gmail.com**
                            3. Notre équipe vous répondra sous 24h
                            """)
                            
                            # Téléchargement local
                            with open(zip_path, "rb") as f:
                                st.download_button(
                                    label="📥 Télécharger le rapport (à envoyer par email)",
                                    data=f,
                                    file_name=os.path.basename(zip_path),
                                    mime="application/zip",
                                    use_container_width=True
                                )
                    else:
                        st.error("❌ Impossible de créer le rapport ZIP")
                        st.info("""
                        **📧 Contactez notre support:**
                        Envoyez un email à **m2techsecretariat@gmail.com** avec:
                        - Les détails de votre analyse
                        - Votre nom et email
                        - Les fichiers d'entrée utilisés
                        """)
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'export: {str(e)}")
                    st.info("""
                    **📧 Support technique:**
                    Envoyez les détails de cette erreur à **m2techsecretariat@gmail.com**
                    """)
            else:
                st.warning("⚠️ Module d'export non disponible")
                st.info("""
                **📧 Contactez-nous:**
                Envoyez un email à **m2techsecretariat@gmail.com** pour obtenir votre rapport.
                """)
        
        progress_bar.progress(100)
        status_text.success("✅ Analyse terminée!")
        
        # ===============================================================
        # RÉSUMÉ FINAL
        # ===============================================================
        st.markdown("---")
        st.subheader("📋 Résumé de l'analyse")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("👤 Client", email)
            st.metric("📞 Contact", phone)
            st.metric("📐 Surface", f"{surface_float} ha")
        
        with col2:
            fractures_count = len(donnees_geo["fractures"])
            points_count = len(donnees_geo["points_forage"])
            dolines_count = len(donnees_geo["dolines"])
            
            st.metric("🔄 Fractures", fractures_count)
            st.metric("📍 Points de forage", points_count)
            st.metric("🕳️ Dolines", dolines_count)
        
        # Message de service client final
        st.markdown("---")
        st.markdown("""
        <div style='background-color: #e8f4fd; padding: 15px; border-radius: 10px; border-left: 5px solid #0066cc;'>
        <h4 style='color: #0066cc;'>📧 Service client</h4>
        <p>Pour toute question ou pour recevoir votre rapport complet par email, contactez :</p>
        <p style='text-align: center; font-size: 18px; font-weight: bold;'>
        m2techsecretariat@gmail.com
        </p>
        <p style='text-align: center; font-size: 14px;'>Réponse sous 24 heures ouvrées</p>
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"❌ Erreur lors de l'analyse: {str(e)[:200]}")
        import traceback
        with st.expander("🔍 Détails techniques"):
            st.code(traceback.format_exc(), language="python")
        
        st.info("""
        **📧 Support technique:**
        Envoyez cette erreur à **m2techsecretariat@gmail.com** pour obtenir de l'aide.
        """)

# ===============================================================
# FOOTER
# ===============================================================
st.markdown("---")
st.caption("💧 Ground Water Finder v2.0 • © 2024 • Contact: m2techsecretariat@gmail.com")