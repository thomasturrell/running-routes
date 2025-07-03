# Running Routes - Enhanced Features Documentation

This document outlines the enhanced features and improvements added to the running-routes repository.

## Enhanced Elevation Data Processing

### Overview
The `enhance_elevation.py` script provides improved elevation data accuracy for GPX files, specifically designed for fell running routes with rugged terrain.

### Features
- **Multiple Data Sources**: Supports Open Elevation API and USGS Elevation Point Query Service
- **Data Smoothing**: Implements Gaussian, median, and moving average smoothing algorithms
- **Validation**: Checks elevation data for consistency and reasonableness
- **Interpolation**: Fills missing elevation data points intelligently

### Usage
```bash
# Basic usage with Open Elevation API
python scripts/enhance_elevation.py input.gpx output.gpx

# Use USGS data source with median smoothing
python scripts/enhance_elevation.py input.gpx output.gpx --api usgs --smooth-method median

# Custom smoothing parameters
python scripts/enhance_elevation.py input.gpx output.gpx --smooth-sigma 2.0
```

### Configuration
The script accepts the following parameters:
- `--api`: Choose elevation data source (`open_elevation`, `usgs`)
- `--smooth-method`: Smoothing algorithm (`gaussian`, `median`, `moving_average`)
- `--smooth-sigma`: Smoothing strength (default: 1.0)
- `--no-validate`: Skip elevation data validation

## Strava API Integration

### Overview
The `strava_integration.py` module provides secure integration with the Strava API for route validation and activity analysis.

### Features
- **Secure Token Management**: Uses environment variables for API credentials
- **Rate Limiting**: Complies with Strava's API rate limits (100/15min, 1000/day)
- **Data Caching**: Reduces API calls through intelligent caching
- **Webhook Support**: Real-time activity updates
- **Route Comparison**: Compare GPX routes with Strava activities

### Setup
1. Create a Strava application at [https://www.strava.com/settings/api](https://www.strava.com/settings/api)
2. Set environment variables:
   ```bash
   export STRAVA_CLIENT_ID="your_client_id"
   export STRAVA_CLIENT_SECRET="your_client_secret"
   export STRAVA_ACCESS_TOKEN="your_access_token"
   export STRAVA_REFRESH_TOKEN="your_refresh_token"
   ```

### Usage
```python
from scripts.strava_integration import StravaAPIClient

# Initialize client
client = StravaAPIClient()

# Get recent activities
activities = client.get_athlete_activities(limit=10)

# Compare route with activities
similar = client.compare_route_with_activities("route.gpx")
```

## Site Performance Improvements

### Analytics
- Google Analytics support added to `_config.yml`
- Privacy-conscious tracking configuration
- Performance monitoring capabilities

### Accessibility Enhancements
- Enhanced GPX viewer with keyboard navigation
- Screen reader support for interactive maps
- ARIA labels and semantic markup
- Focus management for better user experience

### Performance Optimizations
- Compressed Sass/CSS output
- Optimized asset loading
- Browser caching configuration
- Minified JavaScript resources

## Installation and Dependencies

### Python Dependencies
Install required packages for enhanced features:
```bash
pip install gpxpy requests numpy scipy
```

### Optional Dependencies
For full Strava integration:
```bash
pip install python-dotenv
```

For advanced elevation processing:
```bash
pip install matplotlib plotly  # For elevation profile visualization
```

## Configuration Files

### Environment Variables
Create a `.env` file in the project root for development:
```bash
# Strava API
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_ACCESS_TOKEN=your_access_token
STRAVA_REFRESH_TOKEN=your_refresh_token

# Google Analytics (optional)
GOOGLE_ANALYTICS_ID=GA_MEASUREMENT_ID
```

### Jekyll Configuration
The `_config.yml` has been enhanced with:
- Analytics support
- Performance optimizations
- Additional plugins for SEO and caching

## API Rate Limits and Caching

### Strava API
- **Short-term**: 100 requests per 15 minutes
- **Daily**: 1000 requests per 24 hours
- Automatic rate limit handling with exponential backoff

### Elevation APIs
- **Open Elevation**: No rate limits, but please be considerate
- **USGS**: No official limits, but includes built-in rate limiting

### Caching Strategy
- API responses cached for 1 hour by default
- Cache files stored in `cache/` directory
- Automatic cache expiration and cleanup

## Error Handling and Logging

All enhanced features include comprehensive error handling and logging:
- Detailed error messages for troubleshooting
- Graceful degradation when APIs are unavailable
- Configurable logging levels
- Recovery mechanisms for failed requests

## Security Considerations

### API Keys
- Never commit API keys to version control
- Use environment variables for all sensitive data
- Rotate tokens regularly
- Monitor API usage for unusual activity

### Data Privacy
- Minimal data collection and retention
- User consent for analytics tracking
- Secure handling of location data
- GDPR compliance considerations

## Testing

### Manual Testing
Test enhanced features with sample data:
```bash
# Test elevation enhancement
python scripts/enhance_elevation.py src/fell/ramsay-round/ramsay-round.gpx test_output.gpx

# Test Strava integration (requires valid tokens)
python scripts/strava_integration.py
```

### Automated Testing
Run the existing test suite to ensure compatibility:
```bash
python scripts/test_plot_route_from_waypoints.py
```

## Contributing

When contributing to these enhanced features:
1. Maintain backward compatibility
2. Add appropriate error handling
3. Include documentation updates
4. Test with real GPX data
5. Consider rate limits and API quotas

## Future Enhancements

Planned improvements include:
- Machine learning for route optimization
- Real-time weather integration
- Advanced elevation profile analysis
- Mobile app companion
- Community route sharing features