# iOS / iPadOS (ARM64)

Vom Repository-Hauptverzeichnis aus, auf einem Mac mit vollständigem Xcode,
iPhoneOS-SDK, CMake und Python 3.13. Die vorhandenen Checkouts
`deps/cyclonedds` und `deps/cyclonedds-python` werden benötigt.

```sh
sh mobile/ios/setup.sh          # einmalig: isolierte Qt-/Python-Buildumgebung
sh mobile/ios/build-insight.sh  # unsignierte Geräte-App bauen
python3.13 mobile/ios/verify-app.py
```

Ergebnis: `dist/ios/CycloneDDS Insight.app`. Zum Installieren:

```sh
open "build/ios-insight/deployment/ios_arm64/CycloneDDS Insight.xcodeproj"
```

In Xcode unter **Signing & Capabilities → Team** dein Team wählen,
iPhone/iPad anschließen, Entwicklermodus aktivieren, Gerät auswählen und **Run**.
Alternativ bereits signiert bauen: `sh mobile/ios/build-insight.sh --team YL484LJV4J`.
Eine unsignierte `.app` lässt sich nicht direkt auf einem iPhone installieren.

## Nach Änderungen an QML-Imports

Das Buildskript erneut ausführen, bevor das Projekt in Xcode gebaut wird.
Es aktualisiert auch die statisch verlinkten QML-Plugins. Nur in Xcode auf
**Run** zu klicken, aktualisiert diese Plugin-Liste nicht.

Für einen Build direkt aus Xcode die tatsächlich gebaute App prüfen:

```sh
python3.13 mobile/ios/verify-app.py "/Pfad/zum/Xcode-Build/CycloneDDS Insight.app"
```

Ohne Pfad prüft das Skript nur die Kopie unter `dist/ios`; diese kann älter
als der letzte Xcode-Build sein. Insight benötigt sowohl den zur Laufzeit
ausgewählten iOS-Stil als auch den für einzelne Steuerelemente importierten
Basic-Stil. Das Buildskript bindet beide ein.

## DDS-Netzwerk

Der aktuelle signierte Build nutzt **Unicast zum Laptop 192.168.178.22**:

```sh
sh mobile/ios/build-insight.sh --no-multicast --peer 192.168.178.22 --team YL484LJV4J
```

Auf diesem Laptop ist `ParticipantIndex=auto` in Insights gespeicherter
DDS-Konfiguration gesetzt. Die aktualisierte Mac-App liegt unter
`dist/desktop-network/CycloneDDS Insight.app`.
Beide Apps neu starten, gleiche DDS-Domain wählen (z. B. 0), auf iOS
**Lokales Netzwerk erlauben**. Bei abgelehntem Zugriff: Einstellungen →
Datenschutz & Sicherheit → Lokales Netzwerk → Insight aktivieren.

**Ohne Neubau ändern:** Settings → Edit configuration → XML bearbeiten →
**Save for next start**, App vollständig schließen und erneut starten.
Das gilt auf iOS und Desktop. Die gespeicherte Konfiguration überschreibt
`CYCLONEDDS_URI` nur im App-Prozess. Mit **Use environment / defaults** wird
beim nächsten Start wieder die externe bzw. eingebaute Konfiguration verwendet.
Bei geänderter Laptop-IP den `<Peer Address="..." />`-Eintrag aktualisieren.

Für normales Multicast ist der Standardbuild vorbereitet. Noch fehlt Apples
[Multicast-Freischaltung](https://developer.apple.com/contact/request/networking-multicast)
für Team `YL484LJV4J` und App-ID `trittsv.app.cycloneddsinsight`.
Nach Freigabe `sh mobile/ios/build-insight.sh --team YL484LJV4J` ausführen;
eine zuvor gespeicherte Unicast-Konfiguration im Editor ebenfalls zurücksetzen.

## Stand

Gebaut mit Xcode 27, offiziellen PySide6-6.12-Alpha-Snapshots vom 26.09.2026
(enthalten Qt 6.12.1) und Python 3.15.0rc2; Mindestversion iOS/iPadOS 18.
Setup prüft die SHA-256-Werte der Geräte-Wheels und des Python-Frameworks.
Qt-Snapshot-Downloads können später entfernt/ersetzt werden; den Ordner
`build/ios-tools` für reproduzierbare Wiederholungsbuilds aufbewahren.

CycloneDDS und dessen Python-C-Erweiterung werden für iOS neu kompiliert und
statisch eingebunden. Die vollständige QML-Oberfläche und Python-Abhängigkeiten
sind enthalten. IDL-Kompilierung und Desktop-Updater sind auf Mobilgeräten deaktiviert.
Das Cyclone-Logo wird automatisch als iPhone-/iPad-App-Icon eingebunden.
Startimports ohne das auf iOS fehlende `QProcess` prüfen:
`deps/venv/bin/python mobile/ios/check-imports.py` (Desktop-Entwicklungsumgebung).
ARM64-Build, Paketprüfung und Entwicklungssignierung mit Team `YL484LJV4J`
erfolgreich; die Signatur wurde mit `codesign --verify --deep --strict` geprüft.
App-Start auf dem iPhone vom Nutzer bestätigt. Der aktualisierte Unicast-Build muss noch auf dem Gerät gegen den Laptop geprüft werden.

Grundlage: [Qt/PySide6 für iOS](https://www.qt.io/blog/python-mobile-app-development-bringing-pyside6-on-ios).

## iOS-Gerätename in Cyclone DDS

Der Build verwendet [trittsv/cyclonedds, Branch fix/ios-hostname-raw-ethernet](https://github.com/trittsv/cyclonedds/tree/fix/ios-hostname-raw-ethernet),
fest auf Commit `552fb2e4cf180e4702c9aa52b99212ba47389588` gesetzt.
Der Checkout liegt in `build/ios-cyclonedds-upstream`; lokale Cyclone-DDS-Patches
sind nicht mehr nötig. Die separate iOS-Implementierung verwendet UIKit.

Für den persönlichen Namen das separate
[User-Assigned Device Name Entitlement](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.device-information.user-assigned-device-name)
bei Apple beantragen. Nach Freigabe beim Build zusätzlich
`--user-assigned-device-name` angeben (unabhängig von `--multicast`).
Der Name ist ein Anzeigename, kein zwingend auflösbarer DNS-Hostname.



Die vorgebauten PySide6-iOS-Bibliotheken verlinken auch ungenutzte Qt-Permission-
Plugins. Für Apples Prüfung enthält die App daher Kontakte- und Bluetooth-
Beschreibungstexte, die ausdrücklich auf die Nichtverwendung hinweisen. Insight
fordert diese Berechtigungen nicht an. Die Paketprüfung kontrolliert die Texte.

Raw Ethernet ist im genannten Branch für Apple auf macOS begrenzt.
