from NodeGrabbing import store_all_nodes_at_location
import os

if __name__ == '__main__':
    print('Starting Tool...')
    location = "bealeton, va, usa"
    name = "bealeton"
    
    print(f"Startin process to detect sun glare in {location}")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_directory = os.path.join(script_dir, "../data", name)

    print("First step: get all segments we will use to detect sun glare")
    store_all_nodes_at_location(location, base_directory)

    print("Next step: grab all images needed from Google Street View")
    