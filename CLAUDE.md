# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a real-time industrial item monitoring and detection system designed for production line automation. The system features two main architectures:

1. **Basler MVC (Primary)**: High-performance streamlined system optimized for Basler acA640-300gm industrial cameras (280+ FPS)
2. **Main Application (Legacy)**: Full-featured system with comprehensive UI and multi-camera support

## Development Commands

### Quick Start
```bash
# Recommended: Run the high-performance Basler MVC system
python run_ctk_version.py

# Alternative: Direct launch
cd basler_mvc && python main.py

# Test system components
python test_mvc_system.py
```

### Environment Setup
```bash
# Create conda environment
conda create -n RPi_4_camera python=3.10
conda activate RPi_4_camera

# Install core dependencies
pip install customtkinter opencv-python numpy pillow PyYAML

# Install Basler camera support (required for industrial cameras)
pip install pypylon

# Install all dependencies
pip install -r requirements.txt
```

### Testing and Validation
```bash
# Test MVC system components and imports
python test_mvc_system.py

# Test thread synchronization fixes
python test_thread_fix.py

# Validate video recording quality
python recording_quality_analyzer.py

# Verify video FPS accuracy
python video_fps_verifier.py
```

### Building Executables
```bash
# Build standalone executable (Windows)
pyinstaller --clean object_detection_system.spec
.\dist\object_detection_system.exe 2> logs\error.log

# Linux/Mac build
pyinstaller --onefile main.py
```

## Core Architecture

### Basler MVC (High-Performance System)
The primary system uses a clean MVC pattern optimized for industrial cameras:

```
basler_mvc/
├── main.py                           # Entry point with dependency checking
├── controllers/
│   └── main_controller.py            # Coordinates camera and detection models
├── models/
│   ├── basler_camera_model.py        # Basler camera interface (pypylon)
│   ├── detection_model.py            # Modular detection algorithms
│   ├── detection_processor.py        # High-performance frame processing
│   ├── video_recorder_model.py       # 280+ FPS video recording
│   └── video_player_model.py         # Video playback with detection
├── views/
│   └── main_view_ctk_bright.py       # CustomTkinter high-DPI UI
├── config/
│   └── settings.py                   # Centralized configuration
├── utils/
│   ├── system_diagnostics.py         # Hardware diagnostic tools
│   ├── recording_validator.py        # Video quality validation
│   └── memory_monitor.py             # Memory usage monitoring
└── styles/                           # Cross-platform UI themes
```

### Key Design Patterns
- **MVC Architecture**: Clean separation of concerns with observer pattern
- **Dependency Injection**: Models are injected into controllers
- **Multi-threading**: Separate threads for camera capture, processing, and UI
- **Observer Pattern**: Event-driven communication between components
- **Strategy Pattern**: Pluggable detection algorithms

## Performance Targets

### Basler acA640-300gm Specifications
- **Resolution**: 640x480 Mono8
- **Target FPS**: 280+ (theoretical max 376)
- **Capture Latency**: <10ms
- **Processing FPS**: 200+
- **UI Update Rate**: 30 FPS (throttled)

### System Performance Monitoring
The system includes built-in performance monitoring:
- Real-time FPS display (camera/processing/detection)
- Memory usage tracking with warnings
- Frame drop detection and reporting
- Hardware health diagnostics

## Configuration System

### Camera Configuration (basler_mvc/config/settings.py)
```python
CAMERA_CONFIG = {
    'target_model': 'acA640-300gm',
    'target_fps': 350.0,
    'default_exposure_time': 1000.0,  # microseconds
    'enable_jumbo_frames': True,
    'packet_size': 9000,
    'grab_strategy': 'LatestImageOnly'
}
```

### Detection Configuration
```python
DETECTION_CONFIG = {
    'default_method': 'circle',  # 'circle', 'contour', 'enhanced'
    'min_area': 100,
    'max_area': 5000,
    'enable_detection': True
}
```

## Detection Algorithms

The system supports multiple detection methods via modular architecture:

1. **Circle Detection**: HoughCircles for round objects
2. **Contour Detection**: Morphological operations for irregular shapes  
3. **Enhanced Detection**: Hybrid method combining multiple approaches
4. **Background Subtraction**: Motion-based detection
5. **Deep Learning**: YOLO integration (via ultralytics)

### Adding New Detection Methods
1. Inherit from `DetectionMethod` base class in `detection_base.py`
2. Implement `process_frame()` and `detect_objects()` methods
3. Register in `DetectionModel` class

## UI System (CustomTkinter)

### Cross-Platform Display Solution
The system uses CustomTkinter to solve high-DPI display issues:
- **Problem**: Standard tkinter appears blurry on high-DPI screens
- **Solution**: CustomTkinter provides automatic DPI scaling and crisp rendering
- **Theme Support**: Multiple themes in `styles/` directory

### Running Different UI Versions
```bash
# CustomTkinter version (recommended)
python run_ctk_version.py

# Version selector
cd basler_mvc && python main_selector.py
```

## Video Recording and Analysis

### High-Speed Recording
- **Format**: MP4/AVI with configurable codecs
- **Performance**: 280+ FPS recording capability  
- **Quality Validation**: Automatic FPS and frame integrity checking
- **Storage**: Organized in `recordings/` with metadata

### Video Analysis Tools
```bash
# Analyze recording quality
python recording_quality_analyzer.py

# Verify FPS accuracy
python video_fps_verifier.py
```

## Industrial Automation Features

### Vibration Motor Control
The system includes intelligent vibration motor control for automated feeding:
- **Adaptive Frequency**: Automatically adjusts based on counting progress
- **Communication**: Supports RS232/485 and TCP/IP protocols
- **Safety**: Automatic stop on completion or error conditions

### Batch Processing
- **Automated Counting**: Real-time object counting with duplicate elimination
- **Batch Management**: Multi-round processing with automatic record keeping
- **Progress Monitoring**: Real-time progress bars and completion statistics
- **Data Logging**: Comprehensive batch records in JSON format

## Dependencies and Requirements

### Core Dependencies (Required)
```bash
customtkinter>=1.5.0    # High-DPI UI framework
opencv-python>=4.10.0   # Image processing and camera interface
numpy>=1.24.4           # Numerical operations
pillow>=10.4.0          # Image handling
PyYAML>=6.0.1           # Configuration file management
```

### Hardware-Specific Dependencies
```bash
pypylon>=3.0.0          # Basler camera SDK (industrial cameras)
```

### Optional Dependencies
```bash
ultralytics>=8.3.0      # YOLO deep learning models
torch>=2.0.0            # PyTorch backend for AI
Flask>=3.0.0            # Web interface support
psutil>=6.0.0           # System monitoring
```

## Troubleshooting and Diagnostics

### System Health Checks
```bash
# Run comprehensive system diagnostics
python basler_mvc/utils/system_diagnostics.py

# Memory monitoring (runs automatically in background)
# Check logs in basler_mvc/logs/basler_mvc.log
```

### Common Issues and Solutions

#### Camera Connection Issues
1. **Basler Camera Not Detected**:
   - Ensure pypylon is installed: `pip install pypylon`
   - Check camera power and network connection
   - Verify firewall settings for GigE cameras
   - Run camera diagnostic: System → Health Check

2. **Low FPS Performance**:
   - Enable Jumbo Frames (MTU 9000) on network adapter
   - Close unnecessary background applications
   - Check CPU and memory usage
   - Adjust detection parameters to reduce processing load

#### UI Display Issues
1. **Blurry Interface on High-DPI Screens**:
   - Use CustomTkinter version: `python run_ctk_version.py`
   - Install CustomTkinter: `pip install customtkinter`

2. **Interface Not Responding**:
   - Check logs in `basler_mvc/logs/`
   - Restart with debug mode: `python run_main_with_debug.py`

### Log Files and Debugging
- **Main Log**: `basler_mvc/logs/basler_mvc.log`
- **Batch Records**: `basler_mvc/batch_records/`
- **Recording Quality**: `recording_analysis_report.json`
- **Debug Mode**: Use `run_main_with_debug.py` for verbose logging

## Development Guidelines

### Code Organization
- **Controllers**: Business logic and model coordination
- **Models**: Data processing and hardware interfaces
- **Views**: UI components and user interaction
- **Utils**: Shared utilities and diagnostic tools
- **Config**: Centralized configuration management

### Threading Best Practices
- Camera capture runs in dedicated thread with observer notifications
- UI updates are throttled to prevent interface blocking
- Use provided synchronization primitives (locks, events)
- Memory cleanup is automatic but can be monitored

### Performance Optimization
- Frame processing uses optimized NumPy operations
- Detection algorithms are parallelizable where possible
- Memory usage is monitored with configurable limits
- UI updates are decoupled from processing pipeline

### Configuration Management
- All settings centralized in `basler_mvc/config/settings.py`
- Runtime parameter adjustment through UI
- Persistent storage of user preferences
- Validation of configuration parameters on startup

The system is designed for 24/7 industrial operation with comprehensive monitoring, automatic error recovery, and performance optimization for high-speed camera applications.