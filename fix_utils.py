import re

# Lire le fichier
with open('/app/utils/utils_export.py', 'r') as f:
    content = f.read()

# Nouveau code à insérer
new_code = '''    # Chercher le contour par ordre de priorite
    contour_input_path = None
    
    # 1. Chercher dabord les fichiers GPX, KML, KMZ dans INPUT
    input_dir = dossier_client / "INPUT"
    if input_dir.exists():
        contour_files = [f for f in input_dir.iterdir() if f.suffix.lower() in [".gpx", ".kml", ".kmz"]]
        if contour_files:
            contour_input_path = contour_files[0]
            st.info(f"📁 Contour trouve dans INPUT: {contour_input_path.name}")
    
    # 2. Fallback: Utiliser CONTOUR.shp du dossier RENDU
    if contour_input_path is None:
        contour_shp = dossier_RENDU / "CONTOUR.shp"
        if contour_shp.exists():
            contour_input_path = contour_shp
            st.info(f"📁 Fallback: utilisation de CONTOUR.shp comme contour")
    
    # 3. Si rien nest trouve, erreur
    if contour_input_path is None:
        st.error(f"❌ Aucun fichier de contour trouve")
        st.stop()'''

# Pattern pour trouver l'ancien code (2 occurrences)
old_pattern = r'    contour_input_path = next\(\n        f\n        for f in input_dir\.iterdir\(\)\n        if "contour" in f\.name\.lower\(\) and f\.suffix\.lower\(\) in \[\.\"gpx\", \.\"kml\", \.\"kmz\"\]\n    \)'

# Remplacer toutes les occurrences
content = re.sub(old_pattern, new_code, content)

# Sauvegarder
with open('/app/utils/utils_export.py', 'w') as f:
    f.write(content)

print("✅ Les 2 occurrences ont été corrigées avec succès!")
