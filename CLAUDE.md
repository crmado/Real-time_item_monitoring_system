# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Critical Development Guidelines

**IMPORTANT - Read First:**

1. **使用繁體中文回答** - Always respond in Traditional Chinese when communicating with users
2. **保持專案風格一致** - Follow existing project conventions, DO NOT arbitrarily rename variables, functions, or change code structure
3. **禁止創建批次檔** - Do not create batch files or shell scripts unless explicitly requested
4. **最小化文檔** - Avoid writing excessive external documentation. When explanation is needed, add comments directly in the code
5. **代碼優先** - Focus on writing code with inline comments rather than separate documentation files

## Project Overview

**Basler Industrial Vision System** - A high-performance desktop application for real-time object detection and video recording using Basler industrial cameras. The system supports both live camera feeds (280+ FPS) and video file playback for testing without physical hardware.

### Key Architecture Components

**Two Main Implementations:**
1. **basler_pyqt6/** - Production PyQt6 desktop application (primary)
2. **basler_mvc/** - Reference MVC implementation (for algorithm validation)

The project follows a dual-architecture approach where `basler_mvc` serves as the algorithm validation environment, and `basler_pyqt6` is the production desktop application that integrates proven algorithms.

## Core Commands

### Development & Running

```bash
# Quick start (recommended)
./run_pyqt6.sh

# Direct run
python basler_pyqt6/main_v2.py

# Install dependencies (Conda)
conda env create -f environment.yml
conda activate RPi_4_camera_py312
./install_deps.sh

# Install dependencies (pip)
pip install -r requirements.txt
```

### Testing

```bash
# Test unified configuration system
python basler_pyqt6/config/test_config.py

# Run with test video (no camera required)
# 1. Launch application
# 2. File > Load Video File
# 3. Select from basler_pyqt6/testData/
```

### Building & Releasing

```bash
# 1. Update version
vim basler_pyqt6/version.py  # Change __version__

# 2. Build package
python scripts/build.py

# 3. Release to server
python scripts/release.py --notes "Release notes"

# Build options
python scripts/build.py --skip-clean  # Skip cleanup for faster builds
python scripts/build.py --no-package  # Build only, no ZIP
```

### Check camera status
```bash
pypylon-listdevices  # List connected Basler cameras
```

## Architecture Deep Dive

### basler_pyqt6 Structure

```
basler_pyqt6/
├── main_v2.py                 # Application entry point
├── version.py                 # Version & update server config
├── updater.py                 # Auto-update functionality
├── config/                    # Unified configuration system
│   ├── settings.py            # Dataclass-based config definitions
│   ├── detection_params.json  # Runtime configuration (JSON)
│   └── test_config.py         # Configuration tests
├── core/                      # Business logic layer
│   ├── detection.py           # Detection controller (virtual gate counting)
│   ├── camera.py              # Basler camera interface
│   ├── video_player.py        # Video playback manager
│   ├── video_recorder.py      # Video recording (H.264)
│   ├── source_manager.py      # Camera/video source abstraction
│   └── kalman_tracker.py      # Object tracking (currently unused)
└── ui/                        # PyQt6 interface layer
    ├── main_window_v2.py      # Main application window
    ├── widgets/
    │   ├── debug_panel.py     # Parameter adjustment panel
    │   ├── camera_control.py  # Camera control widget
    │   ├── detection_control.py
    │   ├── recording_control.py
    │   ├── system_monitor.py  # CPU/RAM monitoring
    │   └── video_display.py   # Video rendering
    └── dialogs/
        └── update_dialog.py   # Update notification dialog
```

### Configuration System Architecture

**Critical Design Decision**: All detection parameters are centrally managed through the unified configuration system (`basler_pyqt6/config/`).

**Configuration Flow:**
1. `settings.py` defines dataclass-based configurations (type-safe)
2. `detection_params.json` persists runtime changes
3. `detection.py` and UI widgets read from unified config
4. Changes via UI → config → JSON persistence → next startup

**Configuration Categories:**
- **DetectionConfig**: 31 parameters for background subtraction, edge detection, morphology
- **GateConfig**: Virtual gate counting parameters (industrial-grade counting)
- **UIConfig**: UI control ranges and defaults
- **PerformanceConfig**: Image scaling, frame skipping
- **DebugConfig**: Debug output settings

**Key Pattern**: Never hardcode detection parameters. Always read from `get_config()`:
```python
from config.settings import get_config

config = get_config()
min_area = config.detection.min_area  # ✅ Correct
# min_area = 2  # ❌ Wrong - hardcoding
```

### Detection System Architecture

**Core Algorithm**: Virtual Gate Counting Method (工業級虛擬光柵計數法)

The detection system uses a sophisticated but efficient approach:

1. **ROI-based Processing**: Only processes a horizontal region of interest
2. **Background Subtraction**: MOG2 algorithm with basler_mvc validated parameters
3. **Virtual Gate Line**: A horizontal line in the ROI triggers counting when objects cross
4. **Spatiotemporal Deduplication**: Prevents double-counting using distance threshold and frame history

**Why Virtual Gate Instead of Tracking:**
- O(n) complexity vs O(n²) for tracking
- Deterministic: each object counted exactly once
- Handles 280 FPS without performance degradation
- No ID assignment overhead

**Key Detection Parameters** (from basler_mvc validation):
- `min_area: 2` - Optimized for tiny parts
- `bg_var_threshold: 3` - Extremely high sensitivity
- `bg_learning_rate: 0.001` - Prevents small parts from becoming background
- `gate_trigger_radius: 20` - Deduplication distance in pixels

### Source Management

The application abstracts camera vs. video sources through `SourceManager`:

```python
# Handles both:
# 1. Basler camera (pypylon)
# 2. Video files (OpenCV)
# Provides unified interface to main window
```

This allows testing all detection algorithms without physical hardware.

### Auto-Update System

**Update Flow:**
1. Client checks `UPDATE_SERVER_URL` (in `version.py`) every 24h
2. Compares local vs. remote version (semantic versioning)
3. Downloads ZIP package if update available
4. Extracts and replaces application
5. Restarts automatically

**Server Side** (`update_server/`):
- Flask-based update server
- Stores releases as ZIP files
- Maintains `update_manifest.json` with version metadata
- SFTP upload via `scripts/release.py`

### Build System

**PyInstaller Workflow:**
1. `basler_pyqt6.spec` defines bundle configuration
2. `scripts/build.py` orchestrates build process
3. Outputs to `releases/BaslerVisionSystem_v{version}_{timestamp}.zip`
4. Includes MD5 checksum and version JSON

**Spec File Key Points:**
- `--onedir` mode (not `--onefile`) for faster startup
- Bundles pypylon camera drivers
- Includes test data directory
- Platform-specific icon handling

## Version Management

**Single Source of Truth**: `basler_pyqt6/version.py`

Update these values before each release:
```python
__version__ = "2.0.1"  # Semantic versioning
BUILD_DATE = "2025-10-13"
BUILD_TYPE = "release"  # or "beta", "alpha"
UPDATE_SERVER_URL = "http://your-server.com:5000/api"
```

Version comparison uses tuple-based semantic comparison:
```python
compare_versions("2.0.1", "2.1.0")  # Returns -1 (update needed)
```

## Important Implementation Details

### Camera Configuration
- Target model: Basler acA640-300gm (GigE Vision)
- Network setup: Camera at 192.168.1.100, host in same subnet
- Frame buffer: 3 frames to prevent memory bloat at 280 FPS
- Grab strategy: LatestImageOnly (discard intermediate frames)

### Video Recording
- Codec: H.264 (libx264)
- Default CRF: 23 (adjustable quality)
- Thread-based async recording to avoid UI blocking
- Auto-generates timestamps in filename

### Performance Optimization
The system uses several strategies for high-speed operation:
- ROI-based processing reduces computation by ~70%
- Frame skipping option (configurable)
- Image downscaling option (30%, 50%, 75%, 100%)
- Minimal morphological operations to preserve small parts
- Connected components analysis (faster than contour finding)

### basler_mvc Reference

The MVC implementation serves as the "algorithm lab":
- Validates detection parameters through experimentation
- Proven parameters migrate to basler_pyqt6 config
- Uses simpler architecture for rapid prototyping
- Not for production deployment

## Dependency Notes

**Critical**: Python 3.12+ required for numpy>=1.26.0

**Platform-Specific:**
- PyQt6: Install from conda-forge on Conda environments
- pypylon: Requires Basler Pylon SDK (auto-installed via pip)
- opencv-python-headless: GUI-less version (lighter weight)

**Conda vs Pip:**
The install script (`install_deps.sh`) tries conda first, falls back to pip. PyQt6 installation is most reliable via pip even in conda environments.

## Common Gotchas

### Configuration Changes Not Applied
If parameter changes don't take effect:
1. Check if config loaded: `config = get_config()` returns singleton
2. Verify JSON file updated: `basler_pyqt6/config/detection_params.json`
3. For new parameters, add to dataclass in `settings.py` first

### Detection Not Working
1. Verify background subtractor initialized (needs ~100 frames to adapt)
2. Check ROI placement: must include objects
3. Validate min_area/max_area range covers target objects
4. Use debug panel to view binary output

### Build/Package Issues
1. Missing hidden imports: Add to `basler_pyqt6.spec` hiddenimports list
2. Data files not included: Add to datas list in spec file
3. Platform-specific: Test on target platform before releasing

### Performance Issues at High FPS
1. Enable ROI to reduce processing area
2. Increase frame skip ratio
3. Reduce image scale (50% typically sufficient)
4. Disable unused debug visualizations

## Testing Without Hardware

The system fully supports testing without Basler cameras:

1. Launch application
2. File > Load Video File
3. Navigate to `basler_pyqt6/testData/新工業相機收集資料/`
4. Select test video (MP4 format)
5. Use debug panel to adjust detection parameters in real-time
6. Save configuration to persist settings

This workflow allows algorithm development and parameter tuning without physical camera access.

## Code Style Conventions

**Language Usage:**
- **User Communication**: 繁體中文 (Traditional Chinese) - ALL responses to users
- **UI Text**: 繁體中文 (Chinese text in interface)
- **Code Elements**: English (variable names, function names, class names)
- **Logging**: Chinese for user-facing messages, English for technical/debug logs
- **Comments**: 繁體中文 for business logic explanations, English for technical implementation notes

**Naming Conventions:**
- **Class Names**: English PascalCase (e.g., `DetectionController`, `VideoPlayer`)
- **Functions**: English snake_case (e.g., `process_frame`, `get_config`)
- **Variables**: English snake_case (e.g., `min_area`, `frame_count`)
- **Config Keys**: English snake_case (e.g., `bg_var_threshold`, `gate_trigger_radius`)
- **Constants**: English UPPER_SNAKE_CASE (e.g., `UPDATE_SERVER_URL`, `BUILD_TYPE`)

**Critical Rules:**
- ⚠️ **DO NOT rename existing variables/functions/classes** - Maintain consistency with established codebase
- ⚠️ **DO NOT create new batch files or shell scripts** - Use existing scripts only
- ⚠️ **DO NOT create separate documentation files** - Use inline comments instead
- ✅ **DO add explanatory comments in code** - Especially for complex algorithms
- ✅ **DO follow existing patterns** - Study similar code before implementing new features

## Integration Points

### Adding New Detection Algorithms

1. Add parameters to `config/settings.py` DetectionConfig
2. Implement algorithm in `core/detection.py` DetectionController
3. Add UI controls in `ui/widgets/debug_panel.py`
4. Connect signals in `ui/main_window_v2.py`
5. Update JSON schema version if structure changes

### Adding New UI Widgets

Follow the existing pattern in `ui/widgets/`:
- Inherit from QWidget
- Define signals for communication
- Use Qt Designer layouts (programmatic, not .ui files)
- Connect to main window via signal/slot mechanism

### Modifying Auto-Update Behavior

Key files:
- `basler_pyqt6/updater.py` - Client-side update logic
- `update_server/app.py` - Server endpoints
- `scripts/release.py` - Upload automation

## Performance Benchmarks

Typical performance on target hardware (example):
- Camera FPS: 280+ (hardware limited)
- Processing FPS: 150-200 (with full detection pipeline)
- UI Update FPS: 60 (capped for smoothness)
- Detection latency: <5ms per frame
- Memory usage: ~200MB (steady state)

## External Resources

- **Basler Pylon SDK**: https://www.baslerweb.com/pylon
- **PyQt6 Documentation**: https://doc.qt.io/qtforpython-6/
- **OpenCV Docs**: https://docs.opencv.org/4.x/
- **Update Server**: See `update_server/README.md`
- **Config System**: See `basler_pyqt6/config/README.md`
