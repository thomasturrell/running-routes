import argparse
import sys
import gpxpy
import osmnx as ox
from geopy.distance import geodesic
import hashlib
from pathlib import Path

def parse_arguments():
    if len(sys.argv) == 1:
        print("""
Usage: python script.py --input INPUT.gpx --gpx-output OUTPUT.gpx [options]

Options:
  --buffer FLOAT           Buffer around bounding box in degrees (default: 0.01)
  --max-points INT         Maximum number of waypoints (default: 50)
  --max-distance FLOAT     Maximum allowed distance between waypoints in km (default: 5.0)
  --max-cache-age-days INT Maximum number of days before cached graph expires (default: 7)
  --force-refresh          Force refresh of cached graph even if not expired
""")
        sys.exit(0)
    parser = argparse.ArgumentParser(description="Route between GPX waypoints using OpenStreetMap")
    parser.add_argument('--input', required=True, help='Path to input GPX file')
    parser.add_argument('--png-output', help='Path to save the final plot (e.g., route.png)')
    parser.add_argument('--gpx-output', required=True, help='Optional path to save the calculated route as a GPX file')
    parser.add_argument('--buffer', type=float, default=0.01, help='Buffer in degrees to expand the bounding box (default: 0.01)')
    parser.add_argument('--max-points', type=int, default=50, help='Maximum number of waypoints allowed (default: 50)')
    parser.add_argument('--max-distance', type=float, default=20, help='Maximum allowed distance between waypoints in km (default: 5.0)')
    parser.add_argument('--max-cache-age-days', type=int, default=7, help='Max age of cached graph in days (default: 7)')
    parser.add_argument('--force-refresh', action='store_true', help='Force refresh of cached graph even if cache is valid')
    return parser.parse_args()

def parse_gpx(file_path):
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
    waypoints = [(wpt.latitude, wpt.longitude, wpt.name) for wpt in gpx.waypoints]
    print(f"  ↳ {len(waypoints)} waypoints found")
    return waypoints

def validate_waypoints(waypoints, max_points, max_distance):
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
    # Already printed above or earlier in logic
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
    print("[4/6] Snapping waypoints to nearest graph nodes...")
    return [ox.distance.nearest_nodes(graph, lon, lat) for lat, lon, _ in waypoints]

def calculate_routes(graph, node_ids):
    print("[5/6] Calculating routes between nodes...")
    import networkx as nx
    routes = []
    for i in range(len(node_ids) - 1):
        route = nx.shortest_path(graph, node_ids[i], node_ids[i+1], weight='length')
        routes.append(route)
    return routes

def plot_and_save_route(graph, routes, output_path):
    print(f"[6/7] Plotting route and saving to: {output_path}")
    fig, ax = ox.plot_graph_routes(graph, routes, route_linewidth=3, node_size=0, show=False, close=False, figsize=(16, 12))
    fig.savefig(output_path, dpi=300)
    print("  ↳ Plot saved")

def export_route_to_gpx(graph, routes, waypoints, output_path_gpx):
    print(f"[7/7] Exporting route to GPX: {output_path_gpx}")
    import gpxpy.gpx
    gpx = gpxpy.gpx.GPX()

    # Add input waypoints (e.g., summits)
    for lat, lon, name in waypoints:
        gpx.waypoints.append(gpxpy.gpx.GPXWaypoint(latitude=lat, longitude=lon, name=name))

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

def main():
    args = parse_arguments()
    waypoints = parse_gpx(args.input)
    validate_waypoints(waypoints, args.max_points, args.max_distance)
    north, south, east, west = calculate_bounding_box(waypoints, args.buffer)
    graph = download_osm_graph(north, south, east, west, args.max_cache_age_days, args.force_refresh)
    node_ids = snap_waypoints_to_graph(graph, waypoints)
    routes = calculate_routes(graph, node_ids)

    if args.png_output:
        plot_and_save_route(graph, routes, args.png_output)
    export_route_to_gpx(graph, routes, waypoints, args.gpx_output)

if __name__ == '__main__':
    main()
