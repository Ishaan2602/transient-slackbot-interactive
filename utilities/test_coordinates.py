import pandas as pd
import numpy as np

# Test the coordinate processing on your actual data
def test_coordinate_processing():
    # Load the data
    data_transients = pd.read_csv('transients.csv')
    
    print("Testing coordinate processing on first 10 rows:")
    print("=" * 80)
    
    for i, (index, row) in enumerate(data_transients.head(10).iterrows()):
        if i >= 10:  # Limit to first 10
            break
            
        # Process coordinates like in your mentor's code
        if not pd.isna(row['centroid_ra[deg]']) and not np.isnan(float(row['centroid_ra[deg]'])):
            ra = float(row['centroid_ra[deg]'])
            dec = float(row['centroid_dec[deg]'])
            coord_source = "centroid"
        else:
            ra = float(row['ra[deg]'])
            dec = float(row['dec[deg]'])
            coord_source = "initial"
        
        if ra < 0:
            ra = ra + 360.0
        
        # Generate name like in your mentor's code
        source_name = f"{row['source']}_{row['observation']}"
        
        print(f"Row {i+1}: {source_name}")
        print(f"  Coordinates ({coord_source}): RA={ra:.5f}°, Dec={dec:.5f}°")
        print(f"  Detection time: {row['time']}")
        print(f"  Test statistic: {row['test_statistic']}")
        print(f"  Status: {row['status']}")
        print()

if __name__ == "__main__":
    test_coordinate_processing()