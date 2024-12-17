import os
from PIL import Image
from transformers import SegformerFeatureExtractor, SegformerForSemanticSegmentation
import torch
import numpy as np
import cv2


def fill_sky_surrounded_by_buildings(segmentation_map_array):
    # Step 1: Create masks for buildings (2) and sky (10)
    building_mask = (segmentation_map_array == 2).astype(np.uint8) * 255
    sky_mask = (segmentation_map_array == 10).astype(np.uint8) * 255

    # Step 2: Dilation of building mask to grow the building areas
    dilated_building_mask = cv2.dilate(building_mask, np.ones((10, 10), np.uint8), iterations=5)

    # Step 3: Identify the regions where the sky is surrounded by buildings (i.e., dilated_building_mask overlaps with sky_mask)
    surrounded_sky = cv2.bitwise_and(dilated_building_mask, sky_mask)

    # Debug: Plot dilated building mask and surrounded sky
    # plot_image(dilated_building_mask, title="Dilated Building Mask")
    # plot_image(surrounded_sky, title="Surrounded Sky (To be filled)")

    # Step 4: Replace the surrounded sky areas with building class (2)
    updated_segmentation_map = np.copy(segmentation_map_array)
    updated_segmentation_map[surrounded_sky == 255] = 2  # Change the surrounded sky to building (2)

    return updated_segmentation_map

def store_remove_trees_panoramic(panoramic_segmentation_path,output_path):

    segmentation_map = Image.open(panoramic_segmentation_path)
    segmentation_map_array = np.array(segmentation_map)

    tree_mask = (segmentation_map_array == 8).astype(np.uint8) * 255
    building_mask = (segmentation_map_array == 2).astype(np.uint8) * 255
    sky_mask = (segmentation_map_array == 10).astype(np.uint8) * 255

    # Create the combined mask: sky or building areas
    combined_mask = np.maximum(sky_mask, building_mask)

    # Inpaint the tree mask using the combined mask (where 0 in tree_mask will be filled)
    inpainted_tree_mask = cv2.inpaint(tree_mask, combined_mask, 3, cv2.INPAINT_TELEA)

    # normalize result
    inpainted_tree_mask = inpainted_tree_mask / 255.0

    # Replace the tree class (8) in the original segmentation map with the inpainted result
    inpainted_tree_mask = (inpainted_tree_mask * 255).astype(np.uint8)  # Convert back to 0-255 range

    # Create a copy of the original segmentation map to modify
    updated_segmentation_map_array = np.copy(segmentation_map_array)

    # Where the tree mask is present, replace the segmentation value with sky or building (whichever is closest)
    updated_segmentation_map_array[tree_mask == 255] = 10  # Assign sky class (10) where trees were

    # Now, fill the sky surrounded by buildings with the building class
    final_segmentation_map_array = fill_sky_surrounded_by_buildings(updated_segmentation_map_array)

    # Save the final segmentation map to a file
    final_segmentation_map = Image.fromarray(final_segmentation_map_array)
    final_segmentation_map.save(output_path)


def convert_image_to_segmentation_map(image_path, output_path):
    # Load the model and feature extractor
    feature_extractor = SegformerFeatureExtractor.from_pretrained("nvidia/segformer-b5-finetuned-cityscapes-1024-1024")
    model = SegformerForSemanticSegmentation.from_pretrained("nvidia/segformer-b5-finetuned-cityscapes-1024-1024")

    # Check if GPU is available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    # Load and preprocess the image
    image = Image.open(image_path)
    inputs = feature_extractor(images=image, return_tensors="pt").to(device)

    # Perform inference
    with torch.no_grad():
        outputs = model(**inputs)

    # Get logits and convert to class predictions
    logits = outputs.logits  
    predicted_class = torch.argmax(logits, dim=1)  

    # Upsample to match input image size
    predicted_class = torch.nn.functional.interpolate(
        predicted_class.unsqueeze(1).float(),  
        size=image.size[::-1],  
        mode="nearest"
    ).squeeze(1).to(torch.int32)  

    segmentation_map = predicted_class[0].cpu().numpy()

    # save the image
    Image.fromarray(segmentation_map.astype(np.uint8)).save(output_path)

    return segmentation_map


def create_both_segmentation_maps(base_directory):
    # make sure the segmentation maps are generated for each panoramic image
    panoramic_imgs_directory = f"{base_directory}/panoramic_imgs"
    segmentation_map_output_directory = f"{base_directory}/segmentation_maps"
    segmentation_map_without_trees_output_directory = f"{base_directory}/segmentation_maps_without_trees"
    

    image_files = os.listdir(panoramic_imgs_directory)
    # Sort the files using natural sorting
    sorted_images = sorted(image_files)

    # make sure directories exists
    os.makedirs(segmentation_map_output_directory, exist_ok=True)
    os.makedirs(segmentation_map_without_trees_output_directory, exist_ok=True)

    completed_segmentation_maps = os.listdir(segmentation_map_output_directory)
    completed_segmentation_maps_without_trees = os.listdir(segmentation_map_without_trees_output_directory)


    count = 0
    for filename in sorted_images:
        # print(f"\tCreating segmentation map for ({count}) {filename}")
        count+=1
        if filename.split(".")[0]+".png" in completed_segmentation_maps and filename.split(".")[0]+".png" in completed_segmentation_maps_without_trees:
            print(f"\t\tSegmentation map already exists for {filename}... skipping")
            continue
        name = filename.split(".")[0]
        segmentation_save_file = f"{segmentation_map_output_directory}/{name}.png"
        segmentation_without_trees_save_file = f"{segmentation_map_without_trees_output_directory}/{name}.png"
        panoramic_img_file = f"{panoramic_imgs_directory}/{filename}"
        # this saves the segmentation_map to the save_file
        convert_image_to_segmentation_map(panoramic_img_file, segmentation_save_file)
        store_remove_trees_panoramic(segmentation_save_file, segmentation_without_trees_save_file)
    print(f"\tAll segmentation maps created and saved") 

