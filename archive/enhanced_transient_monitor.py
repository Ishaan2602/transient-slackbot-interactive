"""
Enhanced Transient Monitor with ASKAP Image Integration

This is the main monitoring script that:
1. Monitors transients.txt for new detections
2. Generates ASKAP images for new transients
3. Posts notifications with images to Slack
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from slack_bolt import App
from slack_sdk.errors import SlackApiError
import schedule
import time
import threading

# Import ASKAP integration
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'askap_integration'))
from askap_image_processor import ASKAPImageProcessor

# Configuration
SLACK_BOT_TOKEN = 'xoxb-451463007363-9618908142950-FkmLQF1HKzTDGAeebVvzU7Y7'
SLACK_SIGNING_SECRET = 'de2481e9523c65ac16ae1c5bad90a28d'
CHANNEL_ID = "C09KLUNLU68"

# ASKAP Configuration
CASDA_USERNAME = os.getenv('CASDA_USERNAME', 'ishaang6@illinois.edu')
CASDA_PASSWORD = os.getenv('CASDA_PASSWORD', 'obscos_transient')

# File paths
BASE_DIR = r'c:\Users\eluru\UIUC\obscos'
TRANSIENTS_TXT = os.path.join(BASE_DIR, 'transients.txt')
NEW_TRANSIENTS_CSV = os.path.join(BASE_DIR, 'new_transients.csv')
LAST_CHECK_FILE = os.path.join(BASE_DIR, 'last_check.txt')

# ASKAP data directories
ASKAP_DATA_DIR = os.path.join(BASE_DIR, 'askap_data')
ASKAP_IMAGES_DIR = os.path.join(BASE_DIR, 'askap_images')

# Initialize Slack app
app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET
)

# Initialize ASKAP processor
askap_processor = ASKAPImageProcessor(
    username=CASDA_USERNAME,
    password=CASDA_PASSWORD,
    data_dir=ASKAP_DATA_DIR,
    images_dir=ASKAP_IMAGES_DIR
)

def setup_directories():
    """Create necessary directories for ASKAP data and images."""
    os.makedirs(ASKAP_DATA_DIR, exist_ok=True)
    os.makedirs(ASKAP_IMAGES_DIR, exist_ok=True)

def authenticate_casda():
    """Authenticate with CASDA service."""
    if not CASDA_AVAILABLE:
        print("CASDA not available - cannot generate ASKAP images")
        return None
    
    try:
        casda = Casda()
        auth = (CASDA_USERNAME, CASDA_PASSWORD)
        login_response = casda._request("GET", casda._login_url, auth=auth, 
                                      timeout=casda.TIMEOUT, cache=False)
        
        if login_response.status_code == 200:
            casda.USERNAME = CASDA_USERNAME
            casda._auth = auth
            casda._authenticated = True
            print("Successfully authenticated with CASDA")
            return casda
        else:
            print(f"CASDA authentication failed: {login_response.status_code}")
            return None
    except Exception as e:
        print(f"Error authenticating with CASDA: {e}")
        return None

def generate_askap_image(source_name, ra_deg, dec_deg, casda=None):
    """
    Generate ASKAP image for a transient source.
    
    Args:
        source_name (str): Name of the transient source
        ra_deg (float): Right Ascension in degrees
        dec_deg (float): Declination in degrees
        casda: Authenticated CASDA object
    
    Returns:
        str: Path to generated image file, or None if failed
    """
    if not IMAGE_GENERATION_AVAILABLE or casda is None:
        print("Image generation not available")
        return None
    
    try:
        # Create source-specific directory
        source_dir = os.path.join(ASKAP_DATA_DIR, source_name)
        os.makedirs(source_dir, exist_ok=True)
        
        fits_file = os.path.join(source_dir, f'{source_name}_askap.fits')
        image_file = os.path.join(ASKAP_IMAGES_DIR, f'{source_name}_ASKAP_thumb_5x5.png')
        
        # Skip if image already exists
        if os.path.exists(image_file):
            print(f"ASKAP image already exists for {source_name}")
            return image_file
        
        # Query CASDA for ASKAP data
        print(f"Querying CASDA for {source_name} at RA={ra_deg:.6f}, Dec={dec_deg:.6f}")
        centre = ac.SkyCoord(ra_deg*u.degree, dec_deg*u.degree, frame='icrs')
        
        result = Casda.query_region(centre, radius=2.5*u.arcmin)
        public_data = Casda.filter_out_unreleased(result)
        
        # Filter for RACS survey data
        subset = public_data[
            (public_data['obs_collection'] == 'The Rapid ASKAP Continuum Survey') & 
            (np.char.startswith(public_data['filename'], 'RACS-DR1_')) & 
            (np.char.endswith(public_data['filename'], 'A.fits'))
        ]
        
        if len(subset) == 0:
            print(f"No ASKAP data found for {source_name}")
            return None
        
        # Download cutout
        url_list = casda.cutout(subset[:1], coordinates=centre, radius=2.5*u.arcmin)
        filelist = casda.download_files(url_list, savedir=source_dir)
        
        # Process FITS files
        fits_files = glob.glob(os.path.join(source_dir, '*.fits'))
        if not fits_files:
            print(f"No FITS files downloaded for {source_name}")
            return None
        
        # Open and process HDUs
        askap_hdus = [fits.open(fname)[0] for fname in fits_files]
        
        if len(askap_hdus) == 1:
            # Single file processing
            p_hdu = askap_hdus[0]
            image = p_hdu.data[0, 0, :, :]
            header = p_hdu.header
            w_header = wcs.WCS(header)
            w_new = w_header.dropaxis(-1).dropaxis(-1)
            header_new = w_new.to_header()
            fits.writeto(fits_file, image, header_new, overwrite=True)
            array_askap = image
        else:
            # Multiple files - create mosaic
            processed_files = []
            for i, p_hdu in enumerate(askap_hdus):
                temp_file = os.path.join(source_dir, f'{source_name}_{i}.fits')
                image = p_hdu.data[0, 0, :, :]
                header = p_hdu.header
                w_header = wcs.WCS(header)
                w_new = w_header.dropaxis(-1).dropaxis(-1)
                header_new = w_new.to_header()
                fits.writeto(temp_file, image, header_new, overwrite=True)
                processed_files.append(temp_file)
            
            # Create mosaic
            processed_hdus = [fits.open(fname)[0] for fname in processed_files]
            wcs_out, shape_out = find_optimal_celestial_wcs(processed_hdus)
            array_askap, footprint = reproject_and_coadd(
                processed_hdus, wcs_out, shape_out=shape_out, 
                reproject_function=reproject_interp, match_background=True
            )
            
            askap_mosaic_header = wcs_out.to_header()
            fits.writeto(fits_file, array_askap, askap_mosaic_header, overwrite=True)
        
        # Generate thumbnail image
        rcParams.update({'xtick.direction': 'in', 'ytick.direction': 'in'})
        fig = mpl.figure(figsize=(12, 12))
        
        f = aplpy.FITSFigure(fits_file, figure=fig, slices=[0, 0], dimensions=[0, 1])
        f.set_theme('publication')
        f.tick_labels.set_font(size='large')
        f.axis_labels.set_xtext('Right Ascension (J2000)')
        f.axis_labels.set_ytext('Declination (J2000)')
        f.tick_labels.set_yposition('left')
        f.axis_labels.set_yposition('left')
        f.axis_labels.set_font(size='x-large')
        f.ticks.set_color(color='black')
        f.ticks.set_length(length=20.0, minor_factor=0.5)
        f.recenter(ra_deg, dec_deg, radius=0.041666666)  # degree
        f.show_markers(ra_deg, dec_deg, marker='+', s=250, facecolor='cyan')
        f.show_grayscale(pmin=70.0, pmax=99.9, stretch='log', smooth=None)
        f.add_scalebar(3*2.77778e-3)        
        f.scalebar.set_label('30"')
        f.scalebar.set_color('black')
        f.scalebar.set_font(size='x-large')
        f.scalebar.set_linewidth(2)
        f.set_title(f'{source_name} ASKAP grayscale 5x5')
        fig.canvas.draw()
        fig.savefig(image_file, dpi=400)
        f.close()
        
        # Clean up temporary files
        for f in glob.glob(os.path.join(source_dir, 'cutout*')):
            os.remove(f)
        
        print(f"ASKAP thumbnail generated: {image_file}")
        return image_file
        
    except Exception as e:
        print(f"Error generating ASKAP image for {source_name}: {e}")
        return None

# ... [Rest of your existing transient monitoring functions] ...

if __name__ == "__main__":
    setup_directories()
    # Initialize CASDA connection
    casda = authenticate_casda()
    
    # Your existing scheduling and monitoring code here...