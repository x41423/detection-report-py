# Resources

This directory is intentionally kept in the repository even when it is sparse.

- `icons/`
  Reserved for repo-local desktop or frontend icon assets.
- `templates/`
  Reserved for repo-local document templates if the project stops relying on external absolute paths.

Current behavior:

- The application can run without files in these folders.
- Some configuration still points to external template paths outside the repo.
- Empty subdirectories here are placeholders, not accidental trash.

Maintenance rule:

- Do not delete `resources/icons` or `resources/templates` without first checking config, UI flows, and startup scripts.
