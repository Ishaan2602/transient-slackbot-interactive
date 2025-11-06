"""
Test script to verify ASKAP image generation setup
"""
import sys
import os

def test_imports():
    """Test if all required packages are available."""
    print("Testing imports...")
    
    try:
        import astropy
        print(f"astropy {astropy.__version__}")
    except ImportError:
        print("astropy - install with: pip install astropy")
        return False
    
    try:
        from astroquery.casda import Casda
        print("astroquery.casda")
    except ImportError:
        print("astroquery.casda - install with: pip install astroquery")
        return False
    
    try:
        import reproject
        print("reproject")
    except ImportError:
        print("reproject - install with: pip install reproject")
        return False
    
    try:
        import aplpy
        print("aplpy")
    except ImportError:
        print("aplpy - install with: pip install aplpy")
        return False
    
    try:
        import matplotlib
        print(f"matplotlib {matplotlib.__version__}")
    except ImportError:
        print("matplotlib - install with: pip install matplotlib")
        return False
    
    return True

def test_casda_connection():
    """Test CASDA authentication."""
    print("\nTesting CASDA connection...")
    
    try:
        from astroquery.casda import Casda
        casda = Casda()
        
        # Test credentials
        username = 'ishaang6@illinois.edu'
        password = 'obscos_transient'
        auth = (username, password)
        
        login_response = casda._request("GET", casda._login_url, auth=auth, 
                                      timeout=casda.TIMEOUT, cache=False)
        
        if login_response.status_code == 200:
            print("CASDA authentication successful")
            return True
        else:
            print(f"CASDA authentication failed: {login_response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ CASDA connection error: {e}")
        return False

def test_directories():
    """Test directory creation."""
    print("\nTesting directory setup...")
    
    base_dir = r'c:\Users\eluru\UIUC\obscos'
    askap_data_dir = os.path.join(base_dir, 'askap_data')
    askap_images_dir = os.path.join(base_dir, 'askap_images')
    
    try:
        os.makedirs(askap_data_dir, exist_ok=True)
        os.makedirs(askap_images_dir, exist_ok=True)
        print(f"✓ Created directories:")
        print(f"  - {askap_data_dir}")
        print(f"  - {askap_images_dir}")
        return True
    except Exception as e:
        print(f"✗ Directory creation failed: {e}")
        return False

if __name__ == "__main__":
    print("ASKAP Image Generation Setup Test")
    print("=" * 40)
    
    all_tests_passed = True
    
    # Test imports
    if not test_imports():
        all_tests_passed = False
    
    # Test directories
    if not test_directories():
        all_tests_passed = False
    
    # Test CASDA connection (only if imports work)
    if all_tests_passed:
        if not test_casda_connection():
            all_tests_passed = False
    
    print("\n" + "=" * 40)
    if all_tests_passed:
        print("✓ All tests passed! Ready to generate ASKAP images.")
    else:
        print("✗ Some tests failed. Please install missing dependencies.")
        print("\nTo install missing packages, run:")
        print("pip install astropy astroquery reproject aplpy matplotlib")