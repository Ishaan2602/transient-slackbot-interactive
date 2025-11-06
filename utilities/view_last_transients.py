import pandas as pd

def print_last_transients(file_path, num_transients=5):
    """Print information about the last N transients from the txt file."""
    try:
        # Load the transients data (tab-separated)
        print(f"Loading transients data from {file_path}")
        data = pd.read_csv(file_path, sep='\t')
        
        # Get the last N transients
        last_transients = data.tail(num_transients)
        
        print(f"\n=== LAST {num_transients} TRANSIENTS ===\n")
        
        for index, row in last_transients.iterrows():
            print(f"Transient #{len(data) - num_transients + (index - last_transients.index[0]) + 1}")
            print(f"  Source: {row['source']}")
            print(f"  Observation ID: {row['observation']}")
            print(f"  Coordinates: RA={row['ra[deg]']:.5f}°, Dec={row['dec[deg]']:.5f}°")
            print(f"  Field: {row['field']}")
            print(f"  Detection Time: {row['time']}")
            print(f"  Test Statistic: {row['test_statistic']:.1f}")
            print(f"  Peak Flux: {row['peak_flux[mJy]']:.2f} mJy")
            print(f"  Status: {row['status']}")
            if not pd.isna(row['fwhm[days]']):
                print(f"  Duration (FWHM): {row['fwhm[days]']:.2f} days")
            print(f"  Modified: {row['modified']}")
            print("-" * 50)
        
        print(f"Total transients in file: {len(data)}")
        
    except Exception as e:
        print(f"Error reading transients data: {e}")

if __name__ == "__main__":
    # File path
    transients_file = r'c:\Users\eluru\UIUC\obscos\transients.txt'
    
    # Print last 5 transients
    print_last_transients(transients_file, 5)