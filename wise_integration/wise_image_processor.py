"""
WISE Image Processor for Transient Monitor
Downloads and processes unWISE images for transient sources
"""

import os
import glob
import wget
import requests
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
import aplpy
from astropy.io import fits
from astropy.wcs import WCS
from reproject import reproject_interp
from reproject.mosaicking import find_optimal_celestial_wcs, reproject_and_coadd
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

class WISEImageProcessor:
    def __init__(self, wise_data_dir="wise_data", wise_images_dir="wise_images"):
        """
        Initialize WISE image processor
        
        Args:
            wise_data_dir: Directory to store raw WISE data
            wise_images_dir: Directory to store processed WISE images
        """
        self.wise_data_dir = wise_data_dir
        self.wise_images_dir = wise_images_dir
        
        # Create directories if they don't exist
        os.makedirs(self.wise_data_dir, exist_ok=True)
        os.makedirs(self.wise_images_dir, exist_ok=True)
    
    def download_wise_cutout(self, source_name, ra, dec, size=1000):
        """
        Download WISE cutout from unwise.me
        
        Args:
            source_name: Name of the transient source
            ra: Right ascension in degrees
            dec: Declination in degrees
            size: Cutout size in pixels (default: 1000)
            
        Returns:
            str: Path to the final FITS file
        """
        source_dir = os.path.join(self.wise_data_dir, source_name)
        fits_file = os.path.join(source_dir, f"{source_name}_unwise_w1.fits")
        
        # Check if FITS file already exists
        if os.path.exists(fits_file):
            print(f"WISE data for {source_name} already exists")
            return fits_file
        
        # Check if any FITS files exist in the directory
        existing_fits = glob.glob(os.path.join(source_dir, "*.fits"))
        if existing_fits:
            print(f"Found existing FITS files for {source_name}")
            return self._process_existing_fits(source_name, source_dir)
        
        # Download new WISE cutout
        print(f"Downloading WISE cutout for {source_name}...")
        
        # Create unWISE URL for W1 band
        unwise_url = f'https://unwise.me/cutout_fits?version=neo6&ra={ra}&dec={dec}&size={size}&bands=1'
        
        # Create source directory
        os.makedirs(source_dir, exist_ok=True)
        
        try:
            # Download the tar.gz file
            tar_file = os.path.join(self.wise_data_dir, f"{source_name}.tar.gz")
            
            # Use requests instead of wget for better Windows compatibility
            import requests
            print(f"Downloading from: {unwise_url}")
            response = requests.get(unwise_url, timeout=60)
            
            if response.status_code == 200:
                with open(tar_file, 'wb') as f:
                    f.write(response.content)
                print(f"Downloaded {len(response.content)} bytes")
            else:
                print(f"Download failed with status code: {response.status_code}")
                return None
            
            # Extract the files using Python tarfile module (Windows compatible)
            import tarfile
            if os.path.exists(tar_file):
                with tarfile.open(tar_file, 'r:gz') as tar:
                    tar.extractall(path=source_dir)
                print(f"Extracted files to {source_dir}")
            
            # Clean up compressed files
            import time
            time.sleep(0.5)  # Brief pause to ensure file handles are released
            
            for gz_file in glob.glob(os.path.join(source_dir, "*.gz")):
                try:
                    os.remove(gz_file)
                except Exception as e:
                    print(f"Warning: Could not remove {gz_file}: {e}")
            
            if os.path.exists(tar_file):
                try:
                    os.remove(tar_file)
                except Exception as e:
                    print(f"Warning: Could not remove {tar_file}: {e}")
            
            return self._process_downloaded_fits(source_name, source_dir)
            
        except Exception as e:
            print(f"Error downloading WISE cutout: {e}")
            return None
    
    def _process_existing_fits(self, source_name, source_dir):
        """Process existing FITS files"""
        fits_files = glob.glob(os.path.join(source_dir, "*.fits"))
        final_fits = os.path.join(source_dir, f"{source_name}_unwise_w1.fits")
        
        if len(fits_files) == 1 and not os.path.exists(final_fits):
            # Rename single file
            os.rename(fits_files[0], final_fits)
        elif len(fits_files) > 1 and not os.path.exists(final_fits):
            # Create mosaic from multiple files
            self._create_mosaic(fits_files, final_fits)
        
        return final_fits if os.path.exists(final_fits) else fits_files[0] if fits_files else None
    
    def _process_downloaded_fits(self, source_name, source_dir):
        """Process newly downloaded FITS files"""
        fits_files = glob.glob(os.path.join(source_dir, "*.fits"))
        final_fits = os.path.join(source_dir, f"{source_name}_unwise_w1.fits")
        
        print(f"Found {len(fits_files)} FITS files: {fits_files}")
        
        if len(fits_files) > 1:
            # Create mosaic from multiple files
            self._create_mosaic(fits_files, final_fits)
        elif len(fits_files) == 1:
            # Single file - copy it instead of rename to avoid Windows locking issues
            import shutil
            try:
                shutil.copy2(fits_files[0], final_fits)
                print(f"Copied {fits_files[0]} to {final_fits}")
            except Exception as e:
                print(f"Error copying file: {e}")
                return fits_files[0]  # Return original file if copy fails
        else:
            print("No FITS files found after extraction")
            return None
        
        return final_fits if os.path.exists(final_fits) else None
    
    def _create_mosaic(self, fits_files, output_file):
        """Create mosaic from multiple FITS files"""
        try:
            # Open HDUs from the individual fits files
            hdul_list = []
            unwise_hdus = []
            
            for fname in fits_files:
                hdul = fits.open(fname)
                hdul_list.append(hdul)
                unwise_hdus.append(hdul[0])
            
            # Find optimal WCS and create mosaic
            wcs_out, shape_out = find_optimal_celestial_wcs(unwise_hdus)
            array_unwise, footprint = reproject_and_coadd(
                unwise_hdus, wcs_out, shape_out=shape_out, 
                reproject_function=reproject_interp, match_background=True
            )
            
            # Save mosaic
            unwise_mosaic_header = wcs_out.to_header()
            fits.writeto(output_file, array_unwise, unwise_mosaic_header, overwrite=True)
            
            # Clean up - properly close HDUL objects
            for hdul in hdul_list:
                hdul.close()
            
            print(f"Created mosaic: {output_file}")
            
        except Exception as e:
            print(f"Error creating mosaic: {e}")
            # Clean up any open files
            for hdul in hdul_list if 'hdul_list' in locals() else []:
                try:
                    hdul.close()
                except:
                    pass
            # Fallback to first file if mosaic fails
            if fits_files and os.path.exists(fits_files[0]):
                import shutil
                shutil.copy2(fits_files[0], output_file)
    
    def generate_wise_thumbnail(self, source_name, ra, dec, output_size="5x5"):
        """
        Generate WISE thumbnail image
        
        Args:
            source_name: Name of the transient source
            ra: Right ascension in degrees
            dec: Declination in degrees
            output_size: Size of the output image ("2x2" or "5x5")
            
        Returns:
            str: Path to the generated thumbnail image
        """
        # Set radius based on output size
        if output_size == "2x2":
            radius = 0.01666666  # 1 arcmin
            scalebar_size = 2.77778e-3  # 10"
            scalebar_label = '10"'
        else:  # 5x5
            radius = 0.041666666  # 2.5 arcmin
            scalebar_size = 3 * 2.77778e-3  # 30"
            scalebar_label = '30"'
        
        # Check if thumbnail already exists
        thumbnail_path = os.path.join(self.wise_images_dir, f"{source_name}_WISE_thumb_{output_size}.png")
        if os.path.exists(thumbnail_path):
            print(f"WISE thumbnail for {source_name} already exists")
            return thumbnail_path
        
        # Get FITS file path
        fits_file = os.path.join(self.wise_data_dir, source_name, f"{source_name}_unwise_w1.fits")
        
        if not os.path.exists(fits_file):
            print(f"FITS file not found: {fits_file}")
            return None
        
        try:
            # Set matplotlib parameters
            rcParams.update({'xtick.direction': 'in', 'ytick.direction': 'in'})
            
            # Create figure
            fig = plt.figure(figsize=(12, 12))
            
            # Create APLpy figure
            f = aplpy.FITSFigure(fits_file, figure=fig)
            f.set_theme('publication')
            f.tick_labels.set_font(size='large')
            f.axis_labels.set_xtext('Right Ascension (J2000)')
            f.axis_labels.set_ytext('Declination (J2000)')
            f.tick_labels.set_yposition('left')
            f.axis_labels.set_yposition('left')
            f.axis_labels.set_font(size='x-large')
            f.ticks.set_color(color='black')
            f.ticks.set_length(length=20.0, minor_factor=0.5)
            
            # Recenter on transient position
            f.recenter(ra, dec, radius=radius)
            
            # Show transient position marker
            f.show_markers(ra, dec, marker='+', s=250, facecolor='cyan')
            
            # Show grayscale image
            f.show_grayscale(vmin=4.0, vmax=90000.0, stretch='log', smooth=None)
            
            # Add scalebar
            f.add_scalebar(scalebar_size)
            f.scalebar.set_label(scalebar_label)
            f.scalebar.set_color('black')
            f.scalebar.set_font(size='x-large')
            f.scalebar.set_linewidth(2)
            
            # Set title
            f.set_title(f'{source_name} WISE grayscale {output_size}')
            
            # Save figure
            fig.canvas.draw()
            fig.savefig(thumbnail_path, dpi=400, bbox_inches='tight')
            f.close()
            plt.close(fig)
            
            print(f"Generated WISE thumbnail: {thumbnail_path}")
            return thumbnail_path
            
        except Exception as e:
            print(f"Error generating WISE thumbnail: {e}")
            return None
    
    def process_transient_wise_image(self, source_name, ra, dec):
        """
        Complete WISE image processing pipeline for a transient
        
        Args:
            source_name: Name of the transient source
            ra: Right ascension in degrees
            dec: Declination in degrees
            
        Returns:
            str: Path to the generated thumbnail image (None if failed)
        """
        print(f"Processing WISE image for {source_name}...")
        
        # Download WISE cutout
        fits_file = self.download_wise_cutout(source_name, ra, dec)
        if not fits_file:
            print(f"Failed to download WISE data for {source_name}")
            return None
        
        # Generate thumbnail (default 5x5 arcmin)
        thumbnail_path = self.generate_wise_thumbnail(source_name, ra, dec, "5x5")
        
        return thumbnail_path


def generate_wise_image_for_transient(source_name, ra, dec, wise_data_dir="wise_data", wise_images_dir="wise_images"):
    """
    Convenience function to generate WISE image for a transient
    
    Args:
        source_name: Name of the transient source
        ra: Right ascension in degrees
        dec: Declination in degrees
        wise_data_dir: Directory for WISE data storage
        wise_images_dir: Directory for WISE image output
        
    Returns:
        str: Path to generated image (None if failed)
    """
    processor = WISEImageProcessor(wise_data_dir, wise_images_dir)
    return processor.process_transient_wise_image(source_name, ra, dec)