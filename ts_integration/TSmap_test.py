import aplpy
import numpy as np
import astropy
from astropy.io import fits
import sys; import os
from astropy.cosmology import Planck15
import astropy.coordinates as ac
from astropy.wcs import FITSFixedWarning
import warnings; warnings.simplefilter('ignore',category=FITSFixedWarning)
from astropy import units as u
import glob
import requests
import time
import json
import getpass
import matplotlib.pyplot as mpl
from matplotlib.pyplot import *
import argparse
import wget
from reproject import reproject_interp
from reproject.mosaicking import reproject_and_coadd
from reproject.mosaicking import find_optimal_celestial_wcs
from astroquery.mast import Observations
from astropy import wcs
from astropy.wcs import WCS
from astropy.time import Time
from astroquery.utils.tap.core import TapPlus
from astroquery.utils.tap.core import Tap
import casda
from astropy.io import votable
import pandas as pd
sys.path.append('/home/kphadke/spt3g/RHEL_7_x86_64')
from pathlib import Path
from spt3g import core,maps,transients
from spt3g.std_processing import obsid_to_g3time, time_to_obsid
from spt3g.core import G3Time

dir_main='/sptlocal/user/kphadke/transients/'
os.system('cp /sptlocal/transfer/rsync/transfer_database/transients.txt /sptlocal/user/kphadke/transients/pole_database/transients.txt')
#os.system('cp /sptlocal/analysis/transients/data/*TSmap.g3 /sptlocal/user/kphadke/transients/TS_maps/')
#os.system('python /sptlocal/user/kphadke/transients/scripts/convert_TS_g3_to_fits.py')

#os.system('\cp /sptlocal/analysis/transients/data/*flux*.fits /sptlocal/user/kphadke/transients/spt_flux_thumbs/')
#os.system('\cp /sptlocal/analysis/transients/data/*TSmap.fits /sptlocal/user/kphadke/transients/TS_maps/')
data_transients = pd.read_csv('/sptlocal/user/kphadke/transients/pole_database/transients.txt', sep="\t", header=0)
ra_text=data_transients['ra[deg]'].values
dec_text=data_transients['dec[deg]'].values
ra_centroid=data_transients['centroid_ra[deg]'].values
dec_centroid=data_transients['centroid_dec[deg]'].values
test_statistic_text=data_transients['test_statistic'].values
observation_text=data_transients['observation'].values
field_text=data_transients['field'].values
source_names=data_transients['source'].values
fname_lc =data_transients['file'].values

dir_des=dir_main+'DES_cutouts/'
dir_rgb=dir_des+'rgb_cubes/'
dir_wise=dir_main+'unWISE/'
dir_galex=dir_main+'galex/'
dir_askap=dir_main+'askap/'
dir_save=dir_main+'png_save/'
dir_TS=dir_main+'TS_maps/'
dir_TS2=dir_TS+'copy_ext/'
dir_SPT_flux=dir_main+'spt_flux_thumbs/'
dir_SPT_flux2=dir_SPT_flux+'copy_ext/'

os.makedirs(dir_des, exist_ok=True)
os.makedirs(dir_rgb, exist_ok=True)
os.makedirs(dir_wise, exist_ok=True)
os.makedirs(dir_galex, exist_ok=True)
os.makedirs(dir_askap, exist_ok=True)
os.makedirs(dir_save, exist_ok=True)
os.makedirs(dir_SPT_flux, exist_ok=True)

username_DES = 'transientcutout3g'      #getpass.getpass()
#username_DES = 'kphadke'  
username_askap = 'transientcutout3g@gmail.com'    #getpass.getpass()
password = 'spt3GjamzDES'       #getpass.getpass()

base_domain = 'des.ncsa.illinois.edu'
config = {
    'auth_token': '',
    'apiBaseUrl': 'https://{}/desaccess/api'.format(base_domain),
    'filesBaseUrl': 'https://{}/files-desaccess'.format(base_domain),
    'username': username_DES,
    'password': password,
    'database': 'desdr',
    'release': 'dr2',
}

def login():
    """Obtains an auth token using the username and password credentials for a given database.
    """
    # Login to obtain an auth token
    r = requests.post(
        '{}/login'.format(config['apiBaseUrl']),
        data={
            'username': config['username'],
            'password': config['password'],
            'database': config['database']
        }
    )
    # Store the JWT auth token
    config['auth_token'] = r.json()['token']
    print('Login success!')
    return config['auth_token']

def submit_cutout_job(data = {
        'db': config['database'],
        'release': config['release']
    }):
    """Submits a query job and returns the complete server response which includes the job ID."""

    # Submit job
    r = requests.put(
        '{}/job/cutout'.format(config['apiBaseUrl']),
        data=data,
        headers={'Authorization': 'Bearer {}'.format(config['auth_token'])}
    )
    response = r.json()
    # print(json.dumps(response, indent=2))
    
    if response['status'] == 'ok':
        job_id = response['jobid']
        print('Job "{}" submitted.'.format(job_id))
        # Refresh auth token
        config['auth_token'] = response['new_token']
    else:
        job_id = None
        print('Error submitting job: '.format(response['message']))
    
    return response

def get_job_status(job_id):
    """Returns the current status of the job identified by the unique job_id."""

    r = requests.post(
        '{}/job/status'.format(config['apiBaseUrl']),
        data={
            'job-id': job_id
        },
        headers={'Authorization': 'Bearer {}'.format(config['auth_token'])}
    )
    response = r.json()
    # Refresh auth token
    config['auth_token'] = response['new_token']
    # print(json.dumps(response, indent=2))
    return response

def download_job_files(url, outdir):
    os.makedirs(outdir, exist_ok=True)
    r = requests.get('{}/json'.format(url))
    for item in r.json():
        if item['type'] == 'directory':
            suburl = '{}/{}'.format(url, item['name'])
            subdir = '{}/{}'.format(outdir, item['name'])
            download_job_files(suburl, subdir)
        elif item['type'] == 'file':
            data = requests.get('{}/{}'.format(url, item['name']))
            with open('{}/{}'.format(outdir, item['name']), "wb") as file:
                file.write(data.content)

    response = r.json()
    return response


def list_job_files(url):
    r = requests.get('{}/json'.format(url))
    for item in r.json():
        if item['type'] == 'directory':
            suburl = '{}/{}'.format(url, item['name'])
            subdir = '{}/{}'.format(outdir, item['name'])
            list_job_files(suburl, subdir)
        elif item['type'] == 'file':
            print('{}/{}'.format(url, item['name']))
    response = r.json()
    return response

def list_downloaded_files(download_dir):
    for dirpath, dirnames, filenames in os.walk(download_dir):
        for filename in filenames:
            print(os.path.join(dirpath, filename))

def job_status_poll(job_id):
    #print('Polling status of job "{}"...'.format(job_id), end='')
    job_status = ''
    response = None
    while job_status != 'ok':
        # Fetch the current job status
        response = get_job_status(job_id)
        # Quit polling if there is an error getting a status update
        if response['status'] != 'ok':
            break
        job_status = response['jobs'][0]['job_status']
        if job_status == 'success' or job_status == 'failure':
            print('\nJob completed with status: {}'.format(job_status))
            break
        #else:
            # Display another dot to indicate that polling is still active
            #print('.', end='', sep='', flush=True)
        time.sleep(3)
    return response
    
for l in range(1485,len(ra_text)):
    
    TSmap_exist_lc = 0
    TSmap_lc_found = 0
    if (~np.isnan(float(ra_centroid[l]))):
        spt_ra=float(ra_centroid[l])
        TSmap_exist_lc=1
        spt_dec=float(dec_centroid[l])
        if spt_ra < 0:
            spt_ra=spt_ra+360.0
    else:
        spt_ra=float(ra_text[l])
        spt_dec=float(dec_text[l])
    
    spt_coo=ac.SkyCoord(ra=spt_ra*u.degree, dec=spt_dec*u.degree, frame='icrs')
    #spt_name='J'+spt_coo.ra.to_string(unit=u.hourangle, sep="", precision=2, pad=True)[:-1]+spt_coo.dec.to_string(sep="", precision=0, alwayssign=True, pad=True)
    spt_name=str(source_names[l])+'_'+str(observation_text[l])
    lc_filename = str(fname_lc[l])
    #print(spt_name)    
    
    TS_map_name2 = glob.glob(dir_TS+str(spt_name)+'*.fits',recursive=True)
    if len(TS_map_name2)>0:
        TS_map_name = glob.glob(dir_TS2+str(spt_name)+'*.fits',recursive=True)
        if len(TS_map_name)==0:
            TS_hdu=fits.open(TS_map_name2[0])
            TS_image=TS_hdu[1].data
            TS_header=TS_hdu[1].header
            w_TS_header=wcs.WCS(TS_header)
            w_TS_header2=w_TS_header.to_header()
            fits.writeto(dir_TS2+str(spt_name)+'_TSmap.fits',TS_image,w_TS_header2)
            TS_map_name = glob.glob(dir_TS2+str(spt_name)+'*.fits',recursive=True)
            
        TS_hdu=fits.open(TS_map_name[0])
        TS_image=TS_hdu[0].data
        maxTS=np.max(TS_hdu[0].data)
        #print("Maximum TS = "+str(maxTS))
        TS_hdu.close()
        if maxTS > 0.0:
            TS_flag=1
    else:
        TS_flag=0
        if TSmap_exist_lc==1:
            lightcurves = Path("/sptgrid/data/onlinemaps/lightcurve/")
            lightcurves_p = '/sptgrid/data/onlinemaps/lightcurve/'
            #print(peak_lc_file)
            #event_info = data_transients.loc[(data_transients.source == field_text[l]) & (data_transients.observation == int(observation_text[l])), :].iloc[0]
    
            ra, dec = float(ra_text[l])* core.G3Units.deg, float(dec_text[l])*core.G3Units.deg
            #ra, dec = spt_ra* core.G3Units.deg, spt_dec*core.G3Units.deg
            ts, obsid = test_statistic_text[l],observation_text[l]
            #print(ra,dec,ts,peak_obsid)
            
            lc_frame = None
            if len(glob.glob(lightcurves_p+'*/'+str(lc_filename)))>0:
                print("Lightcurve file found")
                peak_lc_file = next(lightcurves.glob('*/'+str(lc_filename)))
                frames = core.G3File(str(peak_lc_file))
                for frame in frames:
                    if frame.type == core.G3FrameType.LightCurve:
                        transients.CheckLightCurveFrame(frame)
                        #if frame['PeakObsID'] != peak_obsid:
                        #    continue
                        #print("Hi2")
                        if not np.allclose([frame["PixelRa"], frame["PixelDec"]], [ra, dec]):
                            continue
                        print("Pixels match RA, Dec")
                        if frame["TestStatistic"]>=45.0:
                            print("Event detected")
                            lc_frame=frame
                            if lc_frame:
                                print("Peak found at:",frame['PeakObsID'],";",obsid_to_g3time(frame['PeakObsID'])," in the file ", peak_lc_file)
                                peakobsid=frame['PeakObsID']
                                break
                        break
                        #print(frame["PixelRa"], frame["PixelDec"], frame['PeakObsID'])
                        #print(frame['PeakObsID'])
                        
                        
                if lc_frame:
                    lc_frame= frame       
                    print(lc_frame["TestStatistic"])    
                    TS_map = lc_frame["TestStatisticMap"]
                    #print(TS_map)
                    #print(str(peak_lc_file.name[:-2]))
                    maps.fitsio.save_skymap_fits(dir_TS+str(spt_name)+'.fits', TS_map, overwrite=True, compress=True)
                    TS_map_name2 = glob.glob(dir_TS+str(spt_name)+'*.fits',recursive=True)
                    TS_hdu=fits.open(TS_map_name2[0])
                    TS_image=TS_hdu[1].data
                    TS_header=TS_hdu[1].header
                    w_TS_header=wcs.WCS(TS_header)
                    w_TS_header2=w_TS_header.to_header()
                    fits.writeto(dir_TS2+str(spt_name)+'_TSmap.fits',TS_image,w_TS_header2)
                    TS_map_name = glob.glob(dir_TS2+str(spt_name)+'*.fits',recursive=True)
                    TS_hdu=fits.open(TS_map_name[0])
                    TS_image=TS_hdu[0].data
                    maxTS=np.max(TS_hdu[0].data)
                    print("Maximum TS = "+str(maxTS))
                    TS_hdu.close()
                    if maxTS > 0.0:
                        TS_flag=1
            else:
                TSmap_exist_lc = 0

            
            #print(G3Time(obsid_to_g3time(obsid)))
            #startobs=obsid
            #endtime=G3Time(obsid_to_g3time(obsid)).mjd+14
            #endobs=time_to_obsid(Time(endtime,format='mjd').iso.replace(' ','T'))
            #for k in range(startobs,endobs):
            #    #print(k)
            #    if len(glob.glob(lightcurves_p+'*/'+str(k)+'.g3'))>0:
            #        #print("Hi")
            #        peak_lc_file = next(lightcurves.glob('*/'+str(k)+'.g3'))
            #        frames = core.G3File(str(peak_lc_file))
            #        for frame in frames:
            #            if frame.type == core.G3FrameType.LightCurve:
            #                transients.CheckLightCurveFrame(frame)
            #                #if frame['PeakObsID'] != peak_obsid:
            #                #    continue
            #                if not np.allclose([frame["PixelRa"], frame["PixelDec"]], [ra, dec]):
            #                    continue
            #                if frame["TestStatistic"]<45.0:
            #                    break
            #                if frame["TestStatistic"]>=45.0:
            #                    print("Event detected")
            #                    lc_frame=frame
            #                    if lc_frame:
            #                        print("Peak found at:",frame['PeakObsID'],";",obsid_to_g3time(frame['PeakObsID'])," in the file ", peak_lc_file)
            #                        peakobsid=frame['PeakObsID']
            #                        TSmap_lc_found = 1
            #                        break
            #                break
            #                #print(frame["PixelRa"], frame["PixelDec"], frame['PeakObsID'])
            #                #print(frame['PeakObsID'])
            #                
            #                
            #        if lc_frame:
            #            lc_frame= frame
            #            if TSmap_lc_found == 1:
            #                peakobsid=frame['PeakObsID']
            #                print(frame['PeakObsID'])
            #                break
            #         
            #if lc_frame:         
            #    #print(lc_frame["TestStatistic"])    
            #    TS_map = lc_frame["TestStatisticMap"]
            #    #print(TS_map)
            #    #print(str(peak_lc_file.name[:-2]))
            #    maps.fitsio.save_skymap_fits(dir_TS+str(spt_name)+'.fits', TS_map, overwrite=True, compress=True)
            #    TS_map_name2 = glob.glob(dir_TS+str(spt_name)+'*.fits',recursive=True)
            #    TS_hdu=fits.open(TS_map_name2[0])
            #    TS_image=TS_hdu[1].data
            #    TS_header=TS_hdu[1].header
            #    w_TS_header=wcs.WCS(TS_header)
            #    w_TS_header2=w_TS_header.to_header()
            #    fits.writeto(dir_TS2+str(spt_name)+'_TSmap.fits',TS_image,w_TS_header2)
            #    TS_map_name = glob.glob(dir_TS2+str(spt_name)+'*.fits',recursive=True)
            #    TS_hdu=fits.open(TS_map_name[0])
            #    TS_image=TS_hdu[0].data
            #    maxTS=np.max(TS_hdu[0].data)
            #    print("Maximum TS = "+str(maxTS))
            #    TS_hdu.close()
            #    if maxTS > 0.0:
            #        TS_flag=1
            #else:
            #    TSmap_exist_lc = 0
            #    print(spt_name,ra,dec,ts,obsid,peak_lc_file)

        
