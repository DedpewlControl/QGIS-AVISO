#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

EXPORT_ROOT = Path(".exports/QGIS-geoJSON")
OUTPUT_ROOT = Path("aviso-preview")
LAYERS = ("REGIONS", "GEO", "FREETEXT")
FILENAME_RE = re.compile(
    r"^(?P<fir>[A-Z]{4})_(?P<icao>[A-Z]{4})_(?P<layer>FREETEXT|GEO|REGIONS)\.geojson$"
)


def changed_airports(args):
    airports = set()
    for arg in args:
        path = Path(arg)
        try:
            rel = path.relative_to(EXPORT_ROOT)
        except ValueError:
            continue

        if len(rel.parts) != 3:
            continue

        fir, icao, filename = rel.parts
        if FILENAME_RE.match(filename):
            airports.add((fir, icao))
    return sorted(airports)


def main():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    airports = changed_airports(sys.argv[1:])

    manifest = []

    for fir, icao in airports:
        merged_features = []
        counts = {}

        # Deliberate draw order:
        # REGIONS = bottom, GEO = middle, FREETEXT = top.
        for z_index, layer in enumerate(LAYERS, start=1):
            path = EXPORT_ROOT / fir / icao / f"{fir}_{icao}_{layer}.geojson"

            if not path.exists():
                continue

            with path.open(encoding="utf-8") as f:
                data = json.load(f)

            features = data.get("features", [])
            counts[layer] = len(features)

            for feature in features:
                feature = dict(feature)
                properties = dict(feature.get("properties") or {})
                properties["_aviso_layer"] = layer
                properties["_aviso_z_index"] = z_index
                feature["properties"] = properties
                merged_features.append(feature)

        out_dir = OUTPUT_ROOT / fir / icao
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{fir}_{icao}_PREVIEW.geojson"

        merged = {
            "type": "FeatureCollection",
            "name": f"{fir}_{icao}_PREVIEW",
            "features": merged_features,
        }

        with out_file.open("w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
            f.write("\n")

        manifest.append({
            "fir": fir,
            "icao": icao,
            "file": out_file.as_posix(),
            "counts": counts,
            "total": len(merged_features),
        })

        print(f"Built {out_file} ({len(merged_features)} features)")

    with (OUTPUT_ROOT / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())