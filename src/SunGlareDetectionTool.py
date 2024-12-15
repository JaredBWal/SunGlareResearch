import os
from NodeGrabbing import store_all_nodes_at_location
from TileGrabbing import grab_tiles_given_directory
from ImageProcessing import create_both_segmentation_maps
from SunGlareDetectionFunctions import calculate_sun_glare_for_panoramic_data_at_date_time
from datetime import datetime, timezone
from VisualizationFunctions import create_sun_glare_map
from TileGrabbing import crop_both_tile_images, combine_panoramic_tiles

# pass in a directory name and a time, and calculate the sun glare
def calculate_sun_glare_for_directory_name_at_time(directory_name, date_time):

    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_directory = os.path.join(script_dir, "../data", directory_name)
    calculate_sun_glare_for_panoramic_data_at_date_time(base_directory, date_time)

    # after calculating sun glare, create a map
    create_sun_glare_map(base_directory, date_time)


def main():
    try:
        print('Starting Tool...')
        location = "washington, dc, usa"
        name = "washington_dc"
        
        print(f"Starting process to detect sun glare in {location}")

        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_directory = os.path.join(script_dir, "../data", name)

        print("First step: get all segments we will use to detect sun glare")
        # store_all_nodes_at_location(location, base_directory)

        print("Next step: grab all images needed from Google Street View")
        grab_tiles_given_directory(base_directory)

        print("Now, Create 2 segmentation maps for each image, one with trees, and one without trees")
        # create_both_segmentation_maps(base_directory)
    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")
        exit()



if __name__ == '__main__':
    main()
    # print("Running sun glare detection tool")

    # date_time_example = datetime(2024, 6, 12, 23, 0, 0, tzinfo=timezone.utc)
    # calculate_sun_glare_for_directory_name_at_time("washington_dc", date_time_example)
    
