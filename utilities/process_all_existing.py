import pandas as pd
import os

def process_all_existing_transients():
    import os
    base_dir = os.path.dirname(os.path.dirname(__file__))
    TRANSIENTS_TXT = os.path.join(base_dir, 'transients.txt')
    NEW_TRANSIENTS_CSV = os.path.join(base_dir, 'new_transients.csv')
    
    print("Processing all existing transients...")
    
    # Load transients data
    print(f"Loading transients data from {TRANSIENTS_TXT}")
    data_transients = pd.read_csv(TRANSIENTS_TXT, sep='\t')
    data_transients['time'] = pd.to_datetime(data_transients['time'])
    
    # Load processed transients
    if os.path.exists(NEW_TRANSIENTS_CSV):
        processed = pd.read_csv(NEW_TRANSIENTS_CSV)
        print(f"Currently processed: {len(processed)} transients")
    else:
        print("No processed file found - will create new one")
        processed = pd.DataFrame()
    
    # Find unprocessed transients
    if len(processed) > 0:
        # Create unique IDs for comparison
        data_transients['unique_id'] = data_transients['source'].astype(str) + '_' + data_transients['observation'].astype(str)
        processed['unique_id'] = processed['source'].astype(str) + '_' + processed['observation'].astype(str)
        
        # Find unprocessed ones
        unprocessed_mask = ~data_transients['unique_id'].isin(processed['unique_id'])
        unprocessed = data_transients[unprocessed_mask]
    else:
        unprocessed = data_transients.copy()
    
    print(f"Total transients in file: {len(data_transients)}")
    print(f"Unprocessed transients: {len(unprocessed)}")
    
    if len(unprocessed) > 0:
        print(f"\nProcessing all {len(unprocessed)} remaining transients...")
        
        # Add processing timestamp
        unprocessed_copy = unprocessed.copy()
        unprocessed_copy['processed_at'] = pd.Timestamp.now(tz='UTC').isoformat()
        
        # Select columns for saving
        columns_to_save = ['source', 'observation', 'ra[deg]', 'dec[deg]', 
                          'field', 'time', 'test_statistic', 'status', 'processed_at']
        unprocessed_subset = unprocessed_copy[columns_to_save]
        
        # Combine with existing processed transients
        if len(processed) > 0:
            combined_df = pd.concat([processed, unprocessed_subset], ignore_index=True)
        else:
            combined_df = unprocessed_subset
        
        # Save to CSV
        combined_df.to_csv(NEW_TRANSIENTS_CSV, index=False)
        print(f"Successfully processed {len(unprocessed)} transients")
        print(f"Total processed: {len(combined_df)}")
    else:
        print("All transients already processed")


if __name__ == "__main__":
    process_all_existing_transients()