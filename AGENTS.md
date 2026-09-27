# Repository instructions

## UI translations

- Whenever adding or changing user-visible text, update all translation files in `src/translations/cyclonedds-insight_*.ts` in the same change, including English. Never leave new or changed strings untranslated or unfinished.
- Follow the existing ID-based translation convention: use `qsTrId("...")` in QML and matching message IDs in every TS file instead of hard-coded text or new `qsTr(...)` strings.
- Before completing the change, check that the affected IDs exist with nonempty translations in every language and compile the catalogs with `pyside6-lrelease`. Regenerate bundled resources when preparing a build.
