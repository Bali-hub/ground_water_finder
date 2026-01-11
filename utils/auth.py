# utils/auth.py - VERSION SIMPLE AVEC MOT DE PASSE
import streamlit as st
import time

def check_password():
    """Fonction d'authentification simple avec mot de passe en clair"""
    
    # Vérifier si l'authentification est activée
    try:
        # Si secrets.toml n'est pas configuré, permettre l'accès
        if "ui" not in st.secrets:
            return True
            
        if not st.secrets["ui"].get("enable_password", False):
            return True
    except:
        # En cas d'erreur de lecture des secrets, permettre l'accès
        return True
    
    # Vérifier si le mot de passe est défini
    try:
        plain_password = st.secrets["auth"].get("plain_password", "")
        if not plain_password:
            return True
    except:
        plain_password = "admin"  # Mot de passe par défaut
    
    # Initialisation du compteur de tentatives
    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = 0
        st.session_state.last_attempt = 0
    
    # Protection contre attaques force brute
    current_time = time.time()
    if st.session_state.login_attempts >= 3:
        if current_time - st.session_state.last_attempt < 300:  # 5 minutes
            wait_time = int(300 - (current_time - st.session_state.last_attempt))
            st.error(f"⏳ Trop de tentatives. Réessayez dans {wait_time} secondes.")
            return False
    
    # Si déjà authentifié
    if "authenticated" in st.session_state and st.session_state.authenticated:
        return True
    
    # Interface d'authentification
    st.title("🔐 GROUND WATER FINDER - AUTHENTIFICATION")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("#### Accès sécurisé")
        st.caption("Entrez le mot de passe administrateur")
        
        password = st.text_input(
            "Mot de passe :",
            type="password",
            key="password_input",
            label_visibility="collapsed"
        )
        
        if st.session_state.login_attempts > 0:
            st.warning(f"Tentative {st.session_state.login_attempts}/3")
        
        if st.button("🚪 Se connecter", type="primary", use_container_width=True):
            if password == plain_password:
                st.session_state.authenticated = True
                st.session_state.login_attempts = 0
                st.success("✅ Authentification réussie !")
                time.sleep(1)  # Petite pause pour voir le message
                st.rerun()
            else:
                st.session_state.login_attempts += 1
                st.session_state.last_attempt = current_time
                st.error("❌ Mot de passe incorrect")
    
    st.markdown("---")
    st.caption("© Ground Water Finder - Application hydrogéologique sécurisée")
    
    return False