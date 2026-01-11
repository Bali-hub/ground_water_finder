@echo off
chcp 65001 >nul
echo ========================================
echo   GROUND WATER FINDER - Streamlit App
echo ========================================
echo.

REM Vérifier Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installé ou pas dans le PATH
    echo.
    echo Solutions:
    echo 1. Installez Python depuis https://python.org
    echo 2. Cochez "Add Python to PATH" pendant l'installation
    echo 3. Redémarrez votre PC après installation
    pause
    exit /b 1
)

REM Vérifier environnement virtuel
if not exist "env_py310" (
    echo [ATTENTION] Environnement virtuel 'env_py310' introuvable
    echo.
    echo Exécutez d'abord 'setup.bat' pour configurer l'environnement
    echo.
    set /p choice="Voulez-vous le créer maintenant ? (O/N): "
    if /i "%choice%"=="O" (
        echo Création de l'environnement virtuel...
        python -m venv env_py310
        echo ✅ Environnement créé
    ) else (
        echo ❌ Annulé
        pause
        exit /b 1
    )
)

REM Activer l'environnement
echo Activation de l'environnement virtuel...
call env_py310\Scripts\activate.bat

REM Vérifier et installer les dépendances
echo Vérification des dépendances...
python -c "
try:
    import streamlit, numba, gpxpy, lxml, geopandas
    print('✅ Toutes les dépendances sont installées')
except ImportError as e:
    print(f'❌ Manque: {e}')
    exit(1)
" >nul 2>&1

if errorlevel 1 (
    echo Installation des dépendances...
    pip install -r requirements.txt
    echo ✅ Dépendances installées
)

REM Vérifier fichier .env
if not exist ".env" (
    echo [ATTENTION] Fichier .env non trouvé
    echo Création d'un modèle...
    (
        echo # Configuration Backblaze B2
        echo # Remplacez les valeurs ci-dessous par vos clés
        echo B2_KEY_ID=""
        echo B2_APP_KEY=""
        echo B2_BUCKET_NAME=""
        echo.
        echo # Pour obtenir ces clés:
        echo # 1. Allez sur https://backblaze.com
        echo # 2. Créez un bucket
        echo # 3. Générez les clés d'application
    ) > .env
    echo.
    echo ⚠️  MODIFIEZ le fichier '.env' avec vos vraies clés
    echo Ouvrez-le avec Notepad et remplissez les valeurs
    pause
)

REM Lancer l'application
echo.
echo ========================================
echo   Lancement de l'application...
echo   Ouvrez http://localhost:8501
echo   Ctrl+C pour arrêter
echo ========================================
echo.

streamlit run app.py --server.port=8501 --server.headless=false

REM Si on arrive ici, l'application s'est arrêtée
echo.
echo Application arrêtée.
pause