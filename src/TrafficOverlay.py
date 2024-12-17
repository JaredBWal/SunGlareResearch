import os
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from geopy.distance import geodesic

# Function to check if the 'segmentProbeCounts' is a JSON string and parse it
def get_probe_count(segment):
    if isinstance(segment['segmentProbeCounts'], str):
        try:
            segment['segmentProbeCounts'] = json.loads(segment['segmentProbeCounts'])
        except json.JSONDecodeError:
            return "N/A"
    
    if isinstance(segment['segmentProbeCounts'], list) and segment['segmentProbeCounts']:
        return segment['segmentProbeCounts'][0].get('probeCount', "N/A")
    
    return "N/A"  # Return "N/A" if it's not a valid list or has no items

# Preprocess sun glare data into a more efficient lookup form
def preprocess_sun_glare_data(sun_glare_df):
    # Create a GeoDataFrame for spatial queries
    sun_glare_df = sun_glare_df[['lat', 'long', 'has_sun_glare']]
    sun_glare_gdf = gpd.GeoDataFrame(sun_glare_df, 
                                     geometry=gpd.points_from_xy(sun_glare_df['long'], sun_glare_df['lat']),
                                     crs="EPSG:4326")  # WGS 84 coordinate system (degree-based)
    
    # Reproject to EPSG:3857 (meters) for accurate buffer distance calculations
    sun_glare_gdf = sun_glare_gdf.to_crs("EPSG:3857")
    return sun_glare_gdf

# Function to check for sun glare efficiently using spatial indexing
def segment_has_glare(segment_coords, sun_glare_gdf):
    # Convert segment coordinates into a GeoDataFrame
    segment_gdf = gpd.GeoDataFrame(geometry=[LineString(segment_coords)], crs="EPSG:4326")
    
    # Reproject to EPSG:3857 (meters)
    segment_gdf = segment_gdf.to_crs("EPSG:3857")
    
    # Create a buffer around the segment geometry (10 meters)
    buffer = segment_gdf.geometry.buffer(10)  # 10 meters buffer
    
    # Spatial query to find which sun glare points are within the buffer
    buffered_gdf = sun_glare_gdf[sun_glare_gdf.geometry.within(buffer.iloc[0])]
     
    return not buffered_gdf.empty  # Return True if glare exists, False otherwise

# Function to get coordinates from the segment
def get_coordinate_from_segment(segment):
    if 'geometry' in segment and segment['geometry'] is not None:
        print(segment['geometry'])
        coords = list(segment['geometry'].coords)
        return coords
    return []

if __name__ == "__main__":
    print("Running TrafficOverlay.py")

    # Load necessary data
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_directory = os.path.join(script_dir, "../data")
    date_string = "2024-06-12_23-00-00"

    print("Loading dataframes...")
    sun_glare_df = pd.read_csv(f"{base_directory}/washington_dc/sun_glare_data_{date_string}.csv")
    geojson_df = gpd.read_file(f"{base_directory}/geojson_data_dc.geojson")

    # Preprocess the sun glare data for efficient querying
    sun_glare_gdf = preprocess_sun_glare_data(sun_glare_df)

    # Iterate through geojson_df and process each segment
    for index, segment in geojson_df.iterrows():
        if 'segmentProbeCounts' in segment:
            probe_count = get_probe_count(segment)
            coords = get_coordinate_from_segment(segment)
            
            if coords:  # Only check for glare if coordinates are available
                has_glare = segment_has_glare(coords, sun_glare_gdf)
                glare_status = "Has glare" if has_glare else "No glare"
            else:
                glare_status = "No coordinates"

            # Output or store the combined information
            print(f"Segment {index}:")
            print(segment)
            print(f"  Probe count: {probe_count}")
            print(f"  Coordinates: {coords}")
            print(f"  Glare Status: {glare_status}")
            print("------")
