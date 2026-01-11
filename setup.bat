@echo off
echo  Configuration de Ground Water Finder...

REM Activer l'environnement virtuel
call env_py310\Scripts\activate.bat

REM Installer les d?pendances
pip install -r requirements.txt

REM Cr?er .env
if not exist ".env" (
    echo B2_KEY_ID="votre_key" > .env
    echo B2_APP_KEY="votre_app_key" >> .env
    echo B2_BUCKET_NAME="votre_bucket" >> .env
    echo  Modifiez .env avec vos vraies cl?s
)

echo  Pr?t ! Lancez : streamlit run app.py
pause
