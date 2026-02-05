"""
TS Map Extractor for SPT-3G Transients

Extracts Test Statistic maps from g3 lightcurve files and converts to FITS format
for overlay on multi-wavelength images.

Based on TSmap_test.py by K. Phadke
"""

import os
import sys
import glob
import numpy as np
from astropy.io import fits
from astropy import wcs
from pathlib import Path

# Add SPT3G software path
SPT3G_PATH = '/cvmfs/spt.opensciencegrid.org/py3-v5/RHEL_9_x86_64/spt3g_software/build'
if os.path.exists(SPT3G_PATH):
    sys.path.insert(0, SPT3G_PATH)

try:
    from spt3g import core, maps, transients
    SPT3G_AVAILABLE = True
except ImportError:
    SPT3G_AVAILABLE = False
    print("Warning: spt3g not available. TS map extraction will be disabled.")


# Directory where lightcurve g3 files are stored
TRANSIENT_ALERTS_DIR = '/sptlocal/transfer/rsync/transient_alerts'


class TSMapExtractor:
    """Extracts Test Statistic maps from SPT3G lightcurve files."""
    
    def __init__(self, ts_maps_dir, transient_alerts_dir=None):
        """
        Initialize the TS map extractor.
        
        Args:
            ts_maps_dir: Directory to save extracted TS map FITS files
            transient_alerts_dir: Directory containing g3 lightcurve files (default: /sptlocal/transfer/rsync/transient_alerts)
        """
        self.ts_maps_dir = ts_maps_dir
        self.transient_alerts_dir = transient_alerts_dir or TRANSIENT_ALERTS_DIR
        
        os.makedirs(self.ts_maps_dir, exist_ok=True)
    
    def get_ts_map_dir(self, source_name):
        """Get the expected directory for a transient's TS map files."""
        source_dir = os.path.join(self.ts_maps_dir, source_name)
        os.makedirs(source_dir, exist_ok=True)
        return source_dir
    
    def get_ts_map_path(self, source_name):
        """Get the expected path for a TS map FITS file."""
        return os.path.join(self.get_ts_map_dir(source_name), f'{source_name}_TSmap.fits')
    
    def ts_map_exists(self, source_name):
        """Check if a TS map already exists for this source."""
        return os.path.exists(self.get_ts_map_path(source_name))
    
    def find_g3_file(self, field, g3_filename):
        """
        Find the g3 lightcurve file for a given field.
        
        Args:
            field: Field name (e.g., 'ra5hdec-52.5')
            g3_filename: The g3 filename from transients.txt (e.g., '283123887.g3')
        
        Returns:
            Path to g3 file if found, None otherwise
        """
        if not g3_filename:
            return None
        
        # The field in transients.txt might be like 'ra0hdec-52.25' but alerts are in 'ra5hdec-52.5'
        # Try both the exact field and variations
        possible_fields = [field]
        
        # Map old field names to new transient_alerts field names
        # ra0hdec-X.XX -> try ra5hdec-XX.X patterns
        if field.startswith('ra0hdec'):
            dec_part = field.split('dec')[1]
            try:
                dec_val = float(dec_part)
                # Round to nearest .5
                dec_rounded = round(dec_val * 2) / 2
                new_field = f"ra5hdec{dec_rounded:+.1f}".replace('+', '-').replace('--', '-')
                possible_fields.append(new_field)
                # Also try without the sign handling
                possible_fields.append(f"ra5hdec-{abs(dec_rounded):.1f}")
            except ValueError:
                pass
        
        for try_field in possible_fields:
            g3_path = os.path.join(self.transient_alerts_dir, try_field, g3_filename)
            if os.path.exists(g3_path):
                return g3_path
        
        # If exact match not found, try searching in all subdirectories
        pattern = os.path.join(self.transient_alerts_dir, '*', g3_filename)
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
        
        return None
    
    def extract_ts_map(self, source_name, ra_deg, dec_deg, field, g3_filename, test_statistic=None):
        """
        Extract TS map from a g3 lightcurve file and save as FITS.
        
        Args:
            source_name: Unique source identifier (e.g., '0446-53_284667264')
            ra_deg: Right ascension in degrees
            dec_deg: Declination in degrees
            field: Field name from transients.txt
            g3_filename: The g3 filename from transients.txt 'file' column
            test_statistic: Expected test statistic value (optional, for verification)
        
        Returns:
            Path to FITS file if successful, None otherwise
        """
        if not SPT3G_AVAILABLE:
            print(f"  SPT3G not available, cannot extract TS map for {source_name}")
            return None
        
        ts_map_path = self.get_ts_map_path(source_name)
        
        # Check if already exists
        if os.path.exists(ts_map_path):
            print(f"  TS map already exists: {ts_map_path}")
            return ts_map_path
        
        # Find the g3 file
        g3_path = self.find_g3_file(field, g3_filename)
        if not g3_path:
            print(f"  G3 file not found: {g3_filename} in field {field}")
            return None
        
        print(f"  Found G3 file: {g3_path}")
        
        # Convert coordinates to G3 units
        ra = ra_deg * core.G3Units.deg
        dec = dec_deg * core.G3Units.deg
        
        try:
            # Read the g3 file and find matching lightcurve frame
            frames = core.G3File(g3_path)
            lc_frame = None
            
            for frame in frames:
                if frame.type == core.G3FrameType.LightCurve:
                    try:
                        transients.CheckLightCurveFrame(frame)
                    except:
                        continue
                    
                    # Check if this frame matches our coordinates
                    if not np.allclose([frame["PixelRa"], frame["PixelDec"]], [ra, dec], rtol=1e-5):
                        continue
                    
                    # Check test statistic threshold
                    if frame["TestStatistic"] >= 45.0:
                        lc_frame = frame
                        print(f"  Found matching frame with TS={frame['TestStatistic']:.1f}")
                        break
            
            if lc_frame is None:
                print(f"  No matching lightcurve frame found in {g3_path}")
                return None
            
            # Extract the TS map
            ts_map = lc_frame["TestStatisticMap"]
            
            # Save as FITS using spt3g's built-in method
            temp_fits = os.path.join(self.ts_maps_dir, f'{source_name}_temp.fits')
            maps.fitsio.save_skymap_fits(temp_fits, ts_map, overwrite=True, compress=True)
            
            # Convert to standard FITS format (extension 1 data with proper WCS)
            with fits.open(temp_fits) as hdul:
                if len(hdul) > 1:
                    ts_image = hdul[1].data
                    ts_header = hdul[1].header
                else:
                    ts_image = hdul[0].data
                    ts_header = hdul[0].header
                
                # Create WCS and convert header
                w_ts = wcs.WCS(ts_header)
                w_ts_2d = w_ts.to_header()
                
                # Save the final FITS file
                fits.writeto(ts_map_path, ts_image, w_ts_2d, overwrite=True)
            
            # Clean up temp file
            if os.path.exists(temp_fits):
                os.remove(temp_fits)
            
            # Verify the output
            with fits.open(ts_map_path) as hdul:
                max_ts = np.nanmax(hdul[0].data)
                print(f"  Saved TS map: {ts_map_path} (max TS = {max_ts:.1f})")
            
            return ts_map_path
            
        except Exception as e:
            print(f"  Error extracting TS map: {e}")
            return None
    
    def extract_ts_map_from_row(self, row):
        """
        Extract TS map from a transient DataFrame row.
        
        Args:
            row: pandas Series with transient data including 'source', 'observation',
                 'ra[deg]', 'dec[deg]', 'field' columns
        
        Returns:
            Path to FITS file if successful, None otherwise
        """
        source_name = f"{row['source']}_{row['observation']}"
        ra_deg = float(row['ra[deg]'])
        dec_deg = float(row['dec[deg]'])
        field = row['field']
        
        # The g3 filename is the observation ID with .g3 extension
        # The 'file' column in transients.txt contains timestamps, not filenames
        obsid = row['observation']
        g3_filename = f"{obsid}.g3"
        
        test_statistic = row.get('test_statistic', None)
        
        return self.extract_ts_map(
            source_name=source_name,
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            field=field,
            g3_filename=g3_filename,
            test_statistic=test_statistic
        )


def extract_ts_map_for_transient(source_name, ra_deg, dec_deg, field, g3_filename, 
                                  ts_maps_dir, test_statistic=None):
    """
    Convenience function to extract a TS map for a single transient.
    
    Args:
        source_name: Unique source identifier
        ra_deg: Right ascension in degrees
        dec_deg: Declination in degrees
        field: Field name
        g3_filename: The g3 filename
        ts_maps_dir: Directory to save TS map
        test_statistic: Expected TS value (optional)
    
    Returns:
        Path to FITS file if successful, None otherwise
    """
    extractor = TSMapExtractor(ts_maps_dir)
    return extractor.extract_ts_map(source_name, ra_deg, dec_deg, field, g3_filename, test_statistic)


def generate_ts_map_cutout(ts_map_fits_path, source_name, ra, dec, output_dir):
    """
    Generate a PNG cutout image of the TS map.
    
    Args:
        ts_map_fits_path: Path to the TS map FITS file
        source_name: Source identifier for filename
        ra, dec: Coordinates in degrees (for marker)
        output_dir: Directory to save PNG
    
    Returns:
        Path to PNG if successful, None otherwise
    """
    import matplotlib.pyplot as plt
    from matplotlib import rcParams
    
    if not ts_map_fits_path or not os.path.exists(ts_map_fits_path):
        return None
    
    # Create per-transient subfolder
    source_dir = os.path.join(output_dir, source_name)
    os.makedirs(source_dir, exist_ok=True)
    png_path = os.path.join(source_dir, f"{source_name}_TSmap.png")
    
    if os.path.exists(png_path):
        return png_path
    
    try:
        # Use aplpy if available for consistent look with other images
        import aplpy
        
        rcParams.update({'xtick.direction': 'in', 'ytick.direction': 'in'})
        fig = plt.figure(figsize=(6, 6))
        
        f = aplpy.FITSFigure(ts_map_fits_path, figure=fig)
        f.set_theme('publication')
        f.tick_labels.set_font(size='large')
        f.axis_labels.set_xtext('Right Ascension (J2000)')
        f.axis_labels.set_ytext('Declination (J2000)')
        f.axis_labels.set_font(size='x-large')
        f.ticks.set_color(color='black')
        
        # Show TS map with colorscale
        ts_data = fits.getdata(ts_map_fits_path)
        vmin = np.nanmin(ts_data)
        vmax = np.nanmax(ts_data)
        f.show_colorscale(vmin=vmin, vmax=vmax, cmap='viridis', stretch='linear')
        
        # Add colorbar
        f.add_colorbar()
        f.colorbar.set_axis_label_text('Test Statistic')
        
        # Mark source position
        f.show_markers(ra, dec, marker='+', s=250, facecolor='red', edgecolor='white', linewidth=2)
        
        # Add contours at significance levels
        if vmax > 50:
            levels = np.array([vmax-11.83, vmax-6.18, vmax-2.3])
            levels = levels[levels > vmin]
            if len(levels) > 0:
                f.show_contour(ts_map_fits_path, colors='white', levels=levels, linewidths=1.5)
        
        # Add scalebar (30 arcsec = 30/3600 deg = 8.333e-3 deg)
        f.add_scalebar(3 * 2.77778e-3)  # 30 arcsec
        f.scalebar.set_label('30"')
        f.scalebar.set_color('white')
        f.scalebar.set_font(size='x-large')
        f.scalebar.set_linewidth(2)
        
        f.set_title(f'{source_name} TS Map (max={vmax:.1f})')
        
        fig.savefig(png_path, dpi=150, bbox_inches='tight')
        f.close()
        plt.close(fig)
        
        return png_path
        
    except ImportError:
        # Fallback without aplpy
        ts_data = fits.getdata(ts_map_fits_path)
        
        fig, ax = plt.subplots(figsize=(6, 6))
        vmax = np.nanmax(ts_data)
        im = ax.imshow(ts_data, origin='lower', cmap='viridis')
        plt.colorbar(im, ax=ax, label='Test Statistic')
        ax.set_title(f'{source_name} TS Map (max={vmax:.1f})')
        fig.savefig(png_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        return png_path
        
    except Exception as e:
        print(f"  Error generating TS map cutout: {e}")
        return None


if __name__ == "__main__":
    # Test the extractor
    import pandas as pd
    
    print("Testing TS Map Extractor")
    print("=" * 60)
    
    # Load transients
    transients_file = os.path.join(os.path.dirname(__file__), '..', 'transients.txt')
    if os.path.exists(transients_file):
        df = pd.read_csv(transients_file, sep='\t')
        
        # Test with a recent transient that has a file
        recent = df[df['file'].notna()].tail(5)
        
        ts_maps_dir = os.path.join(os.path.dirname(__file__), '..', 'ts_maps')
        extractor = TSMapExtractor(ts_maps_dir)
        
        for _, row in recent.iterrows():
            source_name = f"{row['source']}_{row['observation']}"
            print(f"\nProcessing: {source_name}")
            print(f"  Field: {row['field']}")
            print(f"  File: {row['file']}")
            result = extractor.extract_ts_map_from_row(row)
            if result:
                print(f"  Success: {result}")
            else:
                print(f"  Failed to extract TS map")
    else:
        print(f"Transients file not found: {transients_file}")
