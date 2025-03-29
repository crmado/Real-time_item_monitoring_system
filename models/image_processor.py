"""
影像處理模型
處理所有與影像處理相關的功能
"""
import logging

import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor


class ImageProcessor:
    """影像處理類別"""

    # ==================================================================
    # 第一部分：初始化
    # ==================================================================
    def __init__(self):
        """初始化影像處理器"""
        # 優化背景減除器參數，減少歷史幀數以提高效能
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=100,  # 減少歷史幀數以加快處理
            varThreshold=16,
            detectShadows=False  # 關閉陰影檢測以提高速度
        )

        # 簡化核心大小以加快處理速度
        self.gaussian_kernel = (3, 3)  # 減小高斯核尺寸
        self.dilate_kernel = np.ones((2, 2), np.uint8)  # 減小膨脹核尺寸
        self.close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))  # 使用更簡單的形狀

        # 調整閾值參數以更寬鬆地檢測物體
        self.canny_threshold1 = 30  # 降低邊緣檢測閾值
        self.canny_threshold2 = 90
        self.binary_threshold = 20  # 降低二值化閾值

        # 增加線程池大小以提高平行處理能力
        self.thread_pool = ThreadPoolExecutor(max_workers=8)

        # 調整物體檢測參數，放寬條件
        self.min_object_area = 5  # 減少最小面積以檢測更多物體
        self.max_object_area = 500  # 增加最大面積以檢測更大物體
        
        logging.info("初始化影像處理器完成，使用優化的高性能參數配置")

    # ==================================================================
    # 第二部分：影像處理
    # ==================================================================
    def process_frame(self, frame):
        """
        參照用戶提供的程式碼處理單幀影像
        
        Args:
            frame: 輸入的影像幀

        Returns:
            processed_frame: 處理後的影像幀
        """
        if frame is None or frame.size == 0:
            return None

        try:
            # 背景減除
            fg_mask = self.bg_subtractor.apply(frame)
            
            # 高斯模糊去噪 - 使用5x5的核心
            blurred = cv2.GaussianBlur(frame, (5, 5), 0)
            
            # Canny 邊緣檢測 - 使用參考程式碼的參數
            edges = cv2.Canny(blurred, 50, 110)
            
            # 使用前景遮罩過濾邊緣
            result = cv2.bitwise_and(edges, edges, mask=fg_mask)
            
            # 二值化處理 - 使用參考程式碼的參數
            _, thresh = cv2.threshold(result, 30, 255, cv2.THRESH_BINARY)
            
            # 膨脹操作填充空洞 - 使用3x3核心
            kernel = np.ones((3, 3), np.uint8)
            dilated = cv2.dilate(thresh, kernel, iterations=1)
            
            # 使用橢圓形核心進行閉合操作
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel)
            
            return closed
            
        except Exception as e:
            logging.error(f"處理幀時發生錯誤: {str(e)}")
            return None
            
    def detect_objects(self, processed, min_area=None, max_area=None):
        """
        參照用戶提供的程式碼檢測物件

        Args:
            processed: 處理過的影像
            min_area: 最小物件面積 (可選，優先使用類別屬性)
            max_area: 最大物件面積 (可選，優先使用類別屬性)

        Returns:
            valid_objects: 符合條件的物件列表
        """
        if processed is None or processed.size == 0:
            return []

        # 使用參考代碼的面積參數
        min_area = min_area if min_area is not None else 10
        max_area = max_area if max_area is not None else 150

        try:
            # 使用連通區域分析（參考代碼使用的連通度為4）
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                processed,
                connectivity=4
            )

            # 過濾物體
            valid_objects = []
            for i in range(1, num_labels):
                area = stats[i, cv2.CC_STAT_AREA]
                if min_area < area < max_area:
                    x = stats[i, cv2.CC_STAT_LEFT]
                    y = stats[i, cv2.CC_STAT_TOP]
                    w = stats[i, cv2.CC_STAT_WIDTH]
                    h = stats[i, cv2.CC_STAT_HEIGHT]
                    centroid = centroids[i]
                    valid_objects.append((x, y, w, h, centroid))
            
            return valid_objects
            
        except Exception as e:
            logging.error(f"物件檢測時發生錯誤：{str(e)}")
            return []

    def process_multiple_rois(self, frame, roi_lines, roi_height):
        """
        平行處理多個 ROI 區域

        Args:
            frame: 原始影像
            roi_lines: ROI 線列表
            roi_height: ROI 高度

        Returns:
            results: 各 ROI 的處理結果列表 [(roi_line, objects), ...]
        """
        if frame is None or not roi_lines:
            return []

        results = []
        futures = []

        # 提交所有 ROI 處理任務
        for line_y in roi_lines:
            roi = frame[line_y:line_y + roi_height, :]
            future = self.thread_pool.submit(self._process_single_roi, roi, line_y)
            futures.append(future)

        # 收集所有處理結果
        for future in futures:
            try:
                result = future.result(timeout=0.1)  # 設置超時避免阻塞
                if result:
                    results.append(result)
            except Exception as e:
                import logging
                logging.error(f"ROI 處理時發生錯誤：{str(e)}")

        return results

    def _process_single_roi(self, roi, line_y):
        """處理單個 ROI 的輔助函數"""
        processed = self.process_frame(roi)
        objects = self.detect_objects(processed)
        return (line_y, objects)

    def draw_detection_results(self, frame, objects, max_boxes=3):
        """
        在影像上繪製檢測結果 - 限制顯示框數量

        Args:
            frame: 原始影像
            objects: 檢測到的物件列表
            max_boxes: 最大顯示框數量，默認為3

        Returns:
            frame: 繪製結果後的影像
        """
        if frame is None or not objects:
            return frame

        # 創建結果影像的副本，避免修改原始資料
        result_frame = frame.copy()

        # 如果對象數量超過限制，只選擇最大的幾個框
        if len(objects) > max_boxes:
            # 根據物件面積排序（寬x高）
            sorted_objects = sorted(objects, key=lambda obj: obj[2] * obj[3], reverse=True)
            # 只取最大的幾個
            objects_to_draw = sorted_objects[:max_boxes]
        else:
            objects_to_draw = objects

        # 繪製檢測框
        for x, y, w, h, _ in objects_to_draw:
            cv2.rectangle(result_frame, (x, y), (x + w, y + h), (0, 255, 0), 1)
            
            # 添加物件索引標籤
            object_idx = objects_to_draw.index((x, y, w, h, _)) + 1
            cv2.putText(result_frame, f"#{object_idx}", 
                       (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        return result_frame

    def set_parameters(self, params):
        """
        設置處理參數

        Args:
            params: 參數字典

        Returns:
            bool: 是否成功設置
        """
        try:
            if 'min_object_area' in params:
                self.min_object_area = params['min_object_area']

            if 'max_object_area' in params:
                self.max_object_area = params['max_object_area']

            if 'canny_threshold1' in params:
                self.canny_threshold1 = params['canny_threshold1']

            if 'canny_threshold2' in params:
                self.canny_threshold2 = params['canny_threshold2']

            if 'binary_threshold' in params:
                self.binary_threshold = params['binary_threshold']

            # 更新背景減除器
            history = params.get('bg_history', 20000)
            threshold = params.get('bg_threshold', 16)
            shadows = params.get('detect_shadows', True)

            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=history,
                varThreshold=threshold,
                detectShadows=shadows
            )

            return True
        except Exception as e:
            import logging
            logging.error(f"設置影像處理參數時發生錯誤：{str(e)}")
            return False

    def analyze_photo(self, frame):
        """
        分析拍攝的照片，檢測圓形物體

        Args:
            frame: 輸入的圖像幀

        Returns:
            dict: 分析結果字典
        """
        try:
            if frame is None or frame.size == 0:
                return {"success": False, "message": "無效的圖像"}

            # 轉換為灰度圖
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 使用高斯模糊減少噪聲
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # 預留：這裡可以實現更複雜的分析邏輯
            # 例如使用霍夫變換檢測圓形
            circles = cv2.HoughCircles(
                blurred,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=50,
                param1=50,
                param2=30,
                minRadius=50,
                maxRadius=300
            )

            # 生成分析結果
            result = {
                "success": True,
                "original_image": frame,
                "processed_image": blurred,
                "analysis_result": {
                    "has_circles": circles is not None,
                    "circles_data": circles if circles is not None else [],
                    "quality_score": 9.81  # 假設的值，實際應該由分析計算得出
                },
                "waveform_data": self._generate_waveform_data(gray),  # 生成示例波形數據
            }

            return result

        except Exception as e:
            logging.error(f"分析照片時發生錯誤：{str(e)}")
            return {"success": False, "message": str(e)}

    def _generate_waveform_data(self, gray_image):
        """
        從灰度圖生成波形數據（示例方法）

        Args:
            gray_image: 灰度圖像

        Returns:
            list: 波形數據點
        """
        # 從圖像中間行獲取灰度值作為波形
        height, width = gray_image.shape
        middle_row = gray_image[height // 2, :]

        # 對數據進行下採樣以減少點數
        waveform = [int(middle_row[i]) for i in range(0, width, 5)]

        return waveform

    def draw_analysis_results(self, frame, analysis_result):
        """
        在圖像上繪製分析結果

        Args:
            frame: 原始圖像
            analysis_result: 分析結果

        Returns:
            frame: 繪製結果後的圖像
        """
        if not analysis_result or not analysis_result.get("success", False):
            return frame

        result_frame = frame.copy()

        # 如果檢測到圓形，繪製它們
        if analysis_result.get("analysis_result", {}).get("has_circles", False):
            circles = analysis_result["analysis_result"]["circles_data"]
            if circles is not None:
                circles = np.uint16(np.around(circles))
                for i in circles[0, :]:
                    # 繪製外圓
                    cv2.circle(result_frame, (i[0], i[1]), i[2], (0, 255, 0), 2)
                    # 繪製圓心
                    cv2.circle(result_frame, (i[0], i[1]), 2, (0, 0, 255), 3)

        # 添加質量評分
        quality_score = analysis_result.get("analysis_result", {}).get("quality_score", 0)
        cv2.putText(
            result_frame,
            f"Quality: {quality_score:.2f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        return result_frame