# 📜 Running Routes Tools

This repository contains Python scripts for processing and enriching GPX files for fell running routes.

## 🔧 Scripts Overview

### 1. `plot_route_from_waypoints.py`

**Purpose**
Processes a GPX file containing waypoints and calculates a route between them using OpenStreetMap (OSM) data. Outputs a new GPX file with the calculated route and optionally saves a visualisation of the route as a PNG.

**Features**

* Validates waypoints for count and separation distance.
* Downloads and caches OSM graph data.
* Enriches the graph with NASA SRTM elevation data (downloaded automatically) and incorporates ascent/descent into routing costs.
* Caches elevation lookups locally to avoid repeat downloads between runs.
* Snaps waypoints to paths with optional fallback handling.
* Generates a shortest-path route using the OSM network.
* Optionally saves a PNG plot of the route.

**Usage**

```bash
python plot_route_from_waypoints.py input.gpx --output output.gpx [options]
```

**Options**

* `--buffer` – Expand bounding box for OSM data (default: 0.05 degrees)
* `--max-points` – Max allowed number of waypoints (default: 50)
* `--max-distance` – Max allowed distance between waypoints in km (default: 20)
* `--max-cache-age-days` – Maximum graph cache age in days (default: 7)
* `--force-refresh` – Force redownload of OSM graph
* `--snap-threshold` – Maximum distance (in metres) to snap waypoints to a path (default: 5.0)
* `--gain-penalty` – Horizontal metres added per metre climbed when computing least-cost paths (default: 10.0)
* `--loss-penalty` – Horizontal metres added per metre descended (default: 2.0)

---

### 2. `fix_summit_waypoints.py`

**Purpose**
Enriches summit waypoints in GPX files using the Database of British and Irish Hills (DoBIH). Matches waypoints by DoBIH number or name and updates their coordinates, elevation, and metadata with accurate hill data.

**Features**

* Downloads and extracts DoBIH hill data CSV from hills-database.co.uk
* Matches summit waypoints based on `dobih_number` custom extension
* When no DoBIH ID is found, searches by waypoint name and displays possible matches
* Updates waypoint coordinates, elevation, and name with accurate hill data
* Preserves original GPX structure while adding custom namespace extensions
* Provides interactive suggestions for unmatched waypoints

**Usage**

```bash
python fix_summit_waypoints.py input.gpx [--output output.gpx]
```

**Options**

* `--output` – Path to save the enriched GPX file (defaults to `*_enriched.gpx`)

**Example Output**
When a summit waypoint has no DoBIH ID, the script will search by name:

```
🔍 Looking up summit by name: 'Ben Nevis'
Found 3 possible match(es):
--------------------------------------------------------------------------------
ID:      1 | Name: Ben Nevis                    | Lat:  56.7969 | Lon:   -5.0037 | Height: 1345m
ID:   1234 | Name: Ben Nevis (North Face)       | Lat:  56.7980 | Lon:   -5.0020 | Height: 1340m
ID:   5678 | Name: Ben Nevis Summit             | Lat:  56.7969 | Lon:   -5.0037 | Height: 1345m
--------------------------------------------------------------------------------
💡 Add a DoBIH ID extension to waypoint 'Ben Nevis' using one of the IDs above.
   Example: <extensions><rr:dobih_number>1</rr:dobih_number></extensions>
```

**Custom Extension Format**
To manually add DoBIH numbers to waypoints, use this format:

```xml
<wpt lat="56.7969" lon="-5.0037">
    <name>Ben Nevis</name>
    <sym>Summit</sym>
    <extensions>
        <rr:dobih_number>1</rr:dobih_number>
    </extensions>
</wpt>
```

**Output**
* A new GPX file with enriched summit waypoints (default: `*_enriched.gpx`)
* Console output showing match results and suggestions for unmatched waypoints
* Updated waypoint coordinates, elevations, and names from the DoBIH database

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
