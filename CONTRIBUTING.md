# Contributing to Running Routes

Thanks for your interest in contributing! Whether you're submitting a route, improving the code, or fixing a bug, your input is welcome. 🏃

---

## ✨ Quick Start

1. **Fork this repository** and clone your fork:

   ```bash
   git clone https://github.com/your-username/running-routes.git
   cd running-routes
   ```

2. **Set up a Python virtual environment** (for tools like `gpxpy`):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install gpxpy
   ```

3. **Create a new branch** for your changes:

   ```bash
   git checkout -b my-feature-branch
   ```

4. Make your changes and commit them with a clear, descriptive message.

5. Push your branch and open a [pull request](https://github.com/thomasturrell/running-routes/pulls).

---

## 🛠 What You Can Contribute

* 🧽 **New routes** – Add GPX files in `src/` with relevant metadata.
* 🐛 **Bug fixes** – Fix issues in the scripts or data.
* 🧼 **Improvements** – Refactor code, simplify workflows, or improve documentation.
* 🚀 **Enhanced features** – Elevation data improvements, Strava integration, analytics

---

## 📁 Repository Structure

* `src/` – Source data (raw GPX files)
* `scripts/` – Python tools for building and processing GPX
* `docs/` – GitHub Pages site content (auto-published)
* `requirements.txt` – Python dependencies for enhanced features

---

## ✅ Contribution Guidelines

* Keep pull requests focused and minimal.
* Test your scripts locally before submitting.
* Use clear, descriptive commit messages.
* For significant changes, open an issue first to discuss.
* Follow existing code style and documentation patterns.

---

## 🌐 Running the Site Locally (Jekyll)

The GitHub Pages site is built using Jekyll from the `docs/` folder. To preview it locally:

### 1. Install dependencies

```bash
gem install bundler
bundle install
```

If you don't have Ruby installed, see [https://www.ruby-lang.org/en/documentation/installation/](https://www.ruby-lang.org/en/documentation/installation/)

### 2. Serve the site locally

```bash
bundle exec jekyll serve --source docs
```

Visit `http://localhost:4000` in your browser.

---

## 🔧 Enhanced Features Setup

### Python Dependencies

For enhanced elevation processing and Strava integration:

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file for development (not committed):

```bash
# Strava API (optional)
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_ACCESS_TOKEN=your_access_token
STRAVA_REFRESH_TOKEN=your_refresh_token

# Google Analytics (optional)
GOOGLE_ANALYTICS_ID=GA_MEASUREMENT_ID
```

### Testing Enhanced Features

```bash
# Test elevation enhancement
python scripts/enhance_elevation.py src/fell/ramsay-round/ramsay-round.gpx test_output.gpx

# Test existing GPX generation
python scripts/generate_gpx_files.py
```

---

## 🐧 WSL Instructions (Ubuntu on Windows)

If you're using WSL (e.g. Ubuntu on Windows), you may need extra setup:

### 1. Install Ruby and dependencies

```bash
sudo apt update
sudo apt install ruby-full build-essential zlib1g-dev
```

Add gems to your user directory:

```bash
echo '# Install Ruby Gems to ~/.gem' >> ~/.bashrc
echo 'export GEM_HOME="$HOME/.gem"' >> ~/.bashrc
echo 'export PATH="$HOME/.gem/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 2. Install Jekyll & Bundler

```bash
gem install bundler jekyll
```

### 3. Install project dependencies

```bash
bundle install
```

### 4. Run the site

```bash
bundle exec jekyll serve --source docs
```

You should now be able to view the site at `http://localhost:4000`.

---

## 📬 Need Help?

Open an [issue](https://github.com/thomasturrell/running-routes/issues) and we’ll be happy to assist.

Thanks again for contributing!

## 📈 Performance and Accessibility

When contributing to the site:

* **Performance**: Optimize images, minify assets, consider caching
* **Accessibility**: Use semantic HTML, ARIA labels, keyboard navigation
* **Analytics**: Privacy-conscious tracking, user consent
* **Mobile**: Responsive design, touch-friendly interfaces

---

## 📬 Need Help?

Open an [issue](https://github.com/thomasturrell/running-routes/issues) and we'll be happy to assist.

For enhanced features documentation, see [ENHANCED_FEATURES.md](docs/ENHANCED_FEATURES.md).

Thanks again for contributing!
