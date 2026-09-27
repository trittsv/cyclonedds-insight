[![Website](https://img.shields.io/badge/web-cyclonedds.io-blue)](https://cyclonedds.io)
[![License](https://img.shields.io/badge/License-EPL%202.0-blue)](https://choosealicense.com/licenses/epl-2.0/)
[![License](https://img.shields.io/badge/License-EDL%201.0-blue)](https://choosealicense.com/licenses/edl-1.0/)
[![Community](https://img.shields.io/badge/discord-join%20community-5865f2)](https://discord.gg/BkRYQPpZVV)


# CycloneDDS Insight

***Looking for binaries?***
- The latest master build can be downloaded [here](https://dev.azure.com/eclipse-cyclonedds/cyclonedds-insight/_build?definitionId=19&repositoryFilter=8&branchFilter=1200%2C1200%2C1200%2C1200&statusFilter=succeeded) click on latest build / "4 published".
- Released versions are available on the [GitHub Releases](https://github.com/eclipse-cyclonedds/cyclonedds-insight/releases) page (see attached assets).

## Overview

A graphical tool to visualize the current DDS system.

Access the documentation [here](https://cyclonedds.io/docs/cyclonedds-insight/latest) for more information, user manuals and more.

![`cyclonedds insight`](docs/manual/_static/images/cyclonedds-insight.png)

Features:

- Show topics
- Show reader/writer on a topic
- Show qos of each reader/writer
- Show qos mismatches
- Dark and light mode support
- Runs on MacOS, Windows, Linux
- Import idl files
- Create Reader to Listen to a topic

## Development Setup

1. Execute `build.sh` once to set up the project and dependencies.
2. After the initial build or each code change you only need to run: `run.sh`.

For windows use the `.bat` alternatives.

## How to build

For the experimental Android port, see [Android setup and porting status](mobile/android/README.md).
For iPhone and iPad (ARM64), see [iOS build and installation](mobile/ios/README.md).

### DDS configuration in Insight

In **Settings**, use the **Managed by Insight** switch:
- **Use CYCLONEDDS_URI environment variable** (default): uses the startup environment;
  file references remain paths. Without a value, Cyclone DDS uses its defaults.
- **Managed by CycloneDDS Insight**: edit XML and save it in Insight's QSettings.
  Insight sets its own process environment before DDS starts; no shell setup is needed.

Close and reopen the app after changing the source or XML. The text field shows the startup environment value or the saved XML, depending on the selected mode. XML strings are escaped by
QSettings automatically. The editor autosaves to Insight settings in managed mode;
in environment mode it edits the referenced XML file, as before.
XML syntax is checked on save; DDS validates configuration options at startup.

### MacOS / Linux

```bash
./build.sh
```

### Windows

```bash
.\build.bat
```
