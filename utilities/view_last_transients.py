import pandas as pd

def print_last_transients(file_path, num_transients=5):
    try:
        data = pd.read_csv(file_path, sep='\t')
        last_transients = data.tail(num_transients)
        print(f"Last {num_transients} transients:")
        
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
    import os
    base_dir = os.path.dirname(os.path.dirname(__file__))
    transients_file = os.path.join(base_dir, 'transients.txt')
    print_last_transients(transients_file, 5)