# %% [markdown]
# ### Description:
# 
# Goes through each node and attempts to grab its tiles from Google Street Maps API (grabs two tiles that will later become the panoramic)
# 

import requests
import os
import time
import numpy as np
from PIL import Image
import pandas as pd
from dotenv import load_dotenv

API_KEY = ""
SESSION_ID = ""

ERROR_COUNT = 0
DUPLICATE_IMAGE_CALLS = 0 # only 1 image is called, but this lets us know if that happens alot
TOTAL_API_CALLS = 0
API_CALLS = 0

def setup_session():
    global SESSION_ID
    global API_KEY

    load_dotenv(override=True)
    API_KEY = os.getenv("API_KEY")

    print(API_KEY)

    session_url = f"https://tile.googleapis.com/v1/createSession?key={API_KEY}"
    payload = {
        "mapType": "streetview",
        "language": "en-US",
        "region": "US"
    }
    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(session_url, json=payload, headers=headers)

    if response.status_code == 200:
        SESSION_ID = response.json()['session']
    else:
        print("\tError Setting Up API:", response.status_code, response.text)




def check_if_calls_should_sleep():
    global API_CALLS
    global TOTAL_API_CALLS
    global DUPLICATE_IMAGE_CALLS

    API_CALLS+=1
    TOTAL_API_CALLS+=1

    if TOTAL_API_CALLS % 100 == 0:
        print(f"\tTOTAL API CALLS: {TOTAL_API_CALLS}")

    if API_CALLS >= 4000:
        print("\tTaking a Break...Sleeping Calls for 30 seconds")
        time.sleep(30)
        #reset call counter
        API_CALLS = 0


# gets the image for the panoId, the panorama automatically faces the direction of traggic (in the center
def get_image_for_panoId(pano_id, output_path, tile_x=0, tile_y=0, z=1):
    check_if_calls_should_sleep()
    url = f"https://tile.googleapis.com/v1/streetview/tiles/{z}/{tile_x}/{tile_y}?session={SESSION_ID}&key={API_KEY}&panoId={pano_id}&zoom=1"

    response = requests.get(url)
    if response.status_code == 200:
       return response.content
    else:
        print("\tError:", response.status_code, response.text)


def get_data_from_cords(lat, long, radius=25):
    check_if_calls_should_sleep()
    url = f"https://tile.googleapis.com/v1/streetview/metadata?session={SESSION_ID}&key={API_KEY}&lat={lat}&lng={long}&radius={radius}&"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        print("\tError:", response.status_code, response.text)


def get_data_from_panoId(pano_id):
    check_if_calls_should_sleep()

    url = f"https://maps.googleapis.com/maps/api/streetview/metadata?pano={pano_id}&key={API_KEY}"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()
    else:
        print("\tError:", response.status_code, response.text)



def convert_heading_to_anticlockwise_from_east(heading):
    # Convert the heading to anti-clockwise from east
    heading = 90 - heading
    if heading < 0:
        heading += 360

    return heading

# Removes all rows of black pixels from the bottom of an image.
def remove_black_rows(image):
  
    image_array = np.array(image)
    
    # Check for black rows at the bottom
    is_black_row = np.all(image_array == 0, axis=(1, 2))
    
    # Find the last non-black row
    last_non_black_row = np.where(is_black_row == False)[0][-1]
    
    # Slice the image array to remove black rows at the bottom
    cropped_image_array = image_array[:last_non_black_row + 1]
    
    # Convert back to an image
    cropped_image = Image.fromarray(cropped_image_array)
    return cropped_image

def crop_both_tile_images(tile_path_0, tile_path_1):

    # remove black rows from first image, and save
    with Image.open(tile_path_0) as img:
        # first remove potential black/blank rows at the bottom
        img = remove_black_rows(img)
        img.save(tile_path_0)
        # plot_image(img, "no_black_space "+tile_path_0 )


    # remove black rows from second image, crop it to the right, so panorama width is 2x height, and save
    with Image.open(tile_path_1) as img:
        img = remove_black_rows(img)
        width_to_crop = 2 * (img.width - img.height)

        top = 0
        left = 0
        right = img.width - width_to_crop
        bottom = img.height

        cropped_img = img.crop((left, top, right, bottom))


        # plot_image(img, "no_black_space "+tile_path_1 )
        # plot_image(cropped_img, "cropped_" +tile_path_1 )

        cropped_img.save(tile_path_1)

# %%
def combine_panoramic_tiles(tile1_path, tile2_path, output_path):

    # Open the two image tiles
    tile1 = Image.open(tile1_path)
    tile2 = Image.open(tile2_path)

    # Create a new blank image with combined width and same height
    combined_width = tile1.size[0] + tile2.size[0]
    combined_height = tile1.size[1]
    combined_image = Image.new("RGB", (combined_width, combined_height))

    # Paste the tiles side by side
    combined_image.paste(tile1, (0, 0))  # Place tile1 at the left
    combined_image.paste(tile2, (tile1.size[0], 0))  # Place tile2 to the right of tile1

    # Save the combined image
    combined_image.save(output_path)

def write_as_csv(filepath, dict):
    df = pd.DataFrame.from_dict(dict, orient='index')
    df.index.name = 'pano_id'
    df.to_csv(filepath)


# returns true if was successful else false
def save_panoramic_image_from_pano_id(pano_id, base_directory, saved_panoramic_imgs):
    global DUPLICATE_IMAGE_CALLS
    pano_save_path = f"{base_directory}/panoramic_imgs/{pano_id}.jpg"
    image_0_save_path = f"{base_directory}/tile_imgs/{pano_id}_0.jpg"
    image_1_save_path = f"{base_directory}/tile_imgs/{pano_id}_1.jpg"

    try:
        if pano_id not in saved_panoramic_imgs:
            image_0_content = get_image_for_panoId(pano_id, pano_save_path, 0, 0)
            image_1_content = get_image_for_panoId(pano_id, pano_save_path, 1, 0)
            # add pano_id to saved_panoramic_imgs
            saved_panoramic_imgs.append(pano_id)
        else:
            # if already saved, just return true
            print(f"\tDuplicate Image Call for {pano_id} - not making calls")
            DUPLICATE_IMAGE_CALLS += 1
            return True
    except:
        print(f"\tError getting images for segment_id: {pano_id}")
        ERROR_COUNT += 1
        return False

    # Save both of these images
    with open(image_0_save_path, "wb") as file:
        file.write(image_0_content)
    
    with open(image_1_save_path, "wb") as file:
        file.write(image_1_content)

    # crop the images (since some have black rows at the bottom)
    crop_both_tile_images(image_0_save_path, image_1_save_path)


    # combine them into a panoramic
    combine_panoramic_tiles(image_0_save_path, image_1_save_path, pano_save_path)
    # save the panoramic

    return True


def get_store_all_panoramics_from_segments(base_directory):
    global ERROR_COUNT
    panoramic_data_path = f"{base_directory}/panoramic_data.csv"

    # convert csv into dictionary
    segments_csv_path = f"{base_directory}/segments.csv"
    segments = pd.read_csv(segments_csv_path)

    # TODO DEBUG
    # segments = segments.head(50)

    panoramic_directory_path = f"{base_directory}/panoramic_imgs"
    tile_directory_path = f"{base_directory}/tile_imgs"

    # make sure all needed directories exist
    os.makedirs(panoramic_directory_path, exist_ok=True)
    os.makedirs(tile_directory_path, exist_ok=True)


    # get currently saved panoramic images (to check if can avoid re-calling API)
    saved_panoramic_imgs = os.listdir(panoramic_directory_path)
    saved_panoramic_imgs = [img.split(".")[0] for img in saved_panoramic_imgs] # list of pano_ids

    # pano_id : segment_id, lat, long, heading, tilt, month, year
    panoramic_data = pd.read_csv(panoramic_data_path)
    segment_ids_in_panoramic_data = panoramic_data['segment_id'].values
    panoramic_data = panoramic_data.set_index('pano_id').T.to_dict()
         
    error_count = 0

    

    # loop through all segments
    for index, segment in segments.iterrows():
        
        if (segment['segment_id'] in segment_ids_in_panoramic_data):
            # we already have the data for this segment, skip
            print(f"\tAlready have data for segment_id: {segment['segment_id']}, skipping")
            continue

        # NOTE allows for partial saving if quotas are reached
        # if index % 1000 == 0:
        #     # evert 1000 segments, save the data as a safety measure
        #     write_as_csv(panoramic_data_path, panoramic_data)

        segment_id = segment['segment_id']
        
        segment_lat = segment['lat']
        segment_long = segment['long']
        segment_headings = segment['headings']
        segment_links = segment['segment_links']
        segment_heading_links = segment['heading_links']
        segment_line_strings = segment['line_strings']



        try:
            # TODO change radius to 20
            coord_data = get_data_from_cords(segment_lat, segment_long, radius=10)
            pano_id = coord_data['panoId']
            pano_heading = convert_heading_to_anticlockwise_from_east(coord_data['heading'])
            pano_tilt = coord_data['tilt'] - 90 # tilt is 0 when looking straight up, 90 when looking straight ahead
            date = coord_data['date']
            pano_year, pano_month = date.split("-")
            
           

            if (save_panoramic_image_from_pano_id(pano_id, base_directory, saved_panoramic_imgs)):
                # succesful at getting and saving images (including panoramic)
                # now just store the data about the coords
                panoramic_data[pano_id] = {
                    "segment_id": segment_id,
                    "lat": segment_lat,
                    "long": segment_long,
                    "heading": pano_heading,
                    "tilt": pano_tilt,
                    "year": pano_year,
                    "month": pano_month,
                    "segment_headings": segment_headings,
                    "segment_links": segment_links,
                    "segment_heading_links": segment_heading_links,
                    "segment_line_strings": segment_line_strings
                }

            else: 
                error_count += 1
                continue


        except:
            print(f"\tError getting data for segment_id: {segment_id}, skipping")
            ERROR_COUNT += 1
            continue
        
    # save the data about the panoramics
    write_as_csv(panoramic_data_path, panoramic_data)
    



def grab_tiles_given_directory(base_directory):
    # segment_to_get_from_path = f"{data_name_directory}/segments.csv"
    # base_path_to_save_img = f"{data_name_directory}/panoramic_imgs"
    # csv_save_path = f"{data_name_directory}/panoramic_data.csv"
    # get_store_all_panoramics_from_segments(segment_to_get_from_path,base_path_to_save_img,csv_save_path)
    setup_session()
    get_store_all_panoramics_from_segments(base_directory)
    
    print("\tAll Panoramic Images Grabbed")
    print(f"\tTotal API Calls: {TOTAL_API_CALLS}")
    print(f"\tDuplicate Image Calls: {DUPLICATE_IMAGE_CALLS}")
    print(f"\tTotal Image Grabbing Errors: {ERROR_COUNT}")




