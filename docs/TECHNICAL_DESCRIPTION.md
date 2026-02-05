# SPT-3G Transient Monitoring Bot - Technical Documentation

**Role:** Undergraduate Researcher / Observational Cosmology Researcher  
**Institution:** UIUC Department of Astronomy  
**Advisor:** Prof. Joaquin Vieira | **PI:** Kedar Phadke  
**Dates:** Sep 2025 - Present

## Core Objective
Automate the real-time monitoring and multi-wavelength imaging of ~1750 millimeter-wave transient detections from the South Pole Telescope (SPT-3G) survey, with collaborative classification via Slack-based voting system.

---

## Technology Stack

### Core Python Libraries
- **Python 3.13** - Primary development environment
- **astropy 5.0+** - FITS I/O, WCS coordinate transformations, celestial coordinate handling
- **astroquery 0.4.6+** - Archive queries (CASDA interface for ASKAP data)
- **pandas 1.3.0+** - Tabular data management, transient tracking, vote aggregation
- **numpy 1.20.0+** - Array operations, statistical calculations, image array manipulation
- **matplotlib 3.5.0+** - Base plotting infrastructure, figure canvas management
- **aplpy 2.1.0+** - Astronomical image visualization with WCS support
- **reproject 0.10.0+** - FITS image reprojection and mosaicking operations
- **slack_bolt 1.14.0+** - Slack bot framework with event-driven architecture
- **schedule 1.2.0+** - Task scheduling for daily automated checks
- **pyvo** - Virtual Observatory protocols (SIA for DECam queries)
- **dl (Data Lab client)** - NOIRLab Data Lab authentication and access

### External APIs and Services
- **CASDA (CSIRO ASKAP Science Data Archive)** - Radio continuum data retrieval
- **unWISE (unwise.me)** - Infrared survey cutout service
- **NOIRLab Data Lab (datalab.noirlab.edu)** - Optical survey data access
- **Slack API** - Real-time messaging, file uploads, reaction events
- **Legacy Survey Viewer** - External reference links for optical context
- **SIMBAD (CDS)** - Cross-matching for known astronomical sources

---

## Data Ingestion Pipeline

### Input Format
- **Primary Data Source:** `transients.txt` - Tab-separated file with SPT-3G detections
- **Columns Parsed:** source, observation, ra[deg], dec[deg], field, time, test_statistic, peak_flux[mJy], status
- **Coordinate Handling:** Negative RA values normalized to 0-360° range
- **Centroid Support:** Falls back to centroid_ra/centroid_dec when available for improved localization

### State Management
- **Processed Tracking:** `new_transients.csv` maintains history of all processed sources
- **Deduplication:** Composite unique_id from `{source}_{observation}` prevents reprocessing
- **Timestamp Tracking:** `last_check.txt` stores ISO-format UTC timestamp for incremental updates
- **Status Filtering:** Only processes transients with `status='new'` or null status

### Scheduler Configuration
```python
schedule.every().day.at("12:00").do(check_for_new_transients)
```
- Daily execution at 12:00 PM (system timezone)
- Continuous monitoring with 60-second sleep intervals
- Graceful degradation if individual survey components fail

---

## Multi-Wavelength Imaging Architecture

### 1. ASKAP Radio Continuum (887.5 MHz)

#### Survey Details
- **Survey:** RACS-DR1 (Rapid ASKAP Continuum Survey Data Release 1)
- **Wavelength:** 34 cm (887.5 MHz L-band)
- **Polarization:** Stokes I (total intensity) only
- **Spatial Resolution:** ~12-15 arcseconds

#### Authentication & Query
```python
from astroquery.casda import Casda
casda = Casda()
casda._request("GET", casda._login_url, auth=(username, password))
```
- **Credentials:** CASDA_USERNAME_PERSONAL, CASDA_PASSWORD_PERSONAL from environment
- **HTTP Basic Auth** via astroquery session management
- **Query Method:** `Casda.query_region()` with cone search (2.5 arcmin radius)
- **Filtering:**
  - `obs_collection == 'The Rapid ASKAP Continuum Survey'`
  - Filename pattern: `RACS-DR1_*A.fits` (Stokes I images)
  - Public data only (unreleased data filtered out)

#### Data Processing Pipeline
1. **Cutout Download:**
   - CASDA cutout service for on-the-fly extraction
   - Preserves WCS from parent mosaic
   - Typical result: 11-13 RACS tiles per query (handles tile boundaries)

2. **FITS Cube Reduction:**
   ```python
   data = hdul[0].data
   if data.ndim == 4:  # (freq, stokes, y, x)
       data = data[0, 0, :, :]  # Extract 2D image
   ```
   - Reduces 4D cubes to 2D by dropping frequency/Stokes axes

3. **Mosaicking (Multi-Tile Handling):**
   ```python
   from reproject.mosaicking import reproject_and_coadd
   array, footprint = reproject_and_coadd(
       hdus, wcs_out, shape_out=shape_out,
       reproject_function=reproject_interp,
       match_background=True
   )
   ```
   - `find_optimal_celestial_wcs()` determines common projection
   - `reproject_interp` for flux-conserving reprojection
   - `match_background=True` for seamless background matching

4. **Visualization:**
   - **APLpy FITSFigure** with publication theme
   - **Grayscale stretch:** Log scale, pmin=70%, pmax=99.9% (percentile clipping)
   - **Figure specs:** 6×6 inches, 150 DPI → 900×900 pixel PNG
   - **Marker:** Cyan '+' at transient position (s=250)
   - **Scalebar:** 30 arcseconds (3×2.77778e-3 degrees)
   - **Tick marks:** Black, length=20.0, minor_factor=0.5

#### Storage Structure
```
askap_data/{source}_{observation}/
    ├── cutout_*.fits (raw downloads)
    └── {source}_{observation}_mosaic.fits (processed)
askap_images/
    └── {source}_{observation}_ASKAP_thumb_5x5.png
```

---

### 2. WISE Infrared (3.4 μm)

#### Survey Details
- **Survey:** unWISE neo6 coadds (Lang 2014)
- **Band:** W1 only (3.4 μm near-infrared)
- **Depth:** ~5 years of WISE mission data stacked
- **Spatial Resolution:** 6 arcseconds

#### Data Retrieval
- **No Authentication Required** - Public HTTP access
- **URL Format:**
  ```python
  url = f'https://unwise.me/cutout_fits?version=neo6&ra={ra}&dec={dec}&size=1000&bands=1'
  ```
- **Response Format:** tar.gz archive containing FITS file(s)
- **Cutout Size:** 1000 pixels (default)

#### Processing Pipeline
1. **Archive Extraction:**
   ```python
   import tarfile
   with tarfile.open(tar_file, 'r:gz') as tar:
       tar.extractall(path=source_dir)
   ```
   - Extracts FITS to `wise_data/{source}/`
   - Automatic cleanup of .gz and .tar files

2. **Multi-Tile Mosaicking:**
   - Same `reproject_and_coadd()` workflow as ASKAP
   - Handles unWISE tile boundaries (12-18k tiles globally)
   - Creates single `{source}_unwise_w1.fits`

3. **Visualization:**
   - **Fixed flux scaling:** vmin=4.0, vmax=90000.0 (not percentile-based)
   - Log stretch for wide dynamic range
   - Same 6×6 inch, 150 DPI output format
   - Same scalebar/marker styling as ASKAP

#### Storage Structure
```
wise_data/{source}_{observation}/
    ├── *.fits (extracted tiles)
    └── {source}_{observation}_unwise_w1.fits (mosaic)
wise_images/
    └── {source}_{observation}_WISE_thumb_5x5.png
```

---

### 3. DECam Optical RGB (g/r/i bands)

#### Survey Details
- **Surveys:** DECaLS (DECam Legacy Survey) + DES (Dark Energy Survey)
- **Bands:** g (475 nm), r (620 nm), i (750 nm)
- **Image Type:** Stack (multi-epoch coadds for maximum depth)
- **Spatial Resolution:** ~1 arcsecond (seeing-limited)

#### Authentication & Query Protocol
```python
from dl import authClient as ac
token = ac.login(DATALAB_USERNAME, DATALAB_PASSWORD)

from pyvo.dal import sia
svc = sia.SIAService('https://datalab.noirlab.edu/sia/coadd_all')
```
- **Credentials:** DATALAB_USERNAME, DATALAB_PASSWORD from environment
- **Protocol:** SIA (Simple Image Access) - Virtual Observatory standard
- **Service:** `coadd_all` endpoint queries both DECaLS and DES archives

#### Stack Selection Algorithm
```python
imgTable = svc.search((ra, dec), (fov/np.cos(dec*np.pi/180), fov), verbosity=2).to_table()
sel = (imgTable['obs_bandpass'].str.startswith(band)) & 
      (imgTable['proctype'] == 'Stack') & 
      (imgTable['prodtype'] == 'image')
row = Table[np.argmax(Table['exptime'].data.data.astype('float'))]
```
- **FOV:** 0.1 degrees (6 arcmin), declination-corrected
- **Selection Criteria:**
  1. Filter by bandpass (g, r, or i)
  2. Require `proctype='Stack'` (not raw exposures)
  3. Require `prodtype='image'` (not catalogs)
  4. **Select deepest Stack:** `argmax(exptime)` chooses longest total exposure
- **Typical Results:** 11 g-band Stacks, 11 r-band Stacks, 3-7 i-band Stacks per query
- **Download:** Direct FITS retrieval via `access_url` (no cutout service needed)

#### RGB Image Generation Pipeline

1. **Three-Band Download:**
   ```python
   for band in ['g', 'r', 'i']:
       image, header = download_deepest_image(ra, dec, band=band, fov=0.1)
       fits.writeto(f"{source_name}_{band}.fits", image, header)
   ```
   - Each band stored separately as FITS
   - Full Stack images (typically 5-20 MB each)

2. **RGB Cube Creation:**
   ```python
   aplpy.make_rgb_cube([i_fits, r_fits, g_fits], output_cube)
   ```
   - **Band Mapping:** i→Red, r→Green, g→Blue (standard optical astronomy convention)
   - Creates 3D FITS cube with aligned WCS
   - Output: `{source}_des_irg_cube.fits`

3. **RGB Stretch Application:**
   ```python
   aplpy.make_rgb_image(cube_path, rgb_png,
       pmin_r=30.0, pmax_r=97.50,
       pmin_g=30.0, pmax_g=97.50,
       pmin_b=30.0, pmax_b=97.50,
       embed_avm_tags=False)
   ```
   - **Percentile Clipping:** 30th to 97.5th percentile mapped to 0-255 per channel
   - Uniform stretch across all three bands
   - Intermediate PNG: `{source}_rgb_image.png`
   - APLpy auto-generates 2D projection: `{source}_des_irg_cube_2d.fits`

4. **Final Visualization:**
   ```python
   fig = plt.figure(figsize=(6, 6))
   f = aplpy.FITSFigure(rgb_cube_2d, figure=fig)
   f.recenter(ra, dec, radius=0.01666666)  # 2×2 arcmin FOV
   f.show_rgb(rgb_image_path)
   f.add_scalebar(2.77778e-3)  # 10 arcseconds
   ```
   - **White tick marks/scalebar** (better contrast on RGB backgrounds)
   - **Tighter FOV:** 2×2 arcmin (vs 5×5 for radio/IR) for higher detail
   - **Output:** 6×6 inch, 150 DPI PNG (consistent with other surveys)

#### Technical Considerations

**Percentile Stretch Parameters:**
- Controls noise visibility vs dynamic range
- `pmin=30.0`: Makes 30th percentile black (clips faint noise floor)
- `pmax=97.5`: Makes 97.5th percentile white (preserves bright stars)
- Lower pmin (e.g., 20.0) → more noise visible, darker overall
- Higher pmin (e.g., 40.0) → cleaner backgrounds, less faint detail

**Stack Exposure Times:**
- Varies by sky position (DES footprint vs DECaLS-only)
- Typical: 100-600 seconds total integration
- Longer exposures → lower noise → can use lower pmin values
- Code automatically selects deepest available Stack

**Data Quality:**
- All Stacks are pipeline-calibrated (bias/dark/flat/sky-subtracted)
- Astrometry accurate to <0.1 arcsec (suitable for catalog cross-matching)
- Photometry calibrated (could perform aperture photometry on FITS)

#### Storage Structure
```
decam_data/{source}_{observation}/
    ├── {source}_{observation}_g.fits
    ├── {source}_{observation}_r.fits
    ├── {source}_{observation}_i.fits
    ├── {source}_{observation}_des_irg_cube.fits
    ├── {source}_{observation}_des_irg_cube_2d.fits
    └── {source}_{observation}_rgb_image.png
decam_images/
    └── {source}_{observation}_DECam_thumb_2x2.png
```

---

## Slack Bot Architecture

### Framework & Authentication
```python
from slack_bolt import App
app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET
)
```
- **Event-Driven Architecture:** Bolt framework handles webhooks/socket mode
- **Environment Variables:** SLACK_BOT_TOKEN (OAuth token), SLACK_SIGNING_SECRET
- **Channel Configuration:** Hardcoded CHANNEL_ID for transient notifications

### Message Formatting

#### Block Kit Structure
```python
blocks = [
    {"type": "header", "text": {"type": "plain_text", "text": f"New Transient: {name}"}},
    {"type": "section", "fields": [
        {"type": "mrkdwn", "text": "*Coordinates:*\nRA: ..."},
        {"type": "mrkdwn", "text": "*Detection Time:*\n..."}
    ]},
    {"type": "divider"},
    {"type": "context", "elements": [
        {"type": "mrkdwn", "text": "Vote: 🔥 Interesting | 🌌 AGN | ⭐ Star | 🗑️ Junk"}
    ]}
]
```
- **Coordinate Formatting:** RA converted to HMS, Dec to DMS (sexagesimal)
- **Metadata Display:** Test Statistic, Field ID, Peak Flux (mJy), Status
- **Reference Links:** Legacy Survey DR10 viewer, SIMBAD cone search
- **Image Status:** Dynamic fields showing which surveys succeeded/failed

#### Two-Message Upload Strategy
1. **Main Message:** `chat_postMessage()` with blocks
   - Returns `message_ts` for reaction tracking
   - `unfurl_links=False` prevents auto-preview of URLs
2. **Image Upload:** `files_upload_v2()` in separate message
   ```python
   app.client.files_upload_v2(
       channel=CHANNEL_ID,
       file_uploads=[
           {"file": img_path, "title": os.path.basename(img_path)}
           for img_path in [askap_img, wise_img, decam_img]
       ],
       initial_comment=f"Images for {source_name}"
   )
   ```
   - Uploads up to 3 images (ASKAP, WISE, DECam) in single API call
   - Non-threaded for side-by-side display in channel
   - 15-second buffer between transients prevents API rate limits

### Voting System Implementation

#### Reaction Event Handling
```python
@app.event("reaction_added")
def handle_reaction_added(event, say):
    reaction = event.get("reaction")
    timestamp = event.get("item", {}).get("ts")
    transient_id = extract_transient_id(channel, timestamp)
    reaction_counts = get_message_reactions(channel, timestamp)
    vote_tracker.update_vote_counts(transient_id, reaction_counts)
```
- **Monitored Reactions:** 🔥 (fire), 🌌 (milky_way), ⭐ (star), 🗑️ (wastebasket)
- **Real-Time Updates:** Both `reaction_added` and `reaction_removed` events tracked
- **Bot Exclusion:** Bot's own reactions subtracted from counts
- **ID Extraction:** Regex pattern matching on message text to identify transient

#### Vote Aggregation & Storage
```python
# voting_data/vote_counts.csv
transient_id,agn_votes,interesting_votes,star_votes,junk_votes
0210-54_275124274,5,2,0,1
```
- **CSV Backend:** pandas DataFrame for vote persistence
- **Update Mechanism:** Upsert on transient_id (update if exists, insert if new)
- **Classification Thresholds:**
  - AGN: 3 votes
  - Interesting: 2 votes
  - Star: 2 votes
  - Junk: 3 votes
- **Confidence Score:** `max(votes) / sum(votes)` when threshold met

#### Priority Queue Algorithm
```python
import heapq
priority_heap = []
for row in votes_df.iterrows():
    score = (row['interesting_votes']*5 + row['agn_votes']*4 + 
             row['star_votes']*3 + row['junk_votes']*2)
    heapq.heappush(priority_heap, (-score, row['transient_id']))
```
- **Weighted Scoring:** Interesting (×5) > AGN (×4) > Star (×3) > Junk (×2)
- **Min-Heap Implementation:** Negated scores for max-priority behavior
- **Retrieval:** `get_top_transients(n=5)` returns highest-priority targets
- **Use Case:** Prioritize follow-up observations based on team consensus

#### Slack Command Interface
```python
@app.message("voting results")
def handle_voting_results(message, say):
    top_transients = vote_tracker.get_top_transients(10)
    response = "*Voting Results - Top Priority Transients:*\n\n"
    for i, tid in enumerate(top_transients):
        votes = vote_tracker.get_transient_votes(tid)
        response += f"*{i+1}. {tid}* (Total: {sum(votes.values())})\n"
        response += f"   AGN: {votes['AGN']} | Interesting: {votes['Interesting']} | ..."
    say(response)
```
- **Message Trigger:** Text matching "voting results"
- **Output:** Formatted markdown with top 10 transients ranked by priority score

---

## Performance Characteristics

### Timing Benchmarks
- **ASKAP Processing:** ~90-120 seconds per transient
  - Query: 5-10s
  - Cutout download: 40-60s (11-13 tiles × ~3-5s each)
  - Mosaicking: 20-30s
  - Visualization: 10-15s
  
- **WISE Processing:** ~30-60 seconds per transient
  - HTTP download: 10-20s
  - Extraction: 5-10s
  - Mosaicking (if needed): 10-20s
  - Visualization: 5-10s
  
- **DECam Processing:** ~120-180 seconds per transient
  - Stack queries (×3 bands): 20-30s
  - FITS downloads: 60-90s (depends on Stack size)
  - RGB cube generation: 20-30s
  - RGB stretching: 10-15s
  - Visualization: 10-15s

- **Slack Upload:** ~5-10 seconds for 3 images
- **Total Pipeline:** 2-4 minutes per transient (end-to-end)

### Success Rates
- **ASKAP:** ~100% (RACS covers full southern sky)
- **WISE:** ~100% (all-sky coverage)
- **DECam:** ~100% for DES footprint + DECaLS south
  - Some high-latitude fields may lack deep Stacks
  - Graceful degradation: posts transient even if imaging fails

### Scalability
- **Daily Throughput:** Designed for batch processing of daily detections
- **Concurrency:** Sequential processing (no parallelization currently)
- **Rate Limiting:** 15-second buffer between Slack posts
- **Storage Growth:** ~50-100 MB per transient (FITS + PNGs)

---

## Data Quality & Validation

### Image Quality Checks
- **FITS Header Validation:** Verify WCS keywords present before visualization
- **Empty Image Handling:** Check for all-NaN arrays after mosaicking
- **Coordinate Bounds:** Validate RA/Dec within reasonable ranges before queries

### Caching Strategy
- **Existence Checks:** All processors check for existing FITS/PNGs before download
- **Reprocessing Support:** Can regenerate thumbnails from cached FITS
- **Cleanup Utilities:**
  - `cleanup_temp_files()` removes CASDA intermediate cutouts
  - Archive cleanup for .tar.gz and extracted .gz files

### Error Recovery
- **Survey Fallback:** System continues if individual surveys fail
- **Status Indicators:** Slack messages show "Generated" vs "No data available"
- **Logging:** Print statements track each processing stage
- **First-Run Handling:** Marks historical transients as processed to prevent backlog flooding

---

## Future Enhancements (Planned)

### TS Map Contour Overlays
- **Source:** SPT-3G pipeline Test Statistic maps (chi-squared)
- **Contour Levels:** `[maxTS-11.83, maxTS-6.18, maxTS-2.3]` (3σ, 2.5σ, 1.5σ equivalent)
- **Visualization:**
  ```python
  f.show_contour(ts_map_fits, colors='red', levels=contour_levels)
  ```
- **Purpose:** Validate temporal variability significance, distinguish real transients from artifacts
- **Status:** Awaiting TS map FITS file integration

### Adaptive Stretch Parameters
- **Concept:** Adjust RGB pmin/pmax based on Stack exposure time
  ```python
  if exptime < 100:  # Shallow Stack
      pmin, pmax = 50.0, 99.5
  else:  # Deep Stack
      pmin, pmax = 30.0, 97.5
  ```
- **Benefit:** Cleaner backgrounds for noisy fields while preserving faint detail in deep fields

### Production Deployment
- **Server Migration:** Move from local development to persistent server
- **Ngrok Testing:** Webhook debugging for Slack event delivery
- **Systemd Service:** Auto-restart on failure, log rotation

---

## Key Technical Achievements

1. **End-to-End Automation:** Zero manual intervention from detection to Slack notification
2. **Multi-Archive Integration:** Unified interface to 3 independent survey archives (CASDA, unWISE, Data Lab)
3. **Robust Mosaicking:** Handles multi-tile overlaps across all wavelengths with background matching
4. **WCS Preservation:** Maintains accurate astrometry through entire processing chain
5. **Real-Time Collaboration:** Event-driven voting system with sub-second response latency
6. **Priority Intelligence:** Algorithmic ranking for follow-up target selection
7. **Consistent Visualization:** Uniform 6×6 inch, 150 DPI output across all surveys for optimal Slack display
8. **RGB Color Imaging:** Full implementation of i/r/g band integration with percentile stretching for optical survey data

---

## Repository Structure
```
obscos/
├── transient_monitor.py          # Main scheduler and orchestration
├── transients.txt                # Input data (tab-separated)
├── new_transients.csv            # Processing history
├── askap_integration/
│   └── askap_image_processor.py  # CASDA queries, mosaicking, thumbnails
├── wise_integration/
│   └── wise_image_processor.py   # unWISE downloads, extraction
├── decam_integration/
│   └── decam_image_processor.py  # Data Lab queries, RGB generation
├── voting_system/
│   ├── vote_tracker.py           # Vote aggregation, priority queue
│   └── reaction_handler.py       # Slack event handlers
├── tests/
│   ├── test_askap_setup.py       # CASDA authentication tests
│   └── test_voting_system.py     # Vote tracking validation
└── utilities/
    └── view_last_transients.py   # Inspection tools
```

---

**Total Lines of Code:** ~1,200 (excluding documentation)  
**Active Development Period:** Sep 2025 - Present  
**Transients Monitored:** ~1,750 (SPT-3G survey coverage)
