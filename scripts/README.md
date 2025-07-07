# 📜 Running Routes Tools

This repository contains Python scripts for processing and enriching GPX files for fell running routes.

## 🔧 Scripts Overview

### 1. `plot_route_from_waypoints.py`

**Purpose**
Processes a GPX file containing waypoints and calculates a route between them using OpenStreetMap (OSM) data. Outputs a new GPX file with the calculated route and optionally saves a visualisation of the route as a PNG.

**Features**

* Validates waypoints for count and separation distance.
* Downloads and caches OSM graph data.
* Snaps waypoints to paths with optional fallback handling.
* Generates a shortest-path route using the OSM network.
* Optionally saves a PNG plot of the route.

**Usage**

```bash
python plot_route_from_waypoints.py --input input.gpx --gpx-output output.gpx [options]
```

**Options**

* `--png-output` – Save a plot of the route as a PNG
* `--buffer` – Expand bounding box for OSM data (default: 0.05 degrees)
* `--max-points` – Max allowed number of waypoints (default: 50)
* `--max-distance` – Max allowed distance between waypoints in km (default: 20)
* `--max-cache-age-days` – Maximum graph cache age in days (default: 7)
* `--force-refresh` – Force redownload of OSM graph
* `--snap-threshold` – Maximum distance (in metres) to snap waypoints to a path (default: 5.0)

---

### 2. `fix_summit_waypoints.py`

**Purpose**
Enriches summit waypoints in GPX files using the Database of British and Irish Hills (DoBIH). Matches waypoints by custom extension (`dobih_number`) and updates their coordinates, elevation, and metadata.

**Features**

* Downloads and extracts DoBIH hill data CSV from hills-database.co.uk
* Matches summit waypoints based on `dobih_number`
* Updates coordinates and elevation

**Usage**

```bash
python fix_summit_waypoints.py --input input.gpx [options]
```

**Options**

* `--output` – Path to save the enriched GPX file (optional; defaults to `*_enriched.gpx`)
* A new file with enriched summit waypoints (default: `*_enriched.gpx`)

### 3. `generate_gpx_files.py`

**Purpose**
Takes a master route GPX file and generates a full suite of derived files, suitable for devices and visualisation.

**Features**

* Extracts summit and point-of-interest waypoints into separate files
* Generates track-only and flattened track files
* Saves each segment (leg) as a separate file

**Usage**

```bash
python generate_gpx_files.py
```

**Output Variants**

* `*-detailed.gpx`: Original GPX file
* `*-simplified.gpx`: All track segments flattened into one
* `*-track.gpx`: Just the track, no waypoints
* `*-summits.gpx`: Only summit waypoints
* `*-points-of-interest.gpx`: Non-summit waypoints
* `*-leg-*.gpx`: Individual legs from each track segment

**Configuration**
Routes are defined in the script's `ROUTES` list with fields:

* `name`: Human-readable name
* `source`: Path to the source GPX file
* `output`: Directory for output files
* `prefix`: Filename prefix for outputs
