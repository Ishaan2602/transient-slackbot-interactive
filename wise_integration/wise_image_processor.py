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

warnings.filterwarnings('ignore')

class WISEImageProcessor:
    def __init__(self, wise_data_dir="wise_data", wise_images_dir="wise_images"):
        self.wise_data_dir = wise_data_dir
        self.wise_images_dir = wise_images_dir
        
        os.makedirs(self.wise_data_dir, exist_ok=True)
        os.makedirs(self.wise_images_dir, exist_ok=True)
    
    def download_wise_cutout(self, source_name, ra, dec, size=1000):
        source_dir = os.path.join(self.wise_data_dir, source_name)
        fits_file = os.path.join(source_dir, f"{source_name}_unwise_w1.fits")
        
        if os.path.exists(fits_file):
            print(f"WISE data for {source_name} already exists")
            return fits_file
        
        existing_fits = glob.glob(os.path.join(source_dir, "*.fits"))
        if existing_fits:
            print(f"Found existing FITS files for {source_name}")
            return self._process_existing_fits(source_name, source_dir)
        
        print(f"Downloading WISE cutout for {source_name}...")
        
        unwise_url = f'https://unwise.me/cutout_fits?version=neo6&ra={ra}&dec={dec}&size={size}&bands=1'
        
        os.makedirs(source_dir, exist_ok=True)
        
        tar_file = os.path.join(self.wise_data_dir, f"{source_name}.tar.gz")
        
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
        
        import tarfile
        if os.path.exists(tar_file):
            with tarfile.open(tar_file, 'r:gz') as tar:
                tar.extractall(path=source_dir)
            print(f"Extracted files to {source_dir}")
        
        import time
        time.sleep(0.5)
        
        for gz_file in glob.glob(os.path.join(source_dir, "*.gz")):
            try:
                os.remove(gz_file)
            except:
                pass
        
        if os.path.exists(tar_file):
            try:
                os.remove(tar_file)
            except:
                pass
        
        return self._process_downloaded_fits(source_name, source_dir)
    
    def _process_existing_fits(self, source_name, source_dir):
        fits_files = glob.glob(os.path.join(source_dir, "*.fits"))
        final_fits = os.path.join(source_dir, f"{source_name}_unwise_w1.fits")
        
        if len(fits_files) == 1 and not os.path.exists(final_fits):
            os.rename(fits_files[0], final_fits)
        elif len(fits_files) > 1 and not os.path.exists(final_fits):
            self._create_mosaic(fits_files, final_fits)
        
        return final_fits if os.path.exists(final_fits) else fits_files[0] if fits_files else None
    
    def _process_downloaded_fits(self, source_name, source_dir):
        fits_files = glob.glob(os.path.join(source_dir, "*.fits"))
        final_fits = os.path.join(source_dir, f"{source_name}_unwise_w1.fits")
        
        print(f"Found {len(fits_files)} FITS files: {fits_files}")
        
        if len(fits_files) > 1:
            self._create_mosaic(fits_files, final_fits)
        elif len(fits_files) == 1:
            import shutil
            try:
                shutil.copy2(fits_files[0], final_fits)
                print(f"Copied {fits_files[0]} to {final_fits}")
            except:
                return fits_files[0]
        else:
            print("No FITS files found after extraction")
            return None
        
        return final_fits if os.path.exists(final_fits) else None
    
    def _create_mosaic(self, fits_files, output_file):
        hdul_list = []
        unwise_hdus = []
        
        for fname in fits_files:
            hdul = fits.open(fname)
            hdul_list.append(hdul)
            unwise_hdus.append(hdul[0])
        
        wcs_out, shape_out = find_optimal_celestial_wcs(unwise_hdus)
        array_unwise, footprint = reproject_and_coadd(
            unwise_hdus, wcs_out, shape_out=shape_out, 
            reproject_function=reproject_interp, match_background=True
        )
        
        unwise_mosaic_header = wcs_out.to_header()
        fits.writeto(output_file, array_unwise, unwise_mosaic_header, overwrite=True)
        
        for hdul in hdul_list:
            hdul.close()
        
        print(f"Created mosaic: {output_file}")
    
    def generate_wise_thumbnail(self, source_name, ra, dec, output_size="5x5"):
        if output_size == "2x2":
            radius = 0.01666666
            scalebar_size = 2.77778e-3
            scalebar_label = '10"'
        else:
            radius = 0.041666666
            scalebar_size = 3 * 2.77778e-3
            scalebar_label = '30"'
        
        thumbnail_path = os.path.join(self.wise_images_dir, f"{source_name}_WISE_thumb_{output_size}.png")
        if os.path.exists(thumbnail_path):
            print(f"WISE thumbnail for {source_name} already exists")
            return thumbnail_path
        
        fits_file = os.path.join(self.wise_data_dir, source_name, f"{source_name}_unwise_w1.fits")
        
        if not os.path.exists(fits_file):
            print(f"FITS file not found: {fits_file}")
            return None
        
        rcParams.update({'xtick.direction': 'in', 'ytick.direction': 'in'})
        
        fig = plt.figure(figsize=(6, 6))
        
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
        
        f.recenter(ra, dec, radius=radius)
        f.show_markers(ra, dec, marker='+', s=250, facecolor='cyan')
        f.show_grayscale(vmin=4.0, vmax=90000.0, stretch='log', smooth=None)
        
        f.add_scalebar(scalebar_size)
        f.scalebar.set_label(scalebar_label)
        f.scalebar.set_color('black')
        f.scalebar.set_font(size='x-large')
        f.scalebar.set_linewidth(2)
        
        f.set_title(f'{source_name} WISE grayscale {output_size}')
        
        fig.canvas.draw()
        fig.savefig(thumbnail_path, dpi=150, bbox_inches='tight')
        f.close()
        plt.close(fig)
        
        print(f"Generated WISE thumbnail: {thumbnail_path}")
        return thumbnail_path
    
    def process_transient_wise_image(self, source_name, ra, dec):
        print(f"Processing WISE image for {source_name}...")
        
        fits_file = self.download_wise_cutout(source_name, ra, dec)
        if not fits_file:
            print(f"Failed to download WISE data for {source_name}")
            return None
        
        thumbnail_path = self.generate_wise_thumbnail(source_name, ra, dec, "5x5")
        
        return thumbnail_path

def generate_wise_image_for_transient(source_name, ra, dec, wise_data_dir="wise_data", wise_images_dir="wise_images"):
    processor = WISEImageProcessor(wise_data_dir, wise_images_dir)
    return processor.process_transient_wise_image(source_name, ra, dec)