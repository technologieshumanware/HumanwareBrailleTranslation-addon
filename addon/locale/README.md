# Translation Files (.po / .mo)

This directory contains the translation files for the HumanwareBrailleTranslation add-on.

## Structure

```
locale/
├── en/
│   ├── LC_MESSAGES/
│   │   ├── nvda.po    (English translation source)
│   │   └── nvda.mo    (Compiled English translation)
│   └── manifest.ini   (Translated add-on summary/description)
└── fr/
    ├── LC_MESSAGES/
    │   ├── nvda.po    (French translation source)
    │   └── nvda.mo    (Compiled French translation)
    └── manifest.ini   (Translated add-on summary/description)
```

## Files

- **nvda.po**: Translation source file (human-readable, edit this)
- **nvda.mo**: Compiled translation file (binary, generated from .po)
- **manifest.ini**: Translated add-on metadata (summary and description)

## Translated Strings

The following strings are available for translation:

- Add-on summary and description (from buildVars.py)
- Settings panel labels:
  - Disable and use default Braille translation
  - Literary Braille translator
  - Computer Braille translator
  - Preferred braille grade for entry
  - Preferred braille grade for display
- Script descriptions and messages
- Braille type labels (Computer braille, Literary braille)

## Compiling Translations

After editing any `.po` file, you must compile it to `.mo` format:

### Manual compilation
```powershell
msgfmt -o addon/locale/en/LC_MESSAGES/nvda.mo addon/locale/en/LC_MESSAGES/nvda.po
msgfmt -o addon/locale/fr/LC_MESSAGES/nvda.mo addon/locale/fr/LC_MESSAGES/nvda.po
```

## Requirements

You need the `msgfmt` tool from gettext. Install options:

1. **Chocolatey**: `choco install gettext`
2. **Git for Windows**: Includes msgfmt in `C:\Program Files\Git\usr\bin\`
3. **Direct download**: https://mlocati.github.io/articles/gettext-iconv-windows.html

## Adding New Translations

1. Create a new language directory (e.g., `es/LC_MESSAGES/`)
2. Copy the `.po` file from `en/LC_MESSAGES/nvda.po` as a template
3. Update the header information (Language, Language-Team, etc.)
4. Translate the `msgstr` entries
5. Compile to `.mo` using msgfmt

## Notes

- The English locale serves as the default/fallback translation
- Translation initialization is handled in each Python module via `addonHandler.initTranslation()`
- Use `_()` function in code to mark strings for translation
