"""
plot_route_from_waypoint.py

This script processes a GPX file containing waypoints, calculates routes between them using OpenStreetMap (OSM) data,
and generates a new GPX file with the calculated route. It also supports plotting the route and overlaying fallback
connections between waypoints.

Features:
- Parses GPX files to extract waypoints.
- Validates waypoints for maximum count and distance constraints.
- Downloads OSM data for walkable paths within a bounding box.
- Adds elevation data from the Open-Elevation API to graph nodes and factors elevation gain/loss into routing
  costs.
- Snaps waypoints to the nearest nodes in the OSM graph.
- Creates fallback connections between waypoints for routing when no OSM path exists.
- Calculates routes between waypoints using the shortest path algorithm.
- Exports the calculated route to a GPX file and optionally plots it.

Usage:
    python plot_route_from_waypoints.py --input INPUT.gpx --output OUTPUT.gpx [options]

Options:
    --bounding-box-buffer FLOAT  Buffer around bounding box in degrees (default: 0.05)
    --max-waypoints INT          Maximum number of waypoints (default: 50)
    --max-distance FLOAT         Maximum allowed distance between waypoints in km (default: 20)
    --max-cache-age-days INT     Maximum number of days before cached graph expires (default: 7)
    --force-refresh              Force refresh of cached graph even if not expired
    --snap-threshold FLOAT       Maximum distance in meters for snapping waypoints to paths (default: 5.0)
    --gain-penalty FLOAT         Metres of horizontal cost added per metre climbed (default: 10.0)
    --loss-penalty FLOAT         Metres of horizontal cost added per metre descended (default: 2.0)
"""

import argparse
from collections import defaultdict
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import sys
import os
import gpxpy
import osmnx as ox
import requests
from geopy.distance import geodesic
from shapely.geometry import Point as ShapelyPoint
from shapely.ops import split
from osmnx.projection import project_geometry

# GPX Style namespace
import xml.etree.ElementTree as ET

GPX_STYLE_NS = "http://www.topografix.com/GPX/gpx_style/0/2"

CUSTOM_NS = "http://thomasturrell.github.io/running-routes/schema/v1"
OPEN_ELEVATION_ENDPOINT = "https://api.open-elevation.com/api/v1/lookup"
ELEVATION_CACHE_DIR = Path(".elevation_cache")
ELEVATION_CACHE_FILE = ELEVATION_CACHE_DIR / "srtm_cache.json"

def to_latlon(pt_proj, graph_crs):
    return project_geometry(pt_proj, crs=graph_crs, to_latlong=True)[0]

def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments with output path determined.
    """
    if len(sys.argv) == 1:
        print(__doc__)
        sys.exit(0)
    
    parser = argparse.ArgumentParser(description="Route between GPX waypoints using OpenStreetMap")
    parser.add_argument('input', help='Path to input GPX file')
    parser.add_argument(
        '--output',
        help='Path to save the calculated route as a GPX file. Defaults to appending _route to the input file name.',
        default=None
    )
    parser.add_argument('--max-waypoints', type=int, default=50, help='Maximum number of waypoints allowed (default: 50)')
    parser.add_argument('--max-distance', type=float, default=20, help='Maximum allowed distance between waypoints in km (default: 20)')
    parser.add_argument('--max-cache-age-days', type=int, default=7, help='Max age of cached graph in days (default: 7)')
    parser.add_argument('--force-refresh', action='store_true', help='Force refresh of cached graph even if cache is valid')
    parser.add_argument('--snap-threshold', type=float, default=5.0, help='Maximum distance in meters for snapping waypoints to paths (default: 5.0)')
    parser.add_argument('--gain-penalty', type=float, default=10.0, help='Horizontal metres added per metre of climb (default: 10.0)')
    parser.add_argument('--loss-penalty', type=float, default=2.0, help='Horizontal metres added per metre of descent (default: 2.0)')

    args = parser.parse_args()
    
    # Determine the output path if not provided
    if args.output is None:
        args.output = os.path.splitext(args.input)[0] + '_route.gpx'
    
    return args

def validate_arguments(args):
    """
    Validate all input files and arguments.
    
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
    
    # Validate numeric arguments
    if args.max_waypoints <= 0:
        print(f"❌ Error: Max waypoints must be positive: {args.max_waypoints}")
        sys.exit(1)
    
    if args.max_distance <= 0:
        print(f"❌ Error: Max distance must be positive: {args.max_distance}")
        sys.exit(1)
    
    if args.max_cache_age_days < 0:
        print(f"❌ Error: Max cache age must be non-negative: {args.max_cache_age_days}")
        sys.exit(1)

    if args.snap_threshold < 0:
        print(f"❌ Error: Snap threshold must be non-negative: {args.snap_threshold}")
        sys.exit(1)

    if args.gain_penalty < 0 or args.loss_penalty < 0:
        print("❌ Error: Elevation penalties must be non-negative values")
        sys.exit(1)

def get_custom_section(waypoint):
    """
    Extract the custom section from the waypoint's extensions.

    Args:
        waypoint (gpxpy.gpx.GPXWaypoint): The waypoint to extract the section from.

    Returns:
        str or None: The section if found, otherwise None.
    """
    if waypoint.extensions:
        try:
            ext_xml = ''.join(ET.tostring(e, encoding='unicode') for e in waypoint.extensions)
            root = ET.fromstring(f"<extensions>{ext_xml}</extensions>")
            section_elem = root.find(f".//{{{CUSTOM_NS}}}section")
            if section_elem is not None:
                return section_elem.text.strip()
        except ET.ParseError:
            pass
    return None

def extract_waypoints(input: str, max_waypoints: int, max_distance: float):
    """
    Extract waypoints from a GPX file.

    Args:
        input (str): Path to the GPX file.
        max_waypoints (int): Maximum number of waypoints allowed.
        max_distance (float): Maximum allowed distance between waypoints in km.

    Returns:
        list: List of waypoints as tuples (lat, lon, name, symbol, section).
    """
    try:
        with open(input, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)

        waypoints = []
        for waypoint in gpx.waypoints:
            section = get_custom_section(waypoint)
            waypoints.append((waypoint.latitude, waypoint.longitude, waypoint.name, waypoint.symbol, section))

        print(f"✅ Input GPX file validated: {input} ({len(waypoints)} waypoints found)")

    except FileNotFoundError:
        print(f"❌ Error: Cannot read GPX file: {input}")
        sys.exit(1)
    except gpxpy.gpx.GPXException as e:
        print(f"❌ Error: Invalid GPX file format: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: Unexpected error reading GPX file: {e}")
        sys.exit(1)
    
    # Validate waypoints constraints
    validate_waypoints(waypoints, max_waypoints, max_distance)

    return waypoints

def group_waypoints(waypoints) -> dict:
    """
    Group waypoints by their section attribute.
    
    Args:
        waypoints (list): List of waypoints as tuples (lat, lon, name, symbol, section).

    Returns:
        dict: Dictionary mapping section names to lists of waypoints.
    """
    grouped = defaultdict(list)
    for wpt in waypoints:
        section = wpt[4]
        grouped[section].append([wpt[0], wpt[1], wpt[2], wpt[3]])

    return dict(grouped)

def validate_waypoints(waypoints, max_waypoints, max_distance):
    """
    Validate waypoints for maximum count and distance constraints.

    Args:
        waypoints (list): List of waypoints as tuples (latitude, longitude, name, symbol, section).
        max_waypoints (int): Maximum allowed number of waypoints.
        max_distance (float): Maximum allowed distance between consecutive waypoints in km.

    Raises:
        SystemExit: If validation fails.
    """
    # Filter out waypoints with missing latitude or longitude
    valid_waypoints = [wpt for wpt in waypoints if wpt[0] is not None and wpt[1] is not None]

    if len(valid_waypoints) < len(waypoints):
        print(f"❌ Some waypoints are missing latitude or longitude.")
        sys.exit(1)

    if len(valid_waypoints) > max_waypoints:
        print(f"❌ Too many waypoints ({len(valid_waypoints)} > {max_waypoints}). Use --max-waypoints to override.")
        sys.exit(1)

    def haversine_km(p1, p2):
        return geodesic((p1[0], p1[1]), (p2[0], p2[1])).km

    for i in range(len(valid_waypoints) - 1):
        dist = haversine_km(valid_waypoints[i], valid_waypoints[i + 1])
        if dist > max_distance:
            print(f"❌ Distance between waypoint {i+1} and {i+2} is {dist:.2f} km, exceeding limit of {max_distance} km")
            sys.exit(1)

import math

def calculate_bounding_box(waypoints):
    """
    Calculate a bounding box around the waypoints with a 500m buffer.

    Args:
        waypoints (list): List of waypoints as (lat, lon, ...)

    Returns:
        tuple: Bounding box as (north, south, east, west).
    """
    print(f"Calculating bounding box with 500m buffer")

    if not waypoints:
        raise ValueError("No waypoints provided")

    lats = [w[0] for w in waypoints]
    lons = [w[1] for w in waypoints]

    avg_lat = sum(lats) / len(lats)
    lat_buffer = 500 / 111_000  # ~0.0045 degrees
    lon_buffer = 500 / (111_320 * math.cos(math.radians(avg_lat)))  # longitude degrees vary with latitude

    north = max(lats) + lat_buffer
    south = min(lats) - lat_buffer
    east = max(lons) + lon_buffer
    west = min(lons) - lon_buffer

    print(f"  ↳ Bounding box (lat, lon): North={north}, South={south}, East={east}, West={west}")
    return north, south, east, west


def download_osm_graph(north, south, east, west, max_cache_age_days, force_refresh):
    """
    Download or load a cached OSM graph for the specified bounding box.

    Args:
        north, south, east, west (float): Bounding box coordinates.
        max_cache_age_days (int): Maximum age of cached graph in days.
        force_refresh (bool): Force refresh of cached graph.

    Returns:
        networkx.Graph: The OSM graph.
    """
    def bbox_hash(w, s, e, n):
        return hashlib.md5(f"{w},{s},{e},{n}".encode()).hexdigest()
    
    print("Downloading OSM data")
    cache_dir = Path(".graph_cache")
    cache_dir.mkdir(exist_ok=True)
    hash_id = bbox_hash(west, south, east, north)
    cache_file = cache_dir / f"graph_{hash_id}.graphml"

    if cache_file.exists():
        file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_ctime)
        if force_refresh or file_age > timedelta(days=max_cache_age_days):
            print(f"  ↳ Cache found but expired (age: {file_age.days} days), re-downloading...")
        else:
            print(f"  ↳ Using cached graph from {cache_file}")
            return ox.load_graphml(cache_file)

    print("  ↳ No cache found. Downloading from OSM...")
    graph = ox.graph.graph_from_bbox((west, south, east, north), network_type='all', simplify=False, truncate_by_edge=True)
    graph = ox.project_graph(graph)
    print("Graph CRS:", graph.graph.get('crs', '❌ Not defined'))

    ox.save_graphml(graph, filepath=cache_file)
    print("  ↳ Graph downloaded with", len(graph.nodes), "nodes and", len(graph.edges), "edges")
    print(f"Graph has {len(graph.nodes)} nodes and {len(graph.edges)} edges.")
    import networkx as nx
    if not nx.is_connected(graph.to_undirected()):
        print("⚠️ The graph is not fully connected. Some nodes may be isolated.")
    return graph


def _batched(iterable, batch_size):
    for i in range(0, len(iterable), batch_size):
        yield iterable[i:i + batch_size]


def _round_lat_lon(pt_latlon, precision=5):
    return (round(pt_latlon.y, precision), round(pt_latlon.x, precision))


def _load_elevation_cache(cache_file=None):
    cache_file = cache_file or ELEVATION_CACHE_FILE
    try:
        if cache_file.exists():
            with cache_file.open() as f:
                return json.load(f)
    except (OSError, json.JSONDecodeError):
        # If the cache file cannot be loaded (missing, unreadable, or invalid JSON), return an empty cache.
        pass
    return {}


def _save_elevation_cache(cache, cache_file=None):
    cache_file = cache_file or ELEVATION_CACHE_FILE
    try:
        cache_file.parent.mkdir(exist_ok=True)
        with cache_file.open('w') as f:
            json.dump(cache, f)
    except OSError:
        print("⚠️ Failed to save elevation cache")


def fetch_srtm_elevations(graph, nodes=None, batch_size=90):
    """
    Fetch elevation for a list of graph nodes using the Open-Elevation API.

    Args:
        graph (networkx.Graph): Projected graph containing nodes with x/y coordinates.
        nodes (list): Optional list of node IDs to fetch. Defaults to all nodes.
        batch_size (int): Number of coordinates to include per request.

    Returns:
        dict: Mapping of node_id -> elevation in metres.
    """
    nodes = nodes or list(graph.nodes)
    if not nodes:
        return {}

    cache = _load_elevation_cache()
    node_keys = {}
    missing_keys = set()

    for node in nodes:
        pt_latlon = to_latlon(ShapelyPoint(graph.nodes[node]['x'], graph.nodes[node]['y']), graph.graph['crs'])
        lat, lon = _round_lat_lon(pt_latlon)
        coord_key = f"{lat},{lon}"
        node_keys[node] = coord_key
        if coord_key not in cache:
            missing_keys.add(coord_key)

    if missing_keys:
        print(f"Downloading elevation data from Open-Elevation API (missing {len(missing_keys)} nodes)")
        updated = False
        for batch in _batched(sorted(missing_keys), batch_size):
            locations = []
            for coord_key in batch:
                lat_str, lon_str = coord_key.split(",")
                locations.append({"latitude": float(lat_str), "longitude": float(lon_str)})
            payload = {"locations": locations}
            try:
                response = requests.post(OPEN_ELEVATION_ENDPOINT, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()
                results = data.get('results') or []
                for result in results:
                    if isinstance(result, dict):
                        elevation = result.get('elevation')
                        lat = result.get('latitude')
                        lon = result.get('longitude')
                        if lat is not None and lon is not None and elevation is not None:
                            key = f"{round(lat, 5)},{round(lon, 5)}"
                            cache[key] = elevation
                            updated = True
            except requests.RequestException as exc:
                print(f"⚠️ Failed to fetch elevations: {exc}")
                break
        if updated:
            _save_elevation_cache(cache)
    else:
        print("Using cached elevation data")

    elevations = {node: cache[key] for node, key in node_keys.items() if key in cache}
    print(f"  ↳ Retrieved elevation for {len(elevations)}/{len(nodes)} nodes")
    return elevations


def _edge_length(graph, u, v, data):
    if data.get('length') is not None:
        return data['length']
    if 'geometry' in data:
        return data['geometry'].length
    try:
        return geodesic((graph.nodes[u]['y'], graph.nodes[u]['x']), (graph.nodes[v]['y'], graph.nodes[v]['x'])).m
    except Exception:
        return 0


def add_elevation_costs(graph, gain_penalty=10.0, loss_penalty=2.0):
    """
    Add elevation gain/loss aware cost to each edge using pre-populated node elevations.

    Args:
        graph (networkx.MultiDiGraph): Graph with node elevations in metres.
        gain_penalty (float): Horizontal metre cost per metre climbed.
        loss_penalty (float): Horizontal metre cost per metre descended.
    """
    for u, v, key, data in graph.edges(keys=True, data=True):
        elev_u = graph.nodes[u].get('elevation')
        elev_v = graph.nodes[v].get('elevation')

        gain = loss = 0
        if elev_u is not None and elev_v is not None:
            gain = max(0, elev_v - elev_u)
            loss = max(0, elev_u - elev_v)

        length = _edge_length(graph, u, v, data)
        data['length'] = length
        data['elevation_gain'] = gain
        data['elevation_loss'] = loss
        data['cost'] = length + gain_penalty * gain + loss_penalty * loss


def add_srtm_elevation_to_graph(graph, gain_penalty=10.0, loss_penalty=2.0):
    """
    Annotate the graph with elevation data from OpenTopography and attach elevation-aware routing costs.

    Args:
        graph (networkx.MultiDiGraph): Graph to annotate.
        gain_penalty (float): Horizontal metre cost per metre climbed.
        loss_penalty (float): Horizontal metre cost per metre descended.

    Returns:
        networkx.MultiDiGraph: Graph with elevation metadata and cost weights.
    """
    elevations = fetch_srtm_elevations(graph)
    if not elevations:
        print("⚠️ Elevation data could not be fetched; routing will use distance only")
        return graph

    print("Applying elevation data to graph nodes and edges")
    ox.utils_graph.set_node_attributes(graph, elevations, name='elevation')
    add_elevation_costs(graph, gain_penalty=gain_penalty, loss_penalty=loss_penalty)
    return graph


def select_weight_attribute(graph):
    """Choose the best weight attribute for routing."""
    has_cost = any('cost' in data for _, _, data in graph.edges(data=True))
    return 'cost' if has_cost else 'length'

def snap_waypoints_to_graph(graph, waypoints, snap_threshold=5.0):
    """
    Snap waypoints to the nearest edge in the OSM graph by inserting a new node at the projection point.
    Splits the original edge into two with accurate geometry and weights.
    Only snaps waypoints within the specified distance threshold.

    Args:
        graph (networkx.Graph): The OSM graph.
        waypoints (list): List of waypoints as tuples (lat, lon, name, symbol).
        snap_threshold (float): Maximum distance in meters for snapping waypoints to paths.

    Returns:
        tuple[list, list]: List of snapped node IDs and the filtered waypoints kept within the threshold.
    """
    print(f"Snapping waypoints to nearest graph edges (threshold: {snap_threshold}m)...")

    snapped_nodes = []
    kept_waypoints = []
    skipped_waypoints = []

    for wpt in waypoints:
        lat, lon, name, sym = wpt[:4]  # Safe unpacking
        point_wgs = ShapelyPoint(lon, lat)
        point_proj = ox.projection.project_geometry(point_wgs, to_crs=graph.graph['crs'])[0]
        x, y = point_proj.x, point_proj.y

        nearest_node, distance = ox.distance.nearest_nodes(graph, x, y, return_dist=True)

        if distance > snap_threshold:
            print(f"⚠️ Node for waypoint '{name}' is {distance:.1f}m away (>{snap_threshold}m threshold) - skipping")
            skipped_waypoints.append((name, distance))
        else:
            snapped_nodes.append(nearest_node)
            kept_waypoints.append(wpt)
            print(f"  ↳ Snapped waypoint '{name}' to node {nearest_node} ({distance:.1f}m)")

    if skipped_waypoints:
        print(f"⚠️ Summary: {len(skipped_waypoints)} waypoint(s) were skipped (beyond {snap_threshold}m threshold):")
        for name, distance in skipped_waypoints:
            print(f"  - {name}: {distance:.1f}m")

    return snapped_nodes, kept_waypoints

def calculate_paths(graph, node_ids):
    """
    Calculate paths between nodes using the shortest path algorithm.

    Args:
        graph (networkx.Graph): The OSM graph.
        node_ids (list): List of node IDs.

    Returns:
        list: List of paths, each path is a list of node IDs.
    """
    print("Calculating paths between nodes...")
    import networkx as nx
    paths = []
    weight_attr = select_weight_attribute(graph)
    for i in range(len(node_ids) - 1):
        try:
            path = nx.shortest_path(graph, node_ids[i], node_ids[i+1], weight=weight_attr)
        except nx.NetworkXNoPath:
            print(f"  ⚠️ No path found between node {i+1} and {i+2}, inserting fallback path")
            path = [node_ids[i], node_ids[i+1]]
        paths.append(path)
    return paths


def calculate_routes(graph, node_ids):
    """Backward compatible wrapper used by tests."""
    return calculate_paths(graph, node_ids)

def calculate_track_color(route_name):
    """
    Assign a bold, vivid color hex code to a route based on its name.
    Uses a curated palette of strong colors.
    """
    import hashlib

    palette = [
        "e6194b",  # red
        "3cb44b",  # green
        "ffe119",  # yellow
        "0082c8",  # blue
        "f58231",  # orange
        "911eb4",  # purple
        "46f0f0",  # cyan
        "f032e6",  # magenta
        "d2f53c",  # lime
        "fabebe",  # pink
    ]
    if not route_name:
        return "0082c8"  # default blue
    h = int(hashlib.md5(route_name.encode()).hexdigest(), 16)
    return palette[h % len(palette)]


def export_routes_to_gpx(graph, routes, waypoints, output_path_gpx):
    """
    Export the calculated routes to a GPX file with separate tracks for each section.

    Args:
        graph (networkx.Graph): The OSM graph.
        routes (dict): Dictionary mapping route names to lists of paths.
        waypoints (list): List of original waypoints.
        output_path_gpx (str): Path to save the GPX file.
    """
    print(f"Exporting routes to GPX: {output_path_gpx}")
    import gpxpy.gpx
    gpx = gpxpy.gpx.GPX()

    # Add input waypoints - handle both 4 and 5 element tuples
    for wpt in waypoints:
        lat, lon, name, sym = wpt[:4]  # Safe unpacking
        gpx.waypoints.append(gpxpy.gpx.GPXWaypoint(latitude=lat, longitude=lon, name=name, symbol=sym))

    for route_name, route_paths in routes.items():
        if not route_paths:  # Skip empty routes
            continue
            
        print(f"  ↳ Exporting route: {route_name} with {len(route_paths)} segments")
        
        # Create a track for this section
        track = gpxpy.gpx.GPXTrack()
        track.name = route_name if route_name else "Unnamed Section"

        # Build <line> element under the GPX Style namespace
        line_elem = ET.Element(f"{{{GPX_STYLE_NS}}}line")
        ET.SubElement(line_elem, f"{{{GPX_STYLE_NS}}}color").text = calculate_track_color(route_name)
        #ET.SubElement(line_elem, f"{{{GPX_STYLE_NS}}}opacity").text = "0.8"
        #ET.SubElement(line_elem, f"{{{GPX_STYLE_NS}}}width").text = "4"


        # Attach it as an extension to the track
        track.extensions = [line_elem]

        segment = gpxpy.gpx.GPXTrackSegment()
        
        for path in route_paths:
            for u, v in zip(path[:-1], path[1:]):
                edge_data = graph.get_edge_data(u, v)
                if edge_data is None:
                    continue
                    
                # Handle MultiDiGraph edge data properly
                if isinstance(edge_data, dict):
                    edge = edge_data.get(0, edge_data[next(iter(edge_data))])
                else:
                    edge = edge_data

                if 'geometry' in edge:
                    coords = list(edge['geometry'].coords)
                    for idx, (x, y) in enumerate(coords):
                        pt = ShapelyPoint(x, y)
                        pt_latlon = to_latlon(pt, graph.graph['crs'])
                        elevation = None
                        if idx == 0:
                            elevation = graph.nodes[u].get('elevation')
                        elif idx == len(coords) - 1:
                            elevation = graph.nodes[v].get('elevation')
                        segment.points.append(gpxpy.gpx.GPXTrackPoint(pt_latlon.y, pt_latlon.x, elevation=elevation))
                else:
                    pt_u = to_latlon(ShapelyPoint(graph.nodes[u]['x'], graph.nodes[u]['y']), graph.graph['crs'])
                    pt_v = to_latlon(ShapelyPoint(graph.nodes[v]['x'], graph.nodes[v]['y']), graph.graph['crs'])
                    segment.points.append(gpxpy.gpx.GPXTrackPoint(pt_u.y, pt_u.x, elevation=graph.nodes[u].get('elevation')))
                    segment.points.append(gpxpy.gpx.GPXTrackPoint(pt_v.y, pt_v.x, elevation=graph.nodes[v].get('elevation')))

        
        track.segments.append(segment)
        gpx.tracks.append(track)

    # Add custom namespace to GPX content
    gpx.nsmap["gpxstyle"] = GPX_STYLE_NS
    gpx.nsmap["rr"] = CUSTOM_NS
    gpx.creator = "Running Routes Script v1.0"

    gpx_content = gpx.to_xml()


    with open(output_path_gpx, 'w') as f:
        f.write(gpx_content)
    print(f"  ↳ GPX file written with {len(gpx.tracks)} track(s)")

    return gpx


def export_route_to_gpx(graph, routes, waypoints, output_path_gpx):
    """Wrapper to export a single unnamed route list (backwards compatibility)."""
    return export_routes_to_gpx(graph, {None: routes}, waypoints, output_path_gpx)

def main():
    """
    Main entry point of the script.
    """
    args = parse_arguments()
    validate_arguments(args)

    waypoints = extract_waypoints(args.input, args.max_waypoints, args.max_distance)
    north, south, east, west = calculate_bounding_box(waypoints)
    graph = download_osm_graph(north, south, east, west, args.max_cache_age_days, args.force_refresh)
    graph = add_srtm_elevation_to_graph(graph, gain_penalty=args.gain_penalty, loss_penalty=args.loss_penalty)

    groups = group_waypoints(waypoints)

    routes = defaultdict(list)

    for route_name, route_waypoints in groups.items():
        print(f"Processing route: {route_name} with {len(route_waypoints)} waypoints")
        if len(route_waypoints) < 2:
            print(f"⚠️ Route '{route_name}' has less than 2 waypoints, skipping routing")
            continue

        node_ids, filtered_waypoints = snap_waypoints_to_graph(graph, route_waypoints, args.snap_threshold)

        if len(node_ids) < 2:
            print(f"⚠️ Route '{route_name}' has insufficient snapped waypoints, skipping routing")
            continue

        # Calculate routes between snapped waypoints
        route = calculate_paths(graph, node_ids)
        routes[route_name].extend(route)

    export_routes_to_gpx(graph, routes, waypoints, args.output)


if __name__ == '__main__':
    main()