# Contributing to Running Routes

Thanks for your interest in contributing! Whether you're submitting a route, improving the code, or fixing a bug, your input is welcome. 🏃

---

## ✨ Quick Start (Codespaces / Dev Containers)

The fastest way to get started is using **GitHub Codespaces** or **VS Code Dev Containers**. These provide a fully configured development environment with all dependencies pre-installed.

### Option 1: GitHub Codespaces (Recommended)

1. **Open in Codespaces**: Click the green "Code" button on this repository and select "Open with Codespaces", or use the badge below:

2. **Wait for setup**: The Codespace will automatically:
   - Use the Python 3.12 container defined in [`.devcontainer/devcontainer.json`](.devcontainer/devcontainer.json)
   - Install all Python dependencies via `pip install .` (using [`pyproject.toml`](pyproject.toml))
   - Set up VS Code extensions for Python development (`ms-python.python`, `ms-python.debugpy`)

3. **Start contributing**: Once the environment is ready, you can run scripts, tests, and make changes immediately.

### Option 2: VS Code Dev Containers

If you prefer to work locally with Docker:

1. **Install prerequisites**:
   - [VS Code](https://code.visualstudio.com/)
   - [Docker Desktop](https://www.docker.com/products/docker-desktop)
   - [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

2. **Clone and open**:
   ```bash
   git clone https://github.com/your-username/running-routes.git
   code running-routes
   ```

3. **Reopen in Container**: When prompted, click "Reopen in Container", or use the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`) and select "Dev Containers: Reopen in Container".

4. **Environment ready**: The container will set up the same environment as Codespaces, with all dependencies and extensions configured.

---

## 🖥️ Running Locally (Traditional Setup)

If you prefer a traditional local setup without containers:

### 1. Clone the repository

```bash
git clone https://github.com/your-username/running-routes.git
cd running-routes
```

### 2. Set up a Python virtual environment

This project uses [`pyproject.toml`](pyproject.toml) for dependency management. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

Install the project in editable mode with all dependencies:

```bash
pip install -e .
```

### 4. Create a branch and start contributing

```bash
git checkout -b my-feature-branch
```

Make your changes, commit with a clear message, and open a [pull request](https://github.com/thomasturrell/running-routes/pulls).

---

## 🛠 What You Can Contribute

* 🗺️ **New routes** – Add GPX files in [`src/`](src/) with relevant metadata.
* 🐛 **Bug fixes** – Fix issues in the scripts or data.
* 🧼 **Improvements** – Refactor code, simplify workflows, or improve documentation.

---

## 📁 Repository Structure

| Path | Description |
|------|-------------|
| [`src/`](src/) | Source GPX files organised by route type (`fell/`, `road/`, `trail/`) |
| [`scripts/`](scripts/) | Python tools for processing and generating GPX files |
| [`tests/`](tests/) | Pytest test suite |
| [`docs/`](docs/) | GitHub Pages site content (Jekyll, auto-published) |
| [`pyproject.toml`](pyproject.toml) | Project metadata and Python dependencies |
| [`.devcontainer/`](.devcontainer/) | Dev Container configuration for Codespaces/VS Code |
| [`.vscode/`](.vscode/) | VS Code settings and debug configurations |

---

## 📜 Script Examples

The [`scripts/`](scripts/) directory contains Python tools for processing GPX files. See the [scripts README](scripts/README.md) for detailed documentation.

### `plot_route_from_waypoints.py`

Calculates a route between waypoints using OpenStreetMap data:

```bash
# Basic usage
python scripts/plot_route_from_waypoints.py src/fell/bob-graham-round/bob-graham-round-waypoints.gpx

# With custom output path
python scripts/plot_route_from_waypoints.py src/fell/bob-graham-round/bob-graham-round-waypoints.gpx \
    --output src/fell/bob-graham-round/bob-graham-round.gpx

# With additional options
python scripts/plot_route_from_waypoints.py src/fell/bob-graham-round/bob-graham-round-waypoints.gpx \
    --snap-threshold 10.0 \
    --max-cache-age-days 14 \
    --force-refresh
```

### `fix_summit_waypoints.py`

Enriches summit waypoints with accurate coordinates from the Database of British and Irish Hills (DoBIH):

```bash
# Basic usage (outputs to *_enriched.gpx)
python scripts/fix_summit_waypoints.py src/fell/bob-graham-round/bob-graham-round-waypoints.gpx

# With custom output path
python scripts/fix_summit_waypoints.py src/fell/bob-graham-round/bob-graham-round-waypoints.gpx \
    --output src/fell/bob-graham-round/bob-graham-round-waypoints-fixed.gpx
```

### `generate_gpx_files.py`

Generates derivative GPX files (summits, POIs, simplified tracks, individual legs) from master route files:

```bash
python scripts/generate_gpx_files.py
```

This processes all routes defined in the script and outputs files to `docs/assets/gpx/`.

### Running Tests

The test suite uses pytest:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_plot_route_from_waypoints.py
```

---

## ✅ Contribution Guidelines

* Keep pull requests focused and minimal.
* Test your scripts before submitting (`pytest`).
* Use clear, descriptive commit messages.
* For significant changes, open an issue first to discuss.

---

## 🌐 Running the Docs Site Locally (Jekyll)

The GitHub Pages site is built using Jekyll from the [`docs/`](docs/) folder.

### Prerequisites

- **Ruby** (2.7+) – See [Ruby installation guide](https://www.ruby-lang.org/en/documentation/installation/)
- **Bundler** – `gem install bundler`

### Setup and Run

```bash
# Install dependencies (from repo root)
cd docs
bundle install

# Serve the site locally
bundle exec jekyll serve
```

Visit `http://localhost:4000` in your browser.

### WSL / Ubuntu Setup

If you're using WSL or Ubuntu, install Ruby and dependencies first:

```bash
sudo apt update
sudo apt install ruby-full build-essential zlib1g-dev

# Configure gem installation path
echo 'export GEM_HOME="$HOME/.gem"' >> ~/.bashrc
echo 'export PATH="$HOME/.gem/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Install Jekyll and Bundler
gem install bundler jekyll

# Install project dependencies and run
cd docs
bundle install
bundle exec jekyll serve
```

---

## 📬 Need Help?

Open an [issue](https://github.com/thomasturrell/running-routes/issues) and we'll be happy to assist.

Thanks again for contributing!
