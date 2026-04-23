# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.1",
#     "folium>=0.17",
# ]
# ///

import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 郵便番号から地域を調べる

    日本の郵便番号 (7桁) を入力すると、対応する地域を表示します。
    **入力途中でも、その時点で一意に確定する最も詳細な地域まで表示します。**

    データ出典: [日本郵便 郵便番号データダウンロード (ken_all.zip)](https://www.post.japanpost.jp/zipcode/dl/kogaki-zip.html)
    """)
    return


@app.cell
def _():
    import csv
    import io
    import urllib.request
    import zipfile
    from pathlib import Path

    KEN_ALL_URL = "https://www.post.japanpost.jp/zipcode/dl/kogaki/zip/ken_all.zip"
    CACHE_PATH = Path.home() / ".cache" / "marimo-postal" / "ken_all.csv"

    def load_postal_entries():
        if not CACHE_PATH.exists():
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(KEN_ALL_URL) as response:
                payload = response.read()
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                csv_name = next(n for n in archive.namelist() if n.upper().endswith(".CSV"))
                with archive.open(csv_name) as fh:
                    raw_text = fh.read().decode("shift_jis")
            CACHE_PATH.write_text(raw_text, encoding="utf-8")
        else:
            raw_text = CACHE_PATH.read_text(encoding="utf-8")

        rows = []
        for row in csv.reader(io.StringIO(raw_text)):
            if len(row) < 9:
                continue
            zip_code = row[2].strip()
            pref = row[6].strip()
            city = row[7].strip()
            town = row[8].strip()
            rows.append((zip_code, pref, city, town))
        return rows

    entries = load_postal_entries()
    return (entries,)


@app.cell
def _(entries):
    from collections import defaultdict

    prefix_index: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    for zip_code, pref, city, town in entries:
        for i in range(1, len(zip_code) + 1):
            prefix_index[zip_code[:i]].append((zip_code, pref, city, town))
    return (prefix_index,)


@app.cell
def _(mo):
    postal_input = mo.ui.text(
        placeholder="例: 100-0001 / 1000001",
        label="郵便番号",
        max_length=8,
        debounce=1000,
        full_width=True,
    )
    postal_input
    return (postal_input,)


@app.cell
def _(
    mo,
    postal_input,
    prefix_index: dict[str, list[tuple[str, str, str, str]]],
):
    raw = postal_input.value or ""
    digits = "".join(ch for ch in raw if ch.isdigit())[:7]

    def common_prefix(items: list[str]) -> str:
        if not items:
            return ""
        shortest = items[0]
        for item in items[1:]:
            if len(item) < len(shortest):
                shortest = item
        for i, ch in enumerate(shortest):
            if any(item[i] != ch for item in items):
                return shortest[:i]
        return shortest

    if not digits:
        view = mo.md("*郵便番号 (数字) を入力してください。*")
    else:
        matches = prefix_index.get(digits, [])
        display_zip = digits if len(digits) < 4 else f"{digits[:3]}-{digits[3:]}"

        if not matches:
            view = mo.callout(
                mo.md(f"`{display_zip}` に該当する郵便番号は見つかりませんでした。"),
                kind="warn",
            )
        else:
            prefs = sorted({m[1] for m in matches})
            cities = sorted({(m[1], m[2]) for m in matches})
            towns = sorted({(m[1], m[2], m[3]) for m in matches})
            full_addrs = [m[1] + m[2] + m[3] for m in matches]
            determined = common_prefix(full_addrs)

            pref_text = prefs[0] if len(prefs) == 1 else f"— ({len(prefs)} 都道府県の候補)"
            city_text = (
                "".join(cities[0]) if len(cities) == 1 else f"— ({len(cities):,} 市区町村の候補)"
            )
            town_text = "".join(towns[0]) if len(towns) == 1 else f"— ({len(towns):,} 町域の候補)"

            if len(digits) == 7 and len(towns) == 1:
                status = "完全一致しました。"
            else:
                remaining = 7 - len(digits)
                status = (
                    f"現在 **{len(matches):,}** 件の候補があります。"
                    f"残り {remaining} 桁で絞り込めます。"
                )

            view = mo.vstack(
                [
                    mo.md(f"### `{display_zip}`"),
                    mo.md(f"**確定している地域**: {determined or '(まだ確定していません)'}"),
                    mo.md(
                        "| 区分 | 値 |\n"
                        "|---|---|\n"
                        f"| 都道府県 | {pref_text} |\n"
                        f"| 市区町村 | {city_text} |\n"
                        f"| 町域 | {town_text} |\n"
                    ),
                    mo.md(status),
                ]
            )
    view
    return


@app.cell
def _():
    import hashlib
    import json as geojson_json
    import pathlib as _pathlib
    import time
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    NOMINATIM_CACHE = _pathlib.Path.home() / ".cache" / "marimo-postal" / "nominatim"
    USER_AGENT = "marimo-postal-demo/1.0 (+https://github.com/marimo-team)"

    def geocode_region(query: str) -> dict | None:
        NOMINATIM_CACHE.mkdir(parents=True, exist_ok=True)
        cache_key = hashlib.md5(query.encode("utf-8")).hexdigest()
        cache_file = NOMINATIM_CACHE / f"{cache_key}.json"
        if cache_file.exists():
            return geojson_json.loads(cache_file.read_text(encoding="utf-8"))

        url = "https://nominatim.openstreetmap.org/search?" + urlencode(
            {
                "q": query,
                "format": "jsonv2",
                "limit": "1",
                "polygon_geojson": "1",
                "countrycodes": "jp",
                "accept-language": "ja",
            }
        )
        request = Request(url, headers={"User-Agent": USER_AGENT})
        time.sleep(1.0)
        with urlopen(request, timeout=20) as response:
            payload = geojson_json.loads(response.read())
        result = payload[0] if payload else None
        cache_file.write_text(
            geojson_json.dumps(result, ensure_ascii=False),
            encoding="utf-8",
        )
        return result

    return (geocode_region,)


@app.cell
def _(
    geocode_region,
    mo,
    postal_input,
    prefix_index: dict[str, list[tuple[str, str, str, str]]],
):
    import folium

    raw_m = postal_input.value or ""
    digits_m = "".join(ch for ch in raw_m if ch.isdigit())[:7]
    matches_m = prefix_index.get(digits_m, []) if digits_m else []

    MAX_REGIONS = 20

    display_queries: list[tuple[str, str]] = []
    level_label = "日本全体"
    if matches_m:
        prefs_set = sorted({m[1] for m in matches_m})
        cities_set = sorted({(m[1], m[2]) for m in matches_m})
        towns_set = sorted({(m[1], m[2], m[3]) for m in matches_m})
        if len(towns_set) <= MAX_REGIONS:
            display_queries = [(p + c + t, f"{t}, {c}, {p}, Japan") for p, c, t in towns_set]
            level_label = f"町域 {len(towns_set)} 件"
        elif len(cities_set) <= MAX_REGIONS:
            display_queries = [(p + c, f"{c}, {p}, Japan") for p, c in cities_set]
            level_label = f"市区町村 {len(cities_set)} 件"
        else:
            display_queries = [(p, f"{p}, Japan") for p in prefs_set]
            level_label = f"都道府県 {len(prefs_set)} 件"

    fmap = folium.Map(
        location=[36.0, 138.0],
        zoom_start=5,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    def _style(_feature: dict) -> dict:
        return {
            "color": "#1f77b4",
            "weight": 2,
            "fillColor": "#1f77b4",
            "fillOpacity": 0.25,
        }

    bounds_points: list[tuple[float, float]] = []
    drawn = 0
    for region_label, query in display_queries:
        result = geocode_region(query)
        if not result:
            continue
        geom = result.get("geojson") or {}
        if geom.get("type") in ("Polygon", "MultiPolygon"):
            folium.GeoJson(
                geom,
                name=region_label,
                tooltip=region_label,
                style_function=_style,
            ).add_to(fmap)
            bbox = result.get("boundingbox")
            if bbox and len(bbox) == 4:
                south, north, west, east = (float(v) for v in bbox)
                bounds_points.extend([(south, west), (north, east)])
            drawn += 1
        elif result.get("lat") and result.get("lon"):
            lat = float(result["lat"])
            lon = float(result["lon"])
            folium.Marker([lat, lon], tooltip=region_label).add_to(fmap)
            bounds_points.append((lat, lon))
            drawn += 1

    if bounds_points:
        lats = [p[0] for p in bounds_points]
        lons = [p[1] for p in bounds_points]
        fmap.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])

    map_header = mo.md(
        f"#### 地図: {level_label} ({drawn}/{len(display_queries)} 件の境界を描画)"
        if display_queries
        else "#### 地図: 日本全体"
    )
    mo.vstack([map_header, mo.Html(fmap._repr_html_())])
    return


@app.cell
def _(
    mo,
    postal_input,
    prefix_index: dict[str, list[tuple[str, str, str, str]]],
):
    raw_in = postal_input.value or ""
    digits_in = "".join(ch for ch in raw_in if ch.isdigit())[:7]

    matches_for_table = prefix_index.get(digits_in, []) if digits_in else []
    preview_limit = 30
    preview_rows = [
        {
            "郵便番号": f"{m[0][:3]}-{m[0][3:]}",
            "都道府県": m[1],
            "市区町村": m[2],
            "町域": m[3],
        }
        for m in matches_for_table[:preview_limit]
    ]

    if preview_rows:
        label = (
            f"一致する郵便番号 (先頭 {len(preview_rows)} 件 / 全 {len(matches_for_table):,} 件)"
            if len(matches_for_table) > preview_limit
            else f"一致する郵便番号 ({len(matches_for_table):,} 件)"
        )
        preview = mo.ui.table(preview_rows, label=label, selection=None)
    else:
        preview = mo.md("")
    preview
    return


if __name__ == "__main__":
    app.run()
