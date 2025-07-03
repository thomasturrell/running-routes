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
    export_new_paths_to_gpx
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])