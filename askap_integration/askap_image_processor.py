import os
import glob
import numpy as np
import astropy.coordinates as ac
import astropy.units as u
from astropy.io import fits
from astropy import wcs

try:
    from astroquery.casda import Casda
    CASDA_AVAILABLE = True
except ImportError:
    CASDA_AVAILABLE = False
    print("Warning: astroquery.casda not available. Install with: pip install astroquery")

try:
    from reproject import reproject_interp
    from reproject.mosaicking import find_optimal_celestial_wcs, reproject_and_coadd
    import matplotlib.pyplot as mpl
    import matplotlib
    from matplotlib import rcParams
    import aplpy
    IMAGE_GENERATION_AVAILABLE = True
except ImportError:
    IMAGE_GENERATION_AVAILABLE = False
    print("Warning: Image generation libraries not available.")

class ASKAPImageProcessor:
    def __init__(self, username=None, password=None, data_dir=None, images_dir=None):
        self.username = username or os.getenv('CASDA_USERNAME_PERSONAL')
        self.password = password or os.getenv('CASDA_PASSWORD_PERSONAL')
        self.data_dir = data_dir or r'c:\Users\eluru\UIUC\obscos\askap_data'
        self.images_dir = images_dir or r'c:\Users\eluru\UIUC\obscos\askap_images'
        self.casda = None
        
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
    
    def authenticate(self):
        if not CASDA_AVAILABLE:
            print("ERROR: astroquery.casda not available")
            return False
        
        if not self.username or not self.password:
            print("ERROR: CASDA credentials not provided")
            return False
        
        self.casda = Casda()
        auth = (self.username, self.password)
        
        login_response = self.casda._request(
            "GET", 
            self.casda._login_url, 
            auth=auth,
            timeout=self.casda.TIMEOUT, 
            cache=False
        )
        
        if login_response.status_code == 200:
            self.casda.USERNAME = self.username
            self.casda._auth = auth
            self.casda._authenticated = True
            print("CASDA authentication successful")
            return True
        else:
            print(f"CASDA authentication failed: HTTP {login_response.status_code}")
            return False
    
    def query_askap_data(self, ra_deg, dec_deg, radius_arcmin=2.5):
        if not self.casda or not self.casda._authenticated:
            print("ERROR: Not authenticated with CASDA")
            return None
        
        print(f"Querying CASDA at RA={ra_deg:.6f}°, Dec={dec_deg:.6f}°")
        
        centre = ac.SkyCoord(ra_deg*u.degree, dec_deg*u.degree, frame='icrs')
        result = Casda.query_region(centre, radius=radius_arcmin*u.arcmin)
        public_data = Casda.filter_out_unreleased(result)
        
        subset = public_data[
            (public_data['obs_collection'] == 'The Rapid ASKAP Continuum Survey') & 
            (np.char.startswith(public_data['filename'], 'RACS-DR1_')) & 
            (np.char.endswith(public_data['filename'], 'A.fits'))
        ]
        
        print(f"Found {len(subset)} ASKAP images")
        return subset if len(subset) > 0 else None
    
    def download_cutouts(self, query_result, ra_deg, dec_deg, source_name, radius_arcmin=2.5):
        if query_result is None or len(query_result) == 0:
            print("No data to download")
            return []
        
        source_dir = os.path.join(self.data_dir, source_name)
        os.makedirs(source_dir, exist_ok=True)
        
        centre = ac.SkyCoord(ra_deg*u.degree, dec_deg*u.degree, frame='icrs')
        
        print(f"Downloading cutouts for {source_name}...")
        
        url_list = self.casda.cutout(
            query_result[:1], 
            coordinates=centre, 
            radius=radius_arcmin*u.arcmin
        )
        
        filelist = self.casda.download_files(url_list, savedir=source_dir)
        
        fits_files = glob.glob(os.path.join(source_dir, '*.fits'))
        print(f"Downloaded {len(fits_files)} FITS files")
        
        return fits_files
    
    def process_fits_files(self, fits_files, source_name):
        if not fits_files:
            print("No FITS files to process")
            return None, None
        
        source_dir = os.path.join(self.data_dir, source_name)
        final_fits = os.path.join(source_dir, f'{source_name}_askap.fits')
        
        print(f"Processing {len(fits_files)} FITS files...")
        
        askap_hdus = [fits.open(fname)[0] for fname in fits_files]
        
        if len(askap_hdus) == 1:
            print("Processing single FITS file")
            p_hdu = askap_hdus[0]
            
            image = p_hdu.data[0, 0, :, :]
            header = p_hdu.header
            
            w_header = wcs.WCS(header)
            w_new = w_header.dropaxis(-1).dropaxis(-1)
            header_new = w_new.to_header()
            
            fits.writeto(final_fits, image, header_new, overwrite=True)
            array_askap = image
            
        else:
            print(f"Creating mosaic from {len(askap_hdus)} files")
            
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
            
            processed_hdus = [fits.open(fname)[0] for fname in processed_files]
            
            wcs_out, shape_out = find_optimal_celestial_wcs(processed_hdus)
            
            array_askap, footprint = reproject_and_coadd(
                processed_hdus, 
                wcs_out, 
                shape_out=shape_out, 
                reproject_function=reproject_interp,
                match_background=True
            )
            
            askap_mosaic_header = wcs_out.to_header()
            fits.writeto(final_fits, array_askap, askap_mosaic_header, overwrite=True)
            
            for temp_file in processed_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
        
        print(f"FITS processing complete: {final_fits}")
        return array_askap, final_fits
    
    def generate_thumbnail(self, fits_path, source_name, ra_deg, dec_deg):
        if not IMAGE_GENERATION_AVAILABLE:
            print("Image generation libraries not available")
            return None
        
        if not os.path.exists(fits_path):
            print(f"FITS file not found: {fits_path}")
            return None
        
        image_path = os.path.join(self.images_dir, f'{source_name}_ASKAP_thumb_5x5.png')
        
        print(f"Generating thumbnail image...")
        
        rcParams.update({'xtick.direction': 'in', 'ytick.direction': 'in'})
        
        fig = mpl.figure(figsize=(6, 6))
        
        f = aplpy.FITSFigure(fits_path, figure=fig, slices=[0, 0], dimensions=[0, 1])
        f.set_theme('publication')
        
        f.tick_labels.set_font(size='large')
        f.axis_labels.set_xtext('Right Ascension (J2000)')
        f.axis_labels.set_ytext('Declination (J2000)')
        f.tick_labels.set_yposition('left')
        f.axis_labels.set_yposition('left')
        f.axis_labels.set_font(size='x-large')
        
        f.ticks.set_color(color='black')
        f.ticks.set_length(length=20.0, minor_factor=0.5)
        
        f.recenter(ra_deg, dec_deg, radius=0.041666666)
        f.show_markers(ra_deg, dec_deg, marker='+', s=250, facecolor='cyan')
        f.show_grayscale(pmin=70.0, pmax=99.9, stretch='log', smooth=None)
        
        f.add_scalebar(3*2.77778e-3)
        f.scalebar.set_label('30"')
        f.scalebar.set_color('black')
        f.scalebar.set_font(size='x-large')
        f.scalebar.set_linewidth(2)
        
        f.set_title(f'{source_name} ASKAP grayscale 5x5')
        
        fig.canvas.draw()
        fig.savefig(image_path, dpi=150)
        f.close()
        
        print(f"Thumbnail saved: {image_path}")
        return image_path
    
    def cleanup_temp_files(self, source_name):
        source_dir = os.path.join(self.data_dir, source_name)
        temp_files = glob.glob(os.path.join(source_dir, 'cutout*'))
        
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except:
                pass
        
        if temp_files:
            print(f"Cleaned up {len(temp_files)} temporary files")
    
    def process_transient(self, source_name, ra_deg, dec_deg):
        print(f"\nProcessing transient: {source_name}")
        print(f"Coordinates: RA={ra_deg:.6f}°, Dec={dec_deg:.6f}°")
        print("-" * 60)
        
        image_path = os.path.join(self.images_dir, f'{source_name}_ASKAP_thumb_5x5.png')
        if os.path.exists(image_path):
            print(f"Image already exists: {image_path}")
            return image_path
        
        if not self.casda or not self.casda._authenticated:
            if not self.authenticate():
                return None
        
        query_result = self.query_askap_data(ra_deg, dec_deg)
        if query_result is None:
            print("No ASKAP data found for this location")
            return None
        
        fits_files = self.download_cutouts(query_result, ra_deg, dec_deg, source_name)
        if not fits_files:
            return None
        
        image_array, final_fits = self.process_fits_files(fits_files, source_name)
        if final_fits is None:
            return None
        
        image_path = self.generate_thumbnail(final_fits, source_name, ra_deg, dec_deg)
        
        self.cleanup_temp_files(source_name)
        
        if image_path:
            print(f"Successfully processed {source_name}!")
            print(f"Image: {image_path}")
        
        return image_path


def generate_askap_image(source_name, ra_deg, dec_deg, casda=None):
    processor = ASKAPImageProcessor()
    return processor.process_transient(source_name, ra_deg, dec_deg)

def authenticate_casda():
    processor = ASKAPImageProcessor()
    if processor.authenticate():
        return processor
    return None