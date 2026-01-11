# utils/security.py - VERSION CORRIGÉE
"""
Fonctions de sécurité basiques pour le projet.
"""

import os
import re
import streamlit as st
from pathlib import Path


def validate_uploaded_file(uploaded_file):
    """
    Valide un fichier uploadé
    """
    # VALEURS PAR DÉFAUT - PAS DE st.secrets
    allowed_ext = ['.gpx', '.kml', '.kmz']  # Extensions acceptées
    max_size_mb = 50  # Taille max en MB
    
    # Vérifier l'extension
    filename = uploaded_file.name.lower()
    if not any(filename.endswith(ext) for ext in allowed_ext):
        return False, f"Seuls {', '.join(allowed_ext)} sont autorisés"
    
    # Vérifier la taille
    max_size = max_size_mb * 1024 * 1024
    if uploaded_file.size > max_size:
        return False, f"Fichier trop volumineux (> {max_size_mb}MB)"
    
    # Vérifier que c'est un vrai GPX/KML
    if filename.endswith('.gpx'):
        try:
            content = uploaded_file.getvalue().decode('utf-8', errors='ignore')
            if '<gpx' not in content:
                return False, "Fichier GPX invalide"
        except:
            return False, "Erreur de lecture du fichier GPX"
    
    return True, "Fichier valide"


def get_safe_filename(filename):
    """
    Nettoie un nom de fichier pour éviter les injections
    """
    # Garder uniquement caractères sûrs
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    # Limiter la longueur
    safe_name = safe_name[:100]
    return safe_name


def validate_email(email):
    """
    Valide une adresse email basique
    """
    if not email:
        return False, "Email vide"
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Format d'email invalide"
    
    return True, "Email valide"


def validate_phone(phone):
    """
    Valide un numéro de téléphone français basique
    """
    if not phone:
        return False, "Téléphone vide"
    
    # Nettoyer
    clean_phone = re.sub(r'[\s\-\.\(\)]', '', phone)
    
    # Format français
    pattern = r'^(?:\+33|0)[1-9](?:\d{2}){4}$'
    if not re.match(pattern, clean_phone):
        return False, "Format téléphone invalide (ex: 0612345678)"
    
    return True, "Téléphone valide"


def sanitize_path(path):
    """
    Nettoie un chemin pour éviter les path traversal
    """
    # Supprimer les ../
    clean_path = re.sub(r'\.\./', '', str(path))
    # Remplacer les caractères dangereux
    clean_path = re.sub(r'[\\/*?:"<>|]', '_', clean_path)
    return Path(clean_path)