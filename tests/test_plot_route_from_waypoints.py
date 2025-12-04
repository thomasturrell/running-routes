import os
from pathlib import Path
import shutil
import sys
import tempfile

import gpxpy
import gpxpy.gpx
import networkx as nx
import pytest
from geopy.distance import geodesic
from shapely.geometry import LineString

from plot_route_from_waypoints import (
    add_elevation_costs,
    calculate_routes,
    export_route_to_gpx,
    fetch_srtm_elevations,
    extract_waypoints,
    select_weight_attribute,
    snap_waypoints_to_graph,
    validate_waypoints,
)

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



@pytest.fixture
def far_waypoints():
    """Provide waypoints that are far from the graph for threshold testing."""
    return [
        (55.003, -3.000, "Close to node", "Waypoint"),        # Close to existing node
        (55.050, -3.050, "Very far away", "Waypoint"),        # Far from any edge (~5.5km away)
    ]


def test_snap_waypoints_to_graph(mock_graph, waypoints):
    """Test snapping waypoints to the graph."""
    snapped_nodes, filtered_waypoints = snap_waypoints_to_graph(mock_graph, waypoints)
    # Update expected result based on the actual implementation
    assert len(snapped_nodes) > 0
    assert len(filtered_waypoints) == len(snapped_nodes)


def test_snap_waypoints_with_threshold(osm_like_grid_graph, near_waypoints):
    """Test snapping waypoints with distance threshold."""
    # Test with default threshold (5m)
    snapped_nodes, filtered_waypoints = snap_waypoints_to_graph(osm_like_grid_graph, near_waypoints, snap_threshold=5.0)
    
    # All waypoints in near_waypoints should be within threshold for the grid graph
    assert len(snapped_nodes) >= 2  # At least 2 waypoints should be snapped
    assert len(filtered_waypoints) == len(snapped_nodes)


def test_snap_waypoints_with_strict_threshold(osm_like_grid_graph, far_waypoints):
    """Test snapping waypoints with very strict threshold to trigger filtering."""
    # Test with very small threshold to filter out far waypoints
    snapped_nodes, filtered_waypoints = snap_waypoints_to_graph(osm_like_grid_graph, far_waypoints, snap_threshold=0.05)
    
    # The close waypoint should be included, far one should be filtered out
    assert len(snapped_nodes) >= 1  # At least the close waypoint
    assert len(filtered_waypoints) == len(snapped_nodes)
    assert len(filtered_waypoints) < len(far_waypoints)  # Some waypoints should be filtered


def test_snap_waypoints_no_threshold_filtering(osm_like_grid_graph, near_waypoints):
    """Test snapping waypoints with very high threshold (no filtering)."""
    # Test with very high threshold so no waypoints are filtered
    snapped_nodes, filtered_waypoints = snap_waypoints_to_graph(osm_like_grid_graph, near_waypoints, snap_threshold=10000.0)

    # All waypoints should be included with high threshold
    assert len(snapped_nodes) == len(near_waypoints)
    assert len(filtered_waypoints) == len(near_waypoints)


def test_add_elevation_costs_sets_cost_and_gain():
    graph = nx.MultiDiGraph()
    graph.add_node(1, x=0, y=0, elevation=100)
    graph.add_node(2, x=1, y=1, elevation=115)
    graph.add_edge(1, 2, key=0, length=200)

    add_elevation_costs(graph, gain_penalty=10.0, loss_penalty=2.0)
    edge_data = graph.get_edge_data(1, 2)[0]

    assert edge_data['elevation_gain'] == 15
    assert edge_data['elevation_loss'] == 0
    assert edge_data['cost'] == 200 + (15 * 10.0)
    assert select_weight_attribute(graph) == 'cost'


def test_add_elevation_costs_handles_descent():
    graph = nx.MultiDiGraph()
    graph.add_node(1, x=0, y=0, elevation=200)
    graph.add_node(2, x=1, y=1, elevation=180)
    graph.add_edge(1, 2, key=0, length=100)

    add_elevation_costs(graph, gain_penalty=10.0, loss_penalty=1.5)
    edge_data = graph.get_edge_data(1, 2)[0]

    assert edge_data['elevation_gain'] == 0
    assert edge_data['elevation_loss'] == 20
    assert edge_data['cost'] == 100 + (20 * 1.5)


def test_fetch_srtm_elevations_uses_cache(monkeypatch, tmp_path, mock_graph):
    cache_file = tmp_path / "cache.json"
    cache_file.write_text('{"55.89286,-3.20344": 123.4, "55.8825,-3.21407": 200.0, "55.88266,-3.22357": 250.0}')

    import plot_route_from_waypoints as module

    monkeypatch.setattr(module, "ELEVATION_CACHE_FILE", cache_file)

    def fail_request(*args, **kwargs):
        raise AssertionError("Network should not be called when cache is warm")

    monkeypatch.setattr(module.requests, "get", fail_request)

    elevations = fetch_srtm_elevations(mock_graph)

    assert all(val in (123.4, 200.0, 250.0) for val in elevations.values())


def test_fetch_srtm_elevations_includes_api_key(monkeypatch, mock_graph):
    import plot_route_from_waypoints as module

    called_params = {}

    def fake_get(url, params=None, timeout=None):
        called_params.update(params or {})

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                locations = (params or {}).get("locations", "").split("|")
                return {"results": [{"location": loc, "elevation": 100} for loc in locations if loc]}

        return Response()

    monkeypatch.setenv("OPENTOPO_API_KEY", "secret-key")
    monkeypatch.setattr(module, "requests", type("Requests", (), {"get": staticmethod(fake_get)}))

    elevations = fetch_srtm_elevations(mock_graph, nodes=list(mock_graph.nodes))

    assert called_params.get("API_Key") == "secret-key"
    assert elevations


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
    node_ids, filtered_waypoints = snap_waypoints_to_graph(osm_like_grid_graph, near_waypoints)
    routes = calculate_routes(osm_like_grid_graph, node_ids)

    gpx_output_path = tmp_path / "test_route.gpx"
    export_route_to_gpx(osm_like_grid_graph, routes, filtered_waypoints, gpx_output_path)

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


def test_snap_waypoints_fallback_threshold():
    """Test that fallback snapping respects the distance threshold."""
    # Create a simple graph with one edge
    graph = nx.MultiDiGraph()
    graph.add_node(1, x=-3.0, y=55.0)
    graph.add_node(2, x=-2.999, y=55.0)
    graph.add_edge(1, 2, key=0, weight=100, length=100, 
                   geometry=LineString([(-3.0, 55.0), (-2.999, 55.0)]))
    graph.graph['crs'] = 'EPSG:4326'
    
    # Waypoints designed to trigger fallback behavior
    waypoints = [
        (55.0, -3.00002, "Close fallback", "Waypoint"),    # Very close to node 1
        (55.0, -2.9, "Far fallback", "Waypoint"),          # Should be far from any node
    ]
    
    # Test with 100m threshold (to allow the close one through)
    snapped_nodes, filtered_waypoints = snap_waypoints_to_graph(graph, waypoints, snap_threshold=100.0)
    
    # The close waypoint should be snapped via fallback, far one should be skipped
    assert len(snapped_nodes) == 1
    assert len(filtered_waypoints) == 1
    assert filtered_waypoints[0][2] == "Close fallback"  # Name of the waypoint

def make_gpx_with_waypoints(waypoints):
    """
    Helper to generate a GPX string with given waypoints using gpxpy.

    Args:
        waypoints (list): List of waypoints as tuples (lat, lon, name, sym).

    Returns:
        str: GPX string with the given waypoints.
    """
    gpx = gpxpy.gpx.GPX()

    for lat, lon, name, sym in waypoints:
        waypoint = gpxpy.gpx.GPXWaypoint(latitude=lat, longitude=lon)
        if name:
            waypoint.name = name
        if sym:
            waypoint.symbol = sym
        gpx.waypoints.append(waypoint)

    return gpx.to_xml()


class TestExtractWaypoints:
    """Group tests for the extract_waypoints function."""

    def test_extract_waypoints_basic(self, tmp_path):
        """Test extracting waypoints from a valid GPX file."""
        waypoints = [
            (55.0, -3.0, "A", "Flag"),
            (56.0, -2.0, "B", "Summit"),
        ]
        gpx_content = make_gpx_with_waypoints(waypoints)
        gpx_file = tmp_path / "test.gpx"
        gpx_file.write_text(gpx_content)

        result = extract_waypoints(str(gpx_file))
        assert len(result) == 2
        assert result[0][:2] == (55.0, -3.0)
        assert result[0][2] == "A"
        assert result[0][3] == "Flag"
        assert result[1][2] == "B"
        assert result[1][3] == "Summit"

    def test_extract_waypoints_empty(self, tmp_path):
        """Test extracting from a GPX file with no waypoints."""
        gpx_content = make_gpx_with_waypoints([])
        gpx_file = tmp_path / "empty.gpx"
        gpx_file.write_text(gpx_content)

        result = extract_waypoints(str(gpx_file))
        assert result == []

    def test_extract_waypoints_missing_file(self, tmp_path):
        """Test extracting from a missing file triggers sys.exit."""
        missing_path = tmp_path / "does_not_exist.gpx"
        with pytest.raises(SystemExit):
            extract_waypoints(str(missing_path))

    def test_extract_waypoints_invalid_gpx(self, tmp_path):
        """Test extracting from an invalid GPX file triggers sys.exit."""
        gpx_file = tmp_path / "bad.gpx"
        gpx_file.write_text("not a gpx file at all")
        with pytest.raises(SystemExit):
            extract_waypoints(str(gpx_file))

    def test_extract_waypoints_partial_fields(self, tmp_path):
        """Test extracting waypoints with missing name or symbol fields."""
        # Use make_gpx_with_waypoints to generate GPX content
        waypoints = [
            (55.1, -3.1, None, None),  # No name/symbol
            (55.2, -3.2, "WP2", None),  # Name only
            (55.3, -3.3, None, "Summit"),  # Symbol only
        ]
        gpx_content = make_gpx_with_waypoints(waypoints)

        # Write the GPX content to a temporary file
        gpx_file = tmp_path / "partial.gpx"
        gpx_file.write_text(gpx_content)

        # Call the function under test
        result = extract_waypoints(str(gpx_file))

        # Assertions
        assert len(result) == 3
        assert result[0][2] is None or result[0][2] == ""  # No name
        assert result[0][3] is None or result[0][3] == ""  # No symbol
        assert result[1][2] == "WP2"  # Name only
        assert result[1][3] is None or result[1][3] == ""  # No symbol
        assert result[2][2] is None or result[2][2] == ""  # No name
        assert result[2][3] == "Summit"  # Symbol only

class TestValidateWaypoints:
    """Test suite for the validate_waypoints function."""

    def test_missing_lat_lon(self):
        """Test that waypoints with missing latitude or longitude are skipped."""
        waypoints = [
            (None, -3.0, "Missing Latitude", "Flag"),  # Missing latitude
            (55.0, None, "Missing Longitude", "Summit"),  # Missing longitude
            (55.0, -3.0, "Valid Waypoint 1", "Flag"),  # Valid waypoint
            (56.0, -2.0, "Valid Waypoint 2", "Summit"),  # Valid waypoint
        ]
        max_points = 10  # Arbitrary large number
        max_distance = 200  # Arbitrary large distance

        with pytest.raises(SystemExit):
            validate_waypoints(waypoints, max_points, max_distance)

    def test_too_many_waypoints(self):
        """Test that validation fails when there are too many waypoints."""
        waypoints = [(55.0, -3.0), (56.0, -2.0), (57.0, -1.0)]
        max_points = 2  # Allow only 2 waypoints
        max_distance = 100  # Arbitrary large distance to avoid triggering distance validation

        with pytest.raises(SystemExit):
            validate_waypoints(waypoints, max_points, max_distance)

    def test_distance_exceeds_limit(self):
        """Test that validation fails when the distance between waypoints exceeds the limit."""
        waypoints = [(55.0, -3.0), (56.0, -2.0)]  # Distance > 100 km
        max_points = 10  # Arbitrary large number to avoid triggering waypoint count validation
        max_distance = 50  # Set a small distance limit

        with pytest.raises(SystemExit):
            validate_waypoints(waypoints, max_points, max_distance)

    def test_valid_waypoints(self):
        """Test that validation passes for valid waypoints."""
        waypoints = [(55.0, -3.0), (55.1, -3.1)]  # Distance < 100 km
        max_points = 10  # Allow up to 10 waypoints
        max_distance = 100  # Set a large distance limit

        # No exception should be raised
        validate_waypoints(waypoints, max_points, max_distance)

    def test_no_waypoints(self):
        """Test that validation passes when there are no waypoints."""
        waypoints = []  # No waypoints
        max_points = 10  # Arbitrary large number
        max_distance = 100  # Arbitrary large distance

        # No exception should be raised
        validate_waypoints(waypoints, max_points, max_distance)

    def test_single_waypoint(self):
        """Test that validation passes when there is only one waypoint."""
        waypoints = [(55.0, -3.0)]  # Single waypoint
        max_points = 10  # Arbitrary large number
        max_distance = 100  # Arbitrary large distance

        # No exception should be raised
        validate_waypoints(waypoints, max_points, max_distance)

    def test_edge_case_distance_equals_limit(self):
        """Test that validation passes when the distance between waypoints equals the limit."""
        waypoints = [(55.0, -3.0), (55.0, -2.0)]  # Distance ~111 km (1 degree longitude)
        max_points = 10  # Arbitrary large number
        max_distance = geodesic((55.0, -3.0), (55.0, -2.0)).km  # Exact distance between waypoints

        # No exception should be raised
        validate_waypoints(waypoints, max_points, max_distance)


