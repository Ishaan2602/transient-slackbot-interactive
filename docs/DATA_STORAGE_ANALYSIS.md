# Data Storage Analysis

## Current Status

### new_transients.csv (Processed Transients Tracker)
**Purpose**: Track which transients have been posted to Slack to avoid duplicates

**Current Columns** (10):
1. `source` - Source identifier
2. `observation` - Observation ID (obsid)
3. `ra[deg]` - Right ascension
4. `dec[deg]` - Declination  
5. `field` - Field name
6. `time` - Detection timestamp
7. `test_statistic` - Detection significance
8. `status` - Transient status
9. `processed_at` - When we posted to Slack
10. `unique_id` - Composite key (source_observation)

### transients.txt (Live SPT-3G Data)
**Source**: `/sptlocal/transfer/rsync/transfer_database/transients.txt`

**Total Columns** (19):
1-9. Same as above  
10. `centroid_ra[deg]` - Refined RA
11. `centroid_dec[deg]` - Refined Dec
12. `peak_obsid_90` - 90 GHz peak observation
13. `peak_obsid_150` - 150 GHz peak observation
14. `peak_flux[mJy]` - Total peak flux
15. `peak_flux_90[mJy]` - 90 GHz peak flux
16. `peak_flux_150[mJy]` - 150 GHz peak flux
17. `fwhm[days]` - Full width half max (duration)
18. `catalog_source` - Known source match
19. `file` - Associated file (contains timestamps, not g3 filenames)
20. `modified` - Last modification timestamp

---

## Analysis & Recommendations

### ✅ Keep Current (Minimal Storage)
**Rationale**: We have a working product. Storage is minimal (~260KB for 2000 transients).

**What we need**:
- ✅ `unique_id` - Prevent duplicates (essential)
- ✅ `processed_at` - Audit trail (when posted)
- ✅ `source`, `observation` - Identification
- ✅ `ra[deg]`, `dec[deg]` - Coordinates for reference

**What we can drop**:
- ❌ `field`, `time`, `test_statistic`, `status` - Redundant (in transients.txt)

**Minimal Schema** (5 columns):
```
unique_id, source, observation, ra[deg], dec[deg], processed_at
```
**Savings**: 50% reduction → ~130KB

---

### 📊 Alternative: Enhanced Storage (for analytics)
**Use case**: If you want to analyze trends without querying transients.txt

**Add these**:
- `peak_flux[mJy]` - Brightness (useful for filtering)
- `fwhm[days]` - Duration (transient vs persistent)
- `catalog_source` - Known source flag
- `centroid_ra[deg]`, `centroid_dec[deg]` - Better coordinates
- `slack_message_ts` - Slack message timestamp (for voting linkage)
- `images_posted` - Which surveys had images (ASKAP/WISE/DECam flags)
- `ts_map_available` - Whether TS map was overlaid

**Enhanced Schema** (15 columns):
```
unique_id, source, observation, ra[deg], dec[deg], centroid_ra[deg], 
centroid_dec[deg], field, time, test_statistic, peak_flux[mJy], 
fwhm[days], catalog_source, processed_at, slack_message_ts
```

---

## Recommendation

**Keep current schema** - it works and storage is negligible.

**Only change if**:
- You want offline analytics without transients.txt
- You need to link back to Slack messages programmatically
- You're building a dashboard/visualization tool

**File size comparison**:
- Current: 260KB (2000 transients × 10 columns)
- Minimal: 130KB (saves ~130KB, not worth the refactor)
- Enhanced: 390KB (adds tracking/analytics features)

## Conclusion

✅ **Status quo is fine** - working product with minimal overhead  
✅ **unique_id in both files** is redundant but harmless (auto-generated)  
⚠️ Consider adding `slack_message_ts` if voting system needs message lookups
