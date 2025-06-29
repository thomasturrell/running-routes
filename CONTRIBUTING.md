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

---

## 📁 Repository Structure

* `src/` – Source data (raw GPX files)
* `scripts/` – Python tools for building and processing GPX
* `docs/` – GitHub Pages site content (auto-published)

---

## ✅ Contribution Guidelines

* Keep pull requests focused and minimal.
* Test your scripts locally before submitting.
* Use clear, descriptive commit messages.
* For significant changes, open an issue first to discuss.

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
