#!/usr/bin/env python3
"""
Convert merged AVISO QGIS GeoJSON data into AeroNav GNG sector snippets.

Source structure:
    .exports/QGIS-geoJSON/{FIR}/{ICAO}/
        {FIR}_{ICAO}_REGIONS.geojson
        {FIR}_{ICAO}_GEO.geojson
        {FIR}_{ICAO}_FREETEXT.geojson

Output structure:
    .exports/AeroNav-GNG/{FIR}/{ICAO}/
        {FIR}_{ICAO}.sct
        {FIR}_{ICAO}.ese

The workflow passes the paths changed by the merged pull request. The converter
derives the affected FIR/ICAO pairs from those paths and rebuilds the complete
airport output from the three source GeoJSON files now present on the base
branch.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence


SOURCE_ROOT = Path(".exports/QGIS-geoJSON")
OUTPUT_ROOT = Path(".exports/AeroNav-GNG")
REGION_CATEGORY = "AVISO"

SOURCE_RE = re.compile(
    r"^(?P<fir>[A-Z]{4})_(?P<icao>[A-Z]{4})_"
    r"(?P<kind>REGIONS|GEO|FREETEXT)\.geojson$"
)

EXPECTED_FILES = ("REGIONS", "GEO", "FREETEXT")


# ---------------------------------------------------------------------------
# AeroNav / EuroScope colour identifiers
# ---------------------------------------------------------------------------
#
# The new GeoJSON schema stores semantic `type` values instead of a `color`
# property. These mappings turn those types into stable colour identifiers
# for the generated SCT/ESE files.
#
# Keep the identifiers here aligned with the colour definitions configured
# in AeroNav GNG.
#

REGION_COLORS = {
    "background": "COLOR_AoRground1",
    "taxiway": "COLOR_HardSurface2",
    "grass": "COLOR_GrasSurface",
    "unused": "COLOR_HardSurface4",
    "runway": "COLOR_RunwayConcrete",
    "grass_taxiway": "COLOR_GrasSurface2",
    "grass_runway": "COLOR_RunwayGrass",
    "ihp": "COLOR_TaxiwayOrange",
    "cati": "COLOR_Stopbar",
    "catiii": "COLOR_TaxiwayOrange",
    "apron": "COLOR_HardSurface3",
    "building": "COLOR_Building",
}

GEO_COLORS = {
    "twy_centerline": "COLOR_Taxiway",
    "orange": "COLOR_TaxiwayOrange",
    "blue": "COLOR_TaxiwayBlue",
    "direction_red": "COLOR_TaxiwayBrown",
    "direction_green": "COLOR_TaxiwayGreen",
    "direction_yellow": "COLOR_Taxiway",
    "gate_centerline": "COLOR_Taxiway",
    "gate_unused": "COLOR_ParkPosUnused",
}


@dataclass(frozen=True, order=True)
class Airport:
    fir: str
    icao: str

    @property
    def source_dir(self) -> Path:
        return SOURCE_ROOT / self.fir / self.icao

    @property
    def output_dir(self) -> Path:
        return OUTPUT_ROOT / self.fir / self.icao

    def source_file(self, kind: str) -> Path:
        return self.source_dir / f"{self.fir}_{self.icao}_{kind}.geojson"

    @property
    def sct_file(self) -> Path:
        return self.output_dir / f"{self.fir}_{self.icao}.sct"

    @property
    def ese_file(self) -> Path:
        return self.output_dir / f"{self.fir}_{self.icao}.ese"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert affected AVISO GeoJSON airports to SCT/ESE."
    )
    parser.add_argument(
        "changed_paths",
        nargs="*",
        help=(
            "Paths changed by the merged PR. Only paths beneath "
            ".exports/QGIS-geoJSON are considered."
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Rebuild every airport found beneath .exports/QGIS-geoJSON.",
    )
    return parser.parse_args()


def airport_from_path(path: Path) -> Airport | None:
    try:
        relative = path.relative_to(SOURCE_ROOT)
    except ValueError:
        return None

    if len(relative.parts) != 3:
        return None

    fir_dir, icao_dir, filename = relative.parts

    if not re.fullmatch(r"[A-Z]{4}", fir_dir):
        return None
    if not re.fullmatch(r"[A-Z]{4}", icao_dir):
        return None

    match = SOURCE_RE.match(filename)

    # A deleted or renamed source file may no longer match the ideal filename,
    # but the directory still tells us which airport output needs refreshing.
    if match is None:
        return Airport(fir_dir, icao_dir)

    if match.group("fir") != fir_dir or match.group("icao") != icao_dir:
        raise ValueError(
            f"{path}: filename FIR/ICAO does not match its folder structure"
        )

    return Airport(fir_dir, icao_dir)


def discover_all_airports() -> list[Airport]:
    airports: set[Airport] = set()

    if not SOURCE_ROOT.exists():
        return []

    for path in SOURCE_ROOT.glob("*/*/*.geojson"):
        airport = airport_from_path(path)
        if airport:
            airports.add(airport)

    return sorted(airports)


def affected_airports(paths: Iterable[str]) -> list[Airport]:
    airports: set[Airport] = set()

    for raw_path in paths:
        path = Path(raw_path)
        airport = airport_from_path(path)
        if airport:
            airports.add(airport)

    return sorted(airports)


def load_feature_collection(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc

    if data.get("type") != "FeatureCollection":
        raise ValueError(f"{path}: root object must be a FeatureCollection")

    features = data.get("features")
    if not isinstance(features, list):
        raise ValueError(f"{path}: missing or invalid features array")

    return data


def validate_airport_identity(
    airport: Airport,
    kind: str,
    feature: dict,
    index: int,
) -> dict:
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        raise ValueError(
            f"{airport.fir}/{airport.icao} {kind} feature {index}: "
            "missing properties"
        )

    if properties.get("fir") != airport.fir:
        raise ValueError(
            f"{airport.fir}/{airport.icao} {kind} feature {index}: "
            f"fir={properties.get('fir')!r}, expected {airport.fir!r}"
        )

    if properties.get("icao") != airport.icao:
        raise ValueError(
            f"{airport.fir}/{airport.icao} {kind} feature {index}: "
            f"icao={properties.get('icao')!r}, expected {airport.icao!r}"
        )

    if not properties.get("type"):
        raise ValueError(
            f"{airport.fir}/{airport.icao} {kind} feature {index}: "
            "missing type"
        )

    return properties


def decimal_to_dms(value: float, axis: str) -> str:
    """
    Convert decimal degrees to EuroScope-style DMS.

    Latitude:  N45.43.41.717
    Longitude: E000.13.00.831
    """
    if axis == "lat":
        hemisphere = "N" if value >= 0 else "S"
        degree_width = 2
    elif axis == "lon":
        hemisphere = "E" if value >= 0 else "W"
        degree_width = 3
    else:
        raise ValueError(f"Unknown coordinate axis: {axis}")

    absolute = abs(float(value))
    degrees = int(absolute)
    minutes_float = (absolute - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60

    # Guard against floating-point rounding producing 60.000 seconds.
    seconds = round(seconds, 3)
    if seconds >= 60:
        seconds = 0.0
        minutes += 1
    if minutes >= 60:
        minutes = 0
        degrees += 1

    return (
        f"{hemisphere}{degrees:0{degree_width}d}."
        f"{minutes:02d}.{seconds:06.3f}"
    )


def format_vertex(coord: Sequence[float]) -> tuple[str, str]:
    if len(coord) < 2:
        raise ValueError(f"Invalid coordinate: {coord!r}")

    lon = float(coord[0])
    lat = float(coord[1])

    return decimal_to_dms(lat, "lat"), decimal_to_dms(lon, "lon")


def consecutive_pairs(points: Sequence[Sequence[float]]) -> Iterator[
    tuple[Sequence[float], Sequence[float]]
]:
    for index in range(len(points) - 1):
        yield points[index], points[index + 1]


def lines_from_geometry(geometry: dict) -> list[list[Sequence[float]]]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")

    if geometry_type == "LineString":
        return [coordinates]
    if geometry_type == "MultiLineString":
        return coordinates

    raise ValueError(f"Expected LineString/MultiLineString, got {geometry_type!r}")


def polygons_from_geometry(
    geometry: dict,
) -> list[list[list[Sequence[float]]]]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")

    if geometry_type == "Polygon":
        return [coordinates]
    if geometry_type == "MultiPolygon":
        return coordinates

    raise ValueError(f"Expected Polygon/MultiPolygon, got {geometry_type!r}")


def region_name(airport: Airport, feature: dict, polygon_index: int) -> str:
    props = feature.get("properties") or {}
    fid = props.get("fid", polygon_index)
    type_name = str(props.get("type", "region")).upper()
    return f"{airport.icao}_{type_name}_{fid}"


def write_sct(
    airport: Airport,
    regions_data: dict,
    geo_data: dict,
) -> tuple[int, int, int]:
    """Write REGIONS and GEO into the airport SCT file."""
    polygon_count = 0
    vertex_count = 0
    geo_segment_count = 0

    lines: list[str] = [
        f"; Auto-generated AVISO ground layout for {airport.icao} ({airport.fir})",
        "; Do not edit manually.",
        "",
        "[REGIONS]",
    ]

    # REGIONS are written first.
    for feature_index, feature in enumerate(regions_data["features"], start=1):
        props = validate_airport_identity(
            airport, "REGIONS", feature, feature_index
        )
        type_name = str(props["type"])
        color = REGION_COLORS.get(type_name)

        if color is None:
            raise ValueError(
                f"{airport.fir}/{airport.icao} REGIONS feature {feature_index}: "
                f"unsupported type {type_name!r}"
            )

        geometry = feature.get("geometry") or {}

        for polygon in polygons_from_geometry(geometry):
            if not polygon:
                continue

            # SCT REGIONS use the exterior ring.
            exterior = polygon[0]
            if not isinstance(exterior, list) or len(exterior) < 3:
                raise ValueError(
                    f"{airport.fir}/{airport.icao} REGIONS feature "
                    f"{feature_index}: polygon has too few vertices"
                )

            vertices = list(exterior)

            # GeoJSON polygon rings normally repeat the first vertex at the end.
            if len(vertices) > 1 and vertices[0][:2] == vertices[-1][:2]:
                vertices.pop()

            if len(vertices) < 3:
                raise ValueError(
                    f"{airport.fir}/{airport.icao} REGIONS feature "
                    f"{feature_index}: polygon has too few unique vertices"
                )

            # No REGIONNAME line: AeroNav GNG adds region names during package export.
            lines.append(color)

            for vertex in vertices:
                lat, lon = format_vertex(vertex)
                lines.append(f"{lat} {lon}")
                vertex_count += 1

            lines.append("")
            polygon_count += 1

    lines.append("[GEO]")

    for feature_index, feature in enumerate(geo_data["features"], start=1):
        props = validate_airport_identity(
            airport, "GEO", feature, feature_index
        )
        type_name = str(props["type"])
        color = GEO_COLORS.get(type_name)

        if color is None:
            raise ValueError(
                f"{airport.fir}/{airport.icao} GEO feature {feature_index}: "
                f"unsupported type {type_name!r}"
            )

        geometry = feature.get("geometry") or {}

        for line in lines_from_geometry(geometry):
            if not isinstance(line, list) or len(line) < 2:
                raise ValueError(
                    f"{airport.fir}/{airport.icao} GEO feature "
                    f"{feature_index}: line has fewer than two vertices"
                )

            for start_vertex, end_vertex in consecutive_pairs(line):
                start_lat, start_lon = format_vertex(start_vertex)
                end_lat, end_lon = format_vertex(end_vertex)
                lines.append(
                    f"{start_lat} {start_lon} "
                    f"{end_lat} {end_lon} {color}"
                )
                geo_segment_count += 1

    airport.sct_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return polygon_count, vertex_count, geo_segment_count


def write_ese(airport: Airport, freetext_data: dict) -> int:
    """
    Write labels/freetext into the airport ESE file.

    The old source script called these "labels". In EuroScope ESE they belong
    under [FREETEXT], using:
        latitude:longitude:text
    """
    label_count = 0

    lines: list[str] = [
        f"; Auto-generated AVISO ground-layout freetext for {airport.icao} ({airport.fir})",
        "; Do not edit manually.",
        "",
        "[FREETEXT]",
    ]

    for feature_index, feature in enumerate(
        freetext_data["features"], start=1
    ):
        props = validate_airport_identity(
            airport, "FREETEXT", feature, feature_index
        )

        text_value = props.get("freetext")
        if text_value is None or str(text_value).strip() == "":
            raise ValueError(
                f"{airport.fir}/{airport.icao} FREETEXT feature "
                f"{feature_index}: missing freetext"
            )

        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Point":
            raise ValueError(
                f"{airport.fir}/{airport.icao} FREETEXT feature "
                f"{feature_index}: expected Point, got "
                f"{geometry.get('type')!r}"
            )

        lat, lon = format_vertex(geometry["coordinates"])
        safe_text = str(text_value).replace(":", " ")

        # AeroNav GNG handles grouping during package export.
        lines.append(f"{lat}:{lon}:{safe_text}")
        label_count += 1

    airport.ese_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return label_count


def remove_output_for_deleted_airport(airport: Airport) -> None:
    if airport.output_dir.exists():
        shutil.rmtree(airport.output_dir)
        print(
            f"Removed {airport.output_dir} because the source airport "
            "no longer exists."
        )


def convert_airport(airport: Airport) -> None:
    source_files = {
        kind: airport.source_file(kind)
        for kind in EXPECTED_FILES
    }

    present = [path.exists() for path in source_files.values()]

    if not any(present):
        remove_output_for_deleted_airport(airport)
        return

    missing = [
        kind
        for kind, path in source_files.items()
        if not path.exists()
    ]
    if missing:
        raise FileNotFoundError(
            f"{airport.fir}/{airport.icao}: source airport is incomplete; "
            f"missing {', '.join(missing)}"
        )

    regions = load_feature_collection(source_files["REGIONS"])
    geo = load_feature_collection(source_files["GEO"])
    freetext = load_feature_collection(source_files["FREETEXT"])

    airport.output_dir.mkdir(parents=True, exist_ok=True)
    polygon_count, vertex_count, geo_segments = write_sct(
        airport, regions, geo
    )
    label_count = write_ese(airport, freetext)

    print(
        f"{airport.fir}/{airport.icao}: "
        f"{geo_segments} GEO segment(s), "
        f"{label_count} label(s), "
        f"{polygon_count} region polygon(s), "
        f"{vertex_count} region vertex/vertices"
    )
    print(f"  -> {airport.sct_file}")
    print(f"  -> {airport.ese_file}")


def main() -> int:
    args = parse_args()

    airports = (
        discover_all_airports()
        if args.all
        else affected_airports(args.changed_paths)
    )

    if not airports:
        print("No affected AVISO airports found.")
        return 0

    print(f"Converting {len(airports)} airport(s)...")

    try:
        for airport in airports:
            convert_airport(airport)
    except (FileNotFoundError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
