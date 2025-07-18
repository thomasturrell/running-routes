'''
fix_summit_waypoints.py

This script enriches GPX files by updating summit waypoints with accurate coordinates, elevation, and DoBIH (Database of British and Irish Hills) numbers using data from the hills-database.co.uk CSV file.

Features:
- Downloads and extracts hill data from a remote CSV file.
- Matches summit waypoints in GPX files with hill data based on DoBIH number.
- Updates waypoint latitude, longitude, elevation, and adds a custom extension for DoBIH numbers.
- Saves the enriched GPX file with updated summit information.

Usage:
    python fix_summit_waypoints.py <input_gpx_file> [--output <output_gpx_file>]

Example:
    python fix_summit_waypoints.py waypoints.gpx
    python fix_summit_waypoints.py waypoints.gpx --output enriched_waypoints.gpx

Dependencies:
- Python libraries: argparse, requests, zipfile, pandas, gpxpy, xml.etree.ElementTree
- Internet connection to download the hill database.

Output:
- A new GPX file with enriched summit waypoints saved alongside the input file, with "_enriched" appended to the filename.
'''

import argparse
import sys
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

def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments with output path determined.
    """
    if len(sys.argv) == 1:
        print(__doc__)
        sys.exit(0)
    
    parser = argparse.ArgumentParser(description="Enrich GPX summit waypoints with hill data.")
    parser.add_argument('input', help='Path to input GPX file')

    parser.add_argument(
        '--output',
        help='Path to save the enriched GPX file. Defaults to appending _enriched to the input file name.',
        default=None
    )
    
    args = parser.parse_args()
    
    # Determine the output path if not provided
    if args.output is None:
        args.output = os.path.splitext(args.input)[0] + '_enriched.gpx'
    
    return args

def validate_inputs(args):
    """
    Validate all input files and directories.
    
    Args:
        args (argparse.Namespace): Parsed command-line arguments.
        
    Raises:
        SystemExit: If any validation fails.
    """
    # Validate input GPX file exists
    if not os.path.exists(args.input):
        print(f"❌ Error: Input GPX file not found: {args.input}")
        sys.exit(1)
    
    # Validate input is actually a file (not a directory)
    if not os.path.isfile(args.input):
        print(f"❌ Error: Input path is not a file: {args.input}")
        sys.exit(1)
    
    # Validate GPX file extension
    if not args.input.lower().endswith('.gpx'):
        print(f"❌ Error: Input file must be a GPX file: {args.input}")
        sys.exit(1)
    
    # Validate output directory exists (if output path is specified)
    if args.output:
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            print(f"❌ Error: Output directory does not exist: {output_dir}")
            sys.exit(1)
        
        # Check if output file already exists and warn user
        if os.path.exists(args.output):
            print(f"⚠️  Warning: Output file already exists and will be overwritten: {args.output}")
    
    # Validate GPX file can be parsed
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            gpxpy.parse(f)
        print(f"✅ Input GPX file validated: {args.input}")
    except FileNotFoundError:
        print(f"❌ Error: Cannot read GPX file: {args.input}")
        sys.exit(1)
    except gpxpy.gpx.GPXException as e:
        print(f"❌ Error: Invalid GPX file format: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: Unexpected error reading GPX file: {e}")
        sys.exit(1)

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

def find_summits_by_name(hill_df, waypoint_name, max_results=5) -> pd.DataFrame:
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

def enrich_gpx_with_hill_data(input_path: str, hill_df: pd.DataFrame, output_path: str) -> None:
    """Enriches summit waypoints in a GPX file with hill data."""
    print(f"Processing GPX file: {input_path}")

    with open(input_path, 'r', encoding='utf-8') as f:
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
                        print("   Example: <extensions><rr:dobih_number>12345</rr:dobih_number></extensions>")
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
    """Main entry point of the script."""
    args = parse_arguments()

    # Validate inputs
    validate_inputs(args)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    working_dir = os.path.join(script_dir, "hillcsv_data")
    os.makedirs(working_dir, exist_ok=True)

    try:
        csv_path = download_and_extract_csv(HILL_ZIP_URL, working_dir)
        hill_df = load_hill_data(csv_path)
    except Exception as e:
        print(f"❌ Error downloading or processing hill data: {e}")
        sys.exit(1)

    enrich_gpx_with_hill_data(args.input, hill_df, args.output)

if __name__ == "__main__":
    main()
