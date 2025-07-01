"""
plot2.py

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
    --buffer FLOAT           Buffer around bounding box in degrees (default: 0.01)
    --max-points INT         Maximum number of waypoints (default: 50)
    --max-distance FLOAT     Maximum allowed distance between waypoints in km (default: 20)
    --max-cache-age-days INT Maximum number of days before cached graph expires (default: 7)
    --force-refresh          Force refresh of cached graph even if not expired
"""

import argparse
import sys
import gpxpy
import osmnx as ox
from geopy.distance import geodesic
import hashlib
from pathlib import Path


def parse_arguments():
    """
    Parse command-line arguments for the script.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    if len(sys.argv) == 1:
        print(__doc__)
        sys.exit(0)
    parser = argparse.ArgumentParser(description="Route between GPX waypoints using OpenStreetMap")
    parser.add_argument('--input', required=True, help='Path to input GPX file')
    parser.add_argument('--png-output', help='Path to save the final plot (e.g., route.png)')
    parser.add_argument('--gpx-output', required=True, help='Path to save the calculated route as a GPX file')
    parser.add_argument('--buffer', type=float, default=0.01, help='Buffer in degrees to expand the bounding box (default: 0.01)')
    parser.add_argument('--max-points', type=int, default=50, help='Maximum number of waypoints allowed (default: 50)')
    parser.add_argument('--max-distance', type=float, default=20, help='Maximum allowed distance between waypoints in km (default: 20)')
    parser.add_argument('--max-cache-age-days', type=int, default=7, help='Max age of cached graph in days (default: 7)')
    parser.add_argument('--force-refresh', action='store_true', help='Force refresh of cached graph even if cache is valid')
    return parser.parse_args()


def parse_gpx(file_path):
    """
    Parse a GPX file to extract waypoints.

    Args:
        file_path (str): Path to the GPX file.

    Returns:
        list: List of waypoints as tuples (latitude, longitude, name, symbol).
    """
    print("[1/6] Parsing GPX file:", file_path)
    try:
        with open(file_path, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
    except (FileNotFoundError, IOError) as e:
        print(f"❌ Error reading file: {e}")
        sys.exit(1)
    except gpxpy.gpx.GPXException as e:
        print(f"❌ Error parsing GPX: {e}")
        sys.exit(1)
    waypoints = [(wpt.latitude, wpt.longitude, wpt.name, wpt.symbol) for wpt in gpx.waypoints]
    print(f"  ↳ {len(waypoints)} waypoints found")
    return waypoints


def validate_waypoints(waypoints, max_points, max_distance):
    """
    Validate waypoints for maximum count and distance constraints.

    Args:
        waypoints (list): List of waypoints.
        max_points (int): Maximum allowed number of waypoints.
        max_distance (float): Maximum allowed distance between consecutive waypoints in km.

    Raises:
        SystemExit: If validation fails.
    """
    if len(waypoints) > max_points:
        print(f"❌ Too many waypoints ({len(waypoints)} > {max_points}). Use --max-points to override.")
        sys.exit(1)

    def haversine_km(p1, p2):
        return geodesic((p1[0], p1[1]), (p2[0], p2[1])).km

    for i in range(len(waypoints) - 1):
        dist = haversine_km(waypoints[i], waypoints[i + 1])
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
    print(f"[2/6] Calculating bounding box with buffer: {buffer}°")
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

    print("[3/6] Downloading OSM data (walkable paths)...")
    print("  ↳ No cache found. Downloading from OSM...")
    graph = ox.graph.graph_from_bbox((west, south, east, north), network_type='walk')
    ox.save_graphml(graph, filepath=cache_file)
    print("  ↳ Graph downloaded with", len(graph.nodes), "nodes and", len(graph.edges), "edges")
    return graph


def snap_waypoints_to_graph(graph, waypoints):
    """
    Snap waypoints to the nearest nodes in the OSM graph.

    Args:
        graph (networkx.Graph): The OSM graph.
        waypoints (list): List of waypoints.

    Returns:
        list: List of snapped node IDs.
    """
    print("[4/6] Snapping waypoints to nearest graph nodes...")
    snapped_nodes = []
    for lat, lon, name, sym in waypoints:
        # Find the nearest node
        nearest_node = ox.distance.nearest_nodes(graph, lon, lat)
        # Get the new location of the snapped node
        new_lat = graph.nodes[nearest_node]['y']
        new_lon = graph.nodes[nearest_node]['x']
        # Calculate the distance between the original and snapped location
        distance_meters = geodesic((lat, lon), (new_lat, new_lon)).meters
        # Print debug information
        print(f"  ↳ Waypoint '{name}' moved:")
        print(f"     - Original location: lat={lat}, lon={lon}")
        print(f"     - Snapped location:  lat={new_lat}, lon={new_lon}")
        print(f"     - Distance moved:    {distance_meters:.2f} meters")
        # Check if the distance exceeds 5 meters
        if distance_meters > 5:
            print(f"  ⚠️ Distance exceeds 5 meters. Adding waypoint '{name}' as a new node.")
            # Add the waypoint as a new node in the graph
            new_node_id = max(graph.nodes) + 1  # Generate a unique node ID
            graph.add_node(new_node_id, x=lon, y=lat)
            snapped_nodes.append(new_node_id)
        else:
            snapped_nodes.append(nearest_node)
    return snapped_nodes


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
    waypoints = parse_gpx(args.input)
    validate_waypoints(waypoints, args.max_points, args.max_distance)
    north, south, east, west = calculate_bounding_box(waypoints, args.buffer)
    graph = download_osm_graph(north, south, east, west, args.max_cache_age_days, args.force_refresh)

    # Create and merge fallback connection graph
    fallback_graph = create_fallback_connection_graph(waypoints)
    graph = merge_graphs(graph, fallback_graph)

    node_ids = snap_waypoints_to_graph(graph, waypoints)
    routes = calculate_routes(graph, node_ids)

    if args.png_output:
        plot_and_save_route(graph, routes, args.png_output)
    export_route_to_gpx(graph, routes, waypoints, args.gpx_output)


if __name__ == '__main__':
    main()
