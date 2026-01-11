# utils/translations.py
"""
Dictionnaire central pour les traductions FR/EN de Ground Water Finder.
Clé = identifiant unique en snake_case
Valeur = {"fr": "texte français", "en": "english text"}
"""

TRANSLATIONS = {
    # ============================================
    # PAGE D'ACCUEIL / HOME PAGE
    # ============================================
    "home_title": {"fr": "💧 Ground Water Finder", "en": "💧 Ground Water Finder"},
    "home_subtitle": {"fr": "Application de Prospection Hydrogéologique", "en": "Hydrogeological Prospecting Application"},
    "home_select_language": {"fr": "Sélectionnez votre langue", "en": "Select your language"},
    "home_french_option": {"fr": "🇫🇷 Français", "en": "🇫🇷 French"},
    "home_french_desc": {"fr": "Utiliser l'application en français", "en": "Use the application in French"},
    "home_english_option": {"fr": "🇬🇧 Anglais", "en": "🇬🇧 English"},
    "home_english_desc": {"fr": "Utiliser l'application en anglais", "en": "Use the application in English"},
    "home_footer_line1": {"fr": "Outil professionnel d'analyse hydrogéologique", "en": "Professional hydrogeological analysis tool"},
    "home_footer_line2": {"fr": "Version 1.0 • © 2024", "en": "Version 1.0 • © 2024"},

    # ============================================
    # FORMULAIRE CLIENT / CLIENT FORM
    # ============================================
    "form_email": {"fr": "📧 Email client", "en": "📧 Client email"},
    "form_phone": {"fr": "📞 Téléphone", "en": "📞 Phone number"},
    "form_surface": {"fr": "📐 Surface / description zone", "en": "📐 Area / zone description"},
    "form_upload": {"fr": "📤 Déposer un fichier GPX / KML / KMZ", "en": "📤 Upload a GPX / KML / KMZ file"},
    "form_submit": {"fr": "🚀 Lancer le traitement", "en": "🚀 Start processing"},
    "warning_fields_required": {"fr": "⚠️ Tous les champs sont obligatoires.", "en": "⚠️ All fields are required."},

    # ============================================
    # ETAPES DE TRAITEMENT / PROCESSING STEPS
    # ============================================
    "status_folder_creation": {"fr": "📂 Création des dossiers client...", "en": "📂 Creating client folders..."},
    "status_coords_extraction": {"fr": "📍 Extraction des coordonnées...", "en": "📍 Extracting coordinates..."},
    "status_geojson_conversion": {"fr": "🔄 Conversion GeoJSON → GPX...", "en": "🔄 Converting GeoJSON to GPX..."},
    "scan": {"fr": "🌍 Scan...", "en": "🌍 Scan..."},
    "failed": {"fr": "❌ Échec : {error}", "en": "❌ Failed: {error}"},
    "status_gpx_stabilization": {"fr": "📌 Stabilisation GPX...", "en": "📌 Stabilizing GPX..."},
    "status_geoprocessing": {"fr": "🗺️ Géotraitement final...", "en": "🗺️ Final geoprocessing..."},
    "status_file_organization": {"fr": "📋 Organisation fichiers...", "en": "📋 Organizing files..."},
    "status_map_generation": {"fr": "📊 Génération carte...", "en": "📊 Generating map..."},
    "status_zip_creation": {"fr": "📦 Création archive ZIP...", "en": "📦 Creating ZIP archive..."},
    "status_zip_upload": {"fr": "☁️ Upload vers Backblaze B2...", "en": "☁️ Uploading to Backblaze B2..."},
    "status_success": {"fr": "✅ Traitement terminé", "en": "✅ Processing complete"},

    # ============================================
    # ERREURS / ERROR MESSAGES
    # ============================================
    "error_gpx_none": {"fr": "❌ Aucun fichier GPX trouvé", "en": "❌ No GPX files found"},
    "error_gpx_invalid": {"fr": "❌ GPX invalide ou vide : {filename}", "en": "❌ Invalid or empty GPX: {filename}"},
    "error_not_enough_points": {"fr": "Pas assez de points pour créer un polygone", "en": "Not enough points to create a polygon"},
    "error_b2_upload_failed": {"fr": "❌ Échec de l'upload vers Backblaze B2", "en": "❌ Failed to upload to Backblaze B2"},
    "error_zip_creation_failed": {"fr": "❌ Échec de la création du fichier ZIP", "en": "❌ Failed to create ZIP file"},
    "error_map_generation_failed": {"fr": "❌ Échec de la génération de la carte", "en": "❌ Failed to generate map"},
    "error_general": {"fr": "❌ Une erreur est survenue", "en": "❌ An error occurred"},
    "error_contour": {"fr": "Erreur chargement contour", "en": "Error loading contour"},
    "error_zip": {"fr": "Erreur création ZIP", "en": "Error creating ZIP"},
    "b2_secrets_error": {"fr": "❌ Erreur chargement secrets B2", "en": "❌ Error loading B2 secrets"},

    # ============================================
    # SUCCES / SUCCESS MESSAGES
    # ============================================
    "success_gpx_valid": {"fr": "✅ {count} GPX valides", "en": "✅ {count} valid GPX files"},
    "success_map": {"fr": "✅ Carte générée avec succès", "en": "✅ Map generated successfully"},
    "success_zip": {"fr": "✅ Archive créée avec succès", "en": "✅ Archive created successfully"},
    "success_operation": {"fr": "✅ Opération réussie", "en": "✅ Operation successful"},

    # ============================================
    # UTILS_EXPORT / EXPORT
    # ============================================
    "export_map_title": {"fr": "Carte de prospection hydrogéologique", "en": "Hydrogeological Prospection Map"},
    "legend_surface_prospectee": {"fr": "Surface prospectée", "en": "Surveyed Area"},
    "legend_fractures_identifiees": {"fr": "Fractures identifiées", "en": "Identified Fractures"},
    "legend_points_forage": {"fr": "Points de forage", "en": "Drilling Points"},
    "legend_dolines": {"fr": "Dolines (zones favorables)", "en": "Dolines (Favorable Zones)"},
    "export_basemap_loaded": {"fr": "🗺️ Fond chargé : {name}", "en": "🗺️ Basemap loaded: {name}"},
    "export_basemap_failed": {"fr": "⚠️ Échec fond {name}", "en": "⚠️ Failed to load {name}"},
    "export_basemap_none_available": {"fr": "❌ Aucun fond de carte disponible", "en": "❌ No basemap available"},
    "export_creating_structure": {"fr": "Création de la structure de dossiers...", "en": "Creating folder structure..."},
    "export_structure_created": {"fr": "Structure créée dans: {path}", "en": "Structure created in: {path}"},
"export_success": {"fr": "✅ EXPORT TERMINÉ AVEC SUCCÈS!", "en": "✅ EXPORT COMPLETED SUCCESSFULLY!"}
}

# ============================================
# FONCTIONS UTILITAIRES
# ============================================
def get_text(key, lang='fr', **kwargs):
    """
    Récupère le texte traduit pour une clé donnée
    Exemple :
        get_text('export_map_title', lang='fr')
    """
    if key not in TRANSLATIONS:
        return f"[{key}]"
    text = TRANSLATIONS[key].get(lang, TRANSLATIONS[key].get('fr', f"[{key}]"))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception as e:
            print(f"⚠️ Erreur format texte pour {key}: {e}")
    return text

def verify_export_keys():
    """Vérifie que toutes les clés nécessaires pour utils_export.py sont présentes"""
    required_keys = [k for k in TRANSLATIONS if k.startswith("export_") or k.startswith("journal_")]
    missing_keys = [key for key in required_keys if key not in TRANSLATIONS]
    if missing_keys:
        print(f"⚠️ Clés manquantes pour utils_export.py: {missing_keys}")
        return False
    print("✅ Toutes les clés nécessaires pour utils_export.py sont présentes")
    return True

def get_all_keys_for_language(lang="fr"):
    """Retourne toutes les clés pour une langue donnée"""
    return {key: TRANSLATIONS[key].get(lang, f"[{key}]") for key in TRANSLATIONS}

def count_translations():
    """Compte le nombre de traductions par langue"""
    fr_count = sum(1 for key in TRANSLATIONS if "fr" in TRANSLATIONS[key])
    en_count = sum(1 for key in TRANSLATIONS if "en" in TRANSLATIONS[key])
    total_keys = len(TRANSLATIONS)
    return {
        "total_keys": total_keys,
        "french_translations": fr_count,
        "english_translations": en_count,
        "completeness_fr": f"{(fr_count/total_keys)*100:.1f}%",
        "completeness_en": f"{(en_count/total_keys)*100:.1f}%"
    }
