<!--
Provide a short summary of the AVISO changes in the PR title.

Examples:
LFBU - Added ground layout
LFBD - Updated apron and stands
LFBA/LFBC - Updated ground layouts
-->

## Description

<!--
Describe the changes made in this pull request.
Include the FIR and ICAO code(s) affected.
-->

**FIR:** `LFXX`  
**Airport(s):** `LFXX`

<!-- Briefly describe what was added, updated, or corrected. -->


## Source / Reference

<!--
Provide the source(s) used to create or update the ground layout.

Examples:
- AIP AD chart
- Official airport chart
- Satellite imagery
- Other official/reliable aeronautical documentation

Include document names, effective dates, AIRAC cycles and/or links where applicable.
-->

**Source:**  
**Effective date / AIRAC:**  


## Changes

<!--
Describe the relevant ground layout changes.
Remove or leave blank any sections which are not applicable.
-->

### Regions

<!--
Runways, taxiways, aprons, buildings, grass areas, unused areas,
CAT I/III areas, backgrounds, etc.
-->


### GEO

<!--
Gate centerlines, intermediate holding points, etc.
-->


### Freetext

<!--
Taxiway labels, stand labels, intermediate holding point labels,
miscellaneous labels, etc.
-->


## Color scheme

<!--
AVISO ground layouts should use the standard colors provided by the
latest QGIS template unless there is a reason for an airport to use
different colors.

Select ONE of the options below.

If NO colors have been changed, select "Standard color scheme" and
leave the table empty.

If ANY colors have been changed, select "Modified color scheme" and
list EVERY modified type and its RGB value in the table below.

RGB values must use the format:
R, G, B

Example:
255, 128, 0

This information may be used when implementing the airport in AeroNav GNG.
-->

- [ ] **Standard color scheme** — no colors have been changed from the QGIS template.
- [ ] **Modified color scheme** — one or more colors differ from the QGIS template.

<!--
Complete this table ONLY when using a modified color scheme.
Add or remove rows as required.
-->

| Layer | Type | RGB |
| --- | --- | --- |
| `REGIONS` | `type` | `R, G, B` |
| `GEO` | `type` | `R, G, B` |
| `FREETEXT` | `type` | `R, G, B` |


## Visual verification

<!--
Include screenshot(s) of the completed ground layout in QGIS.

Screenshots should provide enough context for reviewers to visually
verify the submitted layout against the source material.

If multiple airports are included in this PR, provide screenshots for
each airport.
-->

### QGIS

<!-- Add screenshot(s) of the completed QGIS ground layout here. -->


## Additional information

<!--
Optional.

Add anything reviewers should know that is not obvious from the submitted
files, such as:

- Intentional omissions
- Limitations of available source material
- Unusual airport layouts
- Special handling required
- Known discrepancies
- Reasons for using non-standard colors
-->


## Checklist

<!--
Go over all of the following points and put an `x` in each box that applies.

Example:
- [x] Completed item

If you are unsure about any of these requirements, please ask before
submitting the pull request.
-->

### Ground layout

- [ ] I have used the latest AVISO QGIS template.
- [ ] The ground layout has been checked against an appropriate and current source.
- [ ] The FIR and airport ICAO codes are correct.
- [ ] I have visually checked the completed ground layout for errors.

### Export

- [ ] The required GeoJSON files have been exported to `.exports/QGIS-geoJSON/{FIR}/{ICAO}/`.
- [ ] The GeoJSON filenames follow the `{FIR}_{ICAO}_{FREETEXT|GEO|REGIONS}.geojson` naming convention.
- [ ] The exported GeoJSON files represent the final version of the submitted ground layout.

### Colors

- [ ] I have selected either **Standard color scheme** or **Modified color scheme** above.
- [ ] If colors were modified, I have listed **all** colors that differ from the standard QGIS template and provided their RGB values.

### Review

- [ ] I have included sufficient screenshots and/or reference material for the changes to be reviewed.
- [ ] My changes follow the formatting and contribution standards of the project.

<!--
The automated AVISO validation workflow will check submitted GeoJSON files
under:

.exports/QGIS-geoJSON/{FIR}/{ICAO}/

The validation results and feature counts will be reported automatically
on this pull request.

Files outside .exports/QGIS-geoJSON/ are not part of this GeoJSON
validation.
-->