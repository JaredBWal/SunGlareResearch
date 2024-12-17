
import folium
import math
from shapely.geometry import LineString
import pandas as pd
import ast

def apply_offset_to_coordinates(coord, heading, offset_buckets):

    lat, lon = coord

    if 0 <= heading < 22.5 or 337.5 <= heading < 360:
        x_offset, y_offset = offset_buckets["north"]
    elif 22.5 <= heading < 67.5:
        x_offset, y_offset = offset_buckets["northeast"]
    elif 67.5 <= heading < 112.5:
        x_offset, y_offset = offset_buckets["east"]
    elif 112.5 <= heading < 157.5:
        x_offset, y_offset = offset_buckets["southeast"]
    elif 157.5 <= heading < 202.5:
        x_offset, y_offset = offset_buckets["south"]
    elif 202.5 <= heading < 247.5:
        x_offset, y_offset = offset_buckets["southwest"]
    elif 247.5 <= heading < 292.5:
        x_offset, y_offset = offset_buckets["west"]
    elif 292.5 <= heading < 337.5:
        x_offset, y_offset = offset_buckets["northwest"]
    else:
        x_offset, y_offset = 0, 0  # Default offset for invalid heading

    # Apply the offsets
    modified_lat = lat + y_offset
    modified_lon = lon + x_offset

    return modified_lat, modified_lon

def draw_linestring_on_map(sun_glare_id,line_string, map_object, color, heading):
    # Buckets for different heading ranges
    one = 0.00001
    half = 0.00001
    modifier = 2
    
    offset_buckets = {
        "north": (-half, -one),        
        "northeast": (modifier*-half, modifier*-half),  
        "east": (-one, -half),        
        "southeast": (modifier*-half, modifier*half),  
        "south": (half, one),      
        "southwest": (modifier*half, modifier*half), 
        "west": (one, half),       
        "northwest": (modifier*half, modifier*-half),  
    }

    if line_string:
        # Convert the LineString to a list of coordinates (lat, lon)
        coordinates = [(coord[1], coord[0]) for coord in line_string.coords]
        
        if heading is not None and offset_buckets:
            # Apply offset to each coordinate based on the heading
            coordinates = [apply_offset_to_coordinates(coord, heading, offset_buckets) for coord in coordinates]
        
        # Create a PolyLine with the given coordinates and color
        folium.PolyLine(
            locations=coordinates,
            color=color,
            weight=6,
            opacity=0.7,
            popup=f"{sun_glare_id}"
        ).add_to(map_object)
    else:
        print("\tLineString is empty, cannot draw.")

def convert_anti_clockwise_east_heading_to_clockwise_north(anti_clockwise_heading):
    # convert the heading from anti-clockwise east to clockwise north
    clockwise_heading = 90 - anti_clockwise_heading
    if clockwise_heading < 0:
        clockwise_heading = 360 + clockwise_heading
    return clockwise_heading


def get_circle_color_for_sun_glare(sun_glare_row):

    if sun_glare_row['angle_risk'] == True:
        if sun_glare_row['has_sun_glare'] == True:
            # sun glare not blocked
            return 'red'
        else:
            # sun glare blocked
            # return orange if blocked by building and yellow if blocked by tree
            if sun_glare_row['blockage_type'] == 'building':
                return 'orange'
            elif sun_glare_row['blockage_type'] == 'tree':
                return 'yellow'
            else:
                # should never  happen but just in case (#TODO switch this color to green)
                return 'black'
    # no chance of sun glare
    return 'green'

def angle_difference(angle1, angle2):
    diff = (angle2 - angle1 + 180) % 360 - 180
    return abs(diff)


# assumes at least 1 segment heading
def get_closest_segment_heading(segment_headings, target_heading):
    target_heading = float(target_heading)
    closest_heading = float(segment_headings[0])
    closest_diff = angle_difference(closest_heading, target_heading)

    for heading in segment_headings:
        heading = float(heading)
        if (angle_difference(heading, target_heading)<closest_diff):
            closest_diff = angle_difference(heading, target_heading)
            closest_heading = heading
    return closest_heading
        


def visualize_just_data(base_directory, date_string, center_point):
    
    sun_glare_dataset_path = f"{base_directory}/sun_glare_data_{date_string}.csv"
    segments_dataset_path = f"{base_directory}/segments.csv"
    panoramic_dataset_path = f"{base_directory}/panoramic_data.csv"

    sun_glare_data = pd.read_csv(sun_glare_dataset_path)
    segments_data = pd.read_csv(segments_dataset_path)
    panoramic_data = pd.read_csv(panoramic_dataset_path)

    segments_data['headings'] = segments_data['headings'].apply(ast.literal_eval)
    segments_data['line_strings'] = segments_data['line_strings'].apply(ast.literal_eval)
    segments_data['segment_links'] = segments_data['segment_links'].apply(ast.literal_eval)
    segments_data['heading_links'] = segments_data['heading_links'].apply(ast.literal_eval)


    m = folium.Map(location=center_point, zoom_start=16)

    row_counter = 0
    for i, row in sun_glare_data.iterrows():
        
        pano_id = row['pano_id']
        pano_heading_id = row['pano_heading_id']
        pano_row = panoramic_data.loc[panoramic_data['pano_id'] == pano_id]
        segment_id = str(pano_row['segment_id'].iloc[0])
        segment_row = segments_data.loc[segments_data['segment_id'] == segment_id]
        
        row_counter += 1
        circle_color = get_circle_color_for_sun_glare(row)

        lat = row['lat']
        long = row['long']
        anti_east_heading = row['heading']
        heading = convert_anti_clockwise_east_heading_to_clockwise_north(row['heading'])
        segment_headings = segment_row['headings'].iloc[0]
        segment_heading = get_closest_segment_heading(segment_headings, heading)


        # get segment link from heading 
        heading_links = segment_row['heading_links'].iloc[0]

        segment_links = []

        if segment_heading in heading_links:
            segment_links = heading_links[segment_heading]
        

        # loop over found segment links to draw them (usually only 1, but some headings can multiple links)
        for segment_link in segment_links:
            segment_line_string = LineString(segment_row['line_strings'].iloc[0][segment_link])
    
            draw_linestring_on_map(pano_heading_id,segment_line_string, m, circle_color, heading)
            # draw circles
            # folium.CircleMarker(
            #     location=[lat, long],
            #     radius=2,
            #     color=circle_color,
            #     fill=True,
            #     fill_color=circle_color,
            #     fill_opacity=0.7,
            #     popup=  f"Pano_id: {pano_id}\n"+
            #             f"Segment_id: {segment_id}\n"+
            #             f"Segment_headings: {segment_headings}\n"+
            #             f"line_string: {segment_line_string}",
            # ).add_to(m)

    saved_html_map_path = f"{base_directory}/sun_glare_map_{date_string}.html"
    m.save(saved_html_map_path)
    print(f"\tMap created with {row_counter} detections and saved to {saved_html_map_path}")


def create_sun_glare_map(base_directory, date_time):
    # TODO center point
    center_point = (38.89565719232077, -77.04168192501736)

    date_string = date_time.strftime("%Y-%m-%d_%H-%M-%S")
    visualize_just_data(base_directory, date_string, center_point)



