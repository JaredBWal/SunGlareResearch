from geopy.distance import geodesic
import math
import osmnx as ox
import networkx as nx
import numpy as np
from shapely.geometry import Point
import pandas as pd
from shapely.geometry import Point, LineString
import os
from SunGlareDetectionFunctions import check_if_any_sun_glare_at_panoramic_with_datetime
import ast
from datetime import datetime, timedelta, timezone
import folium
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plt
from shapely.geometry import MultiPoint


def determine_clusters_and_draw_circles(car_crash_data, m):
    # Filter data to only include crashes with sun glare
    df_sun_glare = car_crash_data[car_crash_data['has_sun_glare'] == True]
    
    # Ensure we only have relevant columns for clustering (lat, long)
    coordinates = df_sun_glare[['long', 'lat']].values

    # DBSCAN clustering with max distance of 100 feet (~30.48 meters)
    eps = 30.48  # 100 feet in meters
    min_samples = 5  # At least 5 crashes to form a cluster
    dbscan = DBSCAN(eps=eps, min_samples=min_samples, metric='haversine')

    # Convert lat, long to radians for DBSCAN
    coordinates_rad = np.radians(coordinates)

    # Fit DBSCAN
    labels = dbscan.fit_predict(coordinates_rad)
    
    # Add cluster labels to the DataFrame
    df_sun_glare['cluster'] = labels

    # Filter out noise points (label == -1)
    clusters = df_sun_glare[df_sun_glare['cluster'] != -1]

    # Create the map centered on the first cluster's mean coordinates
    m = folium.Map(location=[clusters['lat'].mean(), clusters['long'].mean()], zoom_start=12)

    # Draw circles around each cluster
    for cluster_label in clusters['cluster'].unique():
        
        cluster_points = clusters[clusters['cluster'] == cluster_label]
        cluster_center = cluster_points[['lat', 'long']].mean()
        cluster_lat = cluster_center['lat']
        cluster_long = cluster_center['long']

        # Calculate the radius as the average distance to points in the cluster
        # Note: Here we can use geopy to compute the distance between the center and points
        cluster_radius = max(
            [geodesic((cluster_lat, cluster_long), (lat, long)).meters for lat, long in zip(cluster_points['lat'], cluster_points['long'])]
        )

        # Draw circle around the cluster
        folium.Circle(
            location=[cluster_lat, cluster_long],
            radius=cluster_radius,  # Adjust the radius based on the cluster size
            color='blue',
            fill=True,
            fill_opacity=0.4,
            popup=f"Cluster: {len(cluster_points)} crashes"
        ).add_to(m)

    # Save the map to an HTML file
    m.save("car_crashes_clustered_map.html")


def convert_military_integer_to_time(military_int):
    # Ensure the military integer is a string with leading zeros if necessary
    military_time = str(military_int).zfill(4)

    # Extract hours and minutes
    hours = int(military_time[:len(military_time)-2]) if len(military_time) > 2 else 0
    minutes = int(military_time[len(military_time)-2:])

    # Return formatted time
    return hours,minutes

def calculate_sun_glare_for_crashes(location, base_directory):
    simple_name = location.split(",")[0]
    output_crash_path = f"{base_directory}/car_crashes_with_sun_glare.csv"
    # graph = ox.graph_from_place(location, network_type="drive")

    # Load the crash data
    crash_data = pd.read_csv(f"{base_directory}/car_crashes_with_panoramics_{simple_name}.csv")
    panoramic_data = pd.read_csv(f"{base_directory}/panoramic_data.csv")
    panoramic_data['segment_headings'] = panoramic_data['segment_headings'].apply(ast.literal_eval)

    car_crashes_with_sun_glare = []

    # iterate to find the sun glare for each crash
    for index, row in crash_data.iterrows():
        print(f"==={index}===")
        print(f"    matched_pano_id: {row['matched_pano_id']}")
        # Get the crash coordinates
        lat, long = row['LAT'], row['LON']
        car_crash_date = row['Crash Date']
        month, day, year = car_crash_date.split("/")
        hour, minutes = convert_military_integer_to_time(row['Crash Military Time'])
        print(f"    {int(month)}/{day}/{year} {hour}:{minutes}")
        date_time = datetime(int(year), int(month), int(day), int(hour), int(minutes), 0, tzinfo=timezone.utc)
        segmentation_dataset_path = f"{base_directory}/panoramic_segmentation_maps"
        segmentation_maps_without_trees_path = f"{base_directory}/panoramic_segmentation_maps_without_trees"
     
        matched_pano_id = row['matched_pano_id']
        panoramic_img_path = f"{base_directory}/panoramic_imgs/{matched_pano_id}.jpg"
        print(f"    panoramic_img_path: {panoramic_img_path}")
        panoramic_row = panoramic_data[matched_pano_id == panoramic_data['pano_id']].iloc[0]
        # print(f"{panoramic_row['segment_headings'][0]}")
        # print(f"    panoramic_row: {panoramic_row}")
        has_sun_glare = check_if_any_sun_glare_at_panoramic_with_datetime(base_directory, panoramic_row, date_time)
        print(f"    has_sun_glare: {has_sun_glare}")

        car_crashes_with_sun_glare.append({
            'date_time': date_time,
            'lat': lat,
            'long': long,
            'has_sun_glare': has_sun_glare
        })

    # save as csv
    car_crashes_with_sun_glare_df = pd.DataFrame(car_crashes_with_sun_glare)
    car_crashes_with_sun_glare_df.to_csv(output_crash_path, index=False)

    # create map of accidents with sun glare
    # Filter rows where has_sun_glare is True
    sun_glare_data = car_crashes_with_sun_glare_df[car_crashes_with_sun_glare_df['has_sun_glare'] == True]


    # Initialize the map with a default location (mean of latitudes and longitudes)
    m = folium.Map(location=[sun_glare_data['lat'].mean(), sun_glare_data['long'].mean()], zoom_start=12)

    # Add circles for locations with sun glare
    for _, row in sun_glare_data.iterrows():
        folium.Circle(
            location=[row['lat'], row['long']],
            radius=6,  # Radius in meters
            color='red',
            fill=True,
            fill_opacity=0.6,
            popup=f"{row['lat']},{row['long']}\nDate/Time: {row['date_time']}"
        ).add_to(m)
    

    # Save the map as an HTML file

    determine_clusters_and_draw_circles(car_crashes_with_sun_glare_df, m)
    
    m.save(f"{base_directory}/car_crashes_with_sun_glare_map.html")
    print(f"Map saved to {base_directory}/car_crashes_with_sun_glare_map.html")





def main():
    location = "fredericksburg, VA, USA"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_directory = os.path.join(script_dir, "../data", "fredericksburg")
    calculate_sun_glare_for_crashes(location, base_directory)


main()