import os
import gpxpy
import gpxpy.gpx
import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
from shapely.geometry import Point, LineString

ox.settings.use_cache = True
ox.settings.log_console = True

GPX_OUTPUT_FILE = "output/ramsay-round-segmented.gpx"

def load_waypoints_from_gpx(gpx_file):
    with open(gpx_file, 'r') as f:
        gpx = gpxpy.parse(f)
    waypoints = [(w.latitude, w.longitude, w.name) for w in gpx.waypoints]
    print(f"📍 Loaded {len(waypoints)} waypoints")
    return waypoints

def get_graph_around_waypoints(waypoints, padding=0.01):
    lats = [wp[0] for wp in waypoints]
    lons = [wp[1] for wp in waypoints]
    north, south = max(lats) + padding, min(lats) - padding
    east, west = max(lons) + padding, min(lons) - padding
    bbox = (west, south, east, north)  # Reordered for OSMnx 2.0.3

    custom_filter = (
        '["highway"~"path|footway|track|bridleway|cycleway|residential|service|unclassified"]'
    )

    print("🌍 Downloading graph...")
    G = ox.graph.graph_from_bbox(
        bbox=bbox,
        network_type="walk",
        simplify=True,
        retain_all=True,
        truncate_by_edge=True,
        custom_filter=custom_filter
    )
    return G

def route_segment(G, origin_point, destination_point):
    orig_node = ox.distance.nearest_nodes(G, origin_point[1], origin_point[0])
    dest_node = ox.distance.nearest_nodes(G, destination_point[1], destination_point[0])
    try:
        route = nx.shortest_path(G, orig_node, dest_node, weight='length')
        return route
    except nx.NetworkXNoPath:
        return None

def save_gpx(segments, waypoints, output_file):
    gpx = gpxpy.gpx.GPX()

    for lat, lon, name in waypoints:
        wp = gpxpy.gpx.GPXWaypoint(latitude=lat, longitude=lon, name=name, symbol="Summit")
        gpx.waypoints.append(wp)

    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)

    for segment in segments:
        for point in segment:
            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(point[0], point[1]))

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(gpx.to_xml())
    print(f"📂 Saved route with waypoints to {output_file}")

def main(gpx_input, gpx_output):
    waypoints = load_waypoints_from_gpx(gpx_input)

    print("\n🔎 Sample waypoints (lat, lon, type):")
    for lat, lon, name in waypoints[:3]:
        print(f"  {name}: lat={lat} ({type(lat)}), lon={lon} ({type(lon)})")

    G = get_graph_around_waypoints(waypoints)

    segments = []
    for i in range(len(waypoints) - 1):
        start = waypoints[i]
        end = waypoints[i + 1]
        print(f"⭮️ Segment {i+1}: {start[2]} → {end[2]}")
        route_nodes = route_segment(G, start, end)
        if route_nodes:
            segment_points = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route_nodes]
            print(f"✅ Segment {i+1} routed with {len(segment_points)} points")
            segments.append(segment_points)
        else:
            print(f"❌ Failed to route segment {i+1}")

    print("🗾️ Plotting final route...")
    fig, ax = ox.plot_graph_routes(
        G,
        routes=segments,
        route_linewidth=2,
        node_size=0,
        show=False,
        close=False
    )
    plt.show()

    save_gpx(segments, waypoints, gpx_output)

if __name__ == "__main__":
    gpx_input = "src/fell/ramsay-round/ramsay_round_summits.gpx"
    main(gpx_input, GPX_OUTPUT_FILE)