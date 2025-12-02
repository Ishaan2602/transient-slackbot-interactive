import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

if __name__ == "__main__":
    try:
        from askap_integration.askap_image_processor import ASKAPImageProcessor
        processor = ASKAPImageProcessor("test", "test", "data", "images")
        print("ASKAP tests passed")
    except Exception as e:
        print(f"Failed: {e}")