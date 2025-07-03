# Running Routes - Development Setup

This document covers the development setup for both the current Jekyll site and the new Hugo migration.

## Current Jekyll Setup (Production)

The site currently uses Jekyll and is deployed via GitHub Pages.

### Prerequisites
- Ruby (3.2+)
- Python (3.8+)
- Git

### Local Development
1. Install dependencies:
   ```bash
   cd docs
   bundle install
   pip install gpxpy
   ```

2. Generate GPX files:
   ```bash
   python scripts/generate_gpx_files.py
   ```

3. Serve the site:
   ```bash
   cd docs
   bundle exec jekyll serve
   ```

## New Hugo Setup (In Development)

We're migrating to Hugo for improved performance and modern tooling.

### Prerequisites
- Hugo Extended (0.140.2+)
- Python (3.8+)
- Git

### Local Development
1. Install Hugo:
   ```bash
   # On macOS
   brew install hugo
   
   # On Ubuntu/Debian
   sudo snap install hugo --channel=extended
   
   # Or download from https://github.com/gohugoio/hugo/releases
   ```

2. Generate GPX files:
   ```bash
   python scripts/generate_gpx_files.py
   ```

3. Copy assets to Hugo:
   ```bash
   cp -r docs/assets hugo-site/static/
   cp docs/favicon.ico hugo-site/static/
   ```

4. Serve the Hugo site:
   ```bash
   cd hugo-site
   hugo server -D
   ```

## Migration Progress

- [x] Basic Hugo site structure
- [x] Theme configuration (Ananke)
- [x] Content migration (homepage, about)
- [x] Bob Graham Round route page
- [x] GPX viewer shortcode
- [x] GitHub Actions workflow (disabled)
- [ ] Complete content migration
- [ ] Theme customization
- [ ] Performance optimizations
- [ ] Testing and validation

## Deployment

### Current (Jekyll)
Automatically deployed via `.github/workflows/jekyll-gh-pages.yml` on pushes to main.

### Future (Hugo)
Ready to deploy via `.github/workflows/hugo-gh-pages.yml` when migration is complete.
To switch: change the branch trigger from "disabled" to "main" and disable the Jekyll workflow.