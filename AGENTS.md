# AGENTS.md

## Purpose

This repository contains working files for the [Cybots Wiki](https://cybots.fandom.com/wiki/Cybots_Wiki) fandom website.

The repo is primarily used for maintaining and developing:

* Lua scripts and Scribunto modules
* Wiki templates
* Infoboxes
* Page formatting utilities
* Navigation and data modules
* Other MediaWiki-related assets and support files

## Guidelines for AI Agents

* Assume the target platform is **MediaWiki/Fandom**.
* Prefer solutions compatible with **Fandom's Lua/Scribunto environment**.
* Keep templates and modules lightweight and maintainable.
* Preserve backward compatibility with existing wiki pages when possible.
* Avoid unnecessary external dependencies.
* Follow existing naming conventions and file structure.
* When editing templates or modules, consider how changes affect transcluded pages site-wide.
* Write clear comments for non-obvious logic.
* Prefer readable, modular Lua code over overly clever implementations.

## Common Technologies

* Lua (Scribunto)
* MediaWiki template syntax
* Wikitext
* HTML/CSS used within Fandom templates
* Parser functions and template logic

## Notes

This is a working repository, not a standalone application.
Many files are intended to be copied or synchronized into the live Fandom wiki environment.
