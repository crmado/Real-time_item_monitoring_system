#!/usr/bin/env python3
"""
配置系統測試腳本
驗證統一配置管理功能是否正常運作
"""

import sys
from pathlib import Path

# 添加項目路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    get_config,
    init_config,
    save_config,
    validate_config,
    AppConfig
)


def test_config_load():
    """測試配置載入"""
    print("=" * 60)
    print("🧪 測試 1: 配置載入")
    print("=" * 60)

    config = get_config()

    # 檢查配置實例
    assert config is not None, "配置載入失敗"
    assert isinstance(config, AppConfig), "配置類型錯誤"

    # 檢查各個配置節
    assert config.detection is not None, "檢測配置缺失"
    assert config.gate is not None, "光柵配置缺失"
    assert config.ui is not None, "UI 配置缺失"
    assert config.performance is not None, "性能配置缺失"
    assert config.debug is not None, "調試配置缺失"

    print("✅ 配置載入成功")
    print(f"   - 檢測參數: min_area={config.detection.min_area}, max_area={config.detection.max_area}")
    print(f"   - 光柵參數: trigger_radius={config.gate.gate_trigger_radius}")
    print(f"   - 性能參數: image_scale={config.performance.image_scale}")
    print()


def test_config_validation():
    """測試配置驗證"""
    print("=" * 60)
    print("🧪 測試 2: 配置驗證")
    print("=" * 60)

    config = get_config()

    # 驗證配置
    is_valid = validate_config(config)
    assert is_valid, "配置驗證失敗"

    print("✅ 配置驗證通過")
    print()


def test_parameter_update():
    """測試參數更新"""
    print("=" * 60)
    print("🧪 測試 3: 參數更新")
    print("=" * 60)

    config = get_config()

    # 記錄原始值
    original_min_area = config.detection.min_area
    original_radius = config.gate.gate_trigger_radius

    # 更新參數
    success = config.update_detection_params(min_area=10, max_area=2000)
    assert success, "檢測參數更新失敗"

    success = config.update_gate_params(gate_trigger_radius=30)
    assert success, "光柵參數更新失敗"

    # 驗證更新
    assert config.detection.min_area == 10, "min_area 更新失敗"
    assert config.detection.max_area == 2000, "max_area 更新失敗"
    assert config.gate.gate_trigger_radius == 30, "gate_trigger_radius 更新失敗"

    print("✅ 參數更新成功")
    print(f"   - min_area: {original_min_area} → {config.detection.min_area}")
    print(f"   - gate_trigger_radius: {original_radius} → {config.gate.gate_trigger_radius}")

    # 恢復原始值
    config.update_detection_params(min_area=original_min_area)
    config.update_gate_params(gate_trigger_radius=original_radius)
    print("   - 已恢復原始值")
    print()


def test_config_save_load():
    """測試配置保存和載入"""
    print("=" * 60)
    print("🧪 測試 4: 配置保存和載入")
    print("=" * 60)

    # 創建測試配置
    test_config_file = Path(__file__).parent / "test_detection_params.json"

    # 保存配置
    config = get_config()
    config.update_detection_params(min_area=15)
    success = config.save(test_config_file)
    assert success, "配置保存失敗"
    assert test_config_file.exists(), "配置檔案未生成"

    print(f"✅ 配置已保存到: {test_config_file}")

    # 載入配置
    loaded_config = AppConfig.load(test_config_file)
    assert loaded_config.detection.min_area == 15, "配置載入值不正確"

    print(f"✅ 配置已載入，min_area = {loaded_config.detection.min_area}")

    # 清理測試檔案
    test_config_file.unlink()
    print("   - 測試檔案已清理")
    print()


def test_config_to_dict():
    """測試配置轉換為字典"""
    print("=" * 60)
    print("🧪 測試 5: 配置轉換為字典")
    print("=" * 60)

    config = get_config()
    config_dict = config.to_dict()

    # 檢查字典結構
    assert 'detection' in config_dict, "字典缺少 detection 節"
    assert 'gate' in config_dict, "字典缺少 gate 節"
    assert 'ui' in config_dict, "字典缺少 ui 節"
    assert 'performance' in config_dict, "字典缺少 performance 節"
    assert 'debug' in config_dict, "字典缺少 debug 節"

    # 檢查參數
    assert config_dict['detection']['min_area'] == config.detection.min_area
    assert config_dict['gate']['gate_trigger_radius'] == config.gate.gate_trigger_radius

    print("✅ 配置轉字典成功")
    print(f"   - 字典包含 {len(config_dict)} 個配置節")
    print(f"   - detection 節包含 {len(config_dict['detection'])} 個參數")
    print()


def test_ui_config_values():
    """測試 UI 配置值"""
    print("=" * 60)
    print("🧪 測試 6: UI 配置值檢查")
    print("=" * 60)

    config = get_config()
    ui_cfg = config.ui

    # 檢查參數範圍
    assert len(ui_cfg.min_area_range) == 2, "min_area_range 格式錯誤"
    assert len(ui_cfg.max_area_range) == 2, "max_area_range 格式錯誤"

    # 檢查預設值在範圍內
    min_min, min_max = ui_cfg.min_area_range
    assert min_min <= ui_cfg.min_area_default <= min_max, "min_area_default 超出範圍"

    max_min, max_max = ui_cfg.max_area_range
    assert max_min <= ui_cfg.max_area_default <= max_max, "max_area_default 超出範圍"

    print("✅ UI 配置值檢查通過")
    print(f"   - min_area: 範圍 {ui_cfg.min_area_range}, 預設 {ui_cfg.min_area_default}")
    print(f"   - max_area: 範圍 {ui_cfg.max_area_range}, 預設 {ui_cfg.max_area_default}")
    print(f"   - 圖像縮放選項: {ui_cfg.image_scale_options}")
    print(f"   - 預設縮放: {ui_cfg.image_scale_default}")
    print()


def test_detection_integration():
    """測試與檢測控制器的整合"""
    print("=" * 60)
    print("🧪 測試 7: 與檢測控制器整合")
    print("=" * 60)

    try:
        from core.detection import DetectionController

        # 創建檢測控制器
        config = get_config()
        detector = DetectionController(config)

        # 驗證參數是否正確載入
        assert detector.min_area == config.detection.min_area, "min_area 未正確載入"
        assert detector.max_area == config.detection.max_area, "max_area 未正確載入"
        assert detector.bg_var_threshold == config.detection.bg_var_threshold, "bg_var_threshold 未正確載入"
        assert detector.gate_trigger_radius == config.gate.gate_trigger_radius, "gate_trigger_radius 未正確載入"

        print("✅ 檢測控制器整合成功")
        print(f"   - 控制器已載入配置參數")
        print(f"   - min_area = {detector.min_area}")
        print(f"   - gate_trigger_radius = {detector.gate_trigger_radius}")

    except ImportError as e:
        print(f"⚠️ 跳過檢測控制器測試（模組不可用）: {e}")

    print()


def main():
    """主測試函數"""
    print("\n")
    print("🚀 basler_pyqt6 配置系統測試")
    print("=" * 60)
    print()

    try:
        # 執行所有測試
        test_config_load()
        test_config_validation()
        test_parameter_update()
        test_config_save_load()
        test_config_to_dict()
        test_ui_config_values()
        test_detection_integration()

        print("=" * 60)
        print("🎉 所有測試通過！")
        print("=" * 60)
        return True

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ 測試失敗: {e}")
        print("=" * 60)
        return False

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ 測試出現錯誤: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
