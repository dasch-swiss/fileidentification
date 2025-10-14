# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python CLI tool for file format identification, integrity testing, and bulk file conversion
designed for digital preservation workflows.
It wraps around several external programs (siegfried/pygfried, ffmpeg, imagemagick, LibreOffice)
to provide comprehensive file processing capabilities.

## Development Commands

### Package Management

- **Install dependencies**: `uv sync`
- **Run the main script**: `uv run identify.py [path] [options]`
- **Update signatures**: `uv sync --extra update_fmt && uv run update.py`

### Code Quality

- **Lint with ruff**: `uv run ruff check .`
- **Format with ruff**: `uv run ruff format .`
- **Type check with mypy**: `uv run mypy .`

### Policy Testing

If the user edited auto-generated policies, the outcome of the policies can be tested using the `-t` flag:

- **Test conversion policies**: `uv run identify.py path/to/directory -t`
- **Test specific policy**: `uv run identify.py path/to/directory -tf fmt/XXX`

### Docker

- **Build manually**: `docker build -t fileidentification .`
- **execute bash script**: `fidr.sh path/to/directory [options]`

## Architecture

### Core Components

1. **CLI Entry Point** (`identify.py`)
   - Main Typer-based CLI with extensive flag options
   - Orchestrates the FileHandler workflow

2. **FileHandler** (`fileidentification/filehandling.py`)
   - Central orchestrator class that manages the entire workflow
   - Handles file identification, integrity testing, policy application, and conversion
   - Manages temporary directories and file movements

3. **Models** (`fileidentification/definitions/models.py`)
   - **SfInfo**: Core file information model (from siegfried output)
   - **PolicyParams**: File conversion policy specifications
   - **LogMsg/LogOutput/LogTables**: Logging and error tracking models

4. **Wrappers** (`fileidentification/wrappers`):
   - ffmpeg (`fileidentification/wrappers/ffmpeg.py`): Audio/video file testing
   - ImageMagick (`fileidentification/wrappers/imagemagick.py`): Image file testing
   - converter (`fileidentification/wrappers/converter.py`): file conversion

### Data Flow

1. **File Identification**: Uses pygfried (siegfried) to identify file formats by PRONOM PUID
2. **Policy Generation**: Creates JSON policies mapping PUIDs to conversion specifications
3. **Inspection**: Uses ffmpeg/imagemagick to test files on errors, warnings
4. **Conversion**: Applies policies using appropriate tools (ffmpeg, imagemagick, LibreOffice)
5. **Cleanup**: Manages temporary files and moves converted files to final locations

### Key File Structures

- **Policies JSON**: Maps PRONOM PUIDs to conversion specifications
  with fields like `bin`, `accepted`, `target_container`, `processing_args`
- **Log JSON**: Tracks all file operations and modifications
- **Default Policies**: Located in `fileidentification/definitions/default_policies.json`

## Configuration

### Environment Variables (`.env`)

- `DEFAULTPOLICIES`: Path to default policies JSON
- `TMP_DIR`: Temporary directory suffix (default: `_TMP`)
- `POLICIES_J`: Policies JSON file suffix (default: `_policies.json`)
- `LOG_J`: Log JSON file suffix (default: `_log.json`)

### External Dependencies

The project requires these external programs for full functionality:
- **siegfried** (via pygfried): File format identification
- **ffmpeg**: Audio/video processing and testing
- **imagemagick**: Image processing and testing
- **LibreOffice**: Document conversion
- **ghostscript**: PDF processing support

## Common Workflow Patterns

### Full Processing Pipeline

```bash
uv run identify.py path/to/directory -iar
```

- `-i`: inspect the files
- `-a`: apply conversion policies
- `-r`: remove temporary files and finalize

### Policy Development

1. Generate policies: `uv run identify.py path/to/directory`
2. Edit the generated `*_policies.json` file
3. Test policies: `uv run identify.py path/to/directory -t`
4. Apply: `uv run identify.py path/to/directory -ar`

### Available Additional Options

- `-v`: catch more warnings on video and image files during the tests.

- `-x`: move the parents of the converted files to the TMP/_REMOVED folder. When used in generating policies, it sets remove_original in the policies to true (default false).

- `-p path/to/policies.json`: load a custom policies json file instead of the default policies

- `-e`: append file types found in the directory to the given policies if they are missing in it.

- `-s`: move the files that are not listed in the policies to the folder _REMOVED . When used in generating policies, it does not add blank policies for formats that are not mentioned in `DEFAULTPOLICIES` .

- `-b`: create blank policies based on the files types encountered in the given directory.

- `-q`: just print errors

- `--csv`: get an additional output as csv aside from the log.json

- `--convert`: re-convert the files that failed during file conversion

## Important Notes

- The codebase follows PRONOM PUID standards for file format identification
- Policies are defined using PRONOM unique identifiers (PUIDs) as keys
- The tool supports both direct execution and Docker containerization
- All file operations are logged extensively in JSON format
- Temporary files are managed in structured `_TMP` directories
