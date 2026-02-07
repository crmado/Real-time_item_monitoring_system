cmake_minimum_required(VERSION 3.16)
project(BaslerVisionSystem VERSION 2.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# ============================================================================
# 依賴查找
# ============================================================================

# Qt6
find_package(Qt6 REQUIRED COMPONENTS
    Core
    Gui
    Widgets
    Multimedia
    MultimediaWidgets
    Concurrent
)

# OpenCV
find_package(OpenCV REQUIRED COMPONENTS
    core
    imgproc
    videoio
    highgui
    video
)

# Pylon SDK (Basler Camera)
# macOS: /Library/Frameworks/pylon.framework
# Linux: /opt/pylon
# Windows: C:/Program Files/Basler/pylon X/Development
if(APPLE)
    set(PYLON_ROOT "/Library/Frameworks")
    find_library(PYLON_LIBRARY pylon PATHS ${PYLON_ROOT})
    # macOS Pylon SDK 需要包含 Headers 和 GenICam 目錄
    set(PYLON_INCLUDE_DIRS
        "${PYLON_ROOT}/pylon.framework/Headers"
        "${PYLON_ROOT}/pylon.framework/Headers/GenICam"
    )
elseif(UNIX)
    set(PYLON_ROOT "/opt/pylon" CACHE PATH "Pylon SDK root directory")
    set(PYLON_INCLUDE_DIRS "${PYLON_ROOT}/include")
    find_library(PYLON_LIBRARY pylonbase PATHS "${PYLON_ROOT}/lib")
elseif(WIN32)
    set(PYLON_ROOT "C:/Program Files/Basler/pylon 7/Development" CACHE PATH "Pylon SDK root directory")
    set(PYLON_INCLUDE_DIRS "${PYLON_ROOT}/include")
    find_library(PYLON_LIBRARY PylonBase_v7_4 PATHS "${PYLON_ROOT}/lib/x64")
endif()

# ============================================================================
# 源文件 - Core 模組
# ============================================================================

set(CORE_SOURCES
    src/core/camera_controller.cpp
    src/core/video_player.cpp
    src/core/video_recorder.cpp
    src/core/source_manager.cpp
    src/core/detection_controller.cpp
    src/core/vibrator_controller.cpp
)

set(CORE_HEADERS
    include/core/camera_controller.h
    include/core/video_player.h
    include/core/video_recorder.h
    include/core/source_manager.h
    include/core/detection_controller.h
    include/core/vibrator_controller.h
)

# ============================================================================
# 源文件 - Config 模組
# ============================================================================

set(CONFIG_SOURCES
    src/config/settings.cpp
)

set(CONFIG_HEADERS
    include/config/settings.h
)

# ============================================================================
# 源文件 - UI 模組
# ============================================================================

set(UI_SOURCES
    src/ui/main_window.cpp
)

set(UI_HEADERS
    include/ui/main_window.h
)

# ============================================================================
# 源文件 - UI Widgets
# ============================================================================

set(WIDGET_SOURCES
    src/ui/widgets/video_display.cpp
    src/ui/widgets/camera_control.cpp
    src/ui/widgets/recording_control.cpp
    src/ui/widgets/packaging_control.cpp
    src/ui/widgets/debug_panel.cpp
    src/ui/widgets/part_selector.cpp
    src/ui/widgets/method_selector.cpp
    src/ui/widgets/system_monitor.cpp
    src/ui/widgets/method_panels/counting_method_panel.cpp
    src/ui/widgets/method_panels/defect_detection_method_panel.cpp
)

set(WIDGET_HEADERS
    include/ui/widgets/video_display.h
    include/ui/widgets/camera_control.h
    include/ui/widgets/recording_control.h
    include/ui/widgets/packaging_control.h
    include/ui/widgets/debug_panel.h
    include/ui/widgets/part_selector.h
    include/ui/widgets/method_selector.h
    include/ui/widgets/system_monitor.h
    include/ui/widgets/method_panels/counting_method_panel.h
    include/ui/widgets/method_panels/defect_detection_method_panel.h
)

# ============================================================================
# 執行檔
# ============================================================================

add_executable(${PROJECT_NAME}
    src/main.cpp
    ${CORE_SOURCES}
    ${CORE_HEADERS}
    ${CONFIG_SOURCES}
    ${CONFIG_HEADERS}
    ${UI_SOURCES}
    ${UI_HEADERS}
    ${WIDGET_SOURCES}
    ${WIDGET_HEADERS}
)

target_include_directories(${PROJECT_NAME} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${OpenCV_INCLUDE_DIRS}
    ${PYLON_INCLUDE_DIRS}
)

target_link_libraries(${PROJECT_NAME} PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    Qt6::Multimedia
    Qt6::MultimediaWidgets
    Qt6::Concurrent
    ${OpenCV_LIBS}
    ${PYLON_LIBRARY}
)

# ============================================================================
# 安裝
# ============================================================================

install(TARGETS ${PROJECT_NAME}
    BUNDLE DESTINATION .
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

# macOS Bundle 設定
if(APPLE)
    set_target_properties(${PROJECT_NAME} PROPERTIES
        MACOSX_BUNDLE TRUE
        MACOSX_BUNDLE_GUI_IDENTIFIER "com.industrial.basler-vision"
        MACOSX_BUNDLE_BUNDLE_VERSION "${PROJECT_VERSION}"
        MACOSX_BUNDLE_SHORT_VERSION_STRING "${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}"
        MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/resources/macos/Info.plist"
    )
endif()

# ============================================================================
# 編譯選項
# ============================================================================

if(MSVC)
    target_compile_options(${PROJECT_NAME} PRIVATE /W4)
else()
    target_compile_options(${PROJECT_NAME} PRIVATE -Wall -Wextra -Wpedantic)
endif()

# Debug/Release 設定
target_compile_definitions(${PROJECT_NAME} PRIVATE
    $<$<CONFIG:Debug>:DEBUG_MODE>
)

# ============================================================================
# 複製配置文件和資源
# ============================================================================

# 複製配置目錄
add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory
    "$<TARGET_FILE_DIR:${PROJECT_NAME}>/config"
)

# 複製 assets 資源目錄
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/assets")
    add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_CURRENT_SOURCE_DIR}/assets"
        "$<TARGET_FILE_DIR:${PROJECT_NAME}>/assets"
        COMMENT "Copying assets to build directory"
    )
endif()

# 複製 recordings 目錄結構
add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory
    "$<TARGET_FILE_DIR:${PROJECT_NAME}>/recordings"
)

# ============================================================================
# 可選：跳過 Pylon SDK（用於無相機的 CI 環境）
# ============================================================================

option(SKIP_PYLON "Skip Pylon SDK for CI builds" OFF)
if(SKIP_PYLON)
    message(STATUS "Pylon SDK is disabled (SKIP_PYLON=ON)")
    target_compile_definitions(${PROJECT_NAME} PRIVATE NO_PYLON_SDK)
endif()

# ============================================================================
# 輸出配置信息
# ============================================================================

message(STATUS "===========================================")
message(STATUS "Basler Vision System C++ Build Configuration")
message(STATUS "===========================================")
message(STATUS "Version: ${PROJECT_VERSION}")
message(STATUS "Qt6 Version: ${Qt6_VERSION}")
message(STATUS "OpenCV Version: ${OpenCV_VERSION}")
message(STATUS "Pylon Root: ${PYLON_ROOT}")
message(STATUS "Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "===========================================")
