# app_combined.py
import streamlit as st
from pathlib import Path
import sys
from io import StringIO
from utils import utils_setup


# 🧹 CLEAN STARTUP - suppression des fichiers résiduels
def clean_startup():
    from pathlib import Path
    import shutil

    app_dir = Path(__file__).resolve().parent
    clients_dir = app_dir / "data" / "Dossier_clients"

    # Nettoyage dossier clients
    if clients_dir.exists():
        for item in clients_dir.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception as e:
                print(f"Erreur nettoyage: {e}")

clean_startup()

st.set_page_config(page_title="Ground Water Finder - Outils combinés", layout="wide")

# Imports pour l'onglet 5 (upload)
from utils.utils_export import choisir_dossier_client  # utilisé seulement pour la vérification

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
    # Onglet Scan satellites – isolation complète
    st.title("🛰️ Scan satellites")
    app_dir = Path(__file__).resolve().parent
    clients_dir = app_dir / "data" / "Dossier_clients"
    if not clients_dir.exists() or not any(clients_dir.iterdir()):
        st.error("❌ Aucun dossier client trouvé. Veuillez d'abord exécuter l'onglet **Configuration**.")
    else:
        from utils import utils_browser
        # On force l'exécution dans un conteneur Streamlit propre
        with st.container():
            utils_browser.run_streamlit_app()

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

with tab4:
    # Onglet Carte de prospection – appelle directement utils_export.main()
    from utils.utils_export import main as carte_main
    carte_main()

with tab5:
    app_dir = Path(__file__).resolve().parent
    clients_dir = app_dir / "data" / "Dossier_clients"
    if not clients_dir.exists() or not any(clients_dir.iterdir()):
        st.error("❌ Aucun dossier client trouvé.")
    else:
        st.title("☁️ Upload automatique vers Backblaze B2")
        st.markdown("Upload de tous les fichiers ZIP des clients vers le bucket **`ground-water-finder`**.")

        # Capturer la sortie standard pour afficher les logs
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