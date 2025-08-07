# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a real-time item monitoring and detection system designed primarily for industrial production lines. The system consists of two main applications:

1. **Main Application**: Full-featured monitoring system with comprehensive UI and multiple detection modes
2. **Basler MVC**: Streamlined high-performance system optimized specifically for Basler acA640-300gm industrial cameras

## Key Architecture

### Main Application (Root Directory)
- **Architecture**: Full MVC pattern with extensive UI components
- **Language**: Python with Traditional Chinese documentation and UI
- **Camera Support**: Multi-camera support including USB cameras, Basler industrial cameras, and Raspberry Pi libcamera
- **Detection Methods**: Multiple detection algorithms including traditional methods, shape detection, and deep learning
- **Modes**: Live monitoring, video recording, playback analysis, and photo capture modes

### Basler MVC Application (basler_mvc/)
- **Architecture**: Simplified MVC pattern focused on core functionality
- **Target**: Specifically optimized for Basler acA640-300gm camera (640x480 Mono8, 280+ FPS)
- **Performance Focus**: High-speed capture and real-time detection with minimal latency
- **Threading**: Multi-threaded architecture with observer pattern for event handling

## CustomTkinter Upgrade

The project now includes a **CustomTkinter** version to solve cross-platform display issues:
- **Problem**: Original tkinter interface appears blurry on high-DPI screens and different platforms
- **Solution**: CustomTkinter provides automatic DPI scaling and crisp text rendering
- **Installation**: `pip install customtkinter`

### Running CustomTkinter Version
```bash
# Default: CustomTkinter version (recommended)
cd basler_mvc
python main.py

# Version selector (choose between CustomTkinter and original tkinter)
python main_selector.py

# Quick launcher with dependency checking
python ../run_ctk_version.py
```

## Development Commands

### Environment Setup
```bash
# Create and activate conda environment
conda create -n RPi_4_camera python=3.10
conda activate RPi_4_camera

# Install dependencies
pip install -r requirements.txt

# Install Basler camera support (optional)
pip install pypylon
```

### Running the Applications
```bash
# Main application
python main.py

# Basler MVC application  
cd basler_mvc
python main.py

# Test MVC system
python test_mvc_system.py
```

### Building Executables
```bash
# Generate spec file and build
pyinstaller --clean object_detection_system.spec

# Run with error logging
.\dist\object_detection_system.exe 2> logs\error.log

# Linux format
pyinstaller --onefile main.py
```

### Testing Commands
Based on the codebase structure, testing appears to be done through:
- `test_mvc_system.py` - Tests the MVC system components
- `test_thread_fix.py` - Tests thread synchronization fixes
- Various demo files like `run_cross_platform_demo.py`

## Core System Architecture

### Main Application Structure
```
Real-time_item_monitoring_system/
├── main.py                          # Main entry point
├── models/                          # Data layer
│   ├── system_config.py            # System configuration
│   ├── image_processor.py          # Image processing core
│   ├── camera_manager.py           # Camera management
│   └── detection_methods/          # Modular detection algorithms
├── views/                          # UI layer  
│   ├── main_window.py              # Main window
│   └── components/                 # UI components
├── controllers/                    # Control logic layer
│   ├── system_controller.py        # Main system controller
│   └── detection_controller.py     # Detection logic controller
├── utils/                          # Utilities
│   ├── logger.py                   # Logging system
│   ├── config.py                   # Configuration management
│   └── language.py                 # Multi-language support
├── config/                         # Configuration files
├── languages/                      # i18n resources (zh_TW, en_US, zh_CN)
└── basler_mvc/                     # Streamlined Basler system
```

### Basler MVC Structure (High-Performance Subset)
```
basler_mvc/
├── main.py                         # Entry point
├── controllers/
│   └── main_controller.py          # Coordinates camera and detection models
├── models/
│   ├── basler_camera_model.py      # Basler camera interface
│   ├── detection_model.py          # Detection algorithms
│   └── detection_processor.py      # High-performance frame processing
├── views/
│   └── main_view.py                # Simplified UI
├── config/
│   └── settings.py                 # Centralized configuration
└── utils/
    └── system_diagnostics.py       # Diagnostic utilities
```

## Key Technical Details

### Camera Support
- **Basler Industrial Cameras**: Primary target acA640-300gm with pypylon
- **USB Cameras**: Standard OpenCV camera interface  
- **Raspberry Pi**: libcamera support for Pi cameras
- **Auto-detection**: System can detect and configure multiple camera types

### Detection Algorithms
The system supports modular detection methods:
- **Traditional Methods**: Background subtraction, threshold-based detection
- **Shape Detection**: Circle detection using HoughCircles
- **Deep Learning**: YOLO integration for object detection
- **Specialized**: Custom detection methods for specific applications

### Performance Optimization
- **Multi-threading**: Separate threads for capture, processing, and UI
- **Frame Buffering**: Configurable buffer sizes to prevent frame drops  
- **Memory Management**: Automatic cleanup and limited buffer sizes
- **GPU Acceleration**: Optional GPU optimization available

### Configuration System
- **YAML Configuration**: Persistent settings storage
- **Runtime Updates**: Dynamic parameter adjustment
- **Multi-language**: Full internationalization support
- **Theme Management**: Light/dark theme switching

## Important Development Notes

### Working with Basler Cameras
- The `basler_mvc` system is specifically optimized for acA640-300gm cameras
- Always check camera connection status before starting capture
- Use the provided diagnostic utilities for troubleshooting camera issues
- The system includes automatic camera reconnection on connection loss

### Threading and Synchronization  
- The system uses extensive threading for performance
- Always use the provided synchronization primitives (locks, events)
- The camera capture runs in dedicated threads with observer pattern notifications
- UI updates are throttled to prevent overwhelming the interface

### Error Handling and Recovery
- Both applications include comprehensive error handling
- Automatic recovery mechanisms for camera disconnections
- System health monitoring and diagnostic reporting
- Graceful degradation when hardware is unavailable

### Cross-Platform Considerations
- The system includes cross-platform UI management in `basler_mvc/styles/`
- Font and color management for different operating systems
- Platform-specific optimizations for performance

### Video Recording and Playback
- Support for real-time video recording during detection
- Video playback with synchronized detection analysis
- Multiple video formats supported through OpenCV
- Frame-accurate seeking and speed control

## Dependencies and Requirements

### Core Dependencies
- **OpenCV**: Image processing and camera interface (`opencv-python-headless==4.10.0.84`)
- **NumPy**: Numerical operations (`numpy==1.24.4`) 
- **Pillow**: Image handling (`pillow==10.4.0`)
- **PyYAML**: Configuration file handling (`PyYAML==6.0.1`)
- **Tkinter**: GUI framework (usually included with Python)

### Optional Dependencies
- **pypylon**: Basler camera support (for industrial cameras)
- **ultralytics**: YOLO model support (`ultralytics==8.3.67`)
- **torch/torchvision**: Deep learning backend
- **Flask**: Web interface support (`Flask==3.0.3`)

### Development Tools
- **pyinstaller**: Executable building (`pyinstaller==6.11.1`)
- **pytest**: Testing framework (implied by test files)

## System Modes and Workflows

### Main Application Modes
1. **Live Monitoring**: Real-time detection with camera feed
2. **Video Recording**: Capture video while detecting objects  
3. **Video Playback**: Analyze pre-recorded videos with detection
4. **Photo Analysis**: Single image analysis mode

### Typical Development Workflow
1. **Camera Setup**: Use detection utilities to verify camera connectivity
2. **Algorithm Selection**: Choose appropriate detection method based on use case
3. **Parameter Tuning**: Adjust detection parameters through the UI or configuration
4. **Performance Testing**: Monitor FPS and system performance
5. **Integration**: Integrate with external systems through API endpoints

The system is designed for industrial applications requiring high reliability and performance, with extensive monitoring and diagnostic capabilities built-in.