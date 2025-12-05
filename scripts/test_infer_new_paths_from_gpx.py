import pytest
import tempfile
import os
from pathlib import Path
import gpxpy
import gpxpy.gpx
from unittest.mock import patch, MagicMock
import sys

# Add scripts directory to path for imports
sys.path.append(str(Path(__file__).parent))

from infer_new_paths_from_gpx import (
    parse_gpx_tracks,
    calculate_bounding_box,
    identify_new_path_segments,
    export_new_paths_to_gpx,
    export_new_paths_to_osm
)


@pytest.fixture
def sample_gpx_file():
    """Create a temporary GPX file with track data for testing."""
    gpx = gpxpy.gpx.GPX()
    
    # Create a track with a simple path
    track = gpxpy.gpx.GPXTrack()
    track.name = "Test Track"
    
    segment = gpxpy.gpx.GPXTrackSegment()
    
    # Add points in a line (simulating a path)
    test_points = [
        (55.950000, -3.200000),
        (55.950100, -3.199900),
        (55.950200, -3.199800),
        (55.950300, -3.199700),
        (55.950400, -3.199600),
    ]
    
    for lat, lon in test_points:
        segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=lat, longitude=lon))
    
    track.segments.append(segment)
    gpx.tracks.append(track)
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.gpx', delete=False) as f:
        f.write(gpx.to_xml())
        return f.name


def test_parse_gpx_tracks(sample_gpx_file):
    """Test parsing GPX tracks to extract track points."""
    track_points = parse_gpx_tracks(sample_gpx_file)
    
    assert len(track_points) == 5
    assert track_points[0] == (55.950000, -3.200000)
    assert track_points[-1] == (55.950400, -3.199600)
    
    # Clean up
    os.unlink(sample_gpx_file)


def test_calculate_bounding_box():
    """Test bounding box calculation."""
    track_points = [
        (55.950000, -3.200000),
        (55.950400, -3.199600),
        (55.949800, -3.200200),
    ]
    
    north, south, east, west = calculate_bounding_box(track_points, buffer=0.01)
    
    assert north > 55.950400  # Max lat + buffer
    assert south < 55.949800  # Min lat - buffer
    assert east > -3.199600   # Max lon + buffer
    assert west < -3.200200   # Min lon - buffer


def test_identify_new_path_segments():
    """Test identification of new path segments."""
    track_points = [
        (55.950000, -3.200000),
        (55.950100, -3.199900),
        (55.950200, -3.199800),
        (55.950300, -3.199700),
        (55.950400, -3.199600),
        (55.950500, -3.199500),
    ]
    
    # Simulate distances - first 3 points are close to OSM, last 3 are far
    distances = [2.0, 3.0, 4.0, 10.0, 15.0, 20.0]
    
    new_segments = identify_new_path_segments(
        track_points, distances, tolerance=5.0, min_segment_length=2
    )
    
    assert len(new_segments) == 1
    assert len(new_segments[0]) == 3  # Last 3 points
    assert new_segments[0][0] == (55.950300, -3.199700)


def test_export_new_paths_to_gpx():
    """Test exporting new path segments to GPX."""
    new_segments = [
        [
            (55.950000, -3.200000),
            (55.950100, -3.199900),
        ],
        [
            (55.950300, -3.199700),
            (55.950400, -3.199600),
        ]
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.gpx', delete=False) as f:
        output_path = f.name
    
    success = export_new_paths_to_gpx(new_segments, output_path)
    
    assert success
    assert os.path.exists(output_path)
    
    # Verify GPX content
    with open(output_path, 'r') as f:
        content = f.read()
        assert '<gpx' in content
        assert '<trk>' in content
        assert 'New Path Segment 1' in content
        assert 'New Path Segment 2' in content
    
    # Clean up
    os.unlink(output_path)


def test_empty_gpx_handling():
    """Test handling of GPX files with no tracks."""
    gpx = gpxpy.gpx.GPX()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.gpx', delete=False) as f:
        f.write(gpx.to_xml())
        gpx_file = f.name
    
    try:
        # This should exit with error
        with pytest.raises(SystemExit):
            parse_gpx_tracks(gpx_file)
    finally:
        os.unlink(gpx_file)


def test_export_new_paths_to_osm():
    """Test OSM XML export functionality."""
    # Test data - simple path with 3 points
    new_segments = [
        [(55.950000, -3.200000), (55.950100, -3.199900), (55.950200, -3.199800)]
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.osm', delete=False) as f:
        output_path = f.name
    
    try:
        # Test export
        success = export_new_paths_to_osm(new_segments, output_path, verbose=False)
        assert success is True
        
        # Check file exists and has content
        assert os.path.exists(output_path)
        
        with open(output_path, 'r') as f:
            content = f.read()
        
        # Verify XML structure
        assert '<?xml version="1.0" encoding="UTF-8"?>' in content
        assert '<osm version="0.6"' in content
        assert 'generator="infer_new_paths_from_gpx.py"' in content
        
        # Check for nodes (should have 3 nodes)
        assert content.count('<node id="-') == 3
        assert 'lat="55.9500000"' in content
        assert 'lat="55.9501000"' in content  
        assert 'lat="55.9502000"' in content
        assert 'lon="-3.2000000"' in content
        assert 'lon="-3.1999000"' in content
        assert 'lon="-3.1998000"' in content
        
        # Check for way
        assert '<way id="-1"' in content
        assert '<nd ref="-1"' in content
        assert '<nd ref="-2"' in content
        assert '<nd ref="-3"' in content
        
        # Check for proper OSM tags
        assert '<tag k="highway" v="path"' in content
        assert '<tag k="source" v="GPX"' in content
        assert '<tag k="note" v="Potential new path inferred from GPX track segment 1"' in content
        assert '<tag k="fixme"' in content
        
    finally:
        os.unlink(output_path)


def test_export_new_paths_to_osm_multiple_segments():
    """Test OSM XML export with multiple path segments."""
    # Test data - two separate path segments
    new_segments = [
        [(55.950000, -3.200000), (55.950100, -3.199900)],  # First segment
        [(55.960000, -3.180000), (55.960100, -3.179900), (55.960200, -3.179800)]  # Second segment
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.osm', delete=False) as f:
        output_path = f.name
    
    try:
        success = export_new_paths_to_osm(new_segments, output_path, verbose=True)
        assert success is True
        
        with open(output_path, 'r') as f:
            content = f.read()
        
        # Should have 5 nodes total (2 + 3)
        assert content.count('<node id="-') == 5
        
        # Should have 2 ways
        assert content.count('<way id="-') == 2
        assert '<way id="-1"' in content
        assert '<way id="-2"' in content
        
        # Check both segments have proper tags
        assert content.count('<tag k="highway" v="path"') == 2
        assert 'segment 1' in content
        assert 'segment 2' in content
        
    finally:
        os.unlink(output_path)


def test_export_new_paths_to_osm_empty():
    """Test OSM XML export with no segments."""
    new_segments = []
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.osm', delete=False) as f:
        output_path = f.name
    
    try:
        success = export_new_paths_to_osm(new_segments, output_path, verbose=False)
        assert success is True
        
        with open(output_path, 'r') as f:
            content = f.read()
        
        # Should have basic OSM structure but no nodes or ways
        assert '<?xml version="1.0" encoding="UTF-8"?>' in content
        assert '<osm version="0.6"' in content
        assert '<node' not in content
        assert '<way' not in content
        
    finally:
        os.unlink(output_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])