# Running Routes
This repository contains a collection of .gpx files for different types of running, including:

* 🛣️ Road running – Fast, paved routes ideal for tempo runs, intervals, and race preparation
* 🏞️ Trail running – Scenic off-road routes through forests, hills, and countryside paths
* ⛰️ Fell running – Steep, rugged mountain routes with a focus on elevation and summits

All routes are provided in GPX format and can be used with GPS watches and mapping apps like Garmin, Suunto, Strava, Komoot, and OS Maps.

# 🏔️ Running Routes – GPX Files

This folder contains the source `.gpx` and data files for a collection of classic running routes, starting with the **Bob Graham Round** in the English Lake District. More routes will be added over time.

## 📦 Where to Download GPX Files

**The latest downloadable GPX files and live route previews are available on the project website:**

👉 [Running Routes Website](https://thomasturrell.github.io/running-routes/)

You can download:
- GPX files for each leg or section of supported routes
- Simplified (single-track) GPX files for most devices
- Detailed (multi-track) GPX files for advanced use

## 🗂️ Repository Structure

- `src/` — Source data for all routes (GPX, CSV, etc.)
- `docs/` — Website content and generated GPX files for download
- `scripts/` — Scripts to generate and process GPX files

## ⚙️ How to Generate GPX Files

To regenerate the downloadable GPX files, run the script from the project root:

```bash
python scripts/generate_gpx_files.py
```

You need Python 3 and the `gpxpy` library. The recommended way is to use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install gpxpy
```

## 🗺️ Data Sources & Attribution

- **Route planning:** Ordnance Survey (OS) Maps online planner and other sources as noted per route. Routes follow rights of way and footpaths using OS’s routing engine. Minor variations may occur, especially on technical descents or open fell crossings.
- **Summit data:** From [Hill Bagging](https://www.hill-bagging.co.uk), based on the [Database of British and Irish Hills (DoBIH)](https://www.hills-database.co.uk/). Summit data © DoBIH, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

> 🧭 *Always compare with actual race lines, terrain conditions, and satellite imagery before relying on these files in the field.*

## 📝 Notes

- For questions or contributions, open an issue or pull request on GitHub
