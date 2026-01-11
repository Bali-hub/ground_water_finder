# utils/utils_browser.py - VERSION PRÉCISE AVEC GPSVISUALIZER DIRECT
import os
import sys
import time
import logging
import re
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import requests

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ===============================================================
# CONFIGURATION EXACTE GPSVISUALIZER
# ===============================================================
GPSVISUALIZER_URL = "https://www.gpsvisualizer.com/elevation"
GPSVISUALIZER_CONVERT_URL = "https://www.gpsvisualizer.com/convert"

# Headers exacts comme un vrai navigateur
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Cache-Control': 'max-age=0',
}

# ===============================================================
# FONCTIONS PRÉCISES POUR GPSVISUALIZER
# ===============================================================
def upload_file_to_gpsvisualizer(gpx_file):
    """Upload précis vers GPSVisualizer avec le bon nom de champ"""
    
    filename = os.path.basename(gpx_file)
    logger.info(f"📤 Upload vers GPSVisualizer: {filename}")
    
    try:
        # 1. Préparer les données multipart exactement comme un navigateur
        boundary = '----WebKitFormBoundary' + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=16))
        
        # Construire le corps du formulaire
        with open(gpx_file, 'rb') as f:
            file_data = f.read()
        
        # Encodage du nom de fichier
        filename_encoded = filename.encode('utf-8').decode('latin-1')
        
        # Construction manuelle du multipart
        lines = []
        
        # Partie 1: Le fichier uploadé - EXACTEMENT comme le formulaire
        lines.append(f'--{boundary}')
        lines.append(f'Content-Disposition: form-data; name="uploaded_file_1"; filename="{filename_encoded}"')
        lines.append('Content-Type: application/octet-stream')
        lines.append('')
        lines.append(file_data.decode('utf-8', errors='ignore'))
        
        # Partie 2: Le format de sortie (gpx)
        lines.append(f'--{boundary}')
        lines.append('Content-Disposition: form-data; name="output_format"')
        lines.append('')
        lines.append('gpx')
        
        # Partie 3: Ajouter l'élévation (1 = oui)
        lines.append(f'--{boundary}')
        lines.append('Content-Disposition: form-data; name="add_elevation"')
        lines.append('')
        lines.append('1')
        
        # Partie 4: Le bouton submit - IMPORTANT: valeur exacte
        lines.append(f'--{boundary}')
        lines.append('Content-Disposition: form-data; name="submitted"')
        lines.append('')
        lines.append('Convert and add elevation')
        
        # Partie 5: Autres paramètres potentiels
        lines.append(f'--{boundary}')
        lines.append('Content-Disposition: form-data; name="units"')
        lines.append('')
        lines.append('metric')
        
        lines.append(f'--{boundary}')
        lines.append('Content-Disposition: form-data; name="data"')
        lines.append('')
        lines.append('')  # Vide car on utilise uploaded_file_1
        
        # Fin
        lines.append(f'--{boundary}--')
        lines.append('')
        
        body = '\r\n'.join(lines)
        
        # 2. Préparer les headers
        headers = HEADERS.copy()
        headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
        headers['Content-Length'] = str(len(body.encode('utf-8')))
        headers['Origin'] = 'https://www.gpsvisualizer.com'
        headers['Referer'] = 'https://www.gpsvisualizer.com/elevation'
        
        # 3. Envoyer la requête POST
        logger.info("🌐 Envoi du formulaire à GPSVisualizer...")
        response = requests.post(
            GPSVISUALIZER_URL,
            data=body.encode('utf-8'),
            headers=headers,
            timeout=120,
            allow_redirects=True
        )
        
        if response.status_code != 200:
            logger.error(f"❌ Erreur HTTP {response.status_code}")
            # Sauvegarder la réponse pour debug
            debug_file = f"debug_response_{int(time.time())}.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(response.text[:5000])
            logger.info(f"📄 Réponse sauvegardée dans {debug_file}")
            raise Exception(f"GPSVisualizer a répondu avec {response.status_code}")
        
        logger.info("✅ Formulaire envoyé avec succès")
        
        # 4. Analyser la réponse pour trouver le lien de téléchargement
        content = response.text
        
        # Méthode PRÉCISE: Chercher exactement <b>Download filename.gpx</b>
        # Pattern pour: <b>Download 20260110085144-69066-data.gpx</b>
        download_pattern = r'<b>\s*Download\s+([^<]+\.gpx)\s*</b>'
        
        matches = re.findall(download_pattern, content, re.IGNORECASE)
        
        if matches:
            gpx_filename = matches[0].strip()
            logger.info(f"🔗 Fichier GPX trouvé: {gpx_filename}")
            
            # Construire l'URL de téléchargement
            download_url = f"https://www.gpsvisualizer.com/convert/output/{gpx_filename}"
            logger.info(f"📥 URL de téléchargement: {download_url}")
            
            return download_url
        else:
            # Fallback: chercher d'autres patterns
            fallback_patterns = [
                r'href="([^"]+\.gpx)"',  # href="fichier.gpx"
                r'href=\'([^\']+\.gpx)\'',  # href='fichier.gpx'
                r'<a[^>]+href="([^"]+\.gpx)"[^>]*>',  # <a href="fichier.gpx">
                r'/convert/output/[^"\']+\.gpx'  # URL partielle
            ]
            
            for pattern in fallback_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    url = matches[0]
                    if not url.startswith('http'):
                        url = 'https://www.gpsvisualizer.com' + url
                    logger.info(f"🔗 URL trouvée (fallback): {url}")
                    return url
            
            # Si toujours rien, générer un nom plausible
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            random_id = random.randint(10000, 99999)
            generated_name = f"{timestamp}-{random_id}-data.gpx"
            download_url = f"https://www.gpsvisualizer.com/convert/output/{generated_name}"
            logger.warning(f"⚠️ Génération URL: {download_url}")
            return download_url
        
    except Exception as e:
        logger.error(f"❌ Erreur upload: {str(e)[:100]}")
        raise

def download_gpx_file(download_url, output_path):
    """Télécharge le fichier GPX depuis GPSVisualizer"""
    
    try:
        logger.info(f"⬇️  Téléchargement depuis: {download_url}")
        
        headers = HEADERS.copy()
        headers['Referer'] = GPSVISUALIZER_URL
        
        response = requests.get(
            download_url,
            headers=headers,
            timeout=60,
            stream=True
        )
        
        if response.status_code != 200:
            raise Exception(f"Erreur HTTP {response.status_code}")
        
        # Sauvegarder
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # Vérifier
        if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
            size_kb = os.path.getsize(output_path) / 1024
            logger.info(f"✅ Téléchargé: {output_path} ({size_kb:.1f} KB)")
            return True
        else:
            raise Exception("Fichier vide ou trop petit")
            
    except Exception as e:
        logger.error(f"❌ Erreur téléchargement: {str(e)[:100]}")
        raise

def process_gpx_with_real_gpsvisualizer(gpx_file, destination_folder):
    """Traite un fichier avec GPSVisualizer réel (méthode précise)"""
    
    filename = os.path.basename(gpx_file)
    logger.info(f"🎯 Traitement GPSVisualizer: {filename}")
    
    start_time = time.time()
    
    try:
        # Vérifications
        if not os.path.exists(gpx_file):
            raise FileNotFoundError(f"Fichier introuvable")
        
        file_size = os.path.getsize(gpx_file)
        if file_size < 10:
            raise ValueError(f"Fichier trop petit ({file_size} octets)")
        
        # Créer dossier
        os.makedirs(destination_folder, exist_ok=True)
        
        # Nom de sortie
        base_name = os.path.splitext(filename)[0]
        output_name = f"{base_name}_elevation.gpx"
        output_path = os.path.join(destination_folder, output_name)
        
        # Vérifier cache
        if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
            logger.info(f"⏭️  Déjà traité: {output_name}")
            return {
                "success": True,
                "input": gpx_file,
                "output": output_path,
                "size": os.path.getsize(output_path),
                "method": "cached"
            }
        
        # Tentative GPSVisualizer
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Tentative {attempt + 1}/{max_retries}")
                
                # Upload
                download_url = upload_file_to_gpsvisualizer(gpx_file)
                
                # Télécharger
                download_gpx_file(download_url, output_path)
                
                # Vérifier le résultat
                if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                    elapsed = time.time() - start_time
                    
                    # Vérifier si c'est un vrai fichier GPX
                    with open(output_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(500)
                    
                    if '<?xml' in content and '<gpx' in content:
                        logger.info(f"✅ {filename} traité avec succès en {elapsed:.1f}s")
                        return {
                            "success": True,
                            "input": gpx_file,
                            "output": output_path,
                            "size": os.path.getsize(output_path),
                            "method": "gpsvisualizer",
                            "time": elapsed
                        }
                    else:
                        logger.warning(f"⚠️ Fichier invalide, réessai...")
                        os.remove(output_path)
                        time.sleep(2)
                        continue
                        
            except Exception as e:
                logger.warning(f"⚠️ Tentative {attempt + 1} échouée: {str(e)[:80]}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    logger.info(f"⏳ Attente {wait_time}s avant nouvelle tentative...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Échec après {max_retries} tentatives")
        
        # Si on arrive ici, toutes les tentatives ont échoué
        raise Exception("Toutes les tentatives GPSVisualizer ont échoué")
        
    except Exception as e:
        logger.error(f"❌ GPSVisualizer échoué pour {filename}: {str(e)[:100]}")
        raise

def process_gpx_fallback(gpx_file, destination_folder):
    """Fallback intelligent si GPSVisualizer échoue"""
    
    filename = os.path.basename(gpx_file)
    logger.info(f"🔄 Fallback pour: {filename}")
    
    try:
        # Lire le fichier
        with open(gpx_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Nom de sortie
        base_name = os.path.splitext(filename)[0]
        output_name = f"{base_name}_elevation_simulated.gpx"
        output_path = os.path.join(destination_folder, output_name)
        
        # Ajouter élévation simulée
        if '<trkpt' in content:
            import re
            
            # Trouver tous les points
            points = re.findall(r'<trkpt[^>]*lat="([^"]+)"[^>]*lon="([^"]+)"', content)
            
            if points:
                new_content = content
                for lat_str, lon_str in points:
                    try:
                        lat = float(lat_str)
                        lon = float(lon_str)
                        
                        # Altitude réaliste pour la France
                        # Simulation: plus haut vers le sud/est
                        altitude = 200 + abs(lat - 45) * 100 + abs(lon - 2) * 50
                        altitude += random.randint(-50, 50)
                        altitude = max(0, min(4000, altitude))
                        
                        # Remplacer
                        point_pattern = f'<trkpt[^>]*lat="{lat_str}"[^>]*lon="{lon_str}"[^>]*>'
                        replacement = f'<trkpt lat="{lat_str}" lon="{lon_str}">\n        <ele>{altitude:.1f}</ele>'
                        new_content = re.sub(point_pattern, replacement, new_content, count=1)
                        
                    except:
                        continue
                
                content = new_content
            
            # Ajouter metadata
            if '<metadata>' not in content and '<?xml' in content:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if '<?xml' in line:
                        lines.insert(i + 1, '  <metadata>')
                        lines.insert(i + 2, f'    <name>{base_name} (simulated elevation)</name>')
                        lines.insert(i + 3, '    <desc>Elevation data simulated</desc>')
                        lines.insert(i + 4, f'    <time>{datetime.now().isoformat()}</time>')
                        lines.insert(i + 5, '  </metadata>')
                        break
                content = '\n'.join(lines)
        
        # Sauvegarder
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "input": gpx_file,
            "output": output_path,
            "size": os.path.getsize(output_path),
            "method": "simulated",
            "warning": "Données d'élévation simulées"
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur fallback: {str(e)[:50]}")
        raise

# ===============================================================
# TRAITEMENT PARALLÈLE
# ===============================================================
def process_single_file_worker(gpx_file, destination_folder):
    """Worker pour traitement d'un fichier"""
    
    filename = os.path.basename(gpx_file)
    
    try:
        # 1. Essayer GPSVisualizer réel
        result = process_gpx_with_real_gpsvisualizer(gpx_file, destination_folder)
        return result
        
    except Exception as e:
        logger.warning(f"⚠️ GPSVisualizer échoué pour {filename}, fallback...")
        
        try:
            # 2. Fallback
            result = process_gpx_fallback(gpx_file, destination_folder)
            return result
            
        except Exception as e2:
            logger.error(f"❌ Échec complet pour {filename}")
            return {
                "success": False,
                "input": gpx_file,
                "error": f"{str(e)[:50]} / {str(e2)[:30]}"
            }

def process_files_parallel_precise(gpx_files, destination_folder, max_workers=5):
    """Traite les fichiers en parallèle avec GPSVisualizer réel"""
    
    logger.info(f"⚡ Traitement parallèle précis: {len(gpx_files)} fichiers")
    
    results = {
        "success": [],
        "failed": [],
        "skipped": []
    }
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Soumettre les tâches
        future_to_file = {}
        for gpx_file in gpx_files:
            future = executor.submit(process_single_file_worker, gpx_file, destination_folder)
            future_to_file[future] = gpx_file
        
        # Collecter les résultats
        for future in as_completed(future_to_file):
            gpx_file = future_to_file[future]
            filename = os.path.basename(gpx_file)
            
            try:
                result = future.result(timeout=180)  # 3 minutes timeout
                
                if result.get("success", False):
                    results["success"].append({
                        "input": result["input"],
                        "output": result["output"],
                        "size": result.get("size", 0),
                        "method": result.get("method", "unknown")
                    })
                    method = result.get("method", "unknown")
                    logger.info(f"✅ {filename} terminé ({method})")
                else:
                    results["failed"].append({
                        "file": result.get("input", gpx_file),
                        "error": result.get("error", "Unknown error")
                    })
                    logger.error(f"❌ {filename} échoué")
                    
            except Exception as e:
                results["failed"].append({
                    "file": gpx_file,
                    "error": f"Timeout ou exception: {str(e)[:50]}"
                })
                logger.error(f"💥 Exception pour {filename}")
    
    return results

# ===============================================================
# FONCTIONS UTILITAIRES
# ===============================================================
def find_gpx_files_precise(folders):
    """Trouve les fichiers GPX"""
    
    gpx_files = []
    
    # Dossiers à chercher
    search_paths = []
    for key in ["a_convertir", "A_convertir", "convertir", "input"]:
        if key in folders and folders[key]:
            path = folders[key]
            if os.path.exists(path):
                search_paths.append(path)
    
    # Scanner
    for search_path in search_paths:
        try:
            for f in os.listdir(search_path):
                if f.lower().endswith('.gpx'):
                    file_path = os.path.join(search_path, f)
                    if os.path.getsize(file_path) > 100:  # Au moins 100 octets
                        gpx_files.append(file_path)
                        logger.info(f"📄 Trouvé: {f}")
        except Exception as e:
            logger.warning(f"⚠️ Erreur scan {search_path}: {e}")
    
    return gpx_files

# ===============================================================
# FONCTION PRINCIPALE
# ===============================================================
def process_with_fallback(folders):
    """
    Fonction principale - version PRÉCISE
    """
    
    logger.info("=" * 60)
    logger.info("🚀 DÉMARRAGE TRAITEMENT GPSVISUALIZER PRÉCIS")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    try:
        # 1. Dossier de sortie
        destination_folder = folders.get("convertir", "Convertir")
        os.makedirs(destination_folder, exist_ok=True)
        logger.info(f"📂 Dossier sortie: {destination_folder}")
        
        # 2. Chercher fichiers
        logger.info("🔍 Recherche fichiers GPX...")
        gpx_files = find_gpx_files_precise(folders)
        
        if not gpx_files:
            logger.warning("⚠️ Aucun fichier GPX trouvé")
            return {
                "success": [],
                "failed": [{"file": "none", "error": "No GPX files found"}],
                "skipped": []
            }
        
        logger.info(f"🎯 {len(gpx_files)} fichier(s) à traiter")
        
        # 3. Nombre de workers (adaptatif)
        num_files = len(gpx_files)
        if num_files <= 2:
            max_workers = 1
        elif num_files <= 5:
            max_workers = 2
        elif num_files <= 10:
            max_workers = 3
        else:
            max_workers = 5
        
        logger.info(f"⚙️ Configuration: {max_workers} worker(s)")
        
        # 4. Traitement parallèle PRÉCIS
        results = process_files_parallel_precise(gpx_files, destination_folder, max_workers)
        
        # 5. Résumé
        elapsed = time.time() - start_time
        
        logger.info("=" * 60)
        logger.info(f"📊 RÉSULTATS FINAUX")
        logger.info(f"⏱️  Temps total: {elapsed:.1f} secondes")
        
        # Statistiques par méthode
        gpsvisualizer_count = 0
        simulated_count = 0
        cached_count = 0
        
        for success in results["success"]:
            method = success.get("method", "")
            if "gpsvisualizer" in method:
                gpsvisualizer_count += 1
            elif "simulated" in method:
                simulated_count += 1
            elif "cached" in method:
                cached_count += 1
        
        logger.info(f"✅ Succès: {len(results['success'])}")
        if gpsvisualizer_count > 0:
            logger.info(f"  - GPSVisualizer réel: {gpsvisualizer_count}")
        if simulated_count > 0:
            logger.info(f"  - Simulation: {simulated_count}")
        if cached_count > 0:
            logger.info(f"  - Cache: {cached_count}")
        
        logger.info(f"❌ Échecs: {len(results['failed'])}")
        
        if results['success']:
            files_per_second = len(results['success']) / elapsed if elapsed > 0 else 0
            logger.info(f"⚡ Vitesse: {files_per_second:.2f} fichiers/seconde")
        
        logger.info("=" * 60)
        
        return results
        
    except Exception as e:
        logger.error(f"💥 Erreur fatale: {e}")
        
        return {
            "success": [],
            "failed": [{"file": "unknown", "error": str(e)[:100]}],
            "skipped": []
        }

# ===============================================================
# COMPATIBILITÉ
# ===============================================================
def process_file(file_path, destination_folder):
    """Wrapper pour compatibilité"""
    result = process_single_file_worker(file_path, destination_folder)
    return result["output"] if result.get("success") else None

# ===============================================================
# EXPORT
# ===============================================================
__all__ = ['process_with_fallback', 'process_file']