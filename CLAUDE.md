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

**Basler Industrial Vision System (C++ 版本)** - 高性能工業視覺檢測系統，使用 Qt6 + OpenCV 開發，支持 Basler 工業相機實時檢測與視頻錄製（280+ FPS）。

### Key Architecture Components

```
basler_cpp/
├── CMakeLists.txt              # CMake 建構配置
├── include/                    # 頭文件
│   ├── config/settings.h       # 統一配置系統
│   ├── core/                   # 核心業務邏輯
│   │   ├── camera_controller.h # 相機控制器（狀態機）
│   │   ├── video_player.h      # 視頻播放器
│   │   ├── video_recorder.h    # 視頻錄製器
│   │   ├── source_manager.h    # 源管理器
│   │   └── detection_controller.h # 檢測控制器
│   └── ui/                     # UI 層
│       ├── main_window.h       # 主視窗
│       └── widgets/            # UI 組件
├── src/                        # 源文件實現
├── testData/                   # 測試視頻文件
└── config/                     # 配置文件 (JSON)
```

## Core Commands

### Building

```bash
# macOS (推薦)
cd basler_cpp
mkdir build && cd build
cmake .. -DCMAKE_PREFIX_PATH=/opt/homebrew/opt/qt@6
make -j$(sysctl -n hw.ncpu)

# 或使用 VS Code Task
# Cmd+Shift+B → "CMake: Build C++ Project"
```

### Running

```bash
# macOS
./basler_cpp/build/BaslerVisionSystem.app/Contents/MacOS/BaslerVisionSystem

# 或直接開啟 .app
open basler_cpp/build/BaslerVisionSystem.app
```

### Testing with Video Files

無需實體相機，可使用 `basler_cpp/testData/` 中的測試視頻進行開發測試。

### Clean Build

```bash
cd basler_cpp/build
cmake --build . --target clean
# 或 VS Code Task: "CMake: Clean Build"
```

### Reconfigure CMake

```bash
cd basler_cpp
cmake -B build -S .
# 或 VS Code Task: "CMake: Configure"
```

## Architecture Design

### 1. State Machine Camera Control

```
Disconnected ──→ Connecting ──→ Connected ──→ StartingGrab ──→ Grabbing
     ↑                              ↑               ↓              ↓
     └────── Disconnecting ←────────┴── StoppingGrab ←─────────────┘
```

All camera operations are **asynchronous** using `QtConcurrent::run()`.

### 2. Core Modules

| 模組                  | 職責                           |
| --------------------- | ------------------------------ |
| `CameraController`    | 相機連接、狀態機管理、影像擷取 |
| `VideoPlayer`         | 視頻文件播放、幀率控制         |
| `VideoRecorder`       | H.264 視頻錄製                 |
| `SourceManager`       | 抽象相機/視頻源切換            |
| `DetectionController` | 背景減除、虛擬光柵計數         |
| `VibratorController`  | 雙震動機速度控制               |

### 3. Configuration System

配置使用 JSON 格式（`config/default_settings.json`），支持：

- 檢測參數（DetectionConfig）
- 虛擬光柵（GateConfig）
- 包裝控制（PackagingConfig）
- 零件類型庫（PartTypeLibrary）

### 4. Detection Algorithm

**Virtual Gate Counting** - O(n) 複雜度的確定性計數法：

1. ROI 區域處理（減少計算量）
2. MOG2 背景減除
3. 虛擬光柵線觸發計數
4. 時空去重（防止重複計數）

## Dependencies

- **Qt 6.x** - UI 框架
- **OpenCV 4.x** - 圖像處理
- **Pylon SDK 7.x** - Basler 相機 SDK（可選，無相機時 SKIP_PYLON=ON）

### macOS Installation

```bash
brew install qt@6 opencv
# Pylon SDK: https://www.baslerweb.com/en/downloads/software-downloads/
```

### Linux Installation

```bash
sudo apt install qt6-base-dev qt6-multimedia-dev libopencv-dev
```

## CI/CD

使用 GitHub Actions 進行多平台自動打包：

- `.github/workflows/build-cpp-release.yml`
- 支持 Windows、macOS、Linux (x86_64 + ARM64)

觸發方式：

1. 推送 `cpp-v*.*.*` 標籤
2. 手動觸發（workflow_dispatch）
3. Push 到 `feature/cpp-rewrite` 分支

## Key Code Patterns

### Asynchronous Operations

```cpp
void CameraController::connectCamera(int index) {
    QtConcurrent::run([this, index]() {
        // 背景線程執行，不阻塞 UI
        // 完成後通過信號通知
    });
}
```

### State Machine Transitions

```cpp
bool CameraController::transitionTo(CameraState newState) {
    // 檢查合法狀態轉換
    // 原子操作保證線程安全
}
```

### Configuration Access

```cpp
#include "config/settings.h"

auto& settings = Settings::instance();
int minArea = settings.detection().minArea;  // ✅ 正確
// int minArea = 2;  // ❌ 禁止硬編碼
```

## Important Notes

- 所有 UI 更新必須在主線程執行（使用 Qt 信號槽機制）
- 相機操作使用狀態機，禁止直接調用內部方法
- 配置變更後需調用 `settings.save()` 持久化
- 測試視頻位於 `testData/` 目錄
