import os
import gpxpy
import gpxpy.gpx

# Determine base directory relative to script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

SRC = os.path.join(BASE_DIR, "src", "fell", "bob-graham-round", "bob-graham-round.gpx")
GENERATED_DIR = os.path.join(BASE_DIR, "docs", "bob-graham-round", "generated")

def main():
    os.makedirs(GENERATED_DIR, exist_ok=True)

    # Parse the source GPX
    with open(SRC, 'r', encoding='utf-8') as f:
        gpx = gpxpy.parse(f)

    # 1-5: Output a GPX for each leg (one trk per file)
    for i, trk in enumerate(gpx.tracks, 1):
        new_gpx = gpxpy.gpx.GPX()
        new_gpx.creator = gpx.creator
        new_gpx.version = gpx.version
        new_gpx.tracks.append(trk)
        out_name = f"bob-graham-round-leg-{i}.gpx"
        with open(os.path.join(GENERATED_DIR, out_name), 'w', encoding='utf-8') as out_f:
            out_f.write(new_gpx.to_xml())

    # 6: Output a merged GPX with all trkseg in a single trk
    merged_gpx = gpxpy.gpx.GPX()
    merged_gpx.creator = gpx.creator
    merged_gpx.version = gpx.version
    merged_trk = gpxpy.gpx.GPXTrack(name="Bob Graham Round (Simplified)")
    merged_gpx.tracks.append(merged_trk)
    for trk in gpx.tracks:
        for seg in trk.segments:
            merged_trk.segments.append(seg)
    with open(os.path.join(GENERATED_DIR, "bob-graham-round-simplified.gpx"), 'w', encoding='utf-8') as out_f:
        out_f.write(merged_gpx.to_xml())

    # 7: Copy the original complete GPX
    import shutil
    shutil.copyfile(SRC, os.path.join(GENERATED_DIR, "bob-graham-round.gpx"))

    print("GPX export completed successfully.\n")
    print(f"Generated GPX files: {GENERATED_DIR}")

if __name__ == "__main__":
    main()
