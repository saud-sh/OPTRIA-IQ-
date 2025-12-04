from translations.ar import AR
from translations.en import EN

TRANSLATIONS = {
    "ar": AR,
    "en": EN
}

def get_translation(lang: str = "ar") -> dict:
    return TRANSLATIONS.get(lang, AR)

def t(key: str, lang: str = "ar") -> str:
    translations = get_translation(lang)
    return translations.get(key, key)

__all__ = ['AR', 'EN', 'TRANSLATIONS', 'get_translation', 't']
