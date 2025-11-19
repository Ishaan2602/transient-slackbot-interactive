import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def test_askap_imports():
    try:
        from askap_integration.askap_image_processor import ASKAPImageProcessor
        print("ASKAP imports work")
        return True
    except ImportError as e:
        print(f"ASKAP import failed: {e}")
        return False

def test_askap_init():
    try:
        from askap_integration.askap_image_processor import ASKAPImageProcessor
        processor = ASKAPImageProcessor("test", "test", "data", "images")
        print("ASKAP processor initialization works")
        return True
    except Exception as e:
        print(f"ASKAP init failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing ASKAP setup...")
    if test_askap_imports() and test_askap_init():
        print("ASKAP setup tests passed")
    else:
        print("ASKAP setup tests failed")