# utils/lang_helper.py
"""
Gestion de la langue pour Ground Water Finder.
Permet de définir la langue courante et de récupérer les traductions via get_text.
"""

from .translations import TRANSLATIONS

# ===============================================================
# État de la langue courante
# ===============================================================
_current_lang = 'fr'

# ===============================================================
# FONCTIONS PRINCIPALES
# ===============================================================
def set_language(lang: str):
    """
    Définit la langue courante.
    Langue attendue : 'fr' ou 'en'
    """
    global _current_lang
    if lang not in ['fr', 'en']:
        raise ValueError(f"Langue invalide: {lang}. Choisir 'fr' ou 'en'.")
    _current_lang = lang

def get_current_language() -> str:
    """Retourne la langue courante ('fr' ou 'en')"""
    return _current_lang

def get_text(key: str, **kwargs) -> str:
    """
    Retourne la traduction d'une clé selon la langue courante.
    Si la clé est introuvable, retourne la clé entre crochets.
    Permet le formatage avec kwargs.
    """
    if key not in TRANSLATIONS:
        return f"[{key}]"
    text = TRANSLATIONS[key].get(_current_lang, f"[{key}]")
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError as e:
            # Gérer les placeholders manquants
            text += f" ⚠ Placeholder manquant: {e}"
    return text
