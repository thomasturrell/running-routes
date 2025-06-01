import gpxpy
import geopandas as gpd
import contextily as ctx
import matplotlib.pyplot as plt
from shapely.geometry import LineString

# === Settings ===
gpx_file_path = "src/fell/bob-graham-round/bob-graham-round.gpx"  # Change this if your file is named differently
output_image_path = "bob_graham_route_osm_map.png"

# === Parse the GPX file ===
with open(gpx_file_path, 'r') as gpx_file:
    gpx = gpxpy.parse(gpx_file)

points = []
for track in gpx.tracks:
    for segment in track.segments:
        for point in segment.points:
            points.append((point.longitude, point.latitude))  # (lon, lat)

# === Create GeoDataFrame ===
line = LineString(points)
gdf = gpd.GeoDataFrame(geometry=[line], crs="EPSG:4326")
gdf = gdf.to_crs(epsg=3857)  # Web Mercator for OpenStreetMap

# === Plot with OSM basemap ===
fig, ax = plt.subplots(figsize=(10, 10))
gdf.plot(ax=ax, linewidth=2, color="red", zorder=2)
ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, zorder=1)
ax.set_axis_off()
plt.tight_layout()

# === Save the image ===
plt.savefig(output_image_path, dpi=300)
print(f"Saved map to: {output_image_path}")
