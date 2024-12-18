import os
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from geopy.distance import geodesic
import folium


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

# preprocess sun glare data into a more efficient lookup form
def preprocess_sun_glare_data(sun_glare_df):
    sun_glare_df = sun_glare_df[['lat', 'long', 'has_sun_glare']]
    sun_glare_gdf = gpd.GeoDataFrame(sun_glare_df, 
                                     geometry=gpd.points_from_xy(sun_glare_df['long'], sun_glare_df['lat']),
                                     crs="EPSG:4326")  # WGS 84 coordinate system (degree-based)
    sun_glare_gdf = sun_glare_gdf.to_crs("EPSG:3857")
    return sun_glare_gdf

# Function to check for sun glare efficiently using spatial indexing
def segment_has_glare(segment_coords, sun_glare_gdf):
    # convert segment coordinates into a GeoDataFrame
    segment_gdf = gpd.GeoDataFrame(geometry=[LineString(segment_coords)], crs="EPSG:4326")
    segment_gdf = segment_gdf.to_crs("EPSG:3857")
    buffer = segment_gdf.geometry.buffer(10)  # 10 meters buffer
    buffered_gdf = sun_glare_gdf[sun_glare_gdf.geometry.within(buffer.iloc[0])]
    
    # return True if glare exists, otherwise... False 
    return not buffered_gdf.empty  

def get_coordinate_from_segment(segment):
    if 'geometry' in segment and segment['geometry'] is not None:
        coords = list(segment['geometry'].coords)
        return coords
    return []



if __name__ == "__main__":
    print("Running TrafficOverlay.py")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_directory = os.path.join(script_dir, "../data")
    date_string = "2024-06-12_23-00-00"

    print("Loading dataframes...")
    sun_glare_df = pd.read_csv(f"{base_directory}/washington_dc/sun_glare_data_{date_string}.csv")
    geojson_df = gpd.read_file(f"{script_dir}/../public_data/dc_traffic_data.geojson")
    
    # preprocess the sun glare data 
    sun_glare_df = preprocess_sun_glare_data(sun_glare_df)
    line_coords = []  
    total_drivers_effected = 0
    # iterate through geojson_df and process each segment
    print(f"Processing {geojson_df.size} segments... This may take a while")    
    for index, segment in geojson_df.iterrows():

        if 'segmentProbeCounts' in segment:
            probe_count = get_probe_count(segment)
            coords = get_coordinate_from_segment(segment)
            
            if coords:  # Only check for glare if coordinates are available
                has_glare = segment_has_glare(coords, sun_glare_df)
                glare_status = "Has glare" if has_glare else "No glare"
            else:
                glare_status = "No coordinates"
                continue
            total_drivers_effected += 1 if has_glare else 0
         
    print(f"Total drivers in traffic congestion effected by glare: {total_drivers_effected}")