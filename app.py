# app_combined.py
import streamlit as st
from pathlib import Path
import sys
from io import StringIO
from utils import utils_setup
from orchestrator import run_pipeline, arreter_et_supprimer_conteneur

# Imports pour la carte personnalisée (marqueur Google Maps)
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

st.set_page_config(page_title="Ground Water Finder - Outils combinés", layout="wide")

# =========================
# 🚀 FONCTION RELANCER (remplace l'ancien nettoyage)
# =========================
def relancer_environnement():
    """Nettoyage fichiers + suppression ancien conteneur + création nouveau."""
    app_dir = Path(__file__).resolve().parent
    clients_dir = app_dir / "data" / "Dossier_clients"

    # 1. Nettoyer les fichiers clients
    if clients_dir.exists():
        import shutil
        for item in clients_dir.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception as e:
                st.error(f"Erreur nettoyage fichiers: {e}")

    # 2. Supprimer l'ancien conteneur Docker
    with st.spinner("Suppression de l'ancien conteneur..."):
        if arreter_et_supprimer_conteneur():
            st.info("Ancien conteneur supprimé.")
        else:
            st.warning("Aucun conteneur à supprimer ou erreur.")

    # 3. Créer un nouveau conteneur
    with st.spinner("Création d'un nouveau conteneur..."):
        try:
            logs = run_pipeline("gwf")
            st.success("Nouveau conteneur créé et prêt !")
        except Exception as e:
            st.error(f"Erreur lors de la création du conteneur: {e}")

# =========================
# SIDEBAR (bouton modifié)
# =========================


if st.sidebar.button("🔄 Relancer l'environnement"):
    from orchestrator import relancer_conteneur_principal
    import time
    with st.spinner("Relance du conteneur principal..."):
        success = relancer_conteneur_principal()
        if success:
            st.success("Le conteneur a été relancé. La page va se recharger automatiquement.")
            time.sleep(3)
            st.rerun()
        else:
            st.error("Échec de la relance. Vérifiez les logs.")


# =========================
# IMPORTS POUR LES ONGLETS
# =========================
from utils.utils_export import (
    choisir_dossier_client,
    load_contour,
    charger_couche,
    generer_journal,
    shp_to_kml_gpx_kmz
)
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
import matplotlib.patches as mpatches
import shutil

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🛠️ Configuration & Extraction",
    "🛰️ Scan satellites",
    "💧 Geotraitement",
    "🗺️ Carte de prospection",
    "☁️ Upload B2"
])

with tab1:
    utils_setup.create_streamlit_app()

with tab2:
    st.title("🛰️ Scan satellites")

    app_dir = Path(__file__).resolve().parent
    clients_dir = app_dir / "data" / "Dossier_clients"

    if not clients_dir.exists() or not any(clients_dir.iterdir()):
        st.error("❌ Aucun dossier client trouvé. Veuillez d'abord exécuter l'onglet Configuration.")
    else:
        st.info("Cliquez sur le bouton pour lancer le scan satellite.")

        if st.button("🚀 Lancer le scan satellite"):
            try:
                from utils import utils_browser

                with st.spinner("Scan satellite en cours..."):
                    utils_browser.run_streamlit_app()

                st.success("✅ Scan terminé.")

            except Exception as e:
                import traceback
                st.error(f"Erreur : {e}")
                st.code(traceback.format_exc())

with tab3:
    app_dir = Path(__file__).resolve().parent
    clients_dir = app_dir / "data" / "Dossier_clients"
    if not clients_dir.exists() or not any(clients_dir.iterdir()):
        st.error("❌ Aucun dossier client trouvé.")
    else:
        from utils.utils_geotraitement import (
            detecter_client_unique,
            initialiser_client,
            traiter_complet,
            exporter_resultats
        )
        st.title("💧 Traitement GPX/Contour")
        try:
            client_nom = detecter_client_unique()
            st.info(f"📁 Client : **{client_nom}**")
            initialiser_client(client_nom)
            with st.spinner("Traitement..."):
                resultats = traiter_complet()
                exporter_resultats(resultats)
            st.success("✅ Terminé")
            st.json({k: len(v) if isinstance(v, list) else bool(v) for k, v in resultats.items()})
        except Exception as e:
            st.error(str(e))

# ==================== ONGLET 4 (avec marqueur Google Maps) ====================
# ==================== ONGLET 4 (marqueur triangle rouge) ====================
with tab4:
    app_dir = Path(__file__).resolve().parent
    clients_dir = app_dir / "data" / "Dossier_clients"
    if not clients_dir.exists() or not any(clients_dir.iterdir()):
        st.error("❌ Aucun dossier client trouvé.")
    else:
        st.title("🗺️ Carte de prospection")
        try:
            dossier_client, nom_client = choisir_dossier_client()
            input_dir = dossier_client / "INPUT"
            dossier_rendu = dossier_client / "RENDU"
            
            # Logique de fallback pour le contour (inchangée)
            contour_path = None
            if input_dir.exists():
                contour_files = [f for f in input_dir.iterdir() if f.suffix.lower() in [".gpx", ".kml", ".kmz"]]
                if contour_files:
                    contour_path = contour_files[0]
                    st.info(f"📁 Contour trouvé dans INPUT : {contour_path.name}")
            if contour_path is None:
                contour_shp = dossier_rendu / "CONTOUR.shp"
                if contour_shp.exists():
                    contour_path = contour_shp
                    st.info("📁 Fallback : utilisation de CONTOUR.shp comme contour")
            if contour_path is None:
                st.error("❌ Aucun fichier de contour trouvé (ni dans INPUT, ni CONTOUR.shp dans RENDU)")
                st.stop()
            
            # Charger le contour
            if contour_path.suffix.lower() == ".shp":
                contour_gdf = gpd.read_file(contour_path).to_crs(epsg=3857)
            else:
                contour_poly = load_contour(contour_path)
                contour_gdf = gpd.GeoDataFrame(geometry=[contour_poly], crs="EPSG:4326").to_crs(epsg=3857)
            
            # Charger les autres couches
            couches = {"contour": contour_gdf, "lines": None, "dolines": None, "intersections": None}
            for f in dossier_rendu.glob("*"):
                if f.suffix.lower() in (".shp", ".gpx", ".kml", ".kmz"):
                    gdf = charger_couche(f)
                    if gdf is not None and not gdf.empty:
                        gdf = gdf.to_crs(3857)
                        name = f.stem.lower()
                        if "lignes" in name or "lines" in name:
                            couches["lines"] = gdf
                        elif "dolines" in name:
                            couches["dolines"] = gdf
                        elif "intersections" in name:
                            couches["intersections"] = gdf
            
            # Création de la figure
            fig, ax = plt.subplots(figsize=(14, 12))

            handles = []

            # Lignes
            if couches.get("lines") is not None:
                couches["lines"].plot(ax=ax, color="orange", linewidth=3, linestyle="--", alpha=0.8, zorder=6)
            handles.append(mpatches.Patch(facecolor="orange", label="Fractures identifiées"))

            # Dolines
            if couches.get("dolines") is not None:
                couches["dolines"].plot(ax=ax, color="blue", markersize=60, marker="o", alpha=0.5, edgecolor="white", linewidth=1, zorder=4)
            handles.append(mpatches.Patch(facecolor="blue", label="Dolines"))

            # Contour
            if couches.get("contour") is not None:
                couches["contour"].plot(ax=ax, facecolor="none", edgecolor="chocolate", linewidth=3, alpha=0.9, zorder=5)
            handles.append(mpatches.Patch(facecolor="none", edgecolor="chocolate", label="Surface prospectée"))

            # Points de forage (triangle rouge)
            if couches.get("intersections") is not None:
                couches["intersections"].plot(ax=ax, color="red", markersize=100, marker="^", 
                                              edgecolor="black", linewidth=1.5, alpha=0.9, zorder=5)
                handles.append(mpatches.Patch(facecolor="red", label="Points de forage"))

            # Fond de carte (inchangé)
            try:
                ctx.add_basemap(ax, source="http://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", crs="EPSG:3857")
            except:
                try:
                    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, crs="EPSG:3857")
                except:
                    ax.set_facecolor("#e8f4f8")
            
            ax.set_axis_off()
            ax.set_title(f"🗺️ Projet {nom_client}", fontsize=18, weight="bold")
            ax.legend(handles=handles, loc="lower left", fontsize=10, framealpha=0.95)
            plt.tight_layout()
            
            # Export et création du ZIP (inchangé)
            rapport_dir = dossier_rendu / f"Rapport_{nom_client}"
            rapport_dir.mkdir(parents=True, exist_ok=True)
            fig.savefig(rapport_dir / "carte_prospection.png", dpi=150, bbox_inches="tight", facecolor="white")
            st.pyplot(fig, clear_figure=True)
            plt.close(fig)
            
            data_dir = rapport_dir / "Data"
            for sub in ["SHP", "GPX", "KML", "KMZ", "Convertir"]:
                (data_dir / sub).mkdir(parents=True, exist_ok=True)
            
            for f in dossier_rendu.glob("*.shp"):
                base = f.stem
                for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
                    src = dossier_rendu / f"{base}{ext}"
                    if src.exists():
                        shutil.copy(src, data_dir / "SHP" / src.name)
            
            generer_journal(couches, rapport_dir / "journal.txt")
            
            convertir_src = dossier_client / "OUTPUT" / "Convertir"
            if convertir_src.exists():
                shutil.copytree(convertir_src, data_dir / "Convertir", dirs_exist_ok=True)
            
            target = {"kml": data_dir/"KML", "kmz": data_dir/"KMZ", "gpx": data_dir/"GPX"}
            for nom, gdf in couches.items():
                if gdf is not None:
                    shp_to_kml_gpx_kmz(gdf, f"{nom_client}_{nom}", target)
            
            zip_path = dossier_rendu / f"{nom_client}.zip"
            shutil.make_archive(str(zip_path.with_suffix("")), "zip", rapport_dir)
            st.success(f"✅ ZIP généré : {zip_path.name}")
            
        except Exception as e:
            st.error(f"Erreur : {e}")
            import traceback
            st.code(traceback.format_exc())

# ==================== ONGLET 5 (upload automatique) ====================
with tab5:
    app_dir = Path(__file__).resolve().parent
    clients_dir = app_dir / "data" / "Dossier_clients"
    if not clients_dir.exists() or not any(clients_dir.iterdir()):
        st.error("❌ Aucun dossier client trouvé.")
    else:
        st.title("☁️ Upload automatique vers Backblaze B2")
        st.markdown("Upload de tous les fichiers ZIP des clients vers le bucket **`ground-water-finder`**.")

        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            from utils import utils_upload_b2
            utils_upload_b2.main()
            logs = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        st.text_area("Logs d'upload", logs, height=300)
        st.success("✅ Upload terminé (consultez les logs ci-dessus)")