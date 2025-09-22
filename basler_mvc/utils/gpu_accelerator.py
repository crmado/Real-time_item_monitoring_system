#!/usr/bin/env python3
"""
GPU加速器 - 為OpenCV操作提供GPU加速支援
專為高速檢測算法優化，提供回退到CPU的安全機制
"""

import cv2
import numpy as np
import logging
from typing import Optional, Tuple, Any
from enum import Enum

class GPUSupport(Enum):
    """GPU支援狀態"""
    UNAVAILABLE = "unavailable"
    CUDA = "cuda"
    OPENCL = "opencl"
    CPU_FALLBACK = "cpu_fallback"

class GPUAccelerator:
    """GPU加速器 - 安全的GPU加速OpenCV操作"""
    
    def __init__(self, prefer_cuda: bool = True):
        """
        初始化GPU加速器
        
        Args:
            prefer_cuda: 是否優先使用CUDA（如果可用）
        """
        self.gpu_support = self._detect_gpu_support()
        self.prefer_cuda = prefer_cuda
        self.cuda_available = False
        self.opencl_available = False
        
        # 性能統計
        self.gpu_operations = 0
        self.cpu_fallbacks = 0
        
        self._initialize_gpu()
        
        logging.info(f"GPU加速器初始化完成 - 支援狀態: {self.gpu_support.value}")
    
    def _detect_gpu_support(self) -> GPUSupport:
        """檢測GPU支援情況"""
        try:
            # 檢查CUDA支援
            if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                return GPUSupport.CUDA
        except:
            pass
        
        try:
            # 檢查OpenCL支援
            if cv2.ocl.haveOpenCL():
                return GPUSupport.OPENCL
        except:
            pass
        
        return GPUSupport.UNAVAILABLE
    
    def _initialize_gpu(self):
        """初始化GPU環境"""
        if self.gpu_support == GPUSupport.CUDA:
            try:
                # 設置CUDA設備
                cv2.cuda.setDevice(0)
                self.cuda_available = True
                logging.info(f"✅ CUDA加速已啟用 - 設備數量: {cv2.cuda.getCudaEnabledDeviceCount()}")
            except Exception as e:
                logging.warning(f"CUDA初始化失敗: {str(e)}")
                self.gpu_support = GPUSupport.CPU_FALLBACK
        
        elif self.gpu_support == GPUSupport.OPENCL:
            try:
                # 啟用OpenCL
                cv2.ocl.setUseOpenCL(True)
                self.opencl_available = True
                logging.info("✅ OpenCL加速已啟用")
            except Exception as e:
                logging.warning(f"OpenCL初始化失敗: {str(e)}")
                self.gpu_support = GPUSupport.CPU_FALLBACK
    
    def gaussian_blur(self, image: np.ndarray, kernel_size: Tuple[int, int], sigma: float = 0) -> np.ndarray:
        """
        GPU加速高斯模糊
        
        Args:
            image: 輸入圖像
            kernel_size: 核大小
            sigma: 標準差
            
        Returns:
            模糊後的圖像
        """
        try:
            if self.cuda_available and len(image.shape) == 2:  # CUDA支援灰度圖像
                gpu_img = cv2.cuda_GpuMat()
                gpu_img.upload(image)
                
                gpu_result = cv2.cuda.bilateralFilter(gpu_img, -1, sigma or 50, sigma or 50)
                
                result = gpu_result.download()
                self.gpu_operations += 1
                return result
                
            elif self.opencl_available:
                # OpenCL UMat操作
                umat_img = cv2.UMat(image)
                result = cv2.GaussianBlur(umat_img, kernel_size, sigma)
                self.gpu_operations += 1
                return cv2.UMat.get(result)
                
        except Exception as e:
            logging.debug(f"GPU高斯模糊失敗，回退到CPU: {str(e)}")
        
        # CPU回退
        self.cpu_fallbacks += 1
        return cv2.GaussianBlur(image, kernel_size, sigma)
    
    def canny_edge_detection(self, image: np.ndarray, low_threshold: float, high_threshold: float) -> np.ndarray:
        """
        GPU加速Canny邊緣檢測
        
        Args:
            image: 輸入圖像
            low_threshold: 低閾值
            high_threshold: 高閾值
            
        Returns:
            邊緣圖像
        """
        try:
            if self.cuda_available:
                gpu_img = cv2.cuda_GpuMat()
                gpu_img.upload(image)
                
                # CUDA Canny
                gpu_edges = cv2.cuda.Canny(gpu_img, low_threshold, high_threshold)
                
                result = gpu_edges.download()
                self.gpu_operations += 1
                return result
                
            elif self.opencl_available:
                # OpenCL UMat操作
                umat_img = cv2.UMat(image)
                result = cv2.Canny(umat_img, low_threshold, high_threshold)
                self.gpu_operations += 1
                return cv2.UMat.get(result)
                
        except Exception as e:
            logging.debug(f"GPU Canny檢測失敗，回退到CPU: {str(e)}")
        
        # CPU回退
        self.cpu_fallbacks += 1
        return cv2.Canny(image, low_threshold, high_threshold)
    
    def morphology_operations(self, image: np.ndarray, operation: int, kernel: np.ndarray, iterations: int = 1) -> np.ndarray:
        """
        GPU加速形態學操作
        
        Args:
            image: 輸入圖像
            operation: 形態學操作類型
            kernel: 結構元素
            iterations: 迭代次數
            
        Returns:
            處理後的圖像
        """
        try:
            if self.cuda_available:
                gpu_img = cv2.cuda_GpuMat()
                gpu_img.upload(image)
                
                # 創建GPU核
                gpu_kernel = cv2.cuda.createMorphologyFilter(
                    cv2.CV_8UC1, operation, kernel
                )
                
                gpu_result = gpu_kernel.apply(gpu_img)
                
                result = gpu_result.download()
                self.gpu_operations += 1
                return result
                
            elif self.opencl_available:
                # OpenCL UMat操作
                umat_img = cv2.UMat(image)
                result = cv2.morphologyEx(umat_img, operation, kernel, iterations=iterations)
                self.gpu_operations += 1
                return cv2.UMat.get(result)
                
        except Exception as e:
            logging.debug(f"GPU形態學操作失敗，回退到CPU: {str(e)}")
        
        # CPU回退
        self.cpu_fallbacks += 1
        return cv2.morphologyEx(image, operation, kernel, iterations=iterations)
    
    def median_blur(self, image: np.ndarray, kernel_size: int) -> np.ndarray:
        """
        GPU加速中值濾波
        
        Args:
            image: 輸入圖像
            kernel_size: 核大小
            
        Returns:
            濾波後的圖像
        """
        try:
            if self.opencl_available:
                # OpenCL UMat操作
                umat_img = cv2.UMat(image)
                result = cv2.medianBlur(umat_img, kernel_size)
                self.gpu_operations += 1
                return cv2.UMat.get(result)
                
        except Exception as e:
            logging.debug(f"GPU中值濾波失敗，回退到CPU: {str(e)}")
        
        # CPU回退（CUDA不支援中值濾波）
        self.cpu_fallbacks += 1
        return cv2.medianBlur(image, kernel_size)
    
    def background_subtraction_mog2(self, image: np.ndarray, bg_subtractor) -> np.ndarray:
        """
        GPU加速背景減除（如果支援）
        
        Args:
            image: 輸入圖像
            bg_subtractor: 背景減除器
            
        Returns:
            前景遮罩
        """
        try:
            if self.cuda_available:
                # 檢查是否有CUDA版本的背景減除器
                gpu_img = cv2.cuda_GpuMat()
                gpu_img.upload(image)
                
                # 嘗試使用CUDA背景減除器（如果可用）
                if hasattr(cv2.cuda, 'createBackgroundSubtractorMOG2'):
                    # 注意：這需要較新版本的OpenCV
                    pass
                
        except Exception as e:
            logging.debug(f"GPU背景減除失敗，使用CPU版本: {str(e)}")
        
        # 使用CPU版本（最可靠）
        self.cpu_fallbacks += 1
        return bg_subtractor.apply(image)
    
    def resize_image(self, image: np.ndarray, size: Tuple[int, int], interpolation: int = cv2.INTER_LINEAR) -> np.ndarray:
        """
        GPU加速圖像縮放
        
        Args:
            image: 輸入圖像
            size: 目標大小 (width, height)
            interpolation: 插值方法
            
        Returns:
            縮放後的圖像
        """
        try:
            if self.cuda_available:
                gpu_img = cv2.cuda_GpuMat()
                gpu_img.upload(image)
                
                gpu_result = cv2.cuda.resize(gpu_img, size, interpolation=interpolation)
                
                result = gpu_result.download()
                self.gpu_operations += 1
                return result
                
            elif self.opencl_available:
                # OpenCL UMat操作
                umat_img = cv2.UMat(image)
                result = cv2.resize(umat_img, size, interpolation=interpolation)
                self.gpu_operations += 1
                return cv2.UMat.get(result)
                
        except Exception as e:
            logging.debug(f"GPU圖像縮放失敗，回退到CPU: {str(e)}")
        
        # CPU回退
        self.cpu_fallbacks += 1
        return cv2.resize(image, size, interpolation=interpolation)
    
    def get_performance_stats(self) -> dict:
        """獲取性能統計"""
        total_operations = self.gpu_operations + self.cpu_fallbacks
        gpu_usage_percent = (self.gpu_operations / total_operations * 100) if total_operations > 0 else 0
        
        return {
            'gpu_support': self.gpu_support.value,
            'cuda_available': self.cuda_available,
            'opencl_available': self.opencl_available,
            'gpu_operations': self.gpu_operations,
            'cpu_fallbacks': self.cpu_fallbacks,
            'total_operations': total_operations,
            'gpu_usage_percent': round(gpu_usage_percent, 2)
        }
    
    def reset_stats(self):
        """重置性能統計"""
        self.gpu_operations = 0
        self.cpu_fallbacks = 0
        logging.info("GPU加速器統計已重置")
    
    def is_gpu_available(self) -> bool:
        """檢查GPU是否可用"""
        return self.gpu_support in [GPUSupport.CUDA, GPUSupport.OPENCL]
    
    def get_gpu_info(self) -> dict:
        """獲取GPU信息"""
        info = {
            'support_status': self.gpu_support.value,
            'cuda_devices': 0,
            'opencl_available': False
        }
        
        try:
            if self.gpu_support == GPUSupport.CUDA:
                info['cuda_devices'] = cv2.cuda.getCudaEnabledDeviceCount()
                
                # 獲取設備信息
                if info['cuda_devices'] > 0:
                    device_info = cv2.cuda.DeviceInfo(0)
                    info['device_name'] = device_info.name()
                    info['compute_capability'] = f"{device_info.majorVersion()}.{device_info.minorVersion()}"
                    info['total_memory'] = device_info.totalMemory()
                    
            elif self.gpu_support == GPUSupport.OPENCL:
                info['opencl_available'] = cv2.ocl.haveOpenCL()
                
        except Exception as e:
            info['error'] = str(e)
        
        return info


# 全局GPU加速器實例
_global_gpu_accelerator: Optional[GPUAccelerator] = None


def get_global_gpu_accelerator() -> GPUAccelerator:
    """獲取全局GPU加速器實例"""
    global _global_gpu_accelerator
    if _global_gpu_accelerator is None:
        _global_gpu_accelerator = GPUAccelerator()
    return _global_gpu_accelerator


def is_gpu_acceleration_available() -> bool:
    """檢查GPU加速是否可用"""
    accelerator = get_global_gpu_accelerator()
    return accelerator.is_gpu_available()


def get_gpu_stats() -> dict:
    """獲取GPU性能統計"""
    accelerator = get_global_gpu_accelerator()
    return accelerator.get_performance_stats()