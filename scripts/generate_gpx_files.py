# scripts/generate_gpx_files.py

from pathlib import Path
import gpxpy

written_files = []

ROUTES = [
    {
        "name": "Bob Graham Round",
        "source": Path("src/fell/bob-graham-round/bob-graham-round.gpx"),
        "output": Path("docs/assets/gpx/fell/bob-graham-round"),
        "prefix": "bob-graham-round",
    },
    {
        "name": "Ramsay Round",
        "source": Path("src/fell/ramsay-round/ramsay-round.gpx"),
        "output": Path("docs/assets/gpx/fell/ramsay-round"),
        "prefix": "ramsay-round",
    },
    {
        "name": "Paddy Buckley Round",
        "source": Path("src/fell/paddy-buckley-round/paddy-buckley-round.gpx"),
        "output": Path("docs/assets/gpx/fell/paddy-buckley-round"),
        "prefix": "paddy-buckley-round",
    },
    {
        "name": "Allermuir Hill Race",
        "source": Path("src/fell/allermuir-hill-race/allermuir-hill-race.gpx"),
        "output": Path("docs/assets/gpx/fell/allermuir-hill-race"),
        "prefix": "allermuir-hill-race",
    },
    {
        "name": "Wicklow Round",
        "source": Path("src/fell/wicklow-round/wicklow-round.gpx"),
        "output": Path("docs/assets/gpx/fell/wicklow-round"),
        "prefix": "wicklow-round",
    }
]

def load_gpx(path: Path) -> gpxpy.gpx.GPX:
    with path.open() as f:
        return gpxpy.parse(f)

def write_gpx(gpx: gpxpy.gpx.GPX, path: Path):
    gpx.creator = "Thomas Turrell-Croft"
    path.write_text(gpx.to_xml())
    try:
        rel_path = path.relative_to(Path(__file__).parent.parent.resolve())
    except ValueError:
        rel_path = path.resolve()
    print(f"✅ Wrote: {rel_path}")
    written_files.append(str(rel_path))

def extract_summits_and_poi(gpx: gpxpy.gpx.GPX):
    peaks = [wpt for wpt in gpx.waypoints if (wpt.symbol or '').strip().lower() == "summit"]
    poi = [wpt for wpt in gpx.waypoints if (wpt.symbol or '').strip().lower() != "summit"]
    return peaks, poi

def build_summits_gpx(summits):
    g = gpxpy.gpx.GPX()
    for wpt in summits:
        wpt.symbol = "Summit"
    g.waypoints = summits
    return g

def build_poi_gpx(points_of_interest):
    g = gpxpy.gpx.GPX()
    for i, wpt in enumerate(points_of_interest, 1):
        if not wpt.name:
            wpt.name = f"POI {i}"
        if not wpt.symbol:
            wpt.symbol = "Info"
    g.waypoints = points_of_interest
    return g

def build_track_only_gpx(gpx: gpxpy.gpx.GPX):
    g = gpxpy.gpx.GPX()
    g.tracks = gpx.tracks
    return g

def build_simplified_track_gpx(gpx: gpxpy.gpx.GPX, name: str) -> gpxpy.gpx.GPX:
    g = gpxpy.gpx.GPX()
    merged_track = gpxpy.gpx.GPXTrack()
    merged_track.name = f"{name} (Simplified)"
    merged_segment = gpxpy.gpx.GPXTrackSegment()
    for track in gpx.tracks:
        for segment in track.segments:
            merged_segment.points.extend(segment.points)
    merged_track.segments.append(merged_segment)
    g.tracks.append(merged_track)
    return g

def export_individual_legs(gpx: gpxpy.gpx.GPX, output_dir: Path, prefix: str):
    for i, track in enumerate(gpx.tracks, 1):
        leg_gpx = gpxpy.gpx.GPX()
        leg_gpx.tracks.append(track)
        write_gpx(leg_gpx, output_dir / f"{prefix}-leg-{i}.gpx")

def extract_derivative_files(source_path: Path, output_dir: Path, prefix: str, name: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    gpx = load_gpx(source_path)

    summits, poi = extract_summits_and_poi(gpx)
    write_gpx(build_summits_gpx(summits), output_dir / f"{prefix}-summits.gpx")
    write_gpx(build_poi_gpx(poi), output_dir / f"{prefix}-points-of-interest.gpx")
    write_gpx(build_track_only_gpx(gpx), output_dir / f"{prefix}-track.gpx")
    write_gpx(gpx, output_dir / f"{prefix}-detailed.gpx")
    write_gpx(build_simplified_track_gpx(gpx, name), output_dir / f"{prefix}-simplified.gpx")
    export_individual_legs(gpx, output_dir, prefix)

def main():
    for route in ROUTES:
        if not route["source"].exists():
            print(f"⚠️ Warning: Source file for route '{route['name']}' does not exist: {route['source']}")
            continue
        print(f"\n🚀 Processing route: {route['name']}")
        extract_derivative_files(route["source"], route["output"], route["prefix"], route["name"])

    print("\n📦 All Routes Processed Successfully!")
    for file in written_files:
        print(f" - {file}")

if __name__ == "__main__":
    main()
