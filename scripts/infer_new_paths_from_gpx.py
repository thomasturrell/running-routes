"""
infer_new_paths_from_gpx.py

This script processes GPX files to infer paths that are not already present in OpenStreetMap (OSM) data.
It identifies and isolates track segments that do not overlap with known OSM paths, accounting for GPS
inaccuracies through configurable tolerance thresholds.

Features:
- Parses GPX files to extract track points from all segments.
- Downloads OSM data for walkable/bikeable paths within the track's bounding box.
- Compares GPX track points with nearby OSM paths using distance calculations.
- Applies configurable tolerance thresholds to account for GPS inaccuracies.
- Identifies track segments that are significantly away from known OSM paths.
- Outputs new, unmapped route segments as GPX files.

Usage:
    python infer_new_paths_from_gpx.py --input INPUT.gpx --output OUTPUT.gpx [options]

Options:
    --tolerance FLOAT        Distance tolerance in meters for GPS inaccuracies (default: 5.0)
    --min-segment-length INT Minimum number of consecutive points to form a new segment (default: 3)
    --buffer FLOAT           Buffer around bounding box in degrees (default: 0.01)
    --max-cache-age-days INT Maximum number of days before cached graph expires (default: 7)
    --force-refresh          Force refresh of cached graph even if not expired
    --verbose                Enable verbose output for debugging
"""

import argparse
import sys
import gpxpy
import gpxpy.gpx
import osmnx as ox
import numpy as np
from geopy.distance import geodesic
from shapely.geometry import Point, LineString
from shapely.ops import nearest_points
import hashlib
from pathlib import Path
from datetime import datetime, timedelta


def parse_arguments():
    """
    Parse command-line arguments for the script.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    if len(sys.argv) == 1:
        print(__doc__)
        sys.exit(0)
    
    parser = argparse.ArgumentParser(description="Infer new paths from GPX files by comparing with OSM data")
    parser.add_argument('--input', required=True, help='Path to input GPX file')
    parser.add_argument('--output', required=True, help='Path to save the new paths GPX file')
    parser.add_argument('--tolerance', type=float, default=5.0, 
                       help='Distance tolerance in meters for GPS inaccuracies (default: 5.0)')
    parser.add_argument('--min-segment-length', type=int, default=3,
                       help='Minimum number of consecutive points to form a new segment (default: 3)')
    parser.add_argument('--buffer', type=float, default=0.01, 
                       help='Buffer in degrees to expand the bounding box (default: 0.01)')
    parser.add_argument('--max-cache-age-days', type=int, default=7, 
                       help='Max age of cached graph in days (default: 7)')
    parser.add_argument('--force-refresh', action='store_true', 
                       help='Force refresh of cached graph even if cache is valid')
    parser.add_argument('--verbose', action='store_true', 
                       help='Enable verbose output for debugging')
    parser.add_argument('--dry-run', action='store_true',
                       help='Skip OSM download and use mock data for testing')
    
    return parser.parse_args()


def parse_gpx_tracks(file_path, verbose=False):
    """
    Parse GPX file and extract all track points.

    Args:
        file_path (str): Path to the GPX file.
        verbose (bool): Enable verbose output.

    Returns:
        list: List of track points as tuples (latitude, longitude).
    """
    if verbose:
        print(f"[1/6] Parsing GPX file: {file_path}")
    
    try:
        with open(file_path, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
    except (FileNotFoundError, IOError) as e:
        print(f"❌ Error reading file: {e}")
        sys.exit(1)
    except gpxpy.gpx.GPXException as e:
        print(f"❌ Error parsing GPX: {e}")
        sys.exit(1)
    
    track_points = []
    total_segments = 0
    
    for track in gpx.tracks:
        for segment in track.segments:
            total_segments += 1
            for point in segment.points:
                track_points.append((point.latitude, point.longitude))
    
    if verbose:
        print(f"  ↳ {len(track_points)} track points found across {total_segments} segments")
    
    if not track_points:
        print("❌ No track points found in GPX file")
        sys.exit(1)
    
    return track_points


def calculate_bounding_box(track_points, buffer, verbose=False):
    """
    Calculate a bounding box around the track points with a buffer.

    Args:
        track_points (list): List of (lat, lon) tuples.
        buffer (float): Buffer in degrees.
        verbose (bool): Enable verbose output.

    Returns:
        tuple: (north, south, east, west) bounding box coordinates.
    """
    if verbose:
        print("[2/6] Calculating bounding box...")
    
    lats = [point[0] for point in track_points]
    lons = [point[1] for point in track_points]
    
    north = max(lats) + buffer
    south = min(lats) - buffer
    east = max(lons) + buffer
    west = min(lons) - buffer
    
    if verbose:
        print(f"  ↳ Bounding box: N={north:.6f}, S={south:.6f}, E={east:.6f}, W={west:.6f}")
    
    return north, south, east, west


def download_osm_graph(north, south, east, west, max_cache_age_days, force_refresh, verbose=False, dry_run=False):
    """
    Download or load a cached OSM graph for the specified bounding box.
    Includes walkable and bikeable paths that might not be in standard road networks.

    Args:
        north, south, east, west (float): Bounding box coordinates.
        max_cache_age_days (int): Maximum age of cached graph in days.
        force_refresh (bool): Force refresh of cached graph.
        verbose (bool): Enable verbose output.
        dry_run (bool): Skip actual download and create mock graph.

    Returns:
        networkx.Graph: The OSM graph.
    """
    def bbox_hash(w, s, e, n):
        return hashlib.md5(f"{w},{s},{e},{n}".encode()).hexdigest()
    
    if verbose:
        print("[3/6] Downloading OSM data (all paths including footways, tracks, etc.)...")
    
    if dry_run:
        if verbose:
            print("  ↳ Dry run mode: creating mock OSM graph")
        # Create a simple mock graph for testing - put it far from the actual track
        import networkx as nx
        graph = nx.MultiDiGraph()
        # Add mock nodes far from the track points to simulate "no nearby paths"
        mock_west = west - 0.05  # Much further away
        mock_east = mock_west + 0.001  # Small line segment
        mock_south = south - 0.05
        mock_north = mock_south + 0.001
        graph.add_node(1, x=mock_west, y=mock_south)
        graph.add_node(2, x=mock_east, y=mock_north)
        # Add a mock edge with geometry
        from shapely.geometry import LineString
        line_geom = LineString([(mock_west, mock_south), (mock_east, mock_north)])
        graph.add_edge(1, 2, key=0, geometry=line_geom)
        graph.graph['crs'] = 'EPSG:4326'
        if verbose:
            print(f"  ↳ Mock OSM line: ({mock_west:.6f}, {mock_south:.6f}) to ({mock_east:.6f}, {mock_north:.6f})")
        return graph
    
    cache_dir = Path(".graph_cache")
    cache_dir.mkdir(exist_ok=True)
    hash_id = bbox_hash(west, south, east, north)
    cache_file = cache_dir / f"paths_graph_{hash_id}.graphml"

    if cache_file.exists():
        file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_ctime)
        if force_refresh or file_age > timedelta(days=max_cache_age_days):
            if verbose:
                print(f"  ↳ Cache found but expired (age: {file_age.days} days), re-downloading...")
        else:
            if verbose:
                print(f"  ↳ Using cached graph from {cache_file}")
            return ox.load_graphml(cache_file)

    if verbose:
        print("  ↳ No cache found. Downloading from OSM...")
    
    # Custom filter to include various path types that might be used for walking/running
    custom_filter = (
        '["highway"~"path|footway|track|bridleway|cycleway|steps|'
        'residential|service|unclassified|tertiary|secondary|primary|trunk"]'
    )
    
    try:
        graph = ox.graph.graph_from_bbox(
            bbox=(west, south, east, north),
            network_type="walk",
            custom_filter=custom_filter,
            simplify=True,
            retain_all=True,
            truncate_by_edge=True
        )
        
        ox.save_graphml(graph, filepath=cache_file)
        
        if verbose:
            print(f"  ↳ Graph downloaded with {len(graph.nodes)} nodes and {len(graph.edges)} edges")
        
        return graph
    except Exception as e:
        if verbose:
            print(f"❌ Error downloading OSM data: {e}")
            print("  ↳ This might be due to network connectivity issues or Overpass API being unavailable")
            print("  ↳ Try again later or use --dry-run for testing")
        raise


def calculate_distances_to_osm_paths(track_points, osm_graph, verbose=False):
    """
    Calculate distances from each track point to the nearest OSM path.

    Args:
        track_points (list): List of (lat, lon) tuples.
        osm_graph (networkx.Graph): The OSM graph.
        verbose (bool): Enable verbose output.

    Returns:
        list: List of distances in meters for each track point.
    """
    if verbose:
        print("[4/6] Calculating distances to OSM paths...")
    
    distances = []
    
    # Convert OSM edges to LineString geometries for distance calculations
    osm_lines = []
    for u, v, key, data in osm_graph.edges(keys=True, data=True):
        if 'geometry' in data:
            osm_lines.append(data['geometry'])
        else:
            # Create line from node coordinates if no geometry
            u_node = osm_graph.nodes[u]
            v_node = osm_graph.nodes[v]
            line = LineString([(u_node['x'], u_node['y']), (v_node['x'], v_node['y'])])
            osm_lines.append(line)
    
    if verbose:
        print(f"  ↳ Processing {len(track_points)} points against {len(osm_lines)} OSM path segments")
    
    for i, (lat, lon) in enumerate(track_points):
        point = Point(lon, lat)  # Note: shapely uses (x, y) which is (lon, lat)
        
        min_distance = float('inf')
        for line in osm_lines:
            try:
                # Calculate distance using geodesic distance for accuracy
                nearest_point_geom = line.interpolate(line.project(point))
                nearest_lat = nearest_point_geom.y
                nearest_lon = nearest_point_geom.x
                
                distance_meters = geodesic((lat, lon), (nearest_lat, nearest_lon)).meters
                min_distance = min(min_distance, distance_meters)
                
                if verbose and i < 3:  # Debug first few points
                    print(f"    Point {i}: ({lat:.6f}, {lon:.6f}) -> nearest ({nearest_lat:.6f}, {nearest_lon:.6f}), distance: {distance_meters:.1f}m")
            except Exception:
                # Skip problematic geometries
                continue
        
        distances.append(min_distance if min_distance != float('inf') else 1000.0)
        
        if verbose and (i + 1) % 100 == 0:
            print(f"  ↳ Processed {i + 1}/{len(track_points)} points")
    
    if verbose:
        avg_distance = np.mean(distances)
        max_distance = np.max(distances)
        print(f"  ↳ Average distance to OSM paths: {avg_distance:.1f}m, Max: {max_distance:.1f}m")
    
    return distances


def identify_new_path_segments(track_points, distances, tolerance, min_segment_length, verbose=False):
    """
    Identify segments of the track that are significantly away from OSM paths.

    Args:
        track_points (list): List of (lat, lon) tuples.
        distances (list): List of distances in meters for each track point.
        tolerance (float): Distance tolerance in meters.
        min_segment_length (int): Minimum number of consecutive points for a segment.
        verbose (bool): Enable verbose output.

    Returns:
        list: List of new path segments, each segment is a list of (lat, lon) tuples.
    """
    if verbose:
        print(f"[5/6] Identifying new path segments (tolerance: {tolerance}m, min length: {min_segment_length} points)...")
    
    new_segments = []
    current_segment = []
    
    points_beyond_tolerance = sum(1 for d in distances if d > tolerance)
    
    for i, distance in enumerate(distances):
        if distance > tolerance:
            current_segment.append(track_points[i])
        else:
            # End of a potential new segment
            if len(current_segment) >= min_segment_length:
                new_segments.append(current_segment.copy())
            current_segment = []
    
    # Handle segment that goes to the end
    if len(current_segment) >= min_segment_length:
        new_segments.append(current_segment)
    
    total_new_points = sum(len(segment) for segment in new_segments)
    
    if verbose:
        print(f"  ↳ Found {len(new_segments)} new path segments")
        print(f"  ↳ {points_beyond_tolerance}/{len(track_points)} points beyond tolerance")
        print(f"  ↳ {total_new_points} points in valid new segments")
    
    return new_segments


def export_new_paths_to_gpx(new_segments, output_path, verbose=False):
    """
    Export new path segments to a GPX file.

    Args:
        new_segments (list): List of new path segments.
        output_path (str): Path to save the GPX file.
        verbose (bool): Enable verbose output.
    """
    if verbose:
        print(f"[6/6] Exporting {len(new_segments)} new path segments to: {output_path}")
    
    gpx = gpxpy.gpx.GPX()
    gpx.creator = "infer_new_paths_from_gpx.py"
    
    for i, segment_points in enumerate(new_segments):
        track = gpxpy.gpx.GPXTrack()
        track.name = f"New Path Segment {i + 1}"
        
        segment = gpxpy.gpx.GPXTrackSegment()
        
        for lat, lon in segment_points:
            segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=lat, longitude=lon))
        
        track.segments.append(segment)
        gpx.tracks.append(track)
    
    # Write to file
    try:
        with open(output_path, 'w') as f:
            f.write(gpx.to_xml())
        
        if verbose:
            print(f"  ↳ Successfully exported new paths to {output_path}")
        
        return True
    except Exception as e:
        print(f"❌ Error writing GPX file: {e}")
        return False


def main():
    """
    Main entry point of the script.
    """
    args = parse_arguments()
    
    # Step 1: Parse GPX file to extract track points
    track_points = parse_gpx_tracks(args.input, args.verbose)
    
    # Step 2: Calculate bounding box
    north, south, east, west = calculate_bounding_box(track_points, args.buffer, args.verbose)
    
    # Step 3: Download OSM graph
    try:
        osm_graph = download_osm_graph(north, south, east, west, args.max_cache_age_days, 
                                      args.force_refresh, args.verbose, args.dry_run)
    except Exception as e:
        if args.verbose:
            print(f"❌ Failed to download OSM data: {e}")
        print("💡 Suggestion: Try using --dry-run for testing without network connectivity")
        sys.exit(1)
    
    # Step 4: Calculate distances to OSM paths
    distances = calculate_distances_to_osm_paths(track_points, osm_graph, args.verbose)
    
    # Step 5: Identify new path segments
    new_segments = identify_new_path_segments(track_points, distances, args.tolerance, 
                                            args.min_segment_length, args.verbose)
    
    # Step 6: Export results
    if new_segments:
        success = export_new_paths_to_gpx(new_segments, args.output, args.verbose)
        if success:
            total_points = sum(len(segment) for segment in new_segments)
            print(f"✅ Found {len(new_segments)} new path segments with {total_points} total points")
            print(f"   Saved to: {args.output}")
        else:
            sys.exit(1)
    else:
        print("ℹ️  No new paths found - all track points are within tolerance of existing OSM paths")
        # Create empty GPX file for consistency
        empty_gpx = gpxpy.gpx.GPX()
        empty_gpx.creator = "infer_new_paths_from_gpx.py"
        with open(args.output, 'w') as f:
            f.write(empty_gpx.to_xml())
        print(f"   Created empty GPX file: {args.output}")


if __name__ == '__main__':
    main()