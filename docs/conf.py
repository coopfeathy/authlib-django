import os
import sys
sys.path.insert(0, os.path.abspath('..'))

import authlib
import sphinx_typlog_theme

extensions = ['sphinx.ext.autodoc']
templates_path = ['_templates']

source_suffix = '.rst'
master_doc = 'index'

project = u'Authlib'
copyright = u'2017, Hsiaoming Yang'
author = u'Hsiaoming Yang'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = authlib.__version__
# The full version, including alpha/beta/rc tags.
release = authlib.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = 'en'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

html_theme = 'sphinx_typlog_theme'
html_favicon = '_static/favicon.ico'
html_theme_path = [sphinx_typlog_theme.get_path()]
html_theme_options = {
    'logo': 'authlib.png',
    'color': '#3E7FCB',
    'navs': [
        {'url': 'https://authlib.org/', 'title': 'Homepage'},
        {'url': 'https://github.com/lepture/authlib', 'title': 'GitHub'},
    ],
    'description': 'A ready to use authentication library.',
    'github_user': 'lepture',
    'github_repo': 'authlib',
    'analytics_id': 'UA-34098939-7',
    'meta_html': (
        '<link rel="apple-touch-icon" sizes="180x180" '
        'href="//authlib.org/apple-touch-icon.png">'
    )
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_sidebars = {
    '**': [
        'project.html',
        'localtoc.html',
        'relations.html',
        'searchbox.html',
    ]
}

# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'Authlibdoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'Authlib.tex', u'Authlib Documentation',
     u'Hsiaoming Yang', 'manual'),
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'authlib', u'Authlib Documentation',
     [author], 1)
]


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'Authlib', u'Authlib Documentation',
     author, 'Authlib', 'One line description of project.',
     'Miscellaneous'),
]
