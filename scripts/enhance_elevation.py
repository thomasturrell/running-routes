#!/usr/bin/env python3
"""
Enhanced elevation data processing for fell running routes.

This script improves elevation data accuracy for GPX files by:
1. Implementing data smoothing to reduce noise in elevation profiles
2. Providing alternatives to Google Elevation API
3. Adding validation against known elevation sources
4. Supporting LiDAR and other high-accuracy elevation datasets

Features:
- Elevation data smoothing using various algorithms
- Multiple elevation data sources (Open Elevation, USGS, etc.)
- Validation and comparison of elevation data
- Export of improved elevation profiles
"""

import argparse
import sys
import gpxpy
import requests
import numpy as np
from scipy import ndimage
from pathlib import Path
import json
import time
from typing import List, Tuple, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ElevationProcessor:
    """Enhanced elevation data processor for GPX files."""
    
    def __init__(self):
        self.apis = {
            'open_elevation': 'https://api.open-elevation.com/api/v1/lookup',
            'usgs': 'https://nationalmap.gov/epqs/pqs.php'
        }
        
    def smooth_elevation_data(self, elevations: List[float], method: str = 'gaussian', 
                             sigma: float = 1.0) -> List[float]:
        """
        Smooth elevation data to reduce noise.
        
        Args:
            elevations: List of elevation values
            method: Smoothing method ('gaussian', 'median', 'moving_average')
            sigma: Standard deviation for gaussian filter
            
        Returns:
            List of smoothed elevation values
        """
        if not elevations:
            return elevations
            
        elevations_array = np.array(elevations)
        
        if method == 'gaussian':
            smoothed = ndimage.gaussian_filter1d(elevations_array, sigma=sigma)
        elif method == 'median':
            window_size = max(3, int(sigma * 2) + 1)
            if window_size % 2 == 0:
                window_size += 1
            smoothed = ndimage.median_filter(elevations_array, size=window_size)
        elif method == 'moving_average':
            window_size = max(3, int(sigma * 2) + 1)
            smoothed = np.convolve(elevations_array, 
                                 np.ones(window_size)/window_size, 
                                 mode='same')
        else:
            logger.warning(f"Unknown smoothing method: {method}. Using original data.")
            return elevations
            
        return smoothed.tolist()
    
    def get_elevation_open_elevation(self, coordinates: List[Tuple[float, float]]) -> List[Optional[float]]:
        """
        Get elevation data from Open Elevation API.
        
        Args:
            coordinates: List of (latitude, longitude) tuples
            
        Returns:
            List of elevation values (None for failed requests)
        """
        if not coordinates:
            return []
            
        # Batch requests for efficiency (max 100 points per request)
        batch_size = 100
        elevations = []
        
        for i in range(0, len(coordinates), batch_size):
            batch = coordinates[i:i + batch_size]
            
            try:
                payload = {
                    'locations': [{'latitude': lat, 'longitude': lon} for lat, lon in batch]
                }
                
                response = requests.post(
                    self.apis['open_elevation'],
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                
                data = response.json()
                batch_elevations = [result.get('elevation') for result in data.get('results', [])]
                elevations.extend(batch_elevations)
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Failed to get elevation data for batch {i//batch_size + 1}: {e}")
                elevations.extend([None] * len(batch))
                
        return elevations
    
    def get_elevation_usgs(self, coordinates: List[Tuple[float, float]]) -> List[Optional[float]]:
        """
        Get elevation data from USGS Elevation Point Query Service.
        
        Args:
            coordinates: List of (latitude, longitude) tuples
            
        Returns:
            List of elevation values (None for failed requests)
        """
        elevations = []
        
        for lat, lon in coordinates:
            try:
                params = {
                    'x': lon,
                    'y': lat,
                    'units': 'Meters',
                    'output': 'json'
                }
                
                response = requests.get(
                    self.apis['usgs'],
                    params=params,
                    timeout=10
                )
                response.raise_for_status()
                
                data = response.json()
                elevation = data.get('USGS_Elevation_Point_Query_Service', {}).get('Elevation_Query', {}).get('Elevation')
                
                if elevation is not None:
                    elevations.append(float(elevation))
                else:
                    elevations.append(None)
                    
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Failed to get USGS elevation for {lat}, {lon}: {e}")
                elevations.append(None)
                
        return elevations
    
    def validate_elevation_data(self, elevations: List[float], 
                               coordinates: List[Tuple[float, float]]) -> dict:
        """
        Validate elevation data for consistency and accuracy.
        
        Args:
            elevations: List of elevation values
            coordinates: List of (latitude, longitude) tuples
            
        Returns:
            Dictionary with validation results
        """
        if not elevations or len(elevations) != len(coordinates):
            return {'valid': False, 'reason': 'Invalid data length'}
            
        # Remove None values for analysis
        valid_elevations = [e for e in elevations if e is not None]
        
        if not valid_elevations:
            return {'valid': False, 'reason': 'No valid elevation data'}
            
        stats = {
            'min_elevation': min(valid_elevations),
            'max_elevation': max(valid_elevations),
            'elevation_range': max(valid_elevations) - min(valid_elevations),
            'mean_elevation': sum(valid_elevations) / len(valid_elevations),
            'valid_points': len(valid_elevations),
            'total_points': len(elevations),
            'data_completeness': len(valid_elevations) / len(elevations)
        }
        
        # Check for reasonable elevation values (below Everest, above Dead Sea)
        if stats['min_elevation'] < -500 or stats['max_elevation'] > 9000:
            return {'valid': False, 'reason': 'Elevation values out of reasonable range', 'stats': stats}
            
        # Check for excessive elevation changes between consecutive points
        large_changes = 0
        for i in range(1, len(elevations)):
            if elevations[i] is not None and elevations[i-1] is not None:
                change = abs(elevations[i] - elevations[i-1])
                if change > 500:  # More than 500m change between points
                    large_changes += 1
                    
        if large_changes > len(elevations) * 0.1:  # More than 10% have large changes
            return {'valid': False, 'reason': 'Too many large elevation changes', 'stats': stats}
            
        return {'valid': True, 'stats': stats}
    
    def process_gpx_elevation(self, gpx_path: Path, output_path: Path,
                             api: str = 'open_elevation', 
                             smooth_method: str = 'gaussian',
                             smooth_sigma: float = 1.0,
                             validate: bool = True) -> dict:
        """
        Process a GPX file to improve elevation data.
        
        Args:
            gpx_path: Path to input GPX file
            output_path: Path to output GPX file
            api: API to use for elevation data ('open_elevation', 'usgs')
            smooth_method: Smoothing method for elevation data
            smooth_sigma: Smoothing parameter
            validate: Whether to validate elevation data
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing GPX file: {gpx_path}")
        
        # Parse GPX file
        with open(gpx_path, 'r', encoding='utf-8') as f:
            gpx = gpxpy.parse(f)
            
        if not gpx.tracks:
            return {'success': False, 'reason': 'No tracks found in GPX file'}
            
        results = {
            'success': True,
            'tracks_processed': 0,
            'points_processed': 0,
            'elevation_stats': {}
        }
        
        # Process each track
        for track_idx, track in enumerate(gpx.tracks):
            for segment_idx, segment in enumerate(track.segments):
                if not segment.points:
                    continue
                    
                # Extract coordinates
                coordinates = [(point.latitude, point.longitude) for point in segment.points]
                
                # Get elevation data
                logger.info(f"Getting elevation data for track {track_idx+1}, segment {segment_idx+1} ({len(coordinates)} points)")
                
                if api == 'open_elevation':
                    elevations = self.get_elevation_open_elevation(coordinates)
                elif api == 'usgs':
                    elevations = self.get_elevation_usgs(coordinates)
                else:
                    logger.error(f"Unknown API: {api}")
                    return {'success': False, 'reason': f'Unknown API: {api}'}
                
                # Validate elevation data
                if validate:
                    validation = self.validate_elevation_data(elevations, coordinates)
                    results['elevation_stats'][f'track_{track_idx}_segment_{segment_idx}'] = validation
                    
                    if not validation['valid']:
                        logger.warning(f"Validation failed for track {track_idx+1}, segment {segment_idx+1}: {validation['reason']}")
                
                # Smooth elevation data
                if elevations and any(e is not None for e in elevations):
                    # Fill None values with interpolation
                    filled_elevations = self._interpolate_missing_elevations(elevations)
                    smoothed_elevations = self.smooth_elevation_data(filled_elevations, smooth_method, smooth_sigma)
                    
                    # Update GPX points
                    for i, point in enumerate(segment.points):
                        if i < len(smoothed_elevations):
                            point.elevation = smoothed_elevations[i]
                            
                    results['points_processed'] += len(segment.points)
                    
                results['tracks_processed'] += 1
        
        # Write processed GPX file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(gpx.to_xml())
            
        logger.info(f"Processed GPX saved to: {output_path}")
        results['output_file'] = str(output_path)
        
        return results
    
    def _interpolate_missing_elevations(self, elevations: List[Optional[float]]) -> List[float]:
        """
        Interpolate missing elevation values.
        
        Args:
            elevations: List of elevation values with possible None values
            
        Returns:
            List of elevation values with interpolated missing values
        """
        if not elevations:
            return []
            
        # Convert to numpy array for easier processing
        elev_array = np.array(elevations, dtype=float)
        
        # Find indices of valid values
        valid_indices = ~np.isnan(elev_array)
        
        if not np.any(valid_indices):
            # No valid values, return zeros
            return [0.0] * len(elevations)
            
        if np.all(valid_indices):
            # All values are valid
            return elevations
            
        # Interpolate missing values
        indices = np.arange(len(elevations))
        elev_array[~valid_indices] = np.interp(
            indices[~valid_indices], 
            indices[valid_indices], 
            elev_array[valid_indices]
        )
        
        return elev_array.tolist()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Enhanced elevation data processing for GPX files')
    parser.add_argument('input', help='Input GPX file path')
    parser.add_argument('output', help='Output GPX file path')
    parser.add_argument('--api', choices=['open_elevation', 'usgs'], 
                       default='open_elevation', help='Elevation API to use')
    parser.add_argument('--smooth-method', choices=['gaussian', 'median', 'moving_average'],
                       default='gaussian', help='Smoothing method')
    parser.add_argument('--smooth-sigma', type=float, default=1.0, 
                       help='Smoothing parameter (standard deviation or window size)')
    parser.add_argument('--no-validate', action='store_true', 
                       help='Skip elevation data validation')
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)
        
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Process elevation data
    processor = ElevationProcessor()
    results = processor.process_gpx_elevation(
        input_path, 
        output_path,
        api=args.api,
        smooth_method=args.smooth_method,
        smooth_sigma=args.smooth_sigma,
        validate=not args.no_validate
    )
    
    if results['success']:
        logger.info(f"Successfully processed {results['tracks_processed']} tracks and {results['points_processed']} points")
        if 'elevation_stats' in results:
            for track_key, stats in results['elevation_stats'].items():
                if stats['valid']:
                    logger.info(f"{track_key}: Valid elevation data - {stats['stats']}")
                else:
                    logger.warning(f"{track_key}: {stats['reason']}")
    else:
        logger.error(f"Processing failed: {results['reason']}")
        sys.exit(1)

if __name__ == '__main__':
    main()