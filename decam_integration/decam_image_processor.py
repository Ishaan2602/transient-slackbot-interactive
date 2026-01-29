import os
import glob
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
import aplpy
from astropy.io import fits
from astropy.utils.data import download_file
from pyvo.dal import sia
from numpy.core.defchararray import startswith

try:
    from dl import authClient as ac
    DECAM_AVAILABLE = True
except ImportError:
    DECAM_AVAILABLE = False
    print("Warning: Data Lab client not available")

class DECamImageProcessor:
    def __init__(self, username=None, password=None, data_dir=None, images_dir=None):
        self.username = username or os.getenv('DATALAB_USERNAME')
        self.password = password or os.getenv('DATALAB_PASSWORD')
        self.data_dir = data_dir or r'c:\Users\eluru\UIUC\obscos\decam_data'
        self.images_dir = images_dir or r'c:\Users\eluru\UIUC\obscos\decam_images'
        self.token = None
        self.svc = None
        
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
    
    def authenticate(self):
        if not DECAM_AVAILABLE:
            print("ERROR: Data Lab client not available")
            return False
        
        if not self.username or not self.password:
            print("ERROR: Data Lab credentials not provided")
            return False
        
        self.token = ac.login(self.username, self.password)
        self.svc = sia.SIAService('https://datalab.noirlab.edu/sia/coadd_all')
        print("Data Lab authentication successful")
        return True
    
    def download_deepest_image(self, ra, dec, band='g', fov=0.1):
        if not self.svc:
            print("ERROR: Not authenticated with Data Lab")
            return None, None
        
        print(f"Querying DECam data for band {band}...")
        
        imgTable = self.svc.search((ra, dec), (fov/np.cos(dec*np.pi/180), fov), verbosity=2).to_table()
        
        sel0 = startswith(imgTable['obs_bandpass'].astype(str), band)
        print(f"Found {len(imgTable[sel0])} images with bandpass={band}")
        
        sel = sel0 & ((imgTable['proctype'] == 'Stack') & (imgTable['prodtype'] == 'image'))
        Table = imgTable[sel]
        
        if len(Table) > 0:
            row = Table[np.argmax(Table['exptime'].data.data.astype('float'))]
            url = row['access_url']
            print(f"Downloading deepest {band} image...")
            image, hdr = fits.getdata(download_file(url, cache=True, show_progress=False, timeout=180), header=True)
            return image, hdr
        else:
            print(f"No {band} image available")
            return None, None
    
    def download_decam_images(self, source_name, ra, dec):
        source_dir = os.path.join(self.data_dir, source_name)
        os.makedirs(source_dir, exist_ok=True)
        
        bands = ['g', 'r', 'i']
        fits_files = {}
        
        for band in bands:
            fits_file = os.path.join(source_dir, f"{source_name}_{band}.fits")
            
            if os.path.exists(fits_file):
                print(f"DECam {band}-band data for {source_name} already exists")
                fits_files[band] = fits_file
            else:
                image, header = self.download_deepest_image(ra, dec, band=band, fov=0.1)
                if image is not None:
                    fits.writeto(fits_file, image, header)
                    print(f"Saved {band}-band image: {fits_file}")
                    fits_files[band] = fits_file
                else:
                    fits_files[band] = None
        
        return fits_files
    
    def generate_thumbnail(self, fits_files, source_name, ra, dec, ts_map_path=None):
        if not all(fits_files.values()):
            print("Not all bands available for color image")
            return None
        
        source_dir = os.path.join(self.data_dir, source_name)
        rgb_cube_path = os.path.join(source_dir, f'{source_name}_des_irg_cube.fits')
        rgb_image_path = os.path.join(source_dir, f'{source_name}_rgb_image.png')
        suffix = '_w_TS' if ts_map_path and os.path.exists(ts_map_path) else ''
        image_path = os.path.join(self.images_dir, f'{source_name}_DECam_thumb_2x2{suffix}.png')
        
        print(f"Generating DECam RGB thumbnail...")
        
        if not os.path.exists(rgb_cube_path):
            aplpy.make_rgb_cube([fits_files['i'], fits_files['r'], fits_files['g']], rgb_cube_path)
            aplpy.make_rgb_image(rgb_cube_path, rgb_image_path, embed_avm_tags=False, 
                                pmin_r=30.0, pmax_r=97.50, pmin_g=30.0, pmax_g=97.50, 
                                pmin_b=30.0, pmax_b=97.50)
        
        rgb_cube_2d = rgb_cube_path.replace('.fits', '_2d.fits')
        
        rcParams.update({'xtick.direction': 'in', 'ytick.direction': 'in'})
        fig = plt.figure(figsize=(6, 6))
        
        f = aplpy.FITSFigure(rgb_cube_2d, figure=fig)
        f.set_theme('publication')
        
        f.tick_labels.set_font(size='large')
        f.axis_labels.set_xtext('Right Ascension (J2000)')
        f.axis_labels.set_ytext('Declination (J2000)')
        f.tick_labels.set_yposition('left')
        f.axis_labels.set_yposition('left')
        f.axis_labels.set_font(size='x-large')
        
        f.ticks.set_color(color='white')
        f.ticks.set_length(length=20.0, minor_factor=0.5)
        
        # Don't recenter for cutouts - they're already centered
        # f.recenter(ra, dec, radius=0.01666666)
        f.show_markers(ra, dec, marker='+', s=250, facecolor='cyan')
        
        if ts_map_path and os.path.exists(ts_map_path):
            ts_data = fits.getdata(ts_map_path)
            maxTS = np.nanmax(ts_data)
            print(f"TS map found: maxTS = {maxTS:.2f}")
            f.show_contour(ts_map_path, colors='red', levels=np.array([maxTS-11.83, maxTS-6.18, maxTS-2.3]))
        
        f.show_rgb(rgb_image_path)
        
        f.add_scalebar(2.77778e-3)
        f.scalebar.set_label('10"')
        f.scalebar.set_color('white')
        f.scalebar.set_font(size='x-large')
        f.scalebar.set_linewidth(2)
        
        title_suffix = ' w TS map' if ts_map_path and os.path.exists(ts_map_path) else ''
        f.set_title(f'{source_name} DES RGB 2x2{title_suffix}')
        
        fig.canvas.draw()
        fig.savefig(image_path, dpi=150)
        f.close()
        
        print(f"Thumbnail saved: {image_path}")
        return image_path
    
    def process_transient(self, source_name, ra, dec):
        print(f"\nProcessing DECam for transient: {source_name}")
        print(f"Coordinates: RA={ra:.6f}°, Dec={dec:.6f}°")
        print("-" * 60)
        
        ts_maps_dir = os.path.join(os.path.dirname(self.data_dir), 'ts_maps')
        ts_map_path = os.path.join(ts_maps_dir, f'{source_name}_TSmap.fits')
        suffix = '_w_TS' if os.path.exists(ts_map_path) else ''
        image_path = os.path.join(self.images_dir, f'{source_name}_DECam_thumb_2x2{suffix}.png')
        if os.path.exists(image_path):
            print(f"Image already exists: {image_path}")
            return image_path
        
        if not self.token:
            if not self.authenticate():
                return None
        
        fits_files = self.download_decam_images(source_name, ra, dec)
        
        if not any(fits_files.values()):
            print("No DECam data found for this location")
            return None
        
        image_path = self.generate_thumbnail(fits_files, source_name, ra, dec, ts_map_path)
        
        if image_path:
            print(f"Successfully processed {source_name}!")
            print(f"Image: {image_path}")
        
        return image_path

def generate_decam_image(source_name, ra, dec):
    processor = DECamImageProcessor()
    return processor.process_transient(source_name, ra, dec)
