import pytest
import networkx as nx
from unittest.mock import patch
from plot_route_from_waypoints import (
    snap_waypoints_to_graph,
    calculate_routes,
    export_route_to_gpx,
)
from pathlib import Path
import shutil
import pytest
import networkx as nx
from shapely.geometry import LineString


import pytest
import networkx as nx
from shapely.geometry import LineString

@pytest.fixture
def osm_like_grid_graph():
    """4×4 grid with top-left node = 0, rows go down (south), cols go right (east)."""
    G = nx.MultiDiGraph()
    spacing = 0.001  # ~111 m
    rows, cols = 4, 4
    base_lat, base_lon = 55.003, -3.000  # start in top-left corner

    def node_id(r, c): return r * cols + c

    # Add nodes
    for r in range(rows):
        for c in range(cols):
            nid = node_id(r, c)
            lat = base_lat - r * spacing  # 🠗 flip vertically
            lon = base_lon + c * spacing
            G.add_node(nid, x=lon, y=lat)

    # Add bi-directional edges with geometry
    for r in range(rows):
        for c in range(cols):
            nid = node_id(r, c)
            if c < cols - 1:  # right
                nbr = node_id(r, c + 1)
                coords = [(G.nodes[nid]['x'], G.nodes[nid]['y']),
                          (G.nodes[nbr]['x'], G.nodes[nbr]['y'])]
                G.add_edge(nid, nbr, key=0, length=111, weight=111, geometry=LineString(coords))
                G.add_edge(nbr, nid, key=0, length=111, weight=111, geometry=LineString(coords[::-1]))
            if r < rows - 1:  # down
                nbr = node_id(r + 1, c)
                coords = [(G.nodes[nid]['x'], G.nodes[nid]['y']),
                          (G.nodes[nbr]['x'], G.nodes[nbr]['y'])]
                G.add_edge(nid, nbr, key=0, length=111, weight=111, geometry=LineString(coords))
                G.add_edge(nbr, nid, key=0, length=111, weight=111, geometry=LineString(coords[::-1]))

    G.graph['crs'] = 'EPSG:4326'
    return G

@pytest.fixture
def mock_graph():
    """Create a mock MultiDiGraph for testing."""
    graph = nx.MultiDiGraph()
    
    # Add nodes with coordinates
    graph.add_node(1, x=-3.203444, y=55.892861)
    graph.add_node(2, x=-3.21407,  y=55.8825)
    graph.add_node(3, x=-3.223567, y=55.882658)

    # Add edges with weights and LineString geometry
    graph.add_edge(
        1, 2, key=0,
        weight=100,
        length=100,
        geometry=LineString([(-3.203444, 55.892861), (-3.21407, 55.8825)])
    )
    graph.add_edge(
        2, 3, key=0,
        weight=150,
        length=150,
        geometry=LineString([(-3.21407, 55.8825), (-3.223567, 55.882658)])
    )

    # Add CRS metadata (optional but matches OSMnx)
    graph.graph['crs'] = 'EPSG:4326'

    return graph

@pytest.fixture
def waypoints():
    """Provide a known set of waypoints for testing."""
    return [
    (55.003, -3.000, "WP 0",  "Waypoint"),
    (55.003, -2.999, "WP 1",  "Waypoint"),
    (55.003, -2.998, "WP 2",  "Waypoint"),
    (55.003, -2.997, "WP 3",  "Waypoint"),
    (55.002, -3.000, "WP 4",  "Waypoint"),
    (55.002, -2.999, "WP 5",  "Waypoint"),
    (55.002, -2.998, "WP 6",  "Waypoint"),
    (55.002, -2.997, "WP 7",  "Waypoint"),
    (55.001, -3.000, "WP 8",  "Waypoint"),
    (55.001, -2.999, "WP 9",  "Waypoint"),
    (55.001, -2.998, "WP 10", "Waypoint"),
    (55.001, -2.997, "WP 11", "Waypoint"),
    (55.000, -3.000, "WP 12", "Waypoint"),
    (55.000, -2.999, "WP 13", "Waypoint"),
    (55.000, -2.998, "WP 14", "Waypoint"),
    (55.000, -2.997, "WP 15", "Waypoint"),
    ]



@pytest.fixture
def near_waypoints():
    """Provide a known set of waypoints for testing."""
    return [
    (55.003, -3.000, "Exact match (WP 0)", "Waypoint"),           # Exactly node 0
    (55.00298, -2.99902, "Near node (WP 5)", "Waypoint"),         # Close to node 5
    (55.004, -3.001, "Far off (should be added)", "Waypoint"),    # No nearby node
    ]



def test_snap_waypoints_to_graph(mock_graph, waypoints):
    """Test snapping waypoints to the graph."""
    snapped_nodes = snap_waypoints_to_graph(mock_graph, waypoints)
    assert snapped_nodes == [1, 2, 3]

def test_calculate_routes(mock_graph):
    """Test route calculation between nodes."""
    node_ids = [1, 2, 3]
    routes = calculate_routes(mock_graph, node_ids)
    assert routes == [[1, 2], [2, 3]]





def test_export_route_to_gpx1(tmp_path, osm_like_grid_graph, waypoints):
    """Test exporting the route to a GPX file."""
    node_ids = [0, 1, 5, 6, 10, 14, 15]
    routes = calculate_routes(osm_like_grid_graph, node_ids)

    gpx_output_path = tmp_path / "test_route.gpx"
    export_route_to_gpx(osm_like_grid_graph, routes, waypoints, gpx_output_path)

    assert gpx_output_path.exists()

    # Optional: check contents
    with open(gpx_output_path, "r") as f:
        gpx_content = f.read()
        assert "<gpx" in gpx_content
        assert "<wpt" in gpx_content
        assert "<trkpt" in gpx_content



def test_export_route_to_gpx20(tmp_path, osm_like_grid_graph, near_waypoints, request):
    """Test exporting the route to a GPX file."""
    node_ids = snap_waypoints_to_graph(osm_like_grid_graph, near_waypoints)
    routes = calculate_routes(osm_like_grid_graph, node_ids)

    gpx_output_path = tmp_path / "test_route.gpx"
    export_route_to_gpx(osm_like_grid_graph, routes, near_waypoints, gpx_output_path)

    assert gpx_output_path.exists()

    # Optional: check contents
    with open(gpx_output_path, "r") as f:
        gpx_content = f.read()
        assert "<gpx" in gpx_content
        assert "<wpt" in gpx_content
        assert "<trkpt" in gpx_content

    # Save to permanent location
    test_name = request.node.name  # dynamically get test name

    final_output_dir = Path("tests/output")
    final_output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(gpx_output_path, final_output_dir / f"{test_name}-hellos.gpx")




def test_export_route_to_gpx5(tmp_path, osm_like_grid_graph, near_waypoints, request):
    """Test exporting the route to a GPX file."""
    node_ids = [0, 15]
    routes = calculate_routes(osm_like_grid_graph, node_ids)

    gpx_output_path = tmp_path / "test_route.gpx"
    export_route_to_gpx(osm_like_grid_graph, routes, near_waypoints, gpx_output_path)

    assert gpx_output_path.exists()

    # Optional: check contents
    with open(gpx_output_path, "r") as f:
        gpx_content = f.read()
        assert "<gpx" in gpx_content
        assert "<wpt" in gpx_content
        assert "<trkpt" in gpx_content

    # Save to permanent location
    test_name = request.node.name  # dynamically get test name

    final_output_dir = Path("tests/output")
    final_output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(gpx_output_path, final_output_dir / f"{test_name}.gpx")


def test_export_route_to_gpx(tmp_path, mock_graph, waypoints):
    """Test exporting the route to a GPX file."""
    node_ids = [1, 2, 3]
    routes = calculate_routes(mock_graph, node_ids)

    gpx_output_path = tmp_path / "test_route.gpx"
    export_route_to_gpx(mock_graph, routes, waypoints, gpx_output_path)

    assert gpx_output_path.exists()

    # Optional: check contents
    with open(gpx_output_path, "r") as f:
        gpx_content = f.read()
        assert "<gpx" in gpx_content
        assert "<wpt" in gpx_content
        assert "<trkpt" in gpx_content
