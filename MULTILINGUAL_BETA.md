# Private localization beta B002

Installer 1.3.1 Private Beta B002 supports English, German, Russian and French
signed content with independent interface language selection. Existing released
English and private German packages remain supported; no public release changes.

Russian targets the native Interface_ru fonts_ru member. French uses the shared
Interface_en fonts_en member. Each profile permits only its own fontconfig,
Localization translation and three string tables. Catalogs remain application
policy; a signed package cannot choose arbitrary languages or paths.

Restore vanilla before switching content language, then set the game language
in Steam. UI language selects neither the payload nor Steam language.

The first successful Russian/French install upgrades saved history to schema 4,
retaining the existing English/German sequence and restoration histories. The
new installer reads schemas 2, 3 and 4 and recovers their pending operations.
Use Installer 1.3.1 for subsequent repair, restore and return to English/German;
older installers cannot read schema 4. Ordinary English/German operations on
older saved history retain their previous schema until RU/FR is installed.

Common screens and operational messages are localized; uncatalogued technical
diagnostics can remain English. Native volunteer QA is still required. Do not
claim in-game acceptance from the automated tests or publish this private beta.
