
import matplotlib.pyplot as plt
from pysolar.solar import get_altitude, get_azimuth
from datetime import datetime, timezone
from PIL import Image
import math
import numpy as np
import pandas as pd
import ast

def plot_dot_on_image(img_path, xc, yc, color='red', title="Sun's Incidence Point on Cylindrical GSV Panorama"):

    with Image.open(img_path) as img:
        plt.figure(figsize=(10, 5))
        plt.imshow(img)
        plt.scatter(xc, yc, color=color, label="Sun's Incidence Point")
        plt.text(xc + 10, yc - 10, f"({int(xc)}, {int(yc)})", color='red', fontsize=12)
        plt.title(title)
        plt.show()

def get_image_width_height(base_directory, pano_id):

    img_path = f"{base_directory}/panoramic_imgs/{pano_id}.jpg"

    with Image.open(img_path) as img:
        width, height = img.size
    return width, height

def get_sun_position_east(latitude: float, longitude: float, date: datetime):
    altitude = get_altitude(latitude, longitude, date)  # degrees
    azimuth = get_azimuth(latitude, longitude, date)  #  degrees

    # convert to be anticlockwise from east
    azimuth = 90 - azimuth
    if azimuth < 0:
        azimuth = azimuth + 360  

    return altitude, azimuth





def plot_image(image, title="None"):
    plt.figure(figsize=(8, 6))
    plt.imshow(image, cmap="gray")
    plt.title(title)
    plt.axis("off")  # Hide axes for cleaner visualization
    plt.show()

def plot_dot_on_image_obj(img, x, y, title="No Title" , color='red' ):
    plt.figure(figsize=(10, 5))
    plt.imshow(img)
    plt.scatter(x, y, color=color, label="Sun's Incidence Point" )
    plt.text(x + 10, y - 10, f"({int(x)}, {int(y)})", color='red', fontsize=12)
    plt.title(title)
    plt.show()

def get_sun_position_on_panoramic_with_heading_date_slope(base_directory, pano_id, lat, long, heading, date=datetime.now(timezone.utc), driveway_slope=0):
    driving_direction = heading
    
    altitude, azimuth = get_sun_position_east(lat, long, date)
    
    wc, hc = get_image_width_height(base_directory, pano_id)
    cx = wc/2
    cy = hc/2

    rad_azimuth = math.radians(azimuth)
    rad_altitude = math.radians(altitude)
    rad_driving_direction = math.radians(driving_direction)
    rad_driveway_slope = math.radians(driveway_slope)

    sun_x = (((rad_driving_direction - rad_azimuth) / (2 * math.pi)) * wc) + cx
    sun_y = cy - (((rad_altitude - rad_driveway_slope) / (math.pi/2)) * hc)
    
    return sun_x, sun_y

def determine_sun_position(base_directory, pano_id, lat, long, date, heading, tilt):

    # calculate the sun position for the given time
    xc, yc = get_sun_position_on_panoramic_with_heading_date_slope(base_directory, pano_id, lat, long, heading, date=date, driveway_slope=tilt)

    wc, hc = get_image_width_height(base_directory, pano_id)
    
    # wrap the x-coordinate around the panoramic width
    xc = xc % wc

    #plot it 
    # plot_dot_on_image(panoramic_path, xc, yc)

    return xc, yc

def write_as_csv(filepath, dict):
    df = pd.DataFrame.from_dict(dict, orient='index')
    df.index.name = 'pano_heading_id'
    df.to_csv(filepath)


# returns False is the x,y are in the sky class 
def check_if_sun_is_blocked(segmentation_map, x, y, sky_class=10, building_class=2, tree_class=8):

    # create mask of sky
    sky_masks = (segmentation_map == 10).astype(np.uint8) * 255
    building_masks = (segmentation_map == building_class).astype(np.uint8) * 255
    tree_masks = (segmentation_map == tree_class).astype(np.uint8) * 255

    x = int(x)
    y = int(y)

    # Sky is 255, other is 0
    if sky_masks[y,x] == 0:
        # find the object that blocked the sun
        blockage_type = "other"
        

        if building_masks[y,x] == 255:
            blockage_type = "building"
        elif tree_masks[y,x] == 255:
            blockage_type = "tree"
        return True, blockage_type
    return False, "none"

    


def convert_heading_to_anticlockwise_from_east(heading):
    # Convert the heading to anti-clockwise from east
    heading = 90 - heading
    if heading < 0:
        heading += 360

    return heading


def add_sun_glare_row_to_dataset(sun_glare_dict, pano_id, segment_heading, lat, long, has_sun_glare, angle_risk ,blockage_type = "none", ):
    row_id = f"{pano_id}_{segment_heading}"
    sun_glare_dict[row_id] = {
        "lat": lat,
        "long": long,
        "has_sun_glare": has_sun_glare,
        "pano_id": pano_id,
        "heading": segment_heading,
        "angle_risk": angle_risk, # true if sun has proper angle to cause glare
        "blockage_type": blockage_type
    }


def angle_difference(angle1, angle2):
    diff = (angle2 - angle1 + 180) % 360 - 180
    return abs(diff)


# returns True if sun glare is detected at a panoramic image
def calculate_sun_glare_given_heading_panoramic_row(base_directory, segment_heading, pano_row, date_time):
    lat = pano_row["lat"]
    long = pano_row["long"] 
    panoramic_heading = pano_row["heading"]
    tilt = pano_row["tilt"]
    pano_id = pano_row["pano_id"]

    sun_x, sun_y = determine_sun_position(base_directory, pano_id, lat, long, date_time, panoramic_heading, tilt)
    altitude, azimuth = get_sun_position_east(lat, long, date_time)

    h_glare = angle_difference(azimuth, segment_heading)
    v_glare = angle_difference(altitude, tilt)

    if (h_glare < 25) and (v_glare < 25):

        # figure out which segmentation map to use
        if (has_leaves_off(lat, long, date_time.timetuple().tm_yday)):
            # leaves off, so use treeless segmentation map
            print("Leaves are off, using treeless segmentation map")
            segmentation_map_path = f"{base_directory}/segmentation_maps_without_trees/{pano_id}.png"
        else:
            # leaves on, so use regular segmentation map
            print("Leaves are on, using regular segmentation map")
            segmentation_map_path = f"{base_directory}/segmentation_maps/{pano_id}.png"

        print(f"Segmentation Map Path: {segmentation_map_path}")
        segmentation_map = np.array(Image.open(segmentation_map_path))
        sun_glare_blocked, _ = check_if_sun_is_blocked(segmentation_map, sun_x, sun_y)
        return not sun_glare_blocked
    else:
        return False

# looks at all headings at panoramic
def check_if_any_sun_glare_at_panoramic_with_datetime(base_directory, pano_row, date_time):
    segment_headings = pano_row['segment_headings']

    for heading in segment_headings:
        has_sun_glare = calculate_sun_glare_given_heading_panoramic_row(base_directory, heading, pano_row, date_time)
        if has_sun_glare:
            return True
    return False
    

def has_leaves_off(lat, lon, day_of_year):
    default_value = True

    # if data isnt valid, just return default value
    if not (-90 <= lat <= 90 or -180 <= lon <= 180):
        return default_value
    if day_of_year is None:
        return default_value

    # Deciduous trees are found in temperate zones
    temperate_zone_north = (23.5, 66.5)  # Northern Hemisphere
    temperate_zone_south = (-66.5, -23.5)  # Southern Hemisphere

    # Determine if the latitude falls within a temperate zone
    in_temperate_zone = False
    hemisphere = None
    if temperate_zone_north[0] <= lat <= temperate_zone_north[1]:
        in_temperate_zone = True
        hemisphere = "north"
    elif temperate_zone_south[0] <= lat <= temperate_zone_south[1]:
        in_temperate_zone = True
        hemisphere = "south"
    else:
        return False  # Outside temperate zones, unlikely to experience 'leaves off'

    # Northern Hemisphere leafless season: Approx. October 1 (Day 274) to April 15 (Day 105)
    if hemisphere == "north":
        if day_of_year >= 274 or day_of_year <= 105:
            return True  # In leafless season
        else:
            return False  # In growing season

    # Southern Hemisphere leafless season: Approx. May 1 (Day 121) to September 15 (Day 258)
    if hemisphere == "south":
        if 121 <= day_of_year <= 258:
            return True  # In leafless season
        else:
            return False  # In growing season

    return False


def calculate_sun_glare_for_a_single_panoramic_image(base_directory, sun_glare_dict, pano_id, lat, long, panoramic_heading, tilt, date_time, segment_headings):


    sun_x, sun_y = determine_sun_position(base_directory, pano_id, lat, long, date_time, panoramic_heading, tilt)
    altitude, azimuth = get_sun_position_east(lat, long, date_time)
    # each panoramic image can have multiple headings (like an intersection or 2 lane road)
    # we want to save each heading and the sun glare for that heading
    for segment_heading in segment_headings:

        h_glare = angle_difference(azimuth, segment_heading)
        v_glare = angle_difference(altitude, tilt)

        if (h_glare < 25) and (v_glare < 25):
            # angle potential for sun glare, lets check if something blocks it
            # first read the segmentation map from storage

            segmentation_map_path = ""
            # choose the right segmentation map based on the date (ie: if it is leaves on or off)
            if(has_leaves_off(lat, long, date_time.timetuple().tm_yday)):
                # leaves are off, so use the treeless segmentation map
                print("Leaves are off, using treeless segmentation map")
                segmentation_map_path = f"{base_directory}/segmentation_maps_without_trees/{pano_id}.png"
            else:
                # leaves are on, so use regular segmentation map
                print("Leaves are on, using regular segmentation map")
                segmentation_map_path = f"{base_directory}/segmentation_maps/{pano_id}.png"
            print(f"Segmentation Map Path: {segmentation_map_path}")    

            segmentation_map = np.array(Image.open(segmentation_map_path))

            sun_glare_blocked, blockage_type = check_if_sun_is_blocked(segmentation_map, sun_x, sun_y)

            if sun_glare_blocked:
                # plot_dot_on_image(panoramic_file, sun_x, sun_y, color='yellow', title=f"Sun Glare at {date_time}")
                # TODO 
                add_sun_glare_row_to_dataset(sun_glare_dict, pano_id, segment_heading, lat, long, False, True, blockage_type)
            else:
                # plot_dot_on_image(panoramic_file, sun_x, sun_y, color='red', title=f"Sun Glare at {date_time}")
                add_sun_glare_row_to_dataset(sun_glare_dict, pano_id, segment_heading, lat, long, True, True, blockage_type)
        else:
            # plot_dot_on_image(panoramic_file, sun_x, sun_y, color='green', title=f"Sun Glare at {date_time}")
            # False, since angle is not right for sun glare
            add_sun_glare_row_to_dataset(sun_glare_dict, pano_id, segment_heading, lat, long, has_sun_glare=False , angle_risk=False, blockage_type="none")


# calculates and stores sun glare for all panoramic data at a given date and time
# Note: date_time is in UTC
def calculate_sun_glare_for_panoramic_data_at_date_time(base_directory, date_time):
    panoramic_data_path = f"{base_directory}/panoramic_data.csv"
    pano_data = pd.read_csv(panoramic_data_path)
    
    segments_path = f"{base_directory}/segments.csv"
    segments = pd.read_csv(segments_path)
    sun_glare_dict = {}

    for index, panoramic in pano_data.iterrows():
        
        pano_id = panoramic["pano_id"]
        segment_id = panoramic["segment_id"]
        lat = panoramic["lat"]
        long = panoramic["long"]
        # heading is already anticlockwise from east
        heading = panoramic["heading"]
        tilt = panoramic["tilt"]
        year = panoramic["year"]
        month = panoramic["month"]
        segment = segments.loc[segments['segment_id'] == segment_id]
        segment_headings = segment['headings'].apply(ast.literal_eval)
        segment_headings = segment_headings.iloc[0]

        # convert segment headings to anticlockwise from east
        for i in range(len(segment_headings)):
            segment_headings[i] = convert_heading_to_anticlockwise_from_east(segment_headings[i])

        calculate_sun_glare_for_a_single_panoramic_image(base_directory, sun_glare_dict, pano_id, lat, long, heading, tilt, date_time, segment_headings)

        date_time_string = date_time.strftime("%Y-%m-%d_%H-%M-%S")
        sung_glare_data_path = f"{base_directory}/sun_glare_data_{date_time_string}.csv"
        write_as_csv(sung_glare_data_path , sun_glare_dict)



