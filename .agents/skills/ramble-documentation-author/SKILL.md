---
name: ramble-documentation-author
description: "Guide for authoring, updating, and building Ramble documentation in Sphinx/reStructuredText (reST) format under docs/."
---

# Ramble Documentation Author Guide

This skill provides guidelines for writing, updating, and verifying Ramble documentation located in the `docs/` directory, which is published to Read The Docs.

---

## 1. Documentation Structure (`docs/`)

Ramble documentation is written in **reStructuredText (`.rst`)** and managed by Sphinx. Key files and directories:

- `docs/index.rst`: Main table of contents and introduction.
- `docs/getting_started.rst`: Beginner tutorials and workspace quickstart.
- `docs/workspace_config.rst`: Workspace configuration file specifications.
- `docs/configuration_files.rst`: Detailed section syntax descriptions.
- `docs/package_managers.rst`: Package manager integration guides (Spack, EESSI).
- `docs/dev_guides/`: Developer guides for authoring applications, modifiers, workflow managers, etc.
- `docs/command_index.rst`: Ramble CLI command reference.

---

## 2. reStructuredText (reST) Syntax Guidelines

### Headings
Use consistent underline characters for document hierarchy:

```rst
Document Title
==============

Section Title
-------------

Subsection Title
~~~~~~~~~~~~~~~~

Sub-subsection Title
^^^^^^^^^^^^^^^^^^^^
```

### Directives & Alerts

```rst
.. note::
   This is a helpful note regarding workspace variables.

.. warning::
   Overriding Spack compiler specs directly can cause concretization conflicts.

.. code-block:: yaml

   ramble:
     variables:
       n_nodes: 2
```

### Cross-Referencing & Links

- **Document Links**: `:doc:\`workspace_config\`` or `:doc:\`Application Guide <dev_guides/application_dev_guide>\``
- **Section References**: Use explicit targets:
  ```rst
  .. _my-custom-section:

  My Custom Section
  -----------------
  Refer to :ref:`my-custom-section`.
  ```
- **External Links**: `` `Ramble Docs <https://ramble.readthedocs.io/>`_ ``

---

## 3. Building Documentation Locally

Before submitting documentation changes, build the HTML documentation locally to verify formatting and check for syntax errors or broken links.

### Build Steps
1. Navigate to the `docs/` directory:
   ```bash
   cd docs
   ```
2. Build HTML output:
   ```bash
   make html
   ```
   *(Or using `sphinx-build`: `sphinx-build -b html . _build/html`)*
3. Verify output in `docs/_build/html/index.html`.

### Checking Links
Run Sphinx linkcheck to ensure no external or internal links are broken:
```bash
make linkcheck
```

---

## 4. Documentation Best Practices

1. **Keep Examples Runnable**: Ensure all YAML configuration snippets in documentation reflect current Ramble schema and pass validation.
2. **Document New CLI Commands & Directives**: When adding new directives in `lib/ramble/ramble/language/`, ensure corresponding documentation is added to the Developer Guides (`docs/dev_guides/`).
3. **Check Build Warnings**: Treat Sphinx build warnings as errors—resolve any missing cross-reference target warnings during `make html`.
