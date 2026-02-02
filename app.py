import streamlit as st
import asyncio
import sys
import os
import shutil
import time
from datetime import datetime

# Configuration de la page
st.set_page_config(
    page_title="🌍 Ground Water Finder",
    page_icon="🌍",
    layout="wide"
)

# Initialisation de l'état
if "setup_finished" not in st.session_state:
    st.session_state["setup_finished"] = False
if "current_step" not in st.session_state:
    st.session_state["current_step"] = "setup"
if "processing_started" not in st.session_state:
    st.session_state["processing_started"] = False
if "processing_complete" not in st.session_state:
    st.session_state["processing_complete"] = False

# ============================================
# ÉTAPE 1: SETUP (obligatoire en premier)
# ============================================
if not st.session_state["setup_finished"]:
    st.title("🌍 Ground Water Finder - Configuration")
    
    from utils.utils_setup import create_streamlit_app
    
    # Votre code original exactement
    create_streamlit_app()
    
    # Si on arrive ici, utils_setup a TERMINÉ
    st.session_state["setup_finished"] = True
    st.session_state["current_step"] = "processing"
    st.session_state["processing_started"] = True
    st.rerun()

# ============================================
# TRAITEMENT AUTOMATIQUE COMPLET
# ============================================
elif st.session_state["processing_started"] and not st.session_state["processing_complete"]:
    st.title("🌍 Ground Water Finder - Traitement en cours")
    
    # Barre de progression
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Variable pour stocker le nom du client
    nom_client = None
    
    # Étape 1: Scan satellites
    status_text.text("🛰️ Étape 1/4 : Scan satellites...")
    progress_bar.progress(25)
    
    try:
        from utils.utils_browser import process_all_gpx
        
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        asyncio.run(process_all_gpx())
        st.success("✅ Scan satellites terminé")
    except Exception as e:
        st.error(f"❌ Erreur scan satellites: {e}")
        st.stop()
    
    # Étape 2: Traitement géospatial
    status_text.text("🗺️ Étape 2/4 : Traitement géospatial...")
    progress_bar.progress(50)
    
    try:
        from utils import utils_geotraitement as geo
        
        # Détection automatique du client
        nom_client = geo.detecter_client_unique()
        
        # Initialisation du client
        geo.initialiser_client(nom_client)
        
        # Traitement
        resultats = geo.traiter_complet()
        geo.exporter_resultats(resultats)
        st.success("✅ Traitement géospatial terminé")
    except Exception as e:
        st.error(f"❌ Erreur traitement géospatial: {e}")
        st.stop()
    
    # Étape 3: Export - Utiliser utils_export pour créer le ZIP complet
    status_text.text("📊 Étape 3/4 : Export des résultats...")
    progress_bar.progress(75)
    
    try:
        # Sauvegarder le nom du client et le message
        st.session_state["nom_client"] = nom_client
        st.session_state["mail_message"] = """### ℹ️ Information importante

L'obtention du rapport complet est disponible sur demande
en écrivant à :

📧 **m2techsecretariat@gmail.com**

_Vous recevrez le rapport détaillé avec toutes les analyses géospatiales._"""
        
        # Créer un dossier temporaire pour la carte
        temp_dir = "./temp_cartes"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Capturer la sortie de utils_export
        import io
        from contextlib import redirect_stdout, redirect_stderr
        
        output_buffer = io.StringIO()
        
        with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
            from utils import utils_export
            utils_export.main()
        
        # Récupérer le chemin de la carte créée par utils_export
        BASE_CLIENTS = "./data/Dossier_clients"
        dossier_client = os.path.join(BASE_CLIENTS, nom_client)
        dossier_RENDU = os.path.join(dossier_client, "RENDU")
        rapport_dir = os.path.join(dossier_RENDU, f"Rapport_{nom_client}")
        carte_source = os.path.join(rapport_dir, "carte_prospection.png")
        
        if os.path.exists(carte_source):
            # Copier la carte vers le dossier temporaire
            carte_dest = os.path.join(temp_dir, f"carte_{nom_client}.png")
            shutil.copy2(carte_source, carte_dest)
            st.session_state["carte_sauvegardee"] = carte_dest
            st.success("✅ Export terminé - ZIP complet créé avec utils_export")
        else:
            # Fallback: créer une carte simple
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.text(0.5, 0.5, f"Carte de prospection - {nom_client}\n\nLe rapport complet est dans le ZIP", 
                   ha='center', va='center', fontsize=16, transform=ax.transAxes)
            ax.set_axis_off()
            carte_dest = os.path.join(temp_dir, f"carte_{nom_client}.png")
            fig.savefig(carte_dest, dpi=150, bbox_inches='tight')
            plt.close(fig)
            st.session_state["carte_sauvegardee"] = carte_dest
            st.success("✅ Export terminé - ZIP créé (carte simplifiée)")
        
    except Exception as e:
        st.error(f"❌ Erreur export: {e}")
        st.stop()
    
    # Étape 4: Upload B2
    status_text.text("☁️ Étape 4/4 : Upload vers Backblaze B2...")
    progress_bar.progress(100)
    
    try:
        # Attendre un peu pour être sûr que le ZIP est créé
        time.sleep(2)
        
        # Upload avec suppression du dossier
        from utils.utils_upload_b2 import main as upload_main
        results = upload_main(delete_folder=True)
        
        if results:
            success_count = sum(1 for r in results if r.get('success', False))
            st.success(f"✅ {success_count}/{len(results)} fichier(s) uploadé(s) vers B2")
        else:
            st.warning("⚠️ Aucun résultat d'upload")
            
    except Exception as e:
        st.error(f"❌ Erreur upload B2: {e}")
    
    # Marquer le traitement comme terminé
    st.session_state["processing_complete"] = True
    st.rerun()

# ============================================
# AFFICHAGE FINAL (après traitement complet)
# ============================================
elif st.session_state["processing_complete"]:
    st.title("🗺️ Carte de prospection – Affichage complet")
    
    # Vérifier si la carte a été sauvegardée
    if "carte_sauvegardee" in st.session_state and os.path.exists(st.session_state["carte_sauvegardee"]):
        try:
            # Afficher la carte sauvegardée
            import matplotlib.pyplot as plt
            import matplotlib.image as mpimg
            
            fig, ax = plt.subplots(figsize=(14, 12))
            img = mpimg.imread(st.session_state["carte_sauvegardee"])
            ax.imshow(img)
            ax.set_axis_off()
            ax.set_title(f"🗺️ Carte de prospection – Projet {st.session_state.get('nom_client', 'Client')}", 
                        fontsize=18, weight='bold')
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
            
            # Afficher le message
            st.markdown("---")
            st.success("🎉 **Traitement complet terminé avec succès ! Le dossier client a été supprimé après l'upload.**")
            
            # Afficher le message mail depuis la session
            mail_message = st.session_state.get("mail_message", """### ℹ️ Information importante

L'obtention du rapport complet est disponible sur demande
en écrivant à :

📧 **m2techsecretariat@gmail.com**

_Vous recevrez le rapport détaillé avec toutes les analyses géospatiales._""")
            
            st.markdown(mail_message)
            
            # Nettoyer le fichier temporaire après affichage
            try:
                os.remove(st.session_state["carte_sauvegardee"])
                # Nettoyer le dossier temp s'il est vide
                temp_dir = "./temp_cartes"
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except:
                pass
                
        except Exception as e:
            st.error(f"❌ Erreur d'affichage de la carte: {e}")
            # Afficher quand même le message
            st.markdown("---")
            st.success("🎉 **Traitement complet terminé avec succès !**")
            st.markdown(st.session_state.get("mail_message", "📧 m2techsecretariat@gmail.com"))
    else:
        # Fallback si la carte n'est pas sauvegardée
        st.markdown("---")
        st.success("🎉 **Traitement complet terminé avec succès ! Le dossier client a été supprimé après l'upload.**")
        
        mail_message = """### ℹ️ Information importante

L'obtention du rapport complet est disponible sur demande
en écrivant à :

📧 **m2techsecretariat@gmail.com**

_Vous recevrez le rapport détaillé avec toutes les analyses géospatiales._"""
        
        st.markdown(mail_message)

# ============================================
# PIED DE PAGE
# ============================================
st.markdown("---")
st.caption(f"🌍 Ground Water Finder | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")