import i18n
import os

# Setup localization
def setup_i18n(default_locale: str = 'en'):
    i18n.load_path.append(os.path.join(os.path.dirname(__file__), 'locales'))
    i18n.set('file_format', 'json')
    i18n.set('locale', default_locale)
    i18n.set('fallback', 'en')  # fallback language
    i18n.set('filename_format', '{locale}.{format}')

# Function to change language globally
def change_locale(locale: str):
    i18n.set('locale', locale)