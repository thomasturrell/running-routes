# 🏃 Running Routes

This repository contains the source data, scripts, and website content for a collection of running routes, including:

- 🛣️ **Road running** – Fast, paved routes ideal for tempo runs, intervals, and race preparation.
- 🏞️ **Trail running** – Scenic off-road routes through forests, hills, and countryside paths.
- ⛰️ **Fell running** – Steep, rugged mountain routes with a focus on elevation and summits.

All routes are provided in GPX format and can be used with GPS watches and mapping apps like Garmin Connect, Suunto, Strava, Komoot, and OS Maps.

---

## 📥 Download GPX Files

The latest downloadable GPX files and live previews are available at the website:

👉 [Running Routes Website](https://thomasturrell.github.io/running-routes/)

The site includes:
- GPX files for each leg or section of supported routes
- Simplified (single-track) GPX files for compatibility
- Detailed (multi-track) GPX files for analysis/editing
- Preview maps for interactive exploration

---

## 🏃‍♂️ Supported Routes

| Name               | Type         | Region         | Status        |
|--------------------|--------------|----------------|---------------|
| Bob Graham Round   | Fell Running | Lake District  | ✅ Available   |
| [Coming Soon]      | Road/Trail   | UK             | 🕒 Planned     |

---

## ⚙️ How to Generate GPX Files

To regenerate the GPX files locally:

```bash
python scripts/generate_gpx_files.py
```

### 🐍 Recommended Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install gpxpy
```

This will create or update files in `docs/fell/bob-graham-round/` for GitHub Pages publishing.

---

## 🗂️ Repository Structure

```
src/       # Source data (GPX, CSV, planning files)
docs/      # Jekyll website content & generated GPX downloads
scripts/   # Python scripts to build GPX files and Markdown
```

---

## 🗺️ Data Sources & Attribution

- **Route planning**: Ordnance Survey Maps online planner. Routes follow footpaths and rights of way.
- **Summit data**: [Hill Bagging](https://www.hill-bagging.co.uk), based on the [Database of British and Irish Hills (DoBIH)](https://www.hills-database.co.uk/).  
  Summit data © DoBIH, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

> 🧭 *Always compare with race lines, current terrain conditions, and satellite imagery before relying on these files in the field.*

---

## 🧾 License

- Code in this repository is licensed under the MIT License.
- Route data (GPX files) is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), unless otherwise noted.

---

## 🧰 Contributing

Feel free to:
- Report issues
- Submit pull requests for new routes or improvements
- Suggest additions via Discussions or Issues
