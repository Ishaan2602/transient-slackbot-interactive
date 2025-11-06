"""
Test script to generate an ASKAP image for a sample transient
"""
import os
import sys

# Add the askap_integration module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'askap_integration'))

from askap_image_processor import ASKAPImageProcessor

def test_image_generation():
    """Test generating an ASKAP image for a sample transient."""
    
    # Sample transient coordinates
    test_source = "TEST_TRANSIENT_001"
    test_ra = 150.0  # degrees
    test_dec = -30.0  # degrees
    
    print(f"Testing ASKAP image generation for:")
    print(f"Source: {test_source}")
    print(f"RA: {test_ra}°, Dec: {test_dec}°")
    print("-" * 50)
    
    # Initialize ASKAP processor
    base_dir = os.path.join(os.path.dirname(__file__), '..')
    processor = ASKAPImageProcessor(
        username='ishaang6@illinois.edu',
        password='obscos_transient',
        data_dir=os.path.join(base_dir, 'askap_data'),
        images_dir=os.path.join(base_dir, 'askap_images')
    )
    
    # Generate ASKAP image
    print("Processing transient with ASKAP image generation...")
    image_path = processor.process_transient(test_source, test_ra, test_dec)
    
    if image_path and os.path.exists(image_path):
        print(f"ASKAP image generated successfully!")
        print(f"Image saved to: {image_path}")
        print(f"File size: {os.path.getsize(image_path):,} bytes")
        return True
    else:
        print("Failed to generate ASKAP image")
        return False

if __name__ == "__main__":
    print("ASKAP Image Generation Test")
    print("=" * 50)
    
    success = test_image_generation()
    
    print("\n" + "=" * 50)
    if success:
        print("Test completed successfully!")
    else:
        print("Test failed. Check error messages above.")