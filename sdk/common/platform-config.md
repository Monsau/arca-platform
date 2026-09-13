# Platform Configuration SDK

## Purpose

Common configuration loading conventions for Arca Suite products.

## Conventions

- Configuration is loaded from environment variables first.
- Optional configuration files in `config/examples/` document available settings.
- Secrets are referenced by name, never embedded in configuration files.
- Configuration schemas are defined in `schemas/configuration/`.

## Status

Planned. Reference implementation will be added per language.
