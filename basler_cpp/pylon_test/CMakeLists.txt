cmake_minimum_required(VERSION 3.16)
project(PylonTest LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

# Pylon SDK
set(PYLON_ROOT "C:/Program Files/Basler/pylon 8/Development")
set(PYLON_INCLUDE_DIRS "${PYLON_ROOT}/include")

# 找到所有需要的 Pylon 庫
find_library(PYLON_BASE PylonBase_v9 PATHS "${PYLON_ROOT}/lib/x64")
find_library(PYLON_UTILITY PylonUtility_v9 PATHS "${PYLON_ROOT}/lib/x64")
find_library(PYLON_GCBASE GCBase_MD_VC141_v3_1_Basler_pylon PATHS "${PYLON_ROOT}/lib/x64")
find_library(PYLON_GENAPI GenApi_MD_VC141_v3_1_Basler_pylon PATHS "${PYLON_ROOT}/lib/x64")

message(STATUS "PYLON_BASE: ${PYLON_BASE}")
message(STATUS "PYLON_UTILITY: ${PYLON_UTILITY}")

add_executable(pylon_test main.cpp)

target_include_directories(pylon_test PRIVATE ${PYLON_INCLUDE_DIRS})
target_link_libraries(pylon_test PRIVATE 
    ${PYLON_BASE}
    ${PYLON_UTILITY}
    ${PYLON_GCBASE}
    ${PYLON_GENAPI}
)

# 複製 DLL 到輸出目錄
add_custom_command(TARGET pylon_test POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
    "C:/Program Files/Basler/pylon 8/Runtime/x64"
    $<TARGET_FILE_DIR:pylon_test>
)
