'''
fix_summit_waypoints.py

This script enriches GPX files by updating summit waypoints with accurate coordinates, elevation, and DoBIH (Database of British and Irish Hills) numbers using data from the hills-database.co.uk CSV file.

Features:
- Downloads and extracts hill data from a remote CSV file.
- Matches summit waypoints in GPX files with hill data based on DoBIH number.
- Updates waypoint latitude, longitude, elevation, and adds a custom extension for DoBIH numbers.
- Saves the enriched GPX file with updated summit information.

Usage:
    python fix_summit_waypoints.py <path_to_gpx_file>

Example:
    python fix_summit_waypoints.py input=input.gpx

Dependencies:
- Python libraries: argparse, requests, zipfile, pandas, gpxpy, xml.etree.ElementTree
- Internet connection to download the hill database.

Output:
- A new GPX file with enriched summit waypoints saved alongside the input file, with "_enriched" appended to the filename.
'''

import argparse
import requests
import zipfile
import pandas as pd
import os
from io import BytesIO
import gpxpy
import gpxpy.gpx
import xml.etree.ElementTree as ET

# Constants
HILL_ZIP_URL = "https://www.hills-database.co.uk/hillcsv.zip"
CUSTOM_NS = "http://thomasturrell.github.io/running-routes/schema/v1"
CUSTOM_PREFIX = "rr"

def download_and_extract_csv(download_url, extract_to):
    """
    Downloads and extracts the hill database CSV file from the given URL.

    Args:
        download_url (str): URL to download the zip file containing the CSV.
        extract_to (str): Directory to extract the CSV file.

    Returns:
        str: Path to the extracted CSV file.

    Raises:
        FileNotFoundError: If no CSV file is found in the zip archive.
    """
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
    """
    Loads hill data from the extracted CSV file.

    Args:
        csv_path (str): Path to the CSV file.

    Returns:
        pandas.DataFrame: DataFrame containing hill data.
    """
    print("Loading hill data from CSV...")
    df = pd.read_csv(csv_path, low_memory=False)
    return df[['Number', 'Name', 'Latitude', 'Longitude', 'Metres']].dropna()

def get_custom_dobih_number(waypoint):
    """
    Extracts the DoBIH number from a waypoint's custom extensions.

    Args:
        waypoint (gpxpy.gpx.GPXWaypoint): GPX waypoint.

    Returns:
        str or None: DoBIH number if found, otherwise None.
    """
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

def find_summits_by_name(hill_df, waypoint_name, max_results=5):
    """
    Find summits by name in the hill database.

    Args:
        hill_df (pandas.DataFrame): DataFrame containing hill data.
        waypoint_name (str): Name of the waypoint to search for.
        max_results (int): Maximum number of results to return.

    Returns:
        pandas.DataFrame: DataFrame containing matching summits.
    """
    if not waypoint_name:
        return pd.DataFrame()
    
    # Case-insensitive partial match search
    matches = hill_df[hill_df['Name'].str.contains(waypoint_name, case=False, na=False, regex=False)]
    
    # If no partial matches, try exact match
    if matches.empty:
        matches = hill_df[hill_df['Name'].str.lower() == waypoint_name.lower()]
    
    return matches.head(max_results)

def enrich_gpx_with_hill_data(gpx_path, hill_df, output_path):
    """
    Enriches summit waypoints in a GPX file with hill data.

    Args:
        gpx_path (str): Path to the input GPX file.
        hill_df (pandas.DataFrame): DataFrame containing hill data.
        output_path (str): Path to save the enriched GPX file.

    Output:
        Saves an enriched GPX file with updated summit information.
    """
    print(f"Processing GPX file: {gpx_path}")

    with open(gpx_path, 'r', encoding='utf-8') as f:
        gpx = gpxpy.parse(f)

    updated = 0
    warnings = []

    for waypoint in gpx.waypoints:
        if waypoint.symbol == 'Summit':
            hill_id = get_custom_dobih_number(waypoint)

            if hill_id and hill_id.isdigit():
                # DoBIH ID found, try to match by ID
                match = hill_df[hill_df['Number'] == int(hill_id)]
                if not match.empty:
                    matched_row = match.iloc[0]
                    waypoint.latitude = matched_row['Latitude']
                    waypoint.longitude = matched_row['Longitude']
                    waypoint.elevation = matched_row['Metres']
                    waypoint.name = matched_row['Name']
                    updated += 1
                else:
                    warnings.append(f"ID {hill_id} not found in hill database.")
            else:
                # No valid DoBIH ID, try to lookup by name
                if waypoint.name:
                    print(f"\n🔍 Looking up summit by name: '{waypoint.name}'")
                    name_matches = find_summits_by_name(hill_df, waypoint.name)
                    
                    if not name_matches.empty:
                        print(f"Found {len(name_matches)} possible match(es):")
                        print("-" * 80)
                        for idx, row in name_matches.iterrows():
                            print(f"ID: {row['Number']:>6} | Name: {row['Name']:<30} | "
                                  f"Lat: {row['Latitude']:>8.4f} | Lon: {row['Longitude']:>9.4f} | "
                                  f"Height: {row['Metres']:>4.0f}m")
                        print("-" * 80)
                        print(f"💡 Add a DoBIH ID extension to waypoint '{waypoint.name}' using one of the IDs above.")
                        print("   Example: <extensions><rr:dobih_number xmlns:rr=\"http://thomasturrell.github.io/running-routes/schema/v1\">12345</rr:dobih_number></extensions>")
                    else:
                        print(f"❌ No summits found matching name: '{waypoint.name}'")
                        
                    warnings.append(f"Waypoint '{waypoint.name}' has no DoBIH ID - see suggestions above.")
                else:
                    warnings.append(f"Waypoint has no name and no DoBIH ID.")

    with open(output_path, 'w', encoding='utf-8') as f:
        gpx_output = gpx.to_xml()
        gpx_output = gpx_output.replace(
            '<gpx version="1.1" creator="GPXPy">',
            '<gpx version="1.1" creator="GPXPy" xmlns:rr="http://thomasturrell.github.io/running-routes/schema/v1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 https://www.topografix.com/GPX/1/1/gpx.xsd http://thomasturrell.github.io/running-routes/schema/v1 https://thomasturrell.github.io/running-routes/schema/v1/gpx-extension.xsd">'
        )
        f.write(gpx_output)

    print(f"\n✅ Updated {updated} summit(s) with coordinates and elevation.")
    if warnings:
        print("\n⚠️  SUMMARY - The following summit(s) were not updated:")
        for warning in warnings:
            print(f" - {warning}")

    print(f"\n📁 Enriched GPX saved to: {output_path}")

def main():
    """
    Main function to parse arguments and execute the script.
    """
    parser = argparse.ArgumentParser(description="Enrich GPX summit waypoints with hill data.")
    parser.add_argument("input", help="Path to the input GPX file")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    working_dir = os.path.join(script_dir, "hillcsv_data")
    os.makedirs(working_dir, exist_ok=True)

    csv_path = download_and_extract_csv(HILL_ZIP_URL, working_dir)
    hill_df = load_hill_data(csv_path)
    enrich_gpx_with_hill_data(args.input, hill_df, 
                               os.path.splitext(args.input)[0] + "_enriched.gpx")

if __name__ == "__main__":
    main()
