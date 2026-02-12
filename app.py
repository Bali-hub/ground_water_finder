import streamlit as st
import asyncio
import sys
import os
import shutil
import time
from datetime import datetime
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

st.set_page_config(
    page_title="🌍 Ground Water Finder",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": "mailto:m2techsecretariat@gmail.com",
        "Report a bug": "mailto:m2techsecretariat@gmail.com",
        "About": "Ground Water Finder - Analyse géospatiale des eaux souterraines",
    },
)

# ============================================
# DOSSIERS FIXES – COHÉRENTS AVEC LES VOLUMES
# ============================================
BASE_CLIENTS = "/app/data/Dossier_clients"  # ← point de montage du volume
TEMP_DIR = os.path.join(
    os.path.expanduser("~"), "temp_cartes"
)  # /home/appuser/temp_cartes
os.makedirs(TEMP_DIR, exist_ok=True)

# ============================================
# CSS RESPONSIVE – RECOPIEZ ICI VOTRE CODE CSS COMPLET
# ============================================
st.markdown(
    """
<style>
    /* INSÉREZ L'INTÉGRALITÉ DE VOTRE CSS */
</style>
""",
    unsafe_allow_html=True,
)


# ============================================
# FONCTIONS UTILITAIRES
# ============================================
def nettoyer_avant_demarrage():
    """NETTOYAGE AU DÉMARRAGE DU CONTENEUR – supprime TOUS les anciens dossiers clients."""
    print("🧹 Nettoyage avant démarrage...")

    # Créer le dossier parent si nécessaire
    os.makedirs(BASE_CLIENTS, exist_ok=True)

    # 1️⃣ Supprimer tous les sous-dossiers clients
    for item in os.listdir(BASE_CLIENTS):
        item_path = os.path.join(BASE_CLIENTS, item)
        if os.path.isdir(item_path):
            try:
                shutil.rmtree(item_path)
                print(f"✅ Dossier client supprimé: {item_path}")
            except Exception as e:
                print(f"⚠️ Impossible de supprimer {item_path}: {e}")

    # 2️⃣ Nettoyer les dossiers temporaires
    dossiers_temp = [TEMP_DIR, "./temp_maps", "./data/Dossier_clients/temp"]
    for dossier in dossiers_temp:
        if os.path.exists(dossier):
            try:
                shutil.rmtree(dossier)
                print(f"✅ Nettoyé: {dossier}")
            except Exception as e:
                print(f"⚠️ Impossible de nettoyer {dossier}: {e}")

    # 3️⃣ Supprimer les fichiers .zip et anciennes cartes
    fichiers_patterns = [
        os.path.join(BASE_CLIENTS, "*.zip"),
        "*.zip",
        os.path.join(TEMP_DIR, "*.png"),
    ]
    import glob

    for pattern in fichiers_patterns:
        for fichier in glob.glob(pattern):
            try:
                os.remove(fichier)
                print(f"✅ Supprimé: {fichier}")
            except:
                pass


def nettoyer_apres_traitement(nom_client):
    """NETTOYAGE APRÈS UPLOAD RÉUSSI – supprime le dossier client et les ZIP, garde la carte."""
    print(f"🧹 Nettoyage après traitement pour {nom_client}...")

    # Supprimer le dossier client spécifique
    dossier_client = os.path.join(BASE_CLIENTS, nom_client)
    if os.path.exists(dossier_client):
        try:
            shutil.rmtree(dossier_client)
            print(f"✅ Dossier client supprimé: {dossier_client}")
        except Exception as e:
            print(f"⚠️ Impossible de supprimer {dossier_client}: {e}")

    # Supprimer les fichiers .zip résiduels dans BASE_CLIENTS
    import glob

    for zip_file in glob.glob(os.path.join(BASE_CLIENTS, "*.zip")):
        try:
            os.remove(zip_file)
            print(f"✅ ZIP supprimé: {zip_file}")
        except:
            pass


def executer_etape(description, fonction, *args):
    try:
        st.info(f"⏳ {description}...")
        result = fonction(*args)
        st.success(f"✅ {description} terminé")
        return result
    except Exception as e:
        st.error(f"❌ Erreur {description}: {str(e)[:100]}")
        raise


# ============================================
# INITIALISATION DE L'ÉTAT – NETTOYAGE AU DÉMARRAGE DU CONTENEUR
# ============================================
if "etat_application" not in st.session_state:
    st.session_state.etat_application = {
        "setup_fini": False,
        "traitement_en_cours": False,
        "traitement_termine": False,
        "etape_actuelle": 0,
        "nom_client": None,
        "carte_sauvegardee": None,
        "erreur": None,
        "demarrage_time": datetime.now(),
        "mail_message": None,
    }
    # 🔥 NETTOYAGE OBLIGATOIRE À CHAQUE DÉMARRAGE DU CONTENEUR
    nettoyer_avant_demarrage()

# ============================================
# ÉTAPE 1: SETUP
# ============================================
if not st.session_state.etat_application["setup_fini"]:
    st.title("🌍 Ground Water Finder - Configuration")
    try:
        if st.query_params.get("mobile", "false") == "true":
            st.markdown(
                """<div class="info-box">📱 Version Mobile<br>Pour une meilleure expérience, utilisez le mode paysage.</div>""",
                unsafe_allow_html=True,
            )
    except:
        pass

    try:
        from utils.utils_setup import create_streamlit_app

        create_streamlit_app()
        st.session_state.etat_application["setup_fini"] = True
        st.session_state.etat_application["traitement_en_cours"] = True
        st.rerun()
    except Exception as e:
        st.error(f"❌ Erreur configuration: {e}")
        st.stop()

# ============================================
# ÉTAPE 2: TRAITEMENT COMPLET + AFFICHAGE FINAL
# ============================================
elif (
    st.session_state.etat_application["traitement_en_cours"]
    and not st.session_state.etat_application["traitement_termine"]
):
    st.title("🌍 Ground Water Finder - Traitement en cours")
    progress_bar = st.progress(0)
    status_text = st.empty()
    nom_client = None

    try:
        # ----- ÉTAPE 1: SCAN SATELLITES -----
        status_text.text("🛰️ Étape 1/4 : Scan satellites...")
        progress_bar.progress(25)
        executer_etape(
            "Scan satellites",
            lambda: asyncio.run(
                (
                    lambda: (
                        asyncio.set_event_loop_policy(
                            asyncio.WindowsSelectorEventLoopPolicy()
                        )
                        if sys.platform == "win32"
                        else None
                    ),
                    __import__("utils.utils_browser").utils_browser.process_all_gpx(),
                )[1]
            ),
        )

        # ----- ÉTAPE 2: TRAITEMENT GÉOSPATIAL -----
        status_text.text("🗺️ Étape 2/4 : Traitement géospatial...")
        progress_bar.progress(50)

        geo = __import__("utils.utils_geotraitement", fromlist=[""])
        nom_client = executer_etape("Détection du client", geo.detecter_client_unique)
        executer_etape("Initialisation client", geo.initialiser_client, nom_client)
        resultats = executer_etape("Traitement géospatial", geo.traiter_complet)
        executer_etape("Export géospatial", geo.exporter_resultats, resultats)
        st.session_state.etat_application["nom_client"] = nom_client

        # ----- ÉTAPE 3: EXPORT -----
        status_text.text("📊 Étape 3/4 : Export des résultats...")
        progress_bar.progress(75)

        st.session_state.etat_application[
            "mail_message"
        ] = """### ℹ️ Information importante

L'obtention du rapport complet est disponible sur demande
en écrivant à :

📧 **m2techsecretariat@gmail.com**

_Vous recevrez le rapport détaillé avec toutes les analyses géospatiales._"""

        temp_dir = TEMP_DIR
        os.makedirs(temp_dir, exist_ok=True)

        import io
        from contextlib import redirect_stdout, redirect_stderr

        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
            from utils import utils_export

            utils_export.main()

        dossier_client = os.path.join(BASE_CLIENTS, nom_client)
        dossier_RENDU = os.path.join(dossier_client, "RENDU")
        rapport_dir = os.path.join(dossier_RENDU, f"Rapport_{nom_client}")
        carte_source = os.path.join(rapport_dir, "carte_prospection.png")

        if os.path.exists(carte_source):
            carte_dest = os.path.join(temp_dir, f"carte_{nom_client}.png")
            shutil.copy2(carte_source, carte_dest)
            st.session_state.etat_application["carte_sauvegardee"] = carte_dest
            st.success("✅ Export terminé - ZIP complet créé avec utils_export")
        else:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(10, 8))
            ax.text(
                0.5,
                0.5,
                f"Carte de prospection - {nom_client}\n\nLe rapport complet est dans le ZIP",
                ha="center",
                va="center",
                fontsize=16,
                transform=ax.transAxes,
            )
            ax.set_axis_off()
            carte_dest = os.path.join(temp_dir, f"carte_{nom_client}.png")
            fig.savefig(carte_dest, dpi=150, bbox_inches="tight")
            plt.close(fig)
            st.session_state.etat_application["carte_sauvegardee"] = carte_dest
            st.success("✅ Export terminé - ZIP créé (carte simplifiée)")

        # ----- ÉTAPE 4: UPLOAD B2 -----
        status_text.text("☁️ Étape 4/4 : Upload vers Backblaze B2...")
        progress_bar.progress(100)
        time.sleep(2)

        from utils.utils_upload_b2 import main as upload_main

        results = upload_main(delete_folder=True)

        if results:
            success_count = sum(1 for r in results if r.get("success", False))
            st.success(
                f"✅ {success_count}/{len(results)} fichier(s) uploadé(s) vers B2"
            )

            # 🔥 NETTOYAGE APRÈS UPLOAD RÉUSSI (dossier client supprimé, carte conservée)
            if success_count > 0:
                nettoyer_apres_traitement(nom_client)
        else:
            st.warning("⚠️ Aucun résultat d'upload")

        # ✅ TRAITEMENT TERMINÉ – AFFICHAGE DIRECT
        st.session_state.etat_application["traitement_termine"] = True
        st.session_state.etat_application["traitement_en_cours"] = False

        # ----- AFFICHAGE FINAL DE LA CARTE (base64) -----
        st.title("🗺️ Carte de prospection")
        carte_path = st.session_state.etat_application.get("carte_sauvegardee")

        if carte_path and os.path.exists(carte_path):
            try:
                import base64

                with open(carte_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                st.markdown(
                    f'<img src="data:image/png;base64,{img_b64}" style="width:100%; max-width:1200px; display:block; margin:auto; border:1px solid #ddd; border-radius:8px;">',
                    unsafe_allow_html=True,
                )
                st.success("🎉 **Traitement complet terminé avec succès !**")
            except Exception as e:
                st.error(f"❌ Erreur affichage : {e}")
        else:
            st.error("⛔ La carte n'a pas été trouvée.")

        st.markdown("---")
        st.markdown(st.session_state.etat_application["mail_message"])

    except Exception as e:
        st.error(f"❌ Erreur traitement: {e}")
        st.session_state.etat_application["erreur"] = str(e)

# ============================================
# ÉTAT FINAL (rafraîchissement de la page)
# ============================================
elif st.session_state.etat_application["traitement_termine"]:
    st.title("🗺️ Carte de prospection")
    carte_path = st.session_state.etat_application.get("carte_sauvegardee")
    if carte_path and os.path.exists(carte_path):
        try:
            import base64

            with open(carte_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            st.markdown(
                f'<img src="data:image/png;base64,{img_b64}" style="width:100%; max-width:1200px; display:block; margin:auto; border:1px solid #ddd; border-radius:8px;">',
                unsafe_allow_html=True,
            )
            st.success("🎉 **Traitement complet terminé avec succès !**")
        except Exception as e:
            st.error(f"❌ Erreur affichage : {e}")
    else:
        st.error("⛔ La carte n'a pas été trouvée.")
    st.markdown("---")
    st.markdown(st.session_state.etat_application.get("mail_message", ""))

# ============================================
# PIED DE PAGE
# ============================================
st.markdown("---")
st.caption(f"🌍 Ground Water Finder | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
