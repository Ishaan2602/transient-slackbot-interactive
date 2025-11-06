import pandas as pd
import os

def test_first_run_logic():
    """Test the improved first-run logic that skips historical transients."""
    
    TRANSIENTS_TXT = r'c:\Users\eluru\UIUC\obscos\transients.txt'
    NEW_TRANSIENTS_CSV = r'c:\Users\eluru\UIUC\obscos\new_transients.csv'
    
    print("=== TESTING IMPROVED FIRST-RUN LOGIC ===\n")
    
    # Load transients data
    print(f"Loading transients data from {TRANSIENTS_TXT}")
    data_transients = pd.read_csv(TRANSIENTS_TXT, sep='\t')
    data_transients['time'] = pd.to_datetime(data_transients['time'])
    
    print(f"Total transients in file: {len(data_transients)}")
    
    # Simulate first run logic
    recent_threshold = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=30)
    print(f"Recent threshold (last 30 days): {recent_threshold}")
    
    # Historical 'new' transients
    historical_new = data_transients[data_transients['status'] == 'new']
    print(f"Historical 'new' transients (will be marked as processed): {len(historical_new)}")
    
    # Recent NaN transients (what will actually be processed on first run)
    recent_nan_filter = (data_transients['status'].isna()) & (data_transients['time'] > recent_threshold)
    recent_nan_transients = data_transients[recent_nan_filter]
    print(f"Recent NaN transients (last 30 days, will be processed): {len(recent_nan_transients)}")
    
    if len(recent_nan_transients) > 0:
        print(f"\nRecent NaN transients to be processed:")
        for _, row in recent_nan_transients.head(10).iterrows():  # Show first 10
            print(f"  {row['source']}_{row['observation']}: {row['time']}, test_stat={row['test_statistic']:.1f}")
    
    # Show what would happen on subsequent runs
    print(f"\nOn subsequent runs:")
    print(f"- Historical 'new' transients: SKIPPED (already in processed file)")
    print(f"- Any new entries not in processed file: PROCESSED")
    print(f"- Both status='new' and status=NaN will be considered")
    
    # Clean up any existing processed file for clean testing
    if os.path.exists(NEW_TRANSIENTS_CSV):
        print(f"\nNote: Existing processed file found. Remove it to test first-run behavior.")
    else:
        print(f"\nNo processed file found - this simulates first run behavior.")

if __name__ == "__main__":
    test_first_run_logic()