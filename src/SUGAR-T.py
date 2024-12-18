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
    

def create_urban_environment(location, api_key):
    try:
        print('Starting Tool...')
        name = location.replace(", ", "_").replace(" ", "_").lower()

        
        print(f"Starting process to detect sun glare in {location}")

        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_directory = os.path.join(script_dir, "../data", name)

        os.makedirs(base_directory, exist_ok=True)

        print("First step: get all segments we will use to detect sun glare")
        store_all_nodes_at_location(location, base_directory)

        print("Next step: grab all images needed from Google Street View")
        grab_tiles_given_directory(base_directory, api_key)

        print("Now, Create 2 segmentation maps for each image, one with trees, and one without trees")
        create_both_segmentation_maps(base_directory)
    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")
        exit()



def display_main_menu():
    print("SUGAR-T")
    print("Command Options: ")
    print("\tcreate urban environment")
    print("\tcreate sun glare dataset")
    print("\tview created urban environments")
    print("\texit")
    print("Enter command: ", end="")


def ask_for_location():
    location = input("Enter the location you would like to create an urban environment for (city/town, state/region, country): ")
    return location

def ask_for_date_time():
    date_time_str = input("Enter the date and UTC time in the format (YYYY-MM-DD-HH-MM-SS): ")
    y, m, d, h, min, s = date_time_str.split("-")

    return datetime(int(y), int(m), int(d), int(h), int(min), int(s), tzinfo=timezone.utc)

def check_valid_urban_environment_name(name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_directory = os.path.join(script_dir, "../data")
    data_directories = os.listdir(base_directory)
    return name in data_directories

def handle_create_sun_glare_dataset():
    # user wants to create a sun glare dataset
    handle_view_created_urban_environments()

    urban_environment = input("Enter the name of the urban environment you would like to create a sun glare dataset for: ")
    if check_valid_urban_environment_name(urban_environment):
        #ask for date and time
        date_time_str = ask_for_date_time()
        print(f"Creating sun glare dataset for urban environment {urban_environment} at {date_time_str}")

        # valid urban environment name
        print("Creating sun glare dataset for urban environment...")
        calculate_sun_glare_for_directory_name_at_time(urban_environment, date_time_str)
    

def check_urban_environment_already_created(name):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_directory = os.path.join(script_dir, "../data")
    data_directories = os.listdir(base_directory)
    return name in data_directories

def handle_view_created_urban_environments():
    # show all the created urban environments (every folder in the data directory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_directory = os.path.join(script_dir, "../data")
    data_directories = os.listdir(base_directory)
    print("Urban Environments:")
    for directory in data_directories:
        print(f"\t{directory}")

def ask_for_api_key():
    api_key = input("Enter your Google Maps Platoform API key: ")
    return api_key

def handle_create_urban_environment():
    print("Creating urban environment...")
    location = ask_for_location()
    if check_urban_environment_already_created(location):
        print(f"Urban environment for {location} already exists.")
        return
    api_key = ask_for_api_key()

    # create the urban environment    
    print(f"Creating urban environment for {location}")
    create_urban_environment(location, api_key)



def handle_exit():
    print("Exiting SUGAR-T")
    exit()


def run_main_interface():
    print("Running SUGAR-T")
    while(True):
        display_main_menu()
        command = input()

        if command == "exit":
            handle_exit()
            break
        elif command == "create urban environment":
            handle_create_urban_environment()
        elif command == "create sun glare dataset":
            handle_create_sun_glare_dataset()
        elif command == "view created urban environments":
            handle_view_created_urban_environments()
        else:
            print("Invalid command. Please try again.")
        


if __name__ == '__main__':
    run_main_interface()
    

