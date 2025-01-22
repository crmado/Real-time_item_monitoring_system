# run.py
import traceback
import sys

try:
    from object_detection_system import main
    main()
except Exception as e:
    print(f"Error: {e}")
    print("\n===== 詳細錯誤資訊 =====")
    print(traceback.format_exc())
    input("按任意鍵關閉...")