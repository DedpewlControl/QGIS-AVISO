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

LAYERS = ("FREETEXT", "GEO", "REGIONS")


def airport_from_changed_path(path: Path):
    try:
        rel = path.relative_to(EXPORT_ROOT)
    except ValueError:
        return None

    if len(rel.parts) != 3:
        return None

    folder_fir, folder_icao, filename = rel.parts
    match = FILENAME_RE.match(filename)
    if not match:
        return (folder_fir, folder_icao)

    return (match.group("fir"), match.group("icao"))


def validate_file(path: Path, expected_fir: str, expected_icao: str, layer: str):
    errors = []
    result = {
        "file": path.as_posix(),
        "name": path.name,
        "fir": expected_fir,
        "icao": expected_icao,
        "layer": layer,
        "count": 0,
        "errors": errors,
    }

    expected_name = f"{expected_fir}_{expected_icao}_{layer}.geojson"

    if path.name != expected_name:
        errors.append(f"Filename is {path.name!r}; expected {expected_name!r}")

    if not path.exists():
        errors.append("Required AVISO file is missing")
        return result

    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid GeoJSON/JSON: {exc}")
        return result

    if data.get("type") != "FeatureCollection":
        errors.append("Root object must be a FeatureCollection")

    expected_collection_name = f"{expected_fir}_{expected_icao}_{layer}"
    if data.get("name") not in (None, expected_collection_name):
        errors.append(
            f"Collection name is {data.get('name')!r}; "
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

        if properties.get("fir") != expected_fir:
            errors.append(
                f"Feature {index}: fir={properties.get('fir')!r}; "
                f"expected {expected_fir!r}"
            )

        if properties.get("icao") != expected_icao:
            errors.append(
                f"Feature {index}: icao={properties.get('icao')!r}; "
                f"expected {expected_icao!r}"
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
    changed = [Path(arg) for arg in sys.argv[1:] if arg.lower().endswith(".geojson")]

    airports = set()
    path_errors = []

    for path in changed:
        airport = airport_from_changed_path(path)
        if airport is None:
            continue
        fir, icao = airport
        if not re.fullmatch(r"[A-Z]{4}", fir or "") or not re.fullmatch(r"[A-Z]{4}", icao or ""):
            path_errors.append(
                f"`{path.as_posix()}` — invalid path; expected "
                ".exports/QGIS-geoJSON/{FIR}/{ICAO}/{FIR}_{ICAO}_{TYPE}.geojson"
            )
            continue
        airports.add((fir, icao))

    print("## 🗺️ AVISO Ground Layout")
    print()

    if not airports:
        print("No changed airport GeoJSON files found in `.exports/QGIS-geoJSON/`.")
        if path_errors:
            print()
            print("### ❌ Validation failed")
            for error in path_errors:
                print(f"- {error}")
            return 1
        return 0

    all_errors = list(path_errors)

    for fir, icao in sorted(airports):
        results = []
        for layer in LAYERS:
            path = EXPORT_ROOT / fir / icao / f"{fir}_{icao}_{layer}.geojson"
            results.append(validate_file(path, fir, icao, layer))

        print(f"### {icao} ({fir})")
        print()
        print("| File | Features | Status |")
        print("|---|---:|:---:|")

        total = 0
        for result in results:
            total += result["count"]
            status = "❌" if result["errors"] else "✅"
            print(f"| `{result['name']}` | {result['count']} | {status} |")
            for error in result["errors"]:
                all_errors.append(f"`{result['name']}` — {error}")

        print(f"| **Total** | **{total}** | |")
        print()

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
    print("- FREETEXT, GEO and REGIONS are present for each changed airport")
    return 0


if __name__ == "__main__":
    sys.exit(main())