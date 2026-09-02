import streamlit as st
from pathlib import Path
import sys
from io import StringIO
import time
import shutil
import traceback

from utils import utils_setup
from orchestrator import (
    run_pipeline,
    arreter_et_supprimer_conteneur,
    relancer_conteneur_principal
)

# ============================================================
# CONFIGURATION STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Ground Water Finder - Outils combinés",
    layout="wide"
)

# ============================================================
# INITIALISATION DE L'ETAT DU WORKFLOW
# ============================================================

if "setup_done" not in st.session_state:
    st.session_state.setup_done = False

if "browser_done" not in st.session_state:
    st.session_state.browser_done = False

if "geotraitement_done" not in st.session_state:
    st.session_state.geotraitement_done = False

if "carte_done" not in st.session_state:
    st.session_state.carte_done = False

if "upload_done" not in st.session_state:
    st.session_state.upload_done = False


# ============================================================
# FONCTION : RESET COMPLET DU WORKFLOW
# ============================================================

def reset_workflow():
    st.session_state.setup_done = False
    st.session_state.browser_done = False
    st.session_state.geotraitement_done = False
    st.session_state.carte_done = False
    st.session_state.upload_done = False


# ============================================================
# CHEMINS
# ============================================================

app_dir = Path(__file__).resolve().parent
clients_dir = app_dir / "data" / "Dossier_clients"


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("⚙️ Workflow")

st.sidebar.markdown("---")

# Etat Setup
if st.session_state.setup_done:
    st.sidebar.success("✅ 1. Setup terminé")
else:
    st.sidebar.warning("⏳ 1. Setup")

# Etat Browser
if st.session_state.browser_done:
    st.sidebar.success("✅ 2. Scan satellite terminé")
elif st.session_state.setup_done:
    st.sidebar.warning("⏳ 2. Scan satellite")
else:
    st.sidebar.error("🔒 2. Scan satellite verrouillé")

# Etat Geotraitement
if st.session_state.geotraitement_done:
    st.sidebar.success("✅ 3. Géotraitement terminé")
elif st.session_state.browser_done:
    st.sidebar.warning("⏳ 3. Géotraitement")
else:
    st.sidebar.error("🔒 3. Géotraitement verrouillé")

# Etat Carte
if st.session_state.carte_done:
    st.sidebar.success("✅ 4. Carte générée")
elif st.session_state.geotraitement_done:
    st.sidebar.warning("⏳ 4. Carte")
else:
    st.sidebar.error("🔒 4. Carte verrouillée")

# Etat Upload
if st.session_state.upload_done:
    st.sidebar.success("✅ 5. Upload B2 terminé")
elif st.session_state.geotraitement_done:
    st.sidebar.warning("⏳ 5. Upload B2")
else:
    st.sidebar.error("🔒 5. Upload B2 verrouillé")

st.sidebar.markdown("---")


# ============================================================
# BOUTON RELANCER L'ENVIRONNEMENT
# ============================================================

if st.sidebar.button("🔄 Relancer l'environnement"):

    reset_workflow()

    with st.spinner("Relance du conteneur principal..."):

        try:
            success = relancer_conteneur_principal()

            if success:
                st.sidebar.success(
                    "✅ Conteneur relancé."
                )

                time.sleep(2)
                

            else:
                st.sidebar.error(
                    "❌ Échec de la relance. Vérifiez les logs."
                )

        except Exception as e:

            st.sidebar.error(
                f"❌ Erreur lors de la relance : {e}"
            )


# ============================================================
# TITRE PRINCIPAL
# ============================================================

st.title("🌍 GROUND WATER FINDER")

st.markdown(
    """
    ### Pipeline de traitement

    **1️⃣ Setup → 2️⃣ Scan satellite → 3️⃣ Géotraitement → 4️⃣ Carte → 5️⃣ Upload B2**
    """
)

st.markdown("---")


# ============================================================
# IMPORTS POUR LES ONGLETS
# ============================================================

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


# ============================================================
# CREATION DES ONGLETS
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🛠️ 1. Configuration & Extraction",
    "🛰️ 2. Scan satellites",
    "💧 3. Geotraitement",
    "🗺️ 4. Carte de prospection",
    "☁️ 5. Upload B2"
])


# ============================================================
# ONGLET 1 : SETUP
# ============================================================

with tab1:

    st.header("🛠️ Configuration & Extraction")

    if st.session_state.setup_done:

        st.success(
            "✅ Le Setup est déjà terminé."
        )

        st.info(
            "Vous pouvez maintenant passer à l'onglet "
            "« 🛰️ Scan satellites »."
        )

    else:

        # IMPORTANT :
        # create_streamlit_app() contient le traitement complet
        # du Setup. Il est donc appelé uniquement ici.

        utils_setup.create_streamlit_app()

        # ----------------------------------------------------
        # Vérification après traitement
        # ----------------------------------------------------

        # On cherche les dossiers clients
        if clients_dir.exists():

            clients = [
                d for d in clients_dir.iterdir()
                if d.is_dir()
            ]

            # Si un dossier client existe, on vérifie
            # qu'il contient les fichiers GPX nécessaires.

            setup_valid = False

            for client in clients:

                a_convertir = (
                    client /
                    "OUTPUT" /
                    "A_convertir"
                )

                if a_convertir.exists():

                    gpx_files = list(
                        a_convertir.glob("*.gpx")
                    )

                    if gpx_files:

                        setup_valid = True
                        break

            if setup_valid:

                st.session_state.setup_done = True

                st.success(
                    "🎉 SETUP TERMINÉ AVEC SUCCÈS"
                )

                st.info(
                    "➡️ Le scan satellite est maintenant disponible."
                )

                


# ============================================================
# ONGLET 2 : SCAN SATELLITE
# ============================================================

with tab2:

    st.header("🛰️ Scan satellites")

    # --------------------------------------------------------
    # VERROUILLAGE
    # --------------------------------------------------------

    if not st.session_state.setup_done:

        st.error(
            "🔒 SCAN SATELLITE VERROUILLÉ"
        )

        st.warning(
            "Vous devez terminer le Setup avant de lancer "
            "le scan satellite."
        )

    elif st.session_state.browser_done:

        st.success(
            "✅ Le scan satellite est déjà terminé."
        )

        st.info(
            "➡️ Vous pouvez maintenant passer au géotraitement."
        )

    else:

        st.success(
            "✅ Setup terminé. Le scan satellite peut commencer."
        )

        if st.button(
            "🚀 Lancer le scan satellite",
            key="launch_browser"
        ):

            try:

                from utils import utils_browser

                with st.spinner(
                    "🛰️ Scan satellite en cours..."
                ):

                    utils_browser.run_streamlit_app()

                # ------------------------------------------------
                # Vérification des résultats Browser
                # ------------------------------------------------

                if not clients_dir.exists():

                    raise RuntimeError(
                        "Le dossier clients n'existe pas après "
                        "le scan satellite."
                    )

                # On recherche les fichiers produits
                fichiers_trouves = []

                for client in clients_dir.iterdir():

                    if not client.is_dir():
                        continue

                    output = client / "OUTPUT"

                    if output.exists():

                        for f in output.rglob("*"):

                            if f.is_file():
                                fichiers_trouves.append(f)

                if not fichiers_trouves:

                    raise RuntimeError(
                        "Le scan semble terminé mais aucun "
                        "fichier résultat n'a été trouvé."
                    )

                st.session_state.browser_done = True

                st.success(
                    "✅ SCAN SATELLITE TERMINÉ AVEC SUCCÈS"
                )

                st.info(
                    "➡️ Le géotraitement est maintenant disponible."
                )

                

            except Exception as e:

                st.error(
                    f"❌ Erreur pendant le scan satellite : {e}"
                )

                st.code(
                    traceback.format_exc()
                )


# ============================================================
# ONGLET 3 : GEOTRAITEMENT
# ============================================================

with tab3:

    st.header("💧 Géotraitement")

    # --------------------------------------------------------
    # VERROUILLAGE
    # --------------------------------------------------------

    if not st.session_state.setup_done:

        st.error(
            "🔒 GÉOTRAITEMENT VERROUILLÉ"
        )

        st.warning(
            "Le Setup doit être terminé avant le géotraitement."
        )

    elif not st.session_state.browser_done:

        st.error(
            "🔒 GÉOTRAITEMENT VERROUILLÉ"
        )

        st.warning(
            "Le scan satellite doit être terminé avant "
            "de lancer le géotraitement."
        )

    elif st.session_state.geotraitement_done:

        st.success(
            "✅ Le géotraitement est déjà terminé."
        )

        st.info(
            "➡️ Vous pouvez consulter la carte de prospection."
        )

    else:

        from utils.utils_geotraitement import (
            detecter_client_unique,
            initialiser_client,
            traiter_complet,
            exporter_resultats
        )

        st.success(
            "✅ Setup terminé"
        )

        st.success(
            "✅ Scan satellite terminé"
        )

        st.info(
            "Le géotraitement peut maintenant être lancé."
        )

        if st.button(
            "🚀 Lancer le géotraitement",
            key="launch_geotraitement"
        ):

            try:

                with st.spinner(
                    "💧 Géotraitement en cours..."
                ):

                    client_nom = detecter_client_unique()

                    if not client_nom:

                        raise RuntimeError(
                            "Aucun client détecté."
                        )

                    st.info(
                        f"📁 Client : **{client_nom}**"
                    )

                    initialiser_client(client_nom)

                    resultats = traiter_complet()

                    exporter_resultats(resultats)

                # ------------------------------------------------
                # Vérification des résultats
                # ------------------------------------------------

                client_dir = (
                    clients_dir /
                    client_nom
                )

                rendu_dir = client_dir / "RENDU"

                if not rendu_dir.exists():

                    raise RuntimeError(
                        "Le dossier RENDU n'a pas été créé."
                    )

                fichiers_rendu = list(
                    rendu_dir.rglob("*")
                )

                fichiers_rendu = [
                    f for f in fichiers_rendu
                    if f.is_file()
                ]

                if not fichiers_rendu:

                    raise RuntimeError(
                        "Le géotraitement est terminé mais "
                        "aucun fichier résultat n'a été trouvé."
                    )

                st.session_state.geotraitement_done = True

                st.success(
                    "🎉 GÉOTRAITEMENT TERMINÉ AVEC SUCCÈS"
                )

                st.json({
                    k: (
                        len(v)
                        if isinstance(v, list)
                        else bool(v)
                    )
                    for k, v in resultats.items()
                })

                st.info(
                    "➡️ La carte et l'upload B2 sont maintenant disponibles."
                )

                

            except Exception as e:

                st.error(
                    f"❌ Erreur pendant le géotraitement : {e}"
                )

                st.code(
                    traceback.format_exc()
                )


# ============================================================
# ONGLET 4 : CARTE DE PROSPECTION
# ============================================================

with tab4:

    st.header("🗺️ Carte de prospection")

    # --------------------------------------------------------
    # VERROUILLAGE
    # --------------------------------------------------------

    if not st.session_state.geotraitement_done:

        st.error(
            "🔒 CARTE VERROUILLÉE"
        )

        st.warning(
            "Le géotraitement doit être terminé avant "
            "de générer la carte."
        )

    else:

        try:

            dossier_client, nom_client = choisir_dossier_client()

            input_dir = dossier_client / "INPUT"
            dossier_rendu = dossier_client / "RENDU"

            # ------------------------------------------------
            # Recherche du contour
            # ------------------------------------------------

            contour_path = None

            if input_dir.exists():

                contour_files = [
                    f for f in input_dir.iterdir()
                    if f.suffix.lower()
                    in [".gpx", ".kml", ".kmz"]
                ]

                if contour_files:

                    contour_path = contour_files[0]

                    st.info(
                        f"📁 Contour trouvé dans INPUT : "
                        f"{contour_path.name}"
                    )

            # Fallback SHP
            if contour_path is None:

                contour_shp = (
                    dossier_rendu /
                    "CONTOUR.shp"
                )

                if contour_shp.exists():

                    contour_path = contour_shp

                    st.info(
                        "📁 Fallback : CONTOUR.shp"
                    )

            if contour_path is None:

                raise RuntimeError(
                    "Aucun fichier contour trouvé."
                )

            # ------------------------------------------------
            # Chargement du contour
            # ------------------------------------------------

            if contour_path.suffix.lower() == ".shp":

                contour_gdf = (
                    gpd.read_file(
                        contour_path
                    ).to_crs(epsg=3857)
                )

            else:

                contour_poly = load_contour(
                    contour_path
                )

                contour_gdf = (
                    gpd.GeoDataFrame(
                        geometry=[contour_poly],
                        crs="EPSG:4326"
                    )
                    .to_crs(epsg=3857)
                )

            # ------------------------------------------------
            # Chargement des couches
            # ------------------------------------------------

            couches = {
                "contour": contour_gdf,
                "lines": None,
                "dolines": None,
                "intersections": None
            }

            if dossier_rendu.exists():

                for f in dossier_rendu.glob("*"):

                    if f.suffix.lower() in (
                        ".shp",
                        ".gpx",
                        ".kml",
                        ".kmz"
                    ):

                        gdf = charger_couche(f)

                        if (
                            gdf is not None
                            and not gdf.empty
                        ):

                            gdf = gdf.to_crs(3857)

                            name = f.stem.lower()

                            if (
                                "lignes" in name
                                or "lines" in name
                            ):
                                couches["lines"] = gdf

                            elif "dolines" in name:

                                couches["dolines"] = gdf

                            elif "intersections" in name:

                                couches["intersections"] = gdf

            # ------------------------------------------------
            # Création de la carte
            # ------------------------------------------------

            fig, ax = plt.subplots(
                figsize=(14, 12)
            )

            handles = []

            # Fractures
            if couches["lines"] is not None:

                couches["lines"].plot(
                    ax=ax,
                    color="orange",
                    linewidth=3,
                    linestyle="--",
                    alpha=0.8,
                    zorder=6
                )

            handles.append(
                mpatches.Patch(
                    facecolor="orange",
                    label="Fractures identifiées"
                )
            )

            # Dolines
            if couches["dolines"] is not None:

                couches["dolines"].plot(
                    ax=ax,
                    color="blue",
                    markersize=60,
                    marker="o",
                    alpha=0.5,
                    edgecolor="white",
                    linewidth=1,
                    zorder=4
                )

            handles.append(
                mpatches.Patch(
                    facecolor="blue",
                    label="Dolines"
                )
            )

            # Contour
            if couches["contour"] is not None:

                couches["contour"].plot(
                    ax=ax,
                    facecolor="none",
                    edgecolor="chocolate",
                    linewidth=3,
                    alpha=0.9,
                    zorder=5
                )

            handles.append(
                mpatches.Patch(
                    facecolor="none",
                    edgecolor="chocolate",
                    label="Surface prospectée"
                )
            )

            # Points de forage
            if couches["intersections"] is not None:

                couches["intersections"].plot(
                    ax=ax,
                    color="red",
                    markersize=100,
                    marker="^",
                    edgecolor="black",
                    linewidth=1.5,
                    alpha=0.9,
                    zorder=7
                )

                handles.append(
                    mpatches.Patch(
                        facecolor="red",
                        label="Points de forage"
                    )
                )

            # ------------------------------------------------
            # Fond Google / OSM
            # ------------------------------------------------

            try:

                ctx.add_basemap(
                    ax,
                    source=(
                        "http://mt1.google.com/vt/"
                        "lyrs=y&x={x}&y={y}&z={z}"
                    ),
                    crs="EPSG:3857"
                )

            except Exception:

                try:

                    ctx.add_basemap(
                        ax,
                        source=ctx.providers.OpenStreetMap.Mapnik,
                        crs="EPSG:3857"
                    )

                except Exception:

                    ax.set_facecolor(
                        "#e8f4f8"
                    )

            ax.set_axis_off()

            ax.set_title(
                f"🗺️ Projet {nom_client}",
                fontsize=18,
                weight="bold"
            )

            ax.legend(
                handles=handles,
                loc="lower left",
                fontsize=10,
                framealpha=0.95
            )

            plt.tight_layout()

            # ------------------------------------------------
            # Sauvegarde carte
            # ------------------------------------------------

            rapport_dir = (
                dossier_rendu /
                f"Rapport_{nom_client}"
            )

            rapport_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            carte_path = (
                rapport_dir /
                "carte_prospection.png"
            )

            fig.savefig(
                carte_path,
                dpi=150,
                bbox_inches="tight",
                facecolor="white"
            )

            st.pyplot(
                fig,
                clear_figure=True
            )

            plt.close(fig)

            # ------------------------------------------------
            # Création structure Data
            # ------------------------------------------------

            data_dir = rapport_dir / "Data"

            for sub in [
                "SHP",
                "GPX",
                "KML",
                "KMZ",
                "Convertir"
            ]:

                (
                    data_dir / sub
                ).mkdir(
                    parents=True,
                    exist_ok=True
                )

            # ------------------------------------------------
            # Copie SHP
            # ------------------------------------------------

            for f in dossier_rendu.glob("*.shp"):

                base = f.stem

                for ext in [
                    ".shp",
                    ".shx",
                    ".dbf",
                    ".prj",
                    ".cpg"
                ]:

                    src = (
                        dossier_rendu /
                        f"{base}{ext}"
                    )

                    if src.exists():

                        shutil.copy(
                            src,
                            data_dir /
                            "SHP" /
                            src.name
                        )

            # ------------------------------------------------
            # Journal
            # ------------------------------------------------

            generer_journal(
                couches,
                rapport_dir /
                "journal.txt"
            )

            # ------------------------------------------------
            # Convertir
            # ------------------------------------------------

            convertir_src = (
                dossier_client /
                "OUTPUT" /
                "Convertir"
            )

            if convertir_src.exists():

                shutil.copytree(
                    convertir_src,
                    data_dir / "Convertir",
                    dirs_exist_ok=True
                )

            # ------------------------------------------------
            # KML / GPX / KMZ
            # ------------------------------------------------

            target = {
                "kml": data_dir / "KML",
                "kmz": data_dir / "KMZ",
                "gpx": data_dir / "GPX"
            }

            for nom, gdf in couches.items():

                if gdf is not None:

                    shp_to_kml_gpx_kmz(
                        gdf,
                        f"{nom_client}_{nom}",
                        target
                    )

            # ------------------------------------------------
            # ZIP
            # ------------------------------------------------

            zip_path = (
                dossier_rendu /
                f"{nom_client}.zip"
            )

            shutil.make_archive(
                str(zip_path.with_suffix("")),
                "zip",
                rapport_dir
            )

            st.success(
                f"✅ ZIP généré : {zip_path.name}"
            )

            st.session_state.carte_done = True

        except Exception as e:

            st.error(
                f"❌ Erreur lors de la création de la carte : {e}"
            )

            st.code(
                traceback.format_exc()
            )


# ============================================================
# ONGLET 5 : UPLOAD BACKBLAZE B2
# ============================================================

with tab5:

    st.header("☁️ Upload automatique vers Backblaze B2")

    # --------------------------------------------------------
    # VERROUILLAGE
    # --------------------------------------------------------

    if not st.session_state.geotraitement_done:

        st.error(
            "🔒 UPLOAD B2 VERROUILLÉ"
        )

        st.warning(
            "Le géotraitement doit être terminé avant "
            "l'upload vers Backblaze B2."
        )

    elif st.session_state.upload_done:

        st.success(
            "✅ Upload B2 déjà terminé."
        )

    else:

        st.success(
            "✅ Toutes les étapes précédentes sont terminées."
        )

        st.info(
            "Les fichiers ZIP sont prêts à être envoyés "
            "vers le bucket **ground-water-finder**."
        )

        # IMPORTANT :
        # L'upload ne démarre QUE lorsque l'utilisateur
        # clique sur le bouton.

        if st.button(
            "☁️ Lancer l'upload vers Backblaze B2",
            key="launch_upload"
        ):

            old_stdout = sys.stdout
            sys.stdout = StringIO()

            try:

                from utils import utils_upload_b2

                with st.spinner(
                    "☁️ Upload vers Backblaze B2 en cours..."
                ):

                    utils_upload_b2.main()

                logs = sys.stdout.getvalue()

                st.session_state.upload_done = True

                st.success(
                    "🎉 UPLOAD B2 TERMINÉ AVEC SUCCÈS"
                )

                st.text_area(
                    "Logs d'upload",
                    logs,
                    height=300
                )

            except Exception as e:

                logs = sys.stdout.getvalue()

                st.error(
                    f"❌ Erreur pendant l'upload : {e}"
                )

                if logs:

                    st.text_area(
                        "Logs",
                        logs,
                        height=300
                    )

                st.code(
                    traceback.format_exc()
                )

            finally:

                sys.stdout = old_stdout


# ============================================================
# RESUME DU WORKFLOW
# ============================================================

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Progression")

etapes = [
    st.session_state.setup_done,
    st.session_state.browser_done,
    st.session_state.geotraitement_done,
    st.session_state.carte_done,
    st.session_state.upload_done
]

terminees = sum(etapes)

st.sidebar.progress(
    terminees / len(etapes)
)

st.sidebar.write(
    f"**{terminees}/5 étapes terminées**"
)