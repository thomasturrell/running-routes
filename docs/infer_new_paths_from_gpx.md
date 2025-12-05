# Infer New Paths from GPX Files

This script processes GPX files to identify track segments that are not already present in OpenStreetMap (OSM) data. It's designed to help contributors identify new paths that could be added to OSM to improve the completeness of mapping data for runners and hikers.

## Features

- **GPX Track Processing**: Extracts all track points from GPX files (not just waypoints)
- **OSM Data Integration**: Downloads comprehensive OSM path data including footways, tracks, bridleways, and other walkable paths
- **Distance Analysis**: Calculates distances between GPX track points and the nearest OSM paths
- **GPS Accuracy Tolerance**: Applies configurable thresholds to account for GPS inaccuracies and avoid false positives
- **Intelligent Filtering**: Identifies continuous path segments that are significantly away from known OSM paths
- **Multiple Export Formats**: Exports identified new path segments as GPX files for visualization or OSM XML for direct contribution to OpenStreetMap

## Usage

### Basic Usage (GPX Output)

```bash
python scripts/infer_new_paths_from_gpx.py --input route.gpx --output new_paths.gpx
```

### Export as OpenStreetMap XML

```bash
python scripts/infer_new_paths_from_gpx.py --input route.gpx --output new_paths.osm --format osm
```

### Advanced Usage

```bash
python scripts/infer_new_paths_from_gpx.py \
  --input route.gpx \
  --output new_paths.osm \
  --format osm \
  --tolerance 10.0 \
  --min-segment-length 5 \
  --buffer 0.02 \
  --verbose
```

### Testing Without Network Connectivity

```bash
python scripts/infer_new_paths_from_gpx.py \
  --input route.gpx \
  --output new_paths.gpx \
  --dry-run \
  --verbose
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--input` | Required | Path to input GPX file |
| `--output` | Required | Path to save the new paths file |
| `--format` | gpx | Output format: `gpx` (default) or `osm` (OpenStreetMap XML) |
| `--tolerance` | 5.0 | Distance tolerance in meters for GPS inaccuracies |
| `--min-segment-length` | 3 | Minimum number of consecutive points to form a new segment |
| `--buffer` | 0.01 | Buffer in degrees to expand the bounding box for OSM data download |
| `--max-cache-age-days` | 7 | Maximum age of cached OSM graph in days |
| `--force-refresh` | False | Force refresh of cached OSM graph |
| `--verbose` | False | Enable verbose output for debugging |
| `--dry-run` | False | Skip OSM download and use mock data for testing |

## Algorithm

1. **Parse GPX File**: Extract all track points from the input GPX file
2. **Calculate Bounding Box**: Determine the geographic area covered by the track
3. **Download OSM Data**: Fetch or load cached OSM path data for the area
4. **Distance Analysis**: For each track point, calculate the distance to the nearest OSM path
5. **Apply Tolerance**: Identify points that are more than the tolerance distance from any OSM path
6. **Segment Identification**: Group consecutive "distant" points into segments
7. **Filter by Minimum Length**: Only keep segments with enough points to be meaningful
8. **Export Results**: Save the identified new path segments in the chosen format (GPX or OSM XML)

## Output Formats

### GPX Format

The default output format is GPX, which creates a standard GPS Exchange file containing the discovered path segments as tracks. This format is ideal for:
- Viewing in GPS software and mapping applications
- Importing into route planning tools
- Sharing with other users for verification

### OSM XML Format

When using `--format osm`, the script outputs an OpenStreetMap XML file containing:
- **Nodes**: Individual GPS points with precise latitude/longitude coordinates
- **Ways**: Path segments connecting the nodes with appropriate OSM tags
- **Tags**: Standard OSM attributes including:
  - `highway=path` - Identifies the feature as a walking path
  - `source=GPX` - Indicates the data source
  - `note` - Description of the inferred path segment
  - `fixme` - Reminder to verify and add additional tags

The OSM XML format is designed for direct import into OSM editing tools like JOSM or iD editor, making it easy to contribute the discovered paths to OpenStreetMap.

## Tolerance Guidelines

The tolerance parameter should be set based on:

- **GPS Accuracy**: Typical consumer GPS has 3-5m accuracy under good conditions
- **Track Recording Conditions**: Poor weather, dense tree cover, or urban canyons can reduce accuracy
- **OSM Data Precision**: Some OSM paths may not be perfectly positioned

Recommended values:
- **5-10 meters**: For high-quality GPS tracks in good conditions
- **10-20 meters**: For typical recreational GPS tracks
- **20+ meters**: For low-quality GPS or very rough terrain

## Output

The script produces:
- A GPX file containing only the new path segments
- Console output showing statistics about the analysis
- Cache files for OSM data (stored in `.graph_cache/`)

If no new paths are found, an empty GPX file is created for consistency.

## Examples

### Example 1: Finding New Mountain Paths

```bash
# Process a fell running route to find unmapped mountain paths
python scripts/infer_new_paths_from_gpx.py \
  --input src/fell/ramsay-round/ramsay-round.gpx \
  --output new_mountain_paths.gpx \
  --tolerance 15.0 \
  --min-segment-length 5 \
  --verbose
```

### Example 2: Export for OSM Contribution

```bash
# Generate OSM XML file ready for upload to OpenStreetMap
python scripts/infer_new_paths_from_gpx.py \
  --input src/fell/ramsay-round/ramsay-round.gpx \
  --output new_mountain_paths.osm \
  --format osm \
  --tolerance 15.0 \
  --min-segment-length 5 \
  --verbose
```

### Example 3: Urban Route Analysis

```bash
# Analyze urban running route with tighter tolerance
python scripts/infer_new_paths_from_gpx.py \
  --input urban_route.gpx \
  --output new_urban_paths.gpx \
  --tolerance 3.0 \
  --min-segment-length 3 \
  --verbose
```

## Integration with OSM Contribution Workflow

### Using GPX Output
1. **Run the Analysis**: Use this script to identify potential new paths (GPX output)
2. **Validate the Results**: Manually review the output GPX file in a mapping application
3. **Ground Truth**: Visit the identified locations to verify the paths exist
4. **Contribute to OSM**: Use OSM editors like JOSM or iD to add verified paths to OpenStreetMap
5. **Update Local Cache**: Use `--force-refresh` to get updated OSM data including your contributions

### Using OSM XML Output
1. **Run the Analysis**: Use `--format osm` to generate OSM XML directly
2. **Review in JOSM**: Open the OSM file in JOSM to inspect the proposed paths
3. **Ground Truth**: Verify the paths exist in the field
4. **Edit and Upload**: Modify tags as needed (surface, access, etc.) and upload to OSM
5. **Update Local Cache**: Use `--force-refresh` to refresh your local OSM data

## Dependencies

- `gpxpy`: GPX file parsing
- `osmnx`: OpenStreetMap data download and processing  
- `geopy`: Geographic distance calculations
- `shapely`: Geometric operations
- `numpy`: Numerical operations
- `networkx`: Graph operations

## Troubleshooting

### Network Connectivity Issues

If you encounter network errors when downloading OSM data:

```bash
# Use dry-run mode for testing
python scripts/infer_new_paths_from_gpx.py --input route.gpx --output test.gpx --dry-run

# Or try again later when the Overpass API is available
```

### Memory Issues with Large GPX Files

For very large GPX files:
- Reduce the buffer size with `--buffer 0.005`
- Split large GPX files into smaller segments
- Increase the tolerance to reduce processing overhead

### No New Paths Found

If the script reports no new paths:
- Reduce the tolerance value
- Check that your GPX file contains track data (not just waypoints)
- Verify the area has reasonable OSM coverage
- Use `--verbose` to see detailed distance analysis