#!/usr/bin/env python3
import json
import re
import sys
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


def airport_from_path(path: Path):
    try:
        rel = path.relative_to(EXPORT_ROOT)
    except ValueError:
        return None

    # Expected:
    # .exports/QGIS-geoJSON/{FIR}/{ICAO}/{FIR}_{ICAO}_{TYPE}.geojson
    if len(rel.parts) != 3:
        return None

    fir, icao, filename = rel.parts

    if not re.fullmatch(r"[A-Z]{4}", fir):
        return None
    if not re.fullmatch(r"[A-Z]{4}", icao):
        return None

    match = FILENAME_RE.match(filename)
    if not match:
        return (fir, icao)

    return (fir, icao)


def validate_file(path: Path, fir: str, icao: str, layer: str):
    errors = []

    result = {
        "name": path.name,
        "path": path.as_posix(),
        "fir": fir,
        "icao": icao,
        "layer": layer,
        "count": 0,
        "errors": errors,
    }

    expected_filename = f"{fir}_{icao}_{layer}.geojson"

    if path.name != expected_filename:
        errors.append(
            f"Filename is {path.name!r}; expected {expected_filename!r}"
        )

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

    expected_collection_name = f"{fir}_{icao}_{layer}"
    collection_name = data.get("name")
    if collection_name not in (None, expected_collection_name):
        errors.append(
            f"Collection name is {collection_name!r}; "
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
                f"Feature {index}: missing field(s): "
                + ", ".join(sorted(missing))
            )

        if properties.get("fir") != fir:
            errors.append(
                f"Feature {index}: fir={properties.get('fir')!r}; "
                f"expected {fir!r}"
            )

        if properties.get("icao") != icao:
            errors.append(
                f"Feature {index}: icao={properties.get('icao')!r}; "
                f"expected {icao!r}"
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
                f"Feature {index}: geometry is {geometry_type!r}; "
                f"expected {expected}"
            )

    return result


def main():
    changed_paths = [
        Path(arg)
        for arg in sys.argv[1:]
        if arg.lower().endswith(".geojson")
    ]

    airports = set()
    invalid_paths = []

    for path in changed_paths:
        airport = airport_from_path(path)

        if airport is None:
            invalid_paths.append(
                f"`{path.as_posix()}` — invalid path; expected "
                ".exports/QGIS-geoJSON/{FIR}/{ICAO}/{FIR}_{ICAO}_{TYPE}.geojson"
            )
            continue

        airports.add(airport)

    print("## 🗺️ AVISO Ground Layout")
    print()

    if not airports and not invalid_paths:
        print("No changed AVISO GeoJSON files found.")
        return 0

    all_errors = list(invalid_paths)

    for fir, icao in sorted(airports):
        print(f"### {icao} ({fir})")
        print()
        print("| File | Features | Status |")
        print("|---|---:|:---:|")

        total = 0
        results = []

        for layer in LAYERS:
            path = EXPORT_ROOT / fir / icao / f"{fir}_{icao}_{layer}.geojson"
            result = validate_file(path, fir, icao, layer)
            results.append(result)

            total += result["count"]
            status = "❌" if result["errors"] else "✅"

            print(
                f"| `{result['name']}` | "
                f"{result['count']} | {status} |"
            )

        print(f"| **Total** | **{total}** | |")
        print()

        for result in results:
            for error in result["errors"]:
                all_errors.append(
                    f"`{result['name']}` — {error}"
                )

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