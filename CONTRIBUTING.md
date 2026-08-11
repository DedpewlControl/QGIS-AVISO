![alt text](https://raw.githubusercontent.com/DedpewlControl/QGIS-AVISO/refs/heads/main/.github/img/vaccfr_nav_ops_qgis_aviso_banner.jpg "French vACC QGIS AVISO Project Banner")


# Contributing

Thank you for contributing to the French vACC QGIS AVISO Project.

This repository uses QGIS as the source for AVISO ground layouts. Contributors should make changes to the QGIS source data and export the required GeoJSON files for submission through a pull request.

The AeroNav GNG `.sct` and `.ese` files are generated automatically after a pull request is merged and must not be edited manually.

## Repository Structure

AVISO GeoJSON exports are stored under:

```text
.exports/QGIS-geoJSON/
└── {FIR}/
    └── {ICAO}/
        ├── {FIR}_{ICAO}_FREETEXT.geojson
        ├── {FIR}_{ICAO}_GEO.geojson
        └── {FIR}_{ICAO}_REGIONS.geojson
```

For example:

```text
.exports/QGIS-geoJSON/
└── LFBB/
    └── LFBU/
        ├── LFBB_LFBU_FREETEXT.geojson
        ├── LFBB_LFBU_GEO.geojson
        └── LFBB_LFBU_REGIONS.geojson
```

Generated AeroNav GNG files are stored separately under:

```text
.exports/AeroNav-GNG/
└── {FIR}/
    └── {ICAO}/
        ├── {FIR}_{ICAO}.sct
        └── {FIR}_{ICAO}.ese
```

Do **not** manually modify files under `.exports/AeroNav-GNG/`.

## Creating or Updating an AVISO

AVISO ground layouts should be created using the provided QGIS template.

For a new airport:

1. Copy the QGIS template GeoPackage files.
2. Rename them for the appropriate FIR and airport ICAO.
3. Load them into QGIS.
4. Create or update the required ground layout.
5. Export the completed layers as GeoJSON.
6. Place the exported files in the appropriate FIR/ICAO directory under `.exports/QGIS-geoJSON/`.
7. Submit the changes through a pull request.

For an existing airport, update the existing QGIS data and replace the relevant exported GeoJSON files.

## AVISO Layers

Each airport consists of three exported datasets.

### REGIONS

`REGIONS` contains the polygon features forming the ground layout.

Examples include:

- Background
- Taxiways
- Grass
- Unused surfaces
- Runways
- Grass taxiways
- Grass runways
- CAT I areas
- CAT III areas
- Aprons
- Buildings

The `type` field determines how each feature is interpreted and converted.

### GEO

`GEO` contains line features used by the ground layout.

Currently supported types include:

- Gate centerlines
- Intermediate Holding Points (IHP)

### FREETEXT

`FREETEXT` contains text labels and their positions.

Examples include:

- Taxiway identifiers
- Holding point identifiers
- Gate identifiers
- Other ground layout labels

## File Naming

Files must use the following naming convention:

```text
{FIR}_{ICAO}_{LAYER}.geojson
```

where `LAYER` is one of:

```text
FREETEXT
GEO
REGIONS
```

For example:

```text
LFBB_LFBU_FREETEXT.geojson
LFBB_LFBU_GEO.geojson
LFBB_LFBU_REGIONS.geojson
```

The FIR and ICAO contained in the GeoJSON feature properties must match the directory and filename.

## Exporting from QGIS

When the AVISO is complete, export each required layer as GeoJSON.

The resulting files must be placed under:

```text
.exports/QGIS-geoJSON/{FIR}/{ICAO}/
```

Do not export directly into `.exports/AeroNav-GNG/`.

Before committing your changes, check that:

- the correct FIR is used;
- the correct airport ICAO is used;
- all required layers are present;
- features have the correct `type`;
- FREETEXT features contain the correct text;
- geometries have not accidentally been moved or modified;
- no temporary QGIS files have been committed.

## Pull Requests

All AVISO additions and modifications should normally be submitted through a pull request.

The pull request should clearly explain:

- which FIR is affected;
- which airport(s) are affected;
- what has been added or changed;
- why the change is required;
- the source/reference used for the change;
- the applicable AIRAC or effective date, where relevant.

Screenshots from QGIS should be included where they help reviewers understand or verify the change.

If non-standard colours have intentionally been used, document the changed feature types and their RGB values in the pull request.

## Automated Validation

When a pull request modifies files under:

```text
.exports/QGIS-geoJSON/
```

the AVISO validation workflow automatically checks the affected airport data.

The validation includes checks for the expected:

- directory structure;
- filenames;
- FIR and ICAO values;
- GeoJSON structure;
- geometry types;
- required fields;
- FREETEXT, GEO and REGIONS files.

The workflow also reports the number of features contained in each file.

A pull request should not be merged while AVISO validation is failing.

## After a Pull Request Is Merged

Once an AVISO pull request is merged into `main`, a separate GitHub Actions workflow automatically converts the affected airport data for AeroNav GNG.

The conversion produces:

```text
.exports/AeroNav-GNG/{FIR}/{ICAO}/{FIR}_{ICAO}.sct
.exports/AeroNav-GNG/{FIR}/{ICAO}/{FIR}_{ICAO}.ese
```

The generated `.sct` contains the:

```text
[REGIONS]
[GEO]
```

sections.

The generated `.ese` contains:

```text
[FREETEXT]
```

These files are generated from the approved GeoJSON source data and committed automatically.

Contributors therefore **must not manually create or modify the generated `.sct` or `.ese` files**.

## Sources and Accuracy

AVISO layouts should be based on reliable and current information.

Where possible, use official sources such as:

- the French AIP;
- AIP amendments;
- official aerodrome charts;
- NOTAMs;
- official airport documentation.

Other sources, such as current satellite imagery, may be useful for additional verification.

The source used for a significant change should be identified in the pull request.

## AIRAC Changes

Where a change is associated with an AIRAC cycle, include the applicable cycle or effective date in the pull request.

Do not introduce a future aeronautical change early unless this has been specifically agreed.

## Issues

If you identify an incorrect or outdated AVISO but are unable to submit the change yourself, open an AVISO issue.

Please include:

- FIR;
- airport ICAO;
- description of the issue;
- affected feature(s);
- supporting source/reference;
- applicable AIRAC or effective date, if relevant.

## Questions

If you are unsure about the required QGIS structure, feature type, source material, or export process, ask before submitting large changes.

This helps keep the AVISO source data consistent and avoids unnecessary rework.