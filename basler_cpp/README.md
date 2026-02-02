# Basler Vision System - C++ 版本

從 Python (PyQt6) 版本完整移植的 C++ 實現。

## 架構改進（相比 Python 版本）

### 1. 狀態機驅動的相機控制

```
Disconnected ──→ Connecting ──→ Connected ──→ StartingGrab ──→ Grabbing
     ↑                              ↑               ↓              ↓
     └────── Disconnecting ←────────┴── StoppingGrab ←─────────────┘
```

### 2. 完全異步操作

| 操作 | Python 版本 | C++ 版本 |
|------|------------|---------|
| `connectCamera()` | 阻塞 UI | 異步，QtConcurrent |
| `disconnectCamera()` | 阻塞 UI 最多 2 秒 | 異步，信號通知 |
| `startGrabbing()` | 同步啟動線程 | 狀態機控制 |
| `stopGrabbing()` | `join(timeout=2)` 阻塞 | 原子操作，非阻塞 |

### 3. 核心優勢

- **無 GIL 限制**：真正的多線程並行
- **RAII 資源管理**：智能指針自動清理
- **編譯時類型檢查**：減少運行時錯誤
- **更高性能上限**：適合 280+ FPS 高速相機

## 專案結構

```
basler_cpp/
├── CMakeLists.txt                          # CMake 建構配置
├── README.md                               # 專案說明
│
├── include/                                # 頭文件
│   ├── config/
│   │   └── settings.h                      # ✅ 統一配置系統
│   │
│   ├── core/
│   │   ├── camera_controller.h             # ✅ 相機控制器（狀態機）
│   │   ├── video_player.h                  # ✅ 視頻播放器
│   │   ├── video_recorder.h                # ✅ 視頻錄製器
│   │   ├── source_manager.h                # ✅ 源管理器
│   │   ├── detection_controller.h          # ✅ 檢測控制器
│   │   └── vibrator_controller.h           # ✅ 震動機控制器
│   │
│   └── ui/
│       ├── main_window.h                   # ✅ 主視窗
│       └── widgets/
│           ├── video_display.h             # ✅ 視頻顯示組件
│           ├── camera_control.h            # ✅ 相機控制組件
│           ├── recording_control.h         # ✅ 錄影控制組件
│           ├── packaging_control.h         # ✅ 包裝控制組件
│           ├── debug_panel.h               # ✅ 調試面板
│           ├── part_selector.h             # ✅ 零件選擇器
│           ├── method_selector.h           # ✅ 方法選擇器
│           ├── system_monitor.h            # ✅ 系統監控
│           └── method_panels/
│               ├── counting_method_panel.h         # ✅ 計數方法面板
│               └── defect_detection_method_panel.h # ✅ 瑕疵檢測面板
│
├── src/                                    # 源文件
│   ├── main.cpp                            # ✅ 程式入口
│   ├── config/
│   │   └── settings.cpp                    # ✅ 配置實現
│   ├── core/
│   │   ├── camera_controller.cpp           # ✅ 相機控制器實現
│   │   ├── video_player.cpp                # ✅ 視頻播放器實現
│   │   ├── video_recorder.cpp              # ✅ 視頻錄製器實現
│   │   ├── source_manager.cpp              # ✅ 源管理器實現
│   │   └── detection_controller.cpp        # ✅ 檢測控制器實現
│   └── ui/
│       └── main_window.cpp                 # ✅ 主視窗實現
│
├── resources/                              # 資源文件
└── tests/                                  # 測試
```

## 模組對應關係

| Python 模組 | C++ 模組 | 狀態 |
|-------------|----------|------|
| `core/camera.py` | `core/camera_controller.h/cpp` | ✅ 完成 |
| `core/video_player.py` | `core/video_player.h/cpp` | ✅ 完成 |
| `core/video_recorder.py` | `core/video_recorder.h/cpp` | ✅ 完成 |
| `core/source_manager.py` | `core/source_manager.h/cpp` | ✅ 完成 |
| `core/detection.py` | `core/detection_controller.h/cpp` | ✅ 完成 |
| `core/vibrator_controller.py` | `core/vibrator_controller.h` | ✅ 頭文件 |
| `config/settings.py` | `config/settings.h/cpp` | ✅ 完成 |
| `ui/main_window_v2.py` | `ui/main_window.h/cpp` | ✅ 基礎框架 |
| `ui/widgets/*.py` | `ui/widgets/*.h` | ✅ 頭文件 |

## 建構與編譯

### 依賴

- **Qt 6.x** - UI 框架
- **OpenCV 4.x** - 圖像處理
- **Pylon SDK 7.x** - Basler 相機 SDK

### macOS

```bash
# 安裝依賴
brew install qt@6 opencv

# 下載並安裝 Pylon SDK
# https://www.baslerweb.com/en/downloads/software-downloads/

# 建構
cd basler_cpp
mkdir build && cd build
cmake .. -DCMAKE_PREFIX_PATH=/opt/homebrew/opt/qt@6
make -j$(sysctl -n hw.ncpu)
```

### Linux (Ubuntu)

```bash
# 安裝依賴
sudo apt install qt6-base-dev libopencv-dev

# 安裝 Pylon SDK
# https://www.baslerweb.com/en/downloads/software-downloads/

# 建構
cd basler_cpp
mkdir build && cd build
cmake ..
make -j$(nproc)
```

### Windows (Visual Studio)

```batch
# 使用 vcpkg 安裝依賴
vcpkg install qt6 opencv4

# 建構
cd basler_cpp
mkdir build && cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=[vcpkg]/scripts/buildsystems/vcpkg.cmake
cmake --build . --config Release
```

## 待實現功能

### 高優先級
- [ ] UI Widget 實現檔案（.cpp）
- [ ] 震動機控制器實現
- [ ] 完整的主視窗功能

### 中優先級
- [ ] 自動更新系統
- [ ] 單元測試

### 低優先級
- [ ] macOS 圖標和 Info.plist
- [ ] Windows 安裝程式
- [ ] 國際化支援

## 技術亮點

### 1. 狀態機設計（CameraController）
```cpp
enum class CameraState {
    Disconnected, Connecting, Connected,
    StartingGrab, Grabbing, StoppingGrab,
    Disconnecting, Error
};

bool transitionTo(CameraState newState) {
    // 嚴格檢查狀態轉換合法性
    // 原子操作保證線程安全
}
```

### 2. 異步操作（QtConcurrent）
```cpp
void CameraController::connectCamera(int index) {
    QtConcurrent::run([this, index]() {
        // 在背景線程執行，不阻塞 UI
        // 完成後通過信號通知
    });
}
```

### 3. 虛擬光柵計數（DetectionController）
```cpp
// O(n) 複雜度，確定性計數
void virtualGateCounting(const std::vector<DetectedObject>& objects) {
    for (const auto& obj : objects) {
        if (obj.cy >= m_gateLineY && !checkDuplicate(obj.cx, obj.cy)) {
            m_crossingCounter++;
            emit objectsCrossedGate(m_crossingCounter);
        }
    }
}
```

## 與 Python 版本的兼容性

- 配置文件格式（JSON）完全兼容
- 檢測參數相同（basler_mvc 驗證參數）
- 虛擬光柵算法邏輯相同
- UI 佈局和功能對應
