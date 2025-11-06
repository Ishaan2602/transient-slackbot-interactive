# from astroquery.casda import Casda

username_askap = 'ishaang6@illinois.edu'
password = 'obscos_transient'
casda = Casda()
auth = (username_askap,password)
login_response = casda._request("GET", casda._login_url, auth=auth,timeout=casda.TIMEOUT, cache=False)
authenticated = login_response.status_code == 200
if authenticated:
    casda.USERNAME = username_askap
    casda._auth = (username_askap, password)
    casda._authenticated=True

    print("Looking for ASKAP files")
    
    if len(glob.glob(dir_askap+str(spt_name)+'/'+str(spt_name)+'_askap.fits'))<1:
        #updating code with astroquery instead of casda api
        os.makedirs(dir_askap+str(spt_name), exist_ok=True)
        centre = ac.SkyCoord(spt_ra*u.degree, spt_dec*u.degree, frame='icrs')
        result = Casda.query_region(centre, radius=2.5*u.arcmin)
        public_data = Casda.filter_out_unreleased(result)
        subset = public_data[((public_data['obs_collection'] == 'The Rapid ASKAP Continuum Survey') & #
                  (np.char.startswith(public_data['filename'], 'RACS-DR1_')) & #
                  (np.char.endswith(public_data['filename'], 'A.fits'))
                 )]
        url_list = casda.cutout(subset[:1], coordinates=centre, radius=2.5*u.arcmin)
        filelist = casda.download_files(url_list, savedir=dir_askap+str(spt_name))
        askap_hdus =  [fits.open(afname)[0] for afname in glob.glob(dir_askap+str(spt_name)+'/*.fits',recursive=True)]    # Open HDUs from the individual fits files
        if len(askap_hdus) == 1:
            for i in range(len(askap_hdus)):
                p_hdu=askap_hdus[i]
                image=p_hdu.data[0,0,:,:]
                header=p_hdu.header
                w_header=wcs.WCS(header)
                w_new=w_header.dropaxis(-1)
                w_new=w_new.dropaxis(-1)
                header_new=w_new.to_header()
                fits.writeto(dir_askap+str(spt_name)+'/'+str(spt_name)+'_askap.fits',image,header_new)
                array_askap = image
        if len(askap_hdus)>1:                        # if more than one file make mosaic
            for i in range(len(askap_hdus)):
                p_hdu=askap_hdus[i]
                image=p_hdu.data[0,0,:,:]
                header=p_hdu.header
                w_header=wcs.WCS(header)
                w_new=w_header.dropaxis(-1)
                w_new=w_new.dropaxis(-1)
                header_new=w_new.to_header()
                fits.writeto(dir_askap+str(spt_name)+'/'+str(spt_name)+'_'+str(i)+'.fits',image,header_new)
            askap_hdus_2=[fits.open(afname)[0] for afname in glob.glob(dir_askap+str(spt_name)+'/'+str(spt_name)+'_*.fits',recursive=True)]
            wcs_out, shape_out = find_optimal_celestial_wcs(askap_hdus_2)
            array_askap, footprint = reproject_and_coadd(askap_hdus_2, wcs_out, shape_out=shape_out, reproject_function=reproject_interp,match_background=True)
            askap_mosaic_header=wcs_out.to_header()
            if askap_mosaic_header['WCSAXES'] == 4:
                wcs_out=wcs_out.dropaxis(-1)
                wcs_out=wcs_out.dropaxis(-1)
                askap_mosaic_header=wcs_out.to_header()
            fits.writeto(dir_askap+str(spt_name)+'/'+str(spt_name)+'_askap.fits', array_askap, askap_mosaic_header)
            askap_hdus_2.close()

    else:                                                                                                                   # enter this condition if file was already made
        askap_hdus = fits.open(dir_askap+str(spt_name)+'/'+str(spt_name)+'_askap.fits')
        header=askap_hdus[0].header
        print(header['NAXIS'])
        if header['NAXIS'] == 4:
            image=askap_hdus[0].data[0,0,:,:]
            w_header=wcs.WCS(header)
            w_new=w_header.dropaxis(-1)
            w_new=w_new.dropaxis(-1)
            header_new=w_new.to_header()
            fits.writeto(dir_askap+str(spt_name)+'/'+str(spt_name)+'_askap.fits',image,header_new,overwrite=True)
            array_askap=image
            askap_hdus.close()
        else:
            askap_hdus2 = fits.open(dir_askap+str(spt_name)+'/'+str(spt_name)+'_askap.fits')
            array_askap=askap_hdus2[0].data
            askap_hdus2.close()
    for f in glob.glob(dir_askap+str(spt_name)+'/cutout*'):
        os.remove(f)

    if TS_flag == 0 and len(glob.glob(dir_save+str(spt_name)+'_ASKAP_thumb_5x5.png'))==0:
        rcParams.update({'xtick.direction': 'in', 'ytick.direction': 'in'})
        fig = mpl.figure(figsize=(12, 12))

        f = aplpy.FITSFigure(dir_askap+str(spt_name)+'/'+str(spt_name)+'_askap.fits',figure=fig,slices=[0,0],dimensions=[0, 1])
        f.set_theme('publication')
        f.tick_labels.set_font(size='large')
        f.axis_labels.set_xtext('Right Ascension (J2000)')
        f.axis_labels.set_ytext('Declination (J2000)')
        f.tick_labels.set_yposition('left')
        f.axis_labels.set_yposition('left')
        f.axis_labels.set_font(size='x-large')
        f.ticks.set_color(color='black')
        f.ticks.set_length(length=20.0, minor_factor=0.5)
        f.recenter(spt_ra,spt_dec, radius=0.041666666)  # degree
        f.show_markers(spt_ra,spt_dec,marker='+',s=250,facecolor='cyan')
        f.show_grayscale(pmin=70.0,pmax=99.9,stretch='log',smooth=None)
        #f.show_contour(dir_TS+str(spt_name)+'_TSmap.fits',colors='red',levels=np.array([maxTS-11.83,maxTS-6.18,maxTS-2.3]),smooth=1)
        f.add_scalebar(3*2.77778e-3)        
        f.scalebar.set_label('30"')
        f.scalebar.set_color('black')
        f.scalebar.set_font(size='x-large')
        f.scalebar.set_linewidth(2)
        f.set_title(str(spt_name)+' ASKAP grayscale 5x5')
        fig.canvas.draw()
        fig.savefig(dir_save+str(spt_name)+'_ASKAP_thumb_5x5.png',dpi=400)
        f.close()

        print("ASKAP thumbnail made.")