import pandas as pd
import os

# Test the new filtering logic
def test_new_transient_filtering():
    """Test script to show how the new filtering works."""
    
    TRANSIENTS_TXT = r'c:\Users\eluru\UIUC\obscos\transients.txt'
    NEW_TRANSIENTS_CSV = r'c:\Users\eluru\UIUC\obscos\new_transients.csv'
    
    print("=== TESTING NEW TRANSIENT FILTERING LOGIC ===\n")
    
    # Load transients data
    print(f"Loading transients data from {TRANSIENTS_TXT}")
    data_transients = pd.read_csv(TRANSIENTS_TXT, sep='\t')
    data_transients['time'] = pd.to_datetime(data_transients['time'])
    
    print(f"Total transients in file: {len(data_transients)}")
    
    # Check status distribution
    print(f"\nStatus distribution:")
    status_counts = data_transients['status'].value_counts(dropna=False)
    print(status_counts)
    
    # Show recent entries with their status
    print(f"\nLast 10 transients and their status:")
    recent = data_transients.tail(10)[['source', 'observation', 'time', 'status', 'test_statistic']]
    for _, row in recent.iterrows():
        status_str = 'NaN' if pd.isna(row['status']) else str(row['status'])
        print(f"  {row['source']}_{row['observation']}: status='{status_str}', time={row['time']}")
    
    # Check if processed file exists
    if os.path.exists(NEW_TRANSIENTS_CSV):
        try:
            processed = pd.read_csv(NEW_TRANSIENTS_CSV)
            print(f"\nPreviously processed transients: {len(processed)}")
        except Exception as e:
            print(f"\nError reading processed transients file: {e}")
            print("File exists but may be corrupted or empty")
    else:
        print(f"\nNo processed transients file found at {NEW_TRANSIENTS_CSV}")
        print("On first run, will only process transients with status='new'")
        
        # Count how many have status='new'
        new_status_count = len(data_transients[data_transients['status'] == 'new'])
        print(f"Transients with status='new': {new_status_count}")
        
        if new_status_count > 0:
            print("\nFirst 5 transients with status='new':")
            new_ones = data_transients[data_transients['status'] == 'new'].head(5)
            for _, row in new_ones.iterrows():
                print(f"  {row['source']}_{row['observation']}: {row['time']}")

if __name__ == "__main__":
    test_new_transient_filtering()