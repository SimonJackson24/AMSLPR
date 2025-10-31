# Sphinx Documentation Setup Guide

This guide provides instructions for setting up and generating the AMSLPR Sphinx documentation site.

## Prerequisites

- Python 3.8 or later
- pip package manager
- Git (for version control)

## Installation

### 1. Install Sphinx and Dependencies

```bash
# Create virtual environment
python -m venv docs_env
source docs_env/bin/activate  # On Windows: docs_env\Scripts\activate

# Install Sphinx and extensions
pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints myst-parser

# Install additional extensions for API documentation
pip install sphinxcontrib-openapi sphinxcontrib-redoc
```

### 2. Initialize Sphinx Documentation

```bash
# Navigate to docs directory
cd docs

# Initialize Sphinx (if not already done)
sphinx-quickstart --quiet --project="AMSLPR" --author="Automate Systems" \
    --release="1.0.0" --language="en" --suffix=".md" --master="index" \
    --ext-autodoc --ext-doctest --ext-intersphinx --ext-todo \
    --ext-coverage --ext-mathjax --ext-ifconfig --ext-githubpages \
    --makefile --no-batchfile .
```

## Configuration

### Sphinx Configuration (conf.py)

Create the following `conf.py` file in the `docs/` directory:

```python
# Configuration file for the Sphinx documentation builder.

# -- Project information -----------------------------------------------------
project = 'AMSLPR'
copyright = '2025, Automate Systems'
author = 'Automate Systems'
release = '1.0.0'
version = '1.0.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.githubpages',
    'sphinx_rtd_theme',
    'sphinx.ext.autosummary',
    'sphinx.ext.graphviz',
    'myst_parser',
    'sphinxcontrib.openapi',
]

# MyST Parser settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Theme options
html_theme_options = {
    'canonical_url': '',
    'analytics_id': '',
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# -- Extension configuration --------------------------------------------------
# Autodoc settings
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'member-order': 'bysource',
}

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'flask': ('https://flask.palletsprojects.com/en/2.0.x/', None),
    'opencv': ('https://docs.opencv.org/4.5.2/', None),
}

# OpenAPI settings
openapi_spec_path = 'api/openapi_spec.md'
```

## Documentation Structure

### Main Index File (index.md)

Create the main documentation index:

```markdown
# AMSLPR Documentation

Welcome to the AMSLPR (Automate Systems License Plate Recognition) documentation.

## Overview

AMSLPR is a comprehensive license plate recognition system designed for automated vehicle access control and monitoring.

## Documentation Sections

```{toctree}
:maxdepth: 2
:caption: Getting Started

installation
quickstart
```

```{toctree}
:maxdepth: 2
:caption: API Documentation

api/openapi_spec
api/examples
```

```{toctree}
:maxdepth: 2
:caption: Deployment

deployment/docker_deployment
deployment/kubernetes_deployment
deployment/configuration
```

```{toctree}
:maxdepth: 2
:caption: Troubleshooting

troubleshooting/common_issues
troubleshooting/docker_issues
troubleshooting/kubernetes_issues
troubleshooting/configuration_issues
```

```{toctree}
:maxdepth: 2
:caption: Maintenance

maintenance/performance_tuning
maintenance/system_monitoring
maintenance/backup_recovery
```

```{toctree}
:maxdepth: 2
:caption: Development

development/contributing
development/api_reference
development/testing
```

## Quick Links

- [API Documentation](api/openapi_spec.html)
- [Configuration Reference](deployment/configuration.html)
- [Troubleshooting Guide](troubleshooting/common_issues.html)
- [Performance Tuning](maintenance/performance_tuning.html)

## Support

For support and questions:

- **Documentation Issues**: [GitHub Issues](https://github.com/automatesystems/amslpr/issues)
- **Community Support**: [GitHub Discussions](https://github.com/automatesystems/amslpr/discussions)
- **Professional Support**: support@automatesystems.com

## License

This documentation is licensed under the same terms as the AMSLPR project.
```

## Building Documentation

### 1. Generate HTML Documentation

```bash
# From the docs directory
make html

# Or using sphinx-build directly
sphinx-build -b html . _build/html
```

### 2. Generate PDF Documentation

```bash
# Install LaTeX (required for PDF generation)
# On Ubuntu/Debian:
sudo apt-get install texlive-latex-recommended texlive-fonts-recommended texlive-extra-utils texlive-latex-extra

# On macOS:
brew install mactex

# Generate PDF
make latexpdf
```

### 3. Auto-build Documentation

```bash
# Install sphinx-autobuild
pip install sphinx-autobuild

# Start auto-build server
sphinx-autobuild . _build/html --open-browser --reload-delay 1
```

## Advanced Features

### API Documentation Integration

#### OpenAPI/Swagger Integration

```python
# Add to conf.py
extensions.append('sphinxcontrib.openapi')

# In your documentation
.. openapi:: api/openapi_spec.md
   :examples:
```

#### Auto-generated API Docs

```python
# Generate API docs from code
sphinx-apidoc -f -o api/ ../src/

# This creates .rst files for all Python modules
```

### Versioning and Releases

#### Versioned Documentation

```bash
# Create version branches
git checkout -b v1.0
git checkout -b v1.1

# Build version-specific docs
sphinx-build -b html -D release=1.0 . _build/html/v1.0
sphinx-build -b html -D release=1.1 . _build/html/v1.1
```

#### Multi-version Setup

```python
# conf.py for multi-version support
html_context = {
    'display_github': True,
    'github_user': 'automatesystems',
    'github_repo': 'amslpr',
    'github_version': 'main',
    'conf_py_path': '/docs/',
    'versions': [
        ('latest', '/en/latest/'),
        ('v1.0', '/en/v1.0/'),
        ('v0.9', '/en/v0.9/'),
    ],
}
```

### Search and Navigation

#### Full-text Search

Sphinx automatically generates a search index. To enhance search:

```python
# conf.py
html_search_language = 'en'
html_search_options = {
    'type': 'default',
    'dict': '/_static/searchdict.txt',
}
```

#### Cross-references

```markdown
# Link to sections
[Configuration Reference](deployment/configuration.md#database-configuration)

# Link to API endpoints
`GET /api/vehicles`_

# Reference labels
.. _api-vehicles:

API Vehicles Endpoint
=====================
```

### Custom Themes and Styling

#### Custom CSS

Create `_static/custom.css`:

```css
/* Custom styles for AMSLPR documentation */
.wy-nav-content {
    max-width: 1200px;
}

.highlight pre {
    font-size: 14px;
    line-height: 1.4;
}

.api-method {
    background-color: #f8f9fa;
    border-left: 4px solid #007acc;
    padding: 10px;
    margin: 10px 0;
}
```

#### Theme Customization

```python
# conf.py
html_theme_options = {
    'style_nav_header_background': '#2980B9',
    'logo': 'logo.png',
    'canonical_url': 'https://docs.amslpr.com/',
}
```

## Deployment and Hosting

### GitHub Pages Deployment

#### GitHub Actions Workflow

```yaml
# .github/workflows/docs.yml
name: Deploy Documentation

on:
  push:
    branches: [ main ]
    paths: [ 'docs/**' ]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        pip install -r docs/requirements.txt

    - name: Build documentation
      run: |
        cd docs
        make html

    - name: Deploy to GitHub Pages
      uses: peaceiris/actions-gh-pages@v3
      if: github.ref == 'refs/heads/main'
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: docs/_build/html
```

### Netlify Deployment

#### netlify.toml

```toml
[build]
  publish = "docs/_build/html"
  command = "cd docs && make html"

[build.environment]
  PYTHON_VERSION = "3.9"

[[redirects]]
  from = "/api/*"
  to = "/api/openapi_spec.html"
  status = 200
```

### Read the Docs Integration

#### .readthedocs.yaml

```yaml
version: 2

build:
  os: ubuntu-20.04
  tools:
    python: "3.9"

python:
  install:
    - requirements: docs/requirements.txt

sphinx:
  configuration: docs/conf.py
  builder: html
  fail_on_warning: false

formats:
  - pdf
  - epub
```

## Documentation Maintenance

### Content Guidelines

1. **Use clear, concise language**
2. **Include practical examples**
3. **Provide step-by-step instructions**
4. **Use consistent formatting**
5. **Include troubleshooting sections**
6. **Keep content up-to-date**

### Quality Checks

```bash
# Check for broken links
make linkcheck

# Check documentation coverage
make coverage

# Validate HTML output
make html SPHINXOPTS="-W -E"
```

### Documentation Testing

```python
# docs/test_docs.py
import pytest
from sphinx.testing.util import SphinxTestApp

def test_build_html():
    """Test that documentation builds without errors"""
    with SphinxTestApp(srcdir='docs') as app:
        app.build()
        assert not app._warning.getvalue()
```

## Best Practices

### Documentation Structure

1. **Organize by user journey**: Installation → Configuration → Usage → Troubleshooting
2. **Use consistent terminology**: Define terms and use them consistently
3. **Include examples**: Provide code examples for common use cases
4. **Version documentation**: Keep docs in sync with code versions
5. **Accessibility**: Use alt text for images, semantic HTML

### Content Management

1. **Regular reviews**: Review and update documentation quarterly
2. **User feedback**: Monitor GitHub issues and discussions for documentation gaps
3. **Automation**: Use CI/CD to validate documentation builds
4. **Templates**: Create templates for consistent documentation structure
5. **Localization**: Plan for internationalization if needed

### Performance Optimization

1. **Optimize images**: Compress images and use appropriate formats
2. **Minimize JavaScript**: Use lightweight themes and extensions
3. **Enable caching**: Configure proper HTTP caching headers
4. **CDN integration**: Use CDNs for global distribution
5. **Lazy loading**: Implement lazy loading for large content

## Troubleshooting Documentation Issues

### Common Build Issues

1. **Import errors**:
   ```bash
   # Check Python path
   PYTHONPATH=/path/to/project python -c "import src.module"

   # Install missing dependencies
   pip install missing-package
   ```

2. **Theme issues**:
   ```bash
   # Clear cache and rebuild
   make clean
   make html
   ```

3. **Extension conflicts**:
   ```bash
   # Check extension compatibility
   pip show sphinx-rtd-theme
   pip show myst-parser
   ```

### Search Issues

1. **Search not working**:
   - Ensure `html_search_language` is set correctly
   - Check that search index is generated
   - Verify JavaScript is not blocked

2. **Poor search results**:
   - Add more descriptive titles and headings
   - Include keywords in content
   - Use proper meta descriptions

## Support and Resources

### Learning Resources

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [MyST Parser Guide](https://myst-parser.readthedocs.io/)
- [Read the Docs](https://docs.readthedocs.io/)
- [Sphinx RTD Theme](https://sphinx-rtd-theme.readthedocs.io/)

### Community Support

- [Sphinx Users Mailing List](https://groups.google.com/forum/#!forum/sphinx-users)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/sphinx)
- [GitHub Discussions](https://github.com/sphinx-doc/sphinx/discussions)

### Professional Services

For enterprise documentation needs:

- Custom theme development
- Advanced integration setup
- Performance optimization
- Multi-language support
- Automated publishing workflows