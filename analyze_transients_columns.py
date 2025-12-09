#!/usr/bin/env python3
"""
Analyze transients.txt to show which columns are typically populated or empty.
Displays the top X entries with all their values.
"""

import pandas as pd
import sys

def analyze_transients(file_path='transients.txt', num_entries=10):
    """
    Read transients.txt and show column population statistics plus top entries.
    
    Args:
        file_path: Path to transients.txt file
        num_entries: Number of top entries to display in detail
    """
    # Read the file
    print(f"Reading {file_path}...")
    df = pd.read_csv(file_path, sep='\t')
    
    print(f"\nTotal transients: {len(df)}")
    print(f"Total columns: {len(df.columns)}\n")
    
    # Column population analysis
    print("="*80)
    print("COLUMN POPULATION ANALYSIS")
    print("="*80)
    
    for col in df.columns:
        total = len(df)
        non_empty = df[col].notna().sum()
        empty = total - non_empty
        pct_filled = (non_empty / total) * 100
        
        status = "✓ ALWAYS FILLED" if pct_filled == 100 else \
                 "✗ ALWAYS EMPTY" if pct_filled == 0 else \
                 "~ SOMETIMES FILLED"
        
        print(f"{col:25s} │ {non_empty:5d}/{total:5d} filled ({pct_filled:6.2f}%) │ {status}")
    
    # Display top entries in detail
    print("\n" + "="*80)
    print(f"TOP {num_entries} ENTRIES - DETAILED VIEW")
    print("="*80)
    
    for i, (idx, row) in enumerate(df.head(num_entries).iterrows(), 1):
        print(f"\n{'─'*80}")
        print(f"ENTRY #{i}: {row['source']}_{row['observation']}")
        print(f"{'─'*80}")
        
        for col in df.columns:
            value = row[col]
            
            # Format the value display
            if pd.isna(value):
                display_value = "❌ EMPTY"
            elif isinstance(value, float):
                display_value = f"{value:.6f}"
            else:
                display_value = str(value)
            
            # Highlight empty values
            marker = "  " if not pd.isna(value) else "❌"
            print(f"  {marker} {col:25s} : {display_value}")
    
    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    
    always_filled = [col for col in df.columns if df[col].notna().all()]
    always_empty = [col for col in df.columns if df[col].isna().all()]
    sometimes_filled = [col for col in df.columns if col not in always_filled and col not in always_empty]
    
    print(f"\nALWAYS FILLED ({len(always_filled)} columns):")
    for col in always_filled:
        print(f"  ✓ {col}")
    
    print(f"\nALWAYS EMPTY ({len(always_empty)} columns):")
    for col in always_empty:
        print(f"  ✗ {col}")
    
    print(f"\nSOMETIMES FILLED ({len(sometimes_filled)} columns):")
    for col in sometimes_filled:
        filled_count = df[col].notna().sum()
        pct = (filled_count / len(df)) * 100
        print(f"  ~ {col:25s} : {filled_count:5d}/{len(df):5d} ({pct:5.1f}%)")

if __name__ == "__main__":
    # Allow command-line arguments
    num_entries = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    
    try:
        analyze_transients(num_entries=num_entries)
    except FileNotFoundError:
        print("Error: transients.txt not found in current directory")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
