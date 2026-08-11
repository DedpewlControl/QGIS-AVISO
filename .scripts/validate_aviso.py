#!/usr/bin/env python3
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

EXPORT_ROOT = Path(".exports/QGIS-geoJSON")
FILENAME_RE = re.compile(
    r"^(?P<fir>[A-Z]{4})_(?P<icao>[A-Z]{4})_(?P<layer>FREETEXT|GEO|REGIONS)\.geojson$"
)

EXPECTED_GEOMETRY = {
    "FREETEXT": {"Point"},
    "GEO": {"LineString"},
    "REGIONS": {"Polygon"},
}

REQUIRED_FIELDS = {
    "FREETEXT": {"fir", "icao", "type", "freetext", "author"},
    "GEO": {"fir", "icao", "type", "author"},
    "REGIONS": {"fir", "icao", "type", "author"},
}

EXPECTED_FILES = {"FREETEXT", "GEO", "REGIONS"}


def validate_file(path: Path):
    errors = []
    result = {
        "file": path.as_posix(),
        "name": path.name,
        "fir": None,
        "icao": None,
        "layer": None,
        "count": 0,
        "errors": errors,
    }

    try:
        rel = path.relative_to(EXPORT_ROOT)
    except ValueError:
        errors.append(f"File is outside {EXPORT_ROOT.as_posix()}")
        return result

    # Required structure:
    # .exports/QGIS-geoJSON/FIR/ICAO/FIR_ICAO_LAYER.geojson
    if len(rel.parts) != 3:
        errors.append(
            "Invalid path. Expected "
            ".exports/QGIS-geoJSON/{FIR}/{ICAO}/{FIR}_{ICAO}_{TYPE}.geojson"
        )
        return result

    folder_fir, folder_icao, _ = rel.parts

    match = FILENAME_RE.match(path.name)
    if not match:
        errors.append("Invalid filename")
        return result

    file_fir = match.group("fir")
    file_icao = match.group("icao")
    layer = match.group("layer")

    result.update(fir=file_fir, icao=file_icao, layer=layer)

    if folder_fir != file_fir:
        errors.append(
            f"FIR folder is {folder_fir!r}, but filename specifies {file_fir!r}"
        )

    if folder_icao != file_icao:
        errors.append(
            f"Airport folder is {folder_icao!r}, but filename specifies {file_icao!r}"
        )

    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid GeoJSON/JSON: {exc}")
        return result

    if data.get("type") != "FeatureCollection":
        errors.append("Root object must be a FeatureCollection")

    expected_collection_name = f"{file_fir}_{file_icao}_{layer}"
    if data.get("name") not in (None, expected_collection_name):
        errors.append(
            f"Collection name is {data.get('name')!r}, "
            f"expected {expected_collection_name!r}"
        )

    features = data.get("features")
    if not isinstance(features, list):
        errors.append("Missing or invalid 'features' array")
        return result

    result["count"] = len(features)

    for index, feature in enumerate(features, start=1):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            errors.append(f"Feature {index}: invalid GeoJSON Feature")
            continue

        properties = feature.get("properties")
        geometry = feature.get("geometry")

        if not isinstance(properties, dict):
            errors.append(f"Feature {index}: missing/invalid properties")
            continue

        missing = REQUIRED_FIELDS[layer] - set(properties)
        if missing:
            errors.append(
                f"Feature {index}: missing field(s): {', '.join(sorted(missing))}"
            )

        if properties.get("fir") != file_fir:
            errors.append(
                f"Feature {index}: fir={properties.get('fir')!r}; "
                f"expected {file_fir!r}"
            )

        if properties.get("icao") != file_icao:
            errors.append(
                f"Feature {index}: icao={properties.get('icao')!r}; "
                f"expected {file_icao!r}"
            )

        if not properties.get("type"):
            errors.append(f"Feature {index}: type is empty")

        if not properties.get("author"):
            errors.append(f"Feature {index}: author is empty")

        if layer == "FREETEXT" and not properties.get("freetext"):
            errors.append(f"Feature {index}: freetext is empty")

        if not isinstance(geometry, dict):
            errors.append(f"Feature {index}: missing/invalid geometry")
            continue

        geometry_type = geometry.get("type")
        if geometry_type not in EXPECTED_GEOMETRY[layer]:
            expected = ", ".join(sorted(EXPECTED_GEOMETRY[layer]))
            errors.append(
                f"Feature {index}: geometry is {geometry_type!r}; expected {expected}"
            )

    return result


def main():
    paths = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.suffix.lower() == ".geojson" and p.exists():
            paths.append(p)

    if not paths:
        print("## 🗺️ AVISO Ground Layout")
        print()
        print("No changed GeoJSON files found in `.exports/QGIS-geoJSON/`.")
        return 0

    results = [validate_file(path) for path in sorted(set(paths))]
    airports = defaultdict(list)

    for result in results:
        key = (result["fir"] or "UNKNOWN", result["icao"] or "UNKNOWN")
        airports[key].append(result)

    all_errors = []

    print("## 🗺️ AVISO Ground Layout")
    print()

    for (fir, icao), airport_results in sorted(airports.items()):
        print(f"### {icao} ({fir})")
        print()
        print("| File | Features | Status |")
        print("|---|---:|:---:|")

        total = 0
        found_layers = set()

        for result in sorted(
            airport_results, key=lambda r: (r["layer"] or "", r["name"])
        ):
            total += result["count"]
            if result["layer"]:
                found_layers.add(result["layer"])

            status = "❌" if result["errors"] else "✅"
            print(f"| `{result['name']}` | {result['count']} | {status} |")

            for error in result["errors"]:
                all_errors.append(f"`{result['name']}` — {error}")

        print(f"| **Total** | **{total}** | |")
        print()

        # Only require the complete trio when this is a recognisable airport.
        if fir != "UNKNOWN" and icao != "UNKNOWN":
            missing_layers = EXPECTED_FILES - found_layers
            if missing_layers:
                msg = (
                    f"`{fir}/{icao}` — missing AVISO file(s): "
                    + ", ".join(sorted(missing_layers))
                )
                all_errors.append(msg)

    if all_errors:
        print("### ❌ Validation failed")
        print()
        for error in all_errors:
            print(f"- {error}")
        print()
        print(f"**{len(all_errors)} validation issue(s) found.**")
        return 1

    print("### ✅ Validation passed")
    print()
    print("- GeoJSON is valid")
    print("- FIR and ICAO match the folder structure and filenames")
    print("- Expected geometry types are used")
    print("- Required fields are present")
    print("- FREETEXT, GEO and REGIONS files are present for each submitted airport")
    return 0


if __name__ == "__main__":
    sys.exit(main())