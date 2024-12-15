# Description:
# Gets and stores data for nodes (representing street segments)

from folium.plugins import PolyLineTextPath
import folium
import math
import pandas as pd
from geopy.distance import geodesic
from shapely.geometry import LineString, Point
from pyproj import Geod
import osmnx as ox
import os


geod = Geod(ellps="WGS84")

def draw_segments_on_map(segments, center_lat, center_lon, base_directory):
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    for segment_id, segment in segments.items():
        lat = segment['lat']
        long = segment['long']
        folium.CircleMarker(
            location=[lat, long],
            radius=4,
            color='red',
            fill=True,
            fill_opacity=0.8,
            popup=f" {segment_id}: => \nLinks:({segment['segment_links']}\nHeadings:({segment['headings']})"
        ).add_to(m)

        # Draw lines to each segment link
        for linked_segment_id in segment['segment_links']:
            linked_segment = segments.get(linked_segment_id)
            if linked_segment:
                linked_lat = linked_segment['lat']
                linked_long = linked_segment['long']
                
                # Create a PolyLine (line) between the current segment and the linked segment
                folium.PolyLine(
                    locations=[(lat, long), (linked_lat, linked_long)],
                    color='blue',
                    weight=2,
                    opacity=0.5
                ).add_to(m)

        # Draw lines for each heading
        for heading in segment['headings']:
            # Calculate the endpoint of the line for the heading
            distance = 0.0005  # Adjust distance for visual clarity on the map
            adjusted_heading = heading  # Adjust for clockwise from North to counterclockwise from East
            heading_rad = math.radians(adjusted_heading)

            # Calculate the end coordinates based on the heading
            end_lat = lat + distance * math.cos(heading_rad)  # Latitude change uses cos
            end_long = long + distance * math.sin(heading_rad)  # Longitude change uses sin

            # Draw a line indicating the direction of the heading
            folium.PolyLine(
                locations=[(lat, long), (end_lat, end_long)],
                color='green',
                weight=2,
                opacity=0.7
            ).add_to(m)

    # TODO make filepath/name dynamic
    segment_map_save_path = f"{base_directory}/segments_map.html"
    print(f"\tSaving segment's map to: {segment_map_save_path}")
    m.save(segment_map_save_path)

def extract_linestring_segment(line_string, coord1, coord2):
    """
    Extract a LineString segment between two coordinates, following the original LineString geometry.
    """    

    # Ensure the coordinates are in (longitude, latitude) format for shapely
    coord1 = (coord1[1], coord1[0])  # (lon, lat)
    coord2 = (coord2[1], coord2[0])  # (lon, lat)

    # Convert coordinates into Point geometries
    point1 = Point(coord1)
    point2 = Point(coord2)

    if (not line_string) or (not line_string or len(line_string.coords) < 2):
        # we have no line string, so just return an empty line string
        return LineString([coord1, coord2])

    # Project the two coordinates onto the LineString
    start_proj = line_string.interpolate(line_string.project(point1))
    end_proj = line_string.interpolate(line_string.project(point2))

    # Get all points along the LineString
    coords = list(line_string.coords)

    # Manually find the indices of the projected points
    start_idx = None
    end_idx = None
    for i, (x, y) in enumerate(coords):
        if (x, y) == (start_proj.x, start_proj.y):
            start_idx = i
        if (x, y) == (end_proj.x, end_proj.y):
            end_idx = i

    # If indices are found, extract the sublist between the two points
    if start_idx is not None and end_idx is not None:
        if start_idx < end_idx:
            extracted_coords = coords[start_idx:end_idx + 1]
        else:
            extracted_coords = coords[end_idx:start_idx + 1][::-1]  # Reverse if the end point is before the start point
    else:
        # In case indices aren't found, return an empty LineString
        extracted_coords = [coord1, coord2]

    if len(extracted_coords) < 2:
        # we dont really an extracted coords to make a line string, so just return an the basic one
        return LineString([coord1, coord2])
    # if len(extracted_coords.coords) < 2:
    #     # we dont really an extracted coords to make a line string, so just return an the basic one
    #     return LineString([coord1, coord2])

    # Return a new LineString that follows the original geometry between the two coordinates
    return LineString(extracted_coords)

def get_raw_line_string_between_node_ids(line_string, id_1, id_2):
    lat_1, long_1 = id_1.split("_")
    lat_2, long_2 = id_2.split("_")
    return list(extract_linestring_segment(line_string, (float(lat_1), float(long_1)), (float(lat_2), float(long_2))).coords)


def write_as_csv(filepath, dict):
    df = pd.DataFrame.from_dict(dict, orient='index')
    df.index.name = 'segment_id'
    df.to_csv(filepath)

def segment_key(lat, long):
    return f"{lat}_{long}"

def calculate_heading(lat1, lon1, lat2, lon2):
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    # Compute differences in coordinates
    d_lon = lon2 - lon1

    # Calculate heading using the formula
    x = math.sin(d_lon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(d_lon))
    initial_heading = math.atan2(x, y)

    # Convert to degrees and normalize to 0-360
    heading = (math.degrees(initial_heading) + 360) % 360

    return heading

def add_all_nodes_to_segments(graph, nodes, segments):
    # loop through all nodes and add them as segments
    for node_id, node in nodes.iterrows():
        lat = node.geometry.y
        long = node.geometry.x

        segment_headings = []
        segment_links = []

        successors = list(graph.successors(node_id))

        for successor_id in successors:
            successor_node = nodes.loc[successor_id]  
            successor_lat = successor_node.geometry.y
            successor_long = successor_node.geometry.x
            
            # # add segment link
            segment_links.append(segment_key(successor_lat, successor_long))

            # # calculate segment heading
            heading = calculate_heading(lat, long, successor_lat, successor_long)
            segment_headings.append(heading)


        # TODO above code not needed
        segment_headings = []
        segment_links = []
        line_strings = {}
        heading_links = {} # heading -> [link_ids] some headings may have multiple links

        segments[segment_key(lat,long)] = {
            "lat": lat,
            "long": long, 
            "headings": segment_headings, 
            "segment_links": segment_links,
            "line_strings": line_strings,
            "heading_links": heading_links
            }

def flip_linestring_coords(line):
    # Extract the coordinates
    original_coords = list(line.coords)
    # Flip each coordinate pair
    flipped_coords = [(lat, lon) for lon, lat in original_coords]
    # Create a new LineString with flipped coordinates
    return LineString(flipped_coords)

def add_segment_to_segments(segments, lat, long, headings, segment_links):
    segments[segment_key(lat,long)] = {
        "lat": lat,
        "long": long, 
        "headings": headings, 
        "segment_links": segment_links}
    



    #add_link_heading_linestring_to_segment
def add_link_heading_linestring_to_segment(segments, segment_id, link_id, heading, linestring):
    if link_id not in segments[segment_id]['segment_links']:
        # add the link
        segments[segment_id]['segment_links'].append(link_id)
        segments[segment_id]['line_strings'][link_id] = linestring
        # segments[segment_id]['heading_links'][heading] = [link_id]

    if heading not in segments[segment_id]['headings']:
        # add the heading
        segments[segment_id]['headings'].append(heading)

    if heading in segments[segment_id]['heading_links']:
        #heading is already in heading_links, so add to it...
        segments[segment_id]['heading_links'][heading].append(link_id)
    else:
        # heading is not in heading links, so create a new heading_link
        segments[segment_id]['heading_links'][heading] = [link_id]




# TODO-WORKING
def get_equally_spaced_points_from_edge(edge, num_points):
    # Extract the LineString geometry from the edge data
    geometry = edge[2].get('geometry')
    if not geometry:
        # No geometry data
        return []
    
    line = geometry  # The LineString
    total_length = line.length
    
    # Calculate distances at which to extract points
    distances = [i * total_length / (num_points - 1) for i in range(num_points)]
    
    # Extract points along the LineString
    spaced_points = [(line.interpolate(dist).y, line.interpolate(dist).x) for dist in distances]
    
    # Extract all vertices from the LineString
    vertices = list(line.coords)
    vertices_latlon = [(pt[1], pt[0]) for pt in vertices]  # Convert to (lat, lon)
    
    # Calculate headings to the next closest point in the vertices
    points_with_headings = []
    for i, spaced_point in enumerate(spaced_points):
        lat1, lon1 = spaced_point
        # Find the next closest point in the vertices
        closest_vertex_index = min(
            range(len(vertices_latlon)),
            key=lambda i: (vertices_latlon[i][0] - lat1)**2 + (vertices_latlon[i][1] - lon1)**2
        )

        if closest_vertex_index + 1 < len(vertices_latlon):
            next_point = vertices_latlon[closest_vertex_index + 1]
        else:
            next_point = vertices_latlon[closest_vertex_index]  
        
        # Calculate heading if there is a next point
        if next_point:
            lat2, lon2 = next_point
            heading = calculate_heading(lat1, lon1, lat2, lon2)
        else:
            heading = None
        
        points_with_headings.append((lat1, lon1, heading))
    return points_with_headings


def get_total_feet_from_edge(edge):
    geometry = edge[2].get('geometry')
    if not geometry:
        # no geometry data... no locations
        return 0

    line = geometry
    length_in_feet = 0
    flipped_line = flip_linestring_coords(line)
    coords = list(flipped_line.coords)

    # Calculate the geodesic length segment by segment
    for i in range(len(coords) - 1):
        start = coords[i]
        end = coords[i + 1]
        segment_length = geodesic(start, end).feet
        length_in_feet += segment_length

    return length_in_feet



def reverse_heading(heading):
    return (heading + 180) % 360


# attempts to add segments from an edge
def create_segments_from_edge(nodes, edge, segments, closed_edges):
    geometry = edge[2].get('geometry')
    no_linestring = False
    if not geometry:
        # No geometry data, so we can't extract a LineString
        no_linestring = True

    main_line_string = LineString(geometry)  # The LineString

    if edge not in closed_edges:
        # we have not processed this edge yet...
        u = edge[0]
        v = edge[1]
        data = edge[2]

        oneway = bool(data['oneway'])

        # first get the distance between the two nodes
        u_node = nodes.loc[u]
        v_node = nodes.loc[v]
        u_lat = u_node.geometry.y
        u_long = u_node.geometry.x
        v_lat = v_node.geometry.y
        v_long = v_node.geometry.x

        u_key = segment_key(u_lat, u_long)
        v_key = segment_key(v_lat, v_long)
        
        u_heading = calculate_heading(u_lat, u_long, v_lat, v_long)
        # for two way streets we need to add the reverse heading
        v_heading = calculate_heading(v_lat, v_long, u_lat, u_long)

        #########
        FEET_SPACING = 300
        # how many segments do we need to add?
        total_feet = get_total_feet_from_edge(edge)

        num_segments_to_add = int(total_feet // FEET_SPACING) + 2 # add 2 to account for the start and end (we just remove them later)
        segment_locations_headings = get_equally_spaced_points_from_edge(edge, num_segments_to_add)

        # remove the first and last segment location
        segment_locations_headings = segment_locations_headings[1:-1]

        # no locations to add? then make sure we link u to v (and potentially v to u)
        if len(segment_locations_headings) == 0:
            # cant add any intermediate segments, so we must connect the u and v nodes
            # no matter what, we need to link u to v
            line_string = get_raw_line_string_between_node_ids(main_line_string, u_key, v_key)
            add_link_heading_linestring_to_segment(segments, u_key, v_key, u_heading, line_string)

            # segments[u_key]['segment_links'].append(v_key)
            # segments[u_key]['headings'].append(u_heading)
            if not oneway:
                # then v can also point to u
                line_string_reverse = get_raw_line_string_between_node_ids(main_line_string, v_key, u_key)
                add_link_heading_linestring_to_segment(segments, v_key, u_key, v_heading, line_string_reverse)

                # segments[v_key]['segment_links'].append(u_key)
                # segments[v_key]['headings'].append(v_heading)
                
            # no segments to add, so we can end early
            return

        for i, (lat, long, heading) in enumerate(segment_locations_headings):
            location = (lat, long)
            new_segment_lat = location[0]
            new_segment_long = location[1]
            segment_key_str = segment_key(new_segment_lat, new_segment_long)


            # default
            previous_segment = u_key
            next_segment = v_key

            segment_heading = u_heading
            reverse_segment_heading = v_heading

            if i != 0:
                # previous location segment...
                previous_segment = segment_key(segment_locations_headings[i - 1][0], segment_locations_headings[i - 1][1])
                segment_heading = heading
                reverse_segment_heading = reverse_heading(heading)

            else: 
                # we are the first segment, so we need to tell node 'u' to link to us, and head to us
                node_line_string = get_raw_line_string_between_node_ids(main_line_string, u_key, segment_key_str)
                add_link_heading_linestring_to_segment(segments, u_key, segment_key_str, heading, node_line_string)
                # segments[u_key]['segment_links'].append(segment_key_str)
                # segments[u_key]['headings'].append(heading)
                segment_heading = heading

            if i != len(segment_locations_headings) - 1:
                # we are not the last segment, 
                # next location segment...
                next_segment = segment_key(segment_locations_headings[i + 1][0], segment_locations_headings[i + 1][1])
                segment_heading = heading
                reverse_segment_heading = reverse_heading(heading)

            segment_links = []
            segment_headings = []
            line_strings = {}
            heading_links = {}
            
            # since we are are going in the outbound direction of a node (u -> v) we can assume
            # that the next segment in segment_locations is segment we need to link to (no matter what)
            # if we are not oneway (two way) then we need additionally need to link to the previous segment
            
            segment_links.append(next_segment)
            segment_headings.append(segment_heading)
            heading_links[segment_heading] = [next_segment]
            if not no_linestring:
                line_strings[next_segment] = get_raw_line_string_between_node_ids(main_line_string, segment_key_str, next_segment)
            else:
                line_strings[next_segment] = None

            if not oneway:

                segment_links.append(previous_segment)
                segment_headings.append(reverse_segment_heading)
                heading_links[reverse_segment_heading] = [previous_segment]
                if not no_linestring:
                    # previous_lat, previous_long = previous_segment.split("_")
                    # linestring_between_us_and_previous = extract_linestring_segment(main_line_string, (lat, long), (float(previous_lat), float(previous_long)))
                    # line_strings[previous_segment] = list(linestring_between_us_and_previous.coords)
                    line_strings[previous_segment] = get_raw_line_string_between_node_ids(main_line_string, segment_key_str, previous_segment)
                else: 
                    line_strings[previous_segment] = None
            
            
            # add segment to segments
            if segment_key_str not in segments:
                segments[segment_key_str] = {
                    "lat": new_segment_lat,
                    "long": new_segment_long, 
                    "headings": segment_headings, 
                    "segment_links": segment_links,
                    "line_strings": line_strings,
                    "heading_links": heading_links}
                

        # add edge to closed edges
        closed_edges.append(edge)



def add_edges_between_nodes_to_segments(graph, nodes, segments):
    closed_edges = [] # list of edges that have already been processed

    # loop through all nodes and add segements between them
    for node_id, node in nodes.iterrows():
        lat = node.geometry.y
        long = node.geometry.x

        succesor_edges = graph.edges(node_id, data=True)

        # loop through all succesor edges and try to add segments within them
        for edge in succesor_edges:
            create_segments_from_edge(nodes, edge, segments, closed_edges)
            

def grab_store_all_segments(graph, base_directory):
    print("\tGrabbing all segments... This may take a few minutes")
    nodes, edges = ox.graph_to_gdfs(graph)
    segments = {} #key = lat_long, value = lat, long, headings[], segment_links[]

    add_all_nodes_to_segments(graph, nodes, segments)
    add_edges_between_nodes_to_segments(graph, nodes, segments)

    # TODO create metadata file storing this position
    # get points to center the folium map 
    center_lat = nodes.geometry.y.mean()
    center_lon = nodes.geometry.x.mean()

    output_file = f"{base_directory}/segments.csv"

    write_as_csv(output_file, segments)
    print(f"\tSegments dataset saved to: {output_file}")
    
    draw_segments_on_map(segments, center_lat, center_lon, base_directory)


def store_all_nodes_at_location(location, base_directory):
    """
        Location: string representing the location to grab the nodes from
            Example: "Arlington, VA, USA"
        Name: name of directory to store the data
    """
    # point = (38.89383718336061, -77.04345023818883)

    os.makedirs(base_directory, exist_ok=True)
    graph = ox.graph_from_place(location, network_type='drive')
    
    grab_store_all_segments(graph, base_directory)

