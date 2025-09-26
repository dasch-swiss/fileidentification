# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python CLI tool for file format identification, integrity testing, and bulk file conversion
designed for digital preservation workflows.
It wraps around several external programs (siegfried/pygfried, ffmpeg, imagemagick, LibreOffice)
to provide comprehensive file processing capabilities.

## Development Commands

### Package Management

- **Install dependencies**: `uv sync --all-extras --dev`
- **Run the main script**: `uv run identify.py [path] [options]` 
- **Update signatures**: `uv run update.py && uv lock --upgrade`

### Code Quality

- **Lint with ruff**: `uv run ruff check .`
- **Format with ruff**: `uv run ruff format .`
- **Type check with mypy**: `uv run mypy .`

### Testing

The project does not use a formal test framework like pytest. Instead, it uses the `-t` flag for policy testing:

- **Test conversion policies**: `uv run identify.py path/to/directory -t`
- **Test specific policy**: `uv run identify.py path/to/directory -tf fmt/XXX`

### Docker

- **Run with Docker**: `uv run identify.py path/to/directory [flags] --docker`
- **Build manually**: `docker build -t fileidentification .`

## Architecture

### Core Components

1. **CLI Entry Point** (`identify.py`)
   - Main Typer-based CLI with extensive flag options
   - Orchestrates the FileHandler workflow

2. **FileHandler** (`fileidentification/filehandling.py`)
   - Central orchestrator class that manages the entire workflow
   - Handles file identification, integrity testing, policy application, and conversion
   - Manages temporary directories and file movements

3. **Models** (`fileidentification/defenitions/models.py`)
   - **SfInfo**: Core file information model (from siegfried output)
   - **PolicyParams**: File conversion policy specifications
   - **LogMsg/LogOutput**: Logging and error tracking models

4. **Wrappers** (`fileidentification/wrappers/wrappers.py`)
   - **Ffmpeg**: Audio/video integrity testing and conversion
   - **ImageMagick**: Image integrity testing and conversion
   - **Converter**: LibreOffice document conversion
   - **Rsync**: File synchronization operations

### Data Flow

1. **File Identification**: Uses pygfried (siegfried) to identify file formats by PRONOM PUID
2. **Policy Generation**: Creates JSON policies mapping PUIDs to conversion specifications
3. **Integrity Testing**: Uses ffmpeg/imagemagick to validate file integrity
4. **Conversion**: Applies policies using appropriate tools (ffmpeg, imagemagick, LibreOffice)
5. **Cleanup**: Manages temporary files and moves converted files to final locations

### Key File Structures

- **Policies JSON**: Maps PRONOM PUIDs to conversion specifications with fields like `bin`, `accepted`, `target_container`, `processing_args`
- **Log JSON**: Tracks all file operations and modifications
- **Default Policies**: Located in `fileidentification/defenitions/default_policies.json`

## Configuration

### Environment Variables (`.env`)
- `DEFAULTPOLICIES`: Path to default policies JSON
- `TMP_DIR`: Temporary directory suffix (default: `_TMP`)
- `POLICIES_J`: Policies JSON file suffix (default: `_policies.json`)
- `LOG_J`: Log JSON file suffix (default: `_log.json`)
- `RMV_DIR`: Removed files directory suffix (default: `_REMOVED`)

### External Dependencies
The project requires these external programs for full functionality:
- **siegfried** (via pygfried): File format identification
- **ffmpeg**: Audio/video processing and integrity testing
- **imagemagick**: Image processing and integrity testing
- **LibreOffice**: Document conversion
- **ghostscript**: PDF processing support

## Common Workflow Patterns

### Full Processing Pipeline
```bash
uv run identify.py path/to/directory -iar
```
- `-i`: integrity tests
- `-a`: apply conversion policies
- `-r`: remove temporary files and finalize

### Policy Development
1. Generate policies: `uv run identify.py path/to/directory`
2. Edit the generated `*_policies.json` file
3. Test policies: `uv run identify.py path/to/directory -t`
4. Apply: `uv run identify.py path/to/directory -ar`

## Important Notes

- The codebase follows PRONOM PUID standards for file format identification
- Policies are defined using PRONOM unique identifiers (PUIDs) as keys
- The tool supports both direct execution and Docker containerization
- All file operations are logged extensively in JSON format
- Temporary files are managed in structured `_TMP` directories