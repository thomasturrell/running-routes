"""
plot_route_from_waypoint.py

This script processes a GPX file containing waypoints, calculates routes between them using OpenStreetMap (OSM) data, 
and generates a new GPX file with the calculated route. It also supports plotting the route and overlaying fallback 
connections between waypoints.

Features:
- Parses GPX files to extract waypoints.
- Validates waypoints for maximum count and distance constraints.
- Downloads OSM data for walkable paths within a bounding box.
- Snaps waypoints to the nearest nodes in the OSM graph.
- Creates fallback connections between waypoints for routing when no OSM path exists.
- Calculates routes between waypoints using the shortest path algorithm.
- Exports the calculated route to a GPX file and optionally plots it.

Usage:
    python plot2.py --input INPUT.gpx --gpx-output OUTPUT.gpx [options]

Options:
    --buffer FLOAT           Buffer around bounding box in degrees (default: 0.05)
    --max-points INT         Maximum number of waypoints (default: 50)
    --max-distance FLOAT     Maximum allowed distance between waypoints in km (default: 20)
    --max-cache-age-days INT Maximum number of days before cached graph expires (default: 7)
    --force-refresh          Force refresh of cached graph even if not expired
"""

import argparse
import sys
import os
import gpxpy
import osmnx as ox
from geopy.distance import geodesic
import hashlib
from pathlib import Path

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
    parser.add_argument('--bounding-box-buffer', type=float, default=0.05, help='Buffer in degrees to expand the bounding box (default: 0.05)')
    parser.add_argument('--max-points', type=int, default=50, help='Maximum number of waypoints allowed (default: 50)')
    parser.add_argument('--max-distance', type=float, default=20, help='Maximum allowed distance between waypoints in km (default: 20)')
    parser.add_argument('--max-cache-age-days', type=int, default=7, help='Max age of cached graph in days (default: 7)')
    parser.add_argument('--force-refresh', action='store_true', help='Force refresh of cached graph even if cache is valid')
    parser.add_argument('--snap-threshold', type=float, default=5.0, help='Maximum distance in meters for snapping waypoints to paths (default: 5.0)')
    
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
    if args.bounding_box_buffer < 0:
        print(f"❌ Error: Bounding box buffer must be non-negative: {args.bounding_box_buffer}")
        sys.exit(1)
    
    if args.max_points <= 0:
        print(f"❌ Error: Max points must be positive: {args.max_points}")
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

def extract_waypoints(input: str, max_points: int, max_distance: float):
    """
    Extract waypoints from a GPX file.

    Args:
        gpx_file (str): Path to the GPX file.

    Returns:
        List[Waypoint]: List of Waypoint objects extracted from the GPX file.
    """
    # Validate GPX file can be parsed and extract waypoints for further validation
    try:
        with open(input, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
        waypoints = [(wpt.latitude, wpt.longitude, wpt.name, wpt.symbol, wpt.extensions) for wpt in gpx.waypoints]
        print(f"✅ Input GPX file validated: {input} ({len(waypoints)} waypoints found)")
        # prints out all waypoints found
        for i, wpt in enumerate(waypoints, start=1):
            print(f"  ↳ Waypoint {i}: {wpt}")

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
    validate_waypoints(waypoints, max_points, max_distance)

    return waypoints

def validate_waypoints(waypoints, max_points, max_distance):
    """
    Validate waypoints for maximum count and distance constraints.

    Args:
        waypoints (list): List of waypoints as tuples (latitude, longitude, name, symbol).
        max_points (int): Maximum allowed number of waypoints.
        max_distance (float): Maximum allowed distance between consecutive waypoints in km.

    Raises:
        SystemExit: If validation fails.
    """
    # Filter out waypoints with missing latitude or longitude
    valid_waypoints = [wpt for wpt in waypoints if wpt[0] is not None and wpt[1] is not None]

    if len(valid_waypoints) < len(waypoints):
        print(f"❌ Some waypoints are missing latitude or longitude.")
        sys.exit(1)

    if len(valid_waypoints) > max_points:
        print(f"❌ Too many waypoints ({len(valid_waypoints)} > {max_points}). Use --max-points to override.")
        sys.exit(1)

    def haversine_km(p1, p2):
        return geodesic((p1[0], p1[1]), (p2[0], p2[1])).km

    for i in range(len(valid_waypoints) - 1):
        dist = haversine_km(valid_waypoints[i], valid_waypoints[i + 1])
        if dist > max_distance:
            print(f"❌ Distance between waypoint {i+1} and {i+2} is {dist:.2f} km, exceeding limit of {max_distance} km")
            sys.exit(1)

def calculate_bounding_box(waypoints, buffer):
    """
    Calculate a bounding box around the waypoints with a buffer.

    Args:
        waypoints (list): List of waypoints.
        buffer (float): Buffer in degrees to expand the bounding box.

    Returns:
        tuple: Bounding box as (north, south, east, west).
    """
    print(f"Calculating bounding box with buffer: {buffer}°")
    
    if not waypoints:
        raise ValueError("No waypoints provided")
    
    lats = [w[0] for w in waypoints]
    lons = [w[1] for w in waypoints]

    north = max(lats) + buffer
    south = min(lats) - buffer
    east = max(lons) + buffer
    west = min(lons) - buffer

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
        from datetime import datetime, timedelta
        file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_ctime)
        if force_refresh or file_age > timedelta(days=max_cache_age_days):
            print(f"  ↳ Cache found but expired (age: {file_age.days} days), re-downloading...")
        else:
            print(f"  ↳ Using cached graph from {cache_file}")
            return ox.load_graphml(cache_file)

    print("  ↳ No cache found. Downloading from OSM...")
    graph = ox.graph.graph_from_bbox((west, south, east, north))
    ox.save_graphml(graph, filepath=cache_file)
    print("  ↳ Graph downloaded with", len(graph.nodes), "nodes and", len(graph.edges), "edges")
    print(f"Graph has {len(graph.nodes)} nodes and {len(graph.edges)} edges.")
    import networkx as nx
    if not nx.is_connected(graph.to_undirected()):
        print("⚠️ The graph is not fully connected. Some nodes may be isolated.")
    return graph

def snap_waypoints_to_graph(graph, waypoints, snap_threshold=5.0):
    """
    Snap waypoints to the nearest edge in the OSM graph by inserting a new node at the projection point.
    Splits the original edge into two with accurate geometry and weights.
    Only snaps waypoints within the specified distance threshold.

    Args:
        graph (networkx.Graph): The OSM graph.
        waypoints (list): List of waypoints.
        snap_threshold (float): Maximum distance in meters for snapping waypoints to paths.

    Returns:
        tuple: (snapped_node_ids, filtered_waypoints) - only for waypoints within threshold.
    """
    print(f"[4/6] Snapping waypoints to nearest graph edges (threshold: {snap_threshold}m)...")
    import shapely.geometry
    from shapely.ops import split
    import networkx as nx

    snapped_nodes = []
    filtered_waypoints = []
    skipped_waypoints = []
    next_node_id = max(graph.nodes) + 1

    for lat, lon, name, sym in waypoints:
        # First check distance threshold
        try:
            edge_info, distance = ox.distance.nearest_edges(graph, lon, lat, return_dist=True)
            u, v, key = edge_info
            
            # Check if waypoint is within threshold
            if distance > snap_threshold:
                print(f"⚠️ Waypoint '{name}' is {distance:.1f}m from nearest path (>{snap_threshold}m threshold) - skipping")
                skipped_waypoints.append((name, distance))
                continue
        except Exception as e:
            print(f"⚠️ Failed getting distance for waypoint '{name}' — {e}")
            print("  ↳ Skipping due to inability to check threshold")
            continue
            
        # If we get here, waypoint is within threshold for edge snapping
        try:
            edge_data = graph.get_edge_data(u, v)[key]

            # Get geometry
            if 'geometry' in edge_data:
                line = edge_data['geometry']
            else:
                point_u = shapely.geometry.Point((graph.nodes[u]['x'], graph.nodes[u]['y']))
                point_v = shapely.geometry.Point((graph.nodes[v]['x'], graph.nodes[v]['y']))
                line = shapely.geometry.LineString([point_u, point_v])

            total_length = line.length
            if total_length == 0:
                raise ValueError(f"Zero-length edge: {u} → {v}")

            # Project the waypoint onto the edge geometry
            point = shapely.geometry.Point((lon, lat))
            projected_point = line.interpolate(line.project(point))
            proj_lon, proj_lat = projected_point.x, projected_point.y

            # Split geometry at projection point
            split_result = split(line, projected_point)

            # Extract only LineStrings from the result
            split_lines = [geom for geom in split_result.geoms if isinstance(geom, shapely.geometry.LineString)]

            if len(split_lines) != 2:
                raise ValueError(f"Expected 2 LineStrings after split, got {len(split_lines)} — likely projected at edge endpoint")

            geom1, geom2 = split_lines

            geom1, geom2 = split_result[0], split_result[1]
            weight1 = geom1.length
            weight2 = geom2.length

            # Insert the new node
            new_node_id = next_node_id
            next_node_id += 1
            graph.add_node(new_node_id, x=proj_lon, y=proj_lat)

            # Remove old edge and insert two new ones
            graph.remove_edge(u, v, key=key)
            graph.add_edge(u, new_node_id, length=weight1, weight=weight1, geometry=geom1)
            graph.add_edge(new_node_id, v, length=weight2, weight=weight2, geometry=geom2)

            print(f"waypoint: {name} (lat={lat:.6f}, lon={lon:.6f}) - distance: {distance:.1f}m")
            print(f" projected to edge {u} → {v}")
            print(f" inserted node {new_node_id} at lat={proj_lat:.6f}, lon={proj_lon:.6f}")
            print(f" edge split: {weight1:.1f} m + {weight2:.1f} m = {total_length:.1f} m")

            snapped_nodes.append(new_node_id)
            filtered_waypoints.append((lat, lon, name, sym))

        except Exception as e:           
            print(f"⚠️ Failed snapping waypoint '{name}' — {e}")
            print("  ↳ Falling back to nearest node snapping")

            # Fallback to nearest node with distance validation
            nearest_node = ox.distance.nearest_nodes(graph, lon, lat)
            nearest_node_coords = (graph.nodes[nearest_node]['y'], graph.nodes[nearest_node]['x'])
            fallback_distance = geodesic((lat, lon), nearest_node_coords).meters

            if fallback_distance > snap_threshold:
                print(f"⚠️ Fallback node for waypoint '{name}' is {fallback_distance:.1f}m away (>{snap_threshold}m threshold) - skipping")
                skipped_waypoints.append((name, fallback_distance))
                continue

            print(f"  ↳ Using fallback node {nearest_node} at {fallback_distance:.1f}m distance")
            snapped_nodes.append(nearest_node)
            filtered_waypoints.append((lat, lon, name, sym))

    if skipped_waypoints:
        print(f"\n⚠️ Summary: {len(skipped_waypoints)} waypoint(s) were skipped (beyond {snap_threshold}m threshold):")
        for name, distance in skipped_waypoints:
            print(f"  - {name}: {distance:.1f}m")

    return snapped_nodes, filtered_waypoints

def calculate_routes(graph, node_ids):
    """
    Calculate routes between nodes using the shortest path algorithm.

    Args:
        graph (networkx.Graph): The OSM graph.
        node_ids (list): List of node IDs.

    Returns:
        list: List of routes, each route is a list of node IDs.
    """
    print("[5/6] Calculating routes between nodes...")
    import networkx as nx
    routes = []
    for i in range(len(node_ids) - 1):
        try:
            route = nx.shortest_path(graph, node_ids[i], node_ids[i+1], weight='length')
        except nx.NetworkXNoPath:
            print(f"  ⚠️ No path found between node {i+1} and {i+2}, inserting fallback route")
            route = [node_ids[i], node_ids[i+1]]
        routes.append(route)
    return routes

def plot_and_save_route(graph, routes, output_path):
    """
    Plot the route on a map and save it to a file.

    Args:
        graph (networkx.Graph): The OSM graph.
        routes (list): List of routes.
        output_path (str): Path to save the plot.
    """
    print(f"[6/7] Plotting route and saving to: {output_path}")
    fig, ax = ox.plot_graph_routes(graph, routes, route_linewidth=3, node_size=0, show=False, close=False, figsize=(16, 12))
    fig.savefig(output_path, dpi=300)
    print("  ↳ Plot saved")

def export_route_to_gpx(graph, routes, waypoints, output_path_gpx):
    """
    Export the calculated route to a GPX file.

    Args:
        graph (networkx.Graph): The OSM graph.
        routes (list): List of routes.
        waypoints (list): List of original waypoints.
        output_path_gpx (str): Path to save the GPX file.
    """
    print(f"[7/7] Exporting route to GPX: {output_path_gpx}")
    import gpxpy.gpx
    gpx = gpxpy.gpx.GPX()

    # Add input waypoints (e.g., summits)
    for lat, lon, name, sym in waypoints:
        gpx.waypoints.append(gpxpy.gpx.GPXWaypoint(latitude=lat, longitude=lon, name=name, symbol=sym))

    segment = gpxpy.gpx.GPXTrackSegment()
    track = gpxpy.gpx.GPXTrack()
    track.segments.append(segment)
    gpx.tracks.append(track)

    for route in routes:
        for u, v in zip(route[:-1], route[1:]):
            edge_data = graph.get_edge_data(u, v)
            if edge_data is None:
                continue
            edge = edge_data[0] if isinstance(edge_data, dict) else edge_data
            if 'geometry' in edge:
                for x, y in edge['geometry'].coords:
                    segment.points.append(gpxpy.gpx.GPXTrackPoint(y, x))
            else:
                segment.points.append(gpxpy.gpx.GPXTrackPoint(graph.nodes[u]['y'], graph.nodes[u]['x']))
                segment.points.append(gpxpy.gpx.GPXTrackPoint(graph.nodes[v]['y'], graph.nodes[v]['x']))

    with open(output_path_gpx, 'w') as f:
        f.write(gpx.to_xml())
    print("  ↳ GPX file written")

def create_fallback_connection_graph(waypoints):
    """
    Create a fallback connection graph between waypoints.

    Args:
        waypoints (list): List of waypoints.

    Returns:
        networkx.Graph: The fallback connection graph.
    """
    print("[3.5/6] Creating fallback connection graph between waypoints...")
    import networkx as nx
    fallback_graph = nx.Graph()
    for i in range(len(waypoints) - 1):
        lat1, lon1, name1, _ = waypoints[i]
        lat2, lon2, name2, _ = waypoints[i + 1]
        # Add edge with high cost
        fallback_graph.add_edge(
            (lat1, lon1), (lat2, lon2),
            weight=10000,  # High cost to discourage use
            length=geodesic((lat1, lon1), (lat2, lon2)).meters
        )
        print(f"  ↳ Added fallback connection edge: {name1} → {name2} (cost: 10000)")
    return fallback_graph


def merge_graphs(osm_graph, fallback_graph):
    """
    Merge the fallback connection graph with the OSM graph.

    Args:
        osm_graph (networkx.Graph): The OSM graph.
        fallback_graph (networkx.Graph): The fallback connection graph.

    Returns:
        networkx.Graph: The merged graph.
    """
    print("[4/6] Merging fallback connection graph with OSM graph...")
    for edge in fallback_graph.edges(data=True):
        (lat1, lon1), (lat2, lon2), edge_data = edge
        # Find nearest nodes in the OSM graph
        node1 = ox.distance.nearest_nodes(osm_graph, lon1, lat1)
        node2 = ox.distance.nearest_nodes(osm_graph, lon2, lat2)
        # Add edge to OSM graph with high cost
        osm_graph.add_edge(node1, node2, **edge_data)
        print(f"  ↳ Added edge to OSM graph: {node1} → {node2} (cost: {edge_data['weight']})")
    return osm_graph


def main():
    """
    Main entry point of the script.
    """
    args = parse_arguments()
    validate_arguments(args)

    waypoints = extract_waypoints(args.input, args.max_points, args.max_distance)

    north, south, east, west = calculate_bounding_box(waypoints, args.bounding_box_buffer)
    graph = download_osm_graph(north, south, east, west, args.max_cache_age_days, args.force_refresh)

    node_ids, filtered_waypoints = snap_waypoints_to_graph(graph, waypoints, args.snap_threshold)
    routes = calculate_routes(graph, node_ids)

    export_route_to_gpx(graph, routes, filtered_waypoints, args.output)


if __name__ == '__main__':
    main()
