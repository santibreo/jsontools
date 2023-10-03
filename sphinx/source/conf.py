# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
from __future__ import annotations

import sys
from pathlib import Path

REPO_PATH = Path(__file__).absolute().parent.parent.parent

sys.path.insert(0, str(REPO_PATH / 'src'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'JSONtools'
copyright = '2023, Santiago B. Pérez Pita'
author = 'Santiago B. Pérez Pita'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.coverage',
    'sphinx.ext.doctest',
    'sphinx.ext.githubpages',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    #  'sphinx_autodoc_typehints',
    #  'sphinxcontrib.confluencebuilder',
]

# Math has to be rendered to an image for confluence
if any('confluence' in arg for arg in sys.argv):
    extensions.append('sphinx.ext.imgmath')
    imgmath_font_size = 14
    imgmath_image_format = 'svg'
    imgmath_use_preview = True
else:
    extensions.append(
        'sphinx.ext.mathjax',
    )

templates_path = ['_templates']
exclude_patterns = []
pygments_style = 'friendly'

# -- Options for Autodoc -----------------------------------------------------
# Automatically extract typehints when specified and place them in
autodoc_typehints = 'description'
# Don't show class signature with the class' name.
autodoc_class_signature = 'separated'
# Mock imports
autodoc_mock_imports = []

autodoc_typehints_format = 'short'
autosummary_generate = True
autodoc_type_aliases = {
    'Scalar': 'jsontools.Scalar',
    'JsonContent': 'jsontools.JsonContent',
    'JsonKey': 'jsontools.JsonKey',
    'JsonValue': 'jsontools.JsonValue',
    'NamingConvention': 'jsontools.NamingConvention',
}
autodoc_default_options = {
    #  'members': 'var1, var2',
    #  'member-order': 'bysource',
    'special-members': False,
    #  'undoc-members': True,
    'exclude-members': '__init__',
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
add_module_names = False

html_theme = 'furo'
html_title = ''  # This is added to the title, doesn't replace it (sh*t!)
html_short_title = ''
html_static_path = ['_static']
html_logo = str(Path('_static') / 'img/jsontools-logo-optimized.svg')
html_favicon = str(Path('_static') / 'img/jsontools-icon.ico')
html_theme_options = {
    'navigation_with_keys': True,
}
html_css_files = [
    'css/custom.css',
]
