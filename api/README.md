# API Integration Structure

This directory is prepared for future Strava API integration and other API services.

## Planned Structure

```
api/
├── strava/
│   ├── auth.py          # OAuth handling
│   ├── client.py        # API client
│   ├── webhooks.py      # Webhook handlers
│   └── cache.py         # Caching layer
├── elevation/
│   ├── providers.py     # Multiple elevation data sources
│   └── smoothing.py     # Data processing
└── config/
    ├── settings.py      # API configuration
    └── secrets.example  # Example secrets file
```

## Environment Variables

Future API integration will require these environment variables:

```bash
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REFRESH_TOKEN=your_refresh_token
ELEVATION_API_KEY=your_elevation_api_key
REDIS_URL=redis://localhost:6379  # For caching
```

## Next Steps

1. Set up Strava API application
2. Implement OAuth flow for user authentication
3. Create caching layer for API responses
4. Add webhook handlers for real-time updates
5. Integrate elevation data from multiple sources

See [ROADMAP.md](../ROADMAP.md) for detailed implementation plan.