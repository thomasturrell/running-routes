import argparse
import requests
import zipfile
import pandas as pd
import os
from io import BytesIO
import gpxpy
import gpxpy.gpx
import unicodedata
import xml.etree.ElementTree as ET

# Constants
HILL_ZIP_URL = "https://www.hills-database.co.uk/hillcsv.zip"
CUSTOM_NS = "http://thomasturrell.github.io/running-routes/schema/v1"
CUSTOM_PREFIX = "rr"


def download_and_extract_csv(download_url, extract_to):
    print("Downloading hill database...")
    response = requests.get(download_url)
    response.raise_for_status()

    with zipfile.ZipFile(BytesIO(response.content)) as z:
        for name in z.namelist():
            if name.endswith(".csv"):
                z.extract(name, extract_to)
                full_path = os.path.abspath(os.path.join(extract_to, name))
                print(f"Extracted CSV to: {full_path}")
                return full_path

    raise FileNotFoundError("CSV file not found in the zip archive.")


def load_hill_data(csv_path):
    print("Loading hill data from CSV...")
    df = pd.read_csv(csv_path, low_memory=False)
    df = df[['Number', 'Name', 'Latitude', 'Longitude', 'Metres']].dropna()
    df['NormName'] = df['Name'].apply(normalise_name)
    return df


def normalise_name(name):
    return unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII').strip().lower()


def get_custom_dobih_number(waypoint):
    if waypoint.extensions:
        try:
            ext_xml = ''.join(ET.tostring(e, encoding='unicode') for e in waypoint.extensions)
            root = ET.fromstring(f"<extensions>{ext_xml}</extensions>")
            elem = root.find(f".//{{{CUSTOM_NS}}}dobih_number")
            if elem is not None:
                return elem.text.strip()
        except ET.ParseError:
            pass
    return None


def enrich_gpx_with_hill_data(gpx_path, hill_df):
    print(f"Processing GPX file: {gpx_path}")

    with open(gpx_path, 'r', encoding='utf-8') as f:
        gpx = gpxpy.parse(f)

    updated = 0
    warnings = []

    for waypoint in gpx.waypoints:
        if waypoint.symbol == 'Summit':
            matched_row = None
            hill_id = get_custom_dobih_number(waypoint)

            if hill_id and hill_id.isdigit():
                match = hill_df[hill_df['Number'] == int(hill_id)]
                if not match.empty:
                    matched_row = match.iloc[0]
            elif waypoint.name:
                norm_name = normalise_name(waypoint.name.strip())
                match = hill_df[hill_df['NormName'] == norm_name]
                if not match.empty:
                    matched_row = match.iloc[0]

            if matched_row is not None:
                waypoint.latitude = matched_row['Latitude']
                waypoint.longitude = matched_row['Longitude']
                waypoint.elevation = matched_row['Metres']

                # Ensure DoBIH number is stored as extension
                if waypoint.extensions is None:
                    waypoint.extensions = []
                extension = ET.Element(f"{{{CUSTOM_NS}}}dobih_number")
                extension.text = str(matched_row['Number'])
                waypoint.extensions.append(extension)

                updated += 1
            else:
                name_info = waypoint.name if waypoint.name else "(Unnamed)"
                warnings.append(name_info)

    output_path = os.path.splitext(gpx_path)[0] + '_enriched.gpx'
    with open(output_path, 'w', encoding='utf-8') as f:
        gpx_output = gpx.to_xml()
        gpx_output = gpx_output.replace(
            '<gpx version="1.1" creator="GPXPy">',
            '<gpx version="1.1" creator="GPXPy" xmlns:rr="http://thomasturrell.github.io/running-routes/schema/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 https://www.topografix.com/GPX/1/1/gpx.xsd http://thomasturrell.github.io/running-routes/schema/v1 https://thomasturrell.github.io/running-routes/schema/v1/gpx-extension.xsd">'
        )
        f.write(gpx_output)

    print(f"Updated {updated} summit(s) with coordinates and elevation.")
    if warnings:
        print("\nWARNING: The following summit(s) were not found in the CSV:")
        for name in warnings:
            print(f" - {name}")

    print(f"Enriched GPX saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Enrich GPX summit waypoints with hill data.")
    parser.add_argument("gpx_path", help="Path to the input GPX file")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    working_dir = os.path.join(script_dir, "hillcsv_data")
    os.makedirs(working_dir, exist_ok=True)

    csv_path = download_and_extract_csv(HILL_ZIP_URL, working_dir)
    hill_df = load_hill_data(csv_path)
    enrich_gpx_with_hill_data(args.gpx_path, hill_df)


if __name__ == "__main__":
    main()
