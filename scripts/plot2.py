import argparse
import sys
import gpxpy
import osmnx as ox
from geopy.distance import geodesic


def parse_arguments():
    parser = argparse.ArgumentParser(description="Route between GPX waypoints using OpenStreetMap")
    parser.add_argument('--input', required=True, help='Path to input GPX file')
    parser.add_argument('--output', required=True, help='Path to save the final plot (not used yet)')
    parser.add_argument('--buffer', type=float, default=0.01, help='Buffer in degrees to expand the bounding box (default: 0.01)')
    parser.add_argument('--max-points', type=int, default=50, help='Maximum number of waypoints allowed (default: 50)')
    parser.add_argument('--max-distance', type=float, default=5.0, help='Maximum allowed distance between waypoints in km (default: 5.0)')
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


def download_osm_graph(north, south, east, west):
    print("[3/6] Downloading OSM data (walkable paths)...")
    graph = ox.graph.graph_from_bbox(north, south, east, west, network_type='walk')
    print("  ↳ Graph downloaded with", len(graph.nodes), "nodes and", len(graph.edges), "edges")
    return graph


def main():
    args = parse_arguments()
    waypoints = parse_gpx(args.input)
    validate_waypoints(waypoints, args.max_points, args.max_distance)
    north, south, east, west = calculate_bounding_box(waypoints, args.buffer)
    graph = download_osm_graph(north, south, east, west)


if __name__ == '__main__':
    main()
