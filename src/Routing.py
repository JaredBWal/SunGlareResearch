import osmnx as ox
import networkx as nx
import pandas as pd
from geopy.distance import geodesic
import os
import matplotlib.pyplot as plt

# Load sun glare data

name = "washington_dc"
script_dir = os.path.dirname(os.path.abspath(__file__))
base_directory = os.path.join(script_dir, "../data", name)
date_string = "2024-06-12_23-00-00" 
sun_glare_data_path = f"{base_directory}/sun_glare_data_{date_string}.csv"
sun_glare_df = pd.read_csv(sun_glare_data_path)


# load the road network
place_name = "washington, dc, usa"  # Replace with your desired location
G = ox.graph_from_place(place_name, network_type="drive")

# create a glare penalty
GLARE_PENALTY = 3  


# function to find nearest node
def nearest_node(graph, lat, lon):
    return ox.distance.nearest_nodes(graph, lon, lat)

# mark edges with glare risk
def add_glare_penalty(graph, glare_df):
    for _, row in glare_df.iterrows():
        node = nearest_node(graph, row["lat"], row["long"])
        for _, _, data in graph.edges(node, data=True):
            if row["has_sun_glare"]:
                # add penalty weight for edges with glare
                data["weight"] = data.get("weight", 1) * GLARE_PENALTY  
            else:
                data["weight"] = data.get("weight", 1)
    return graph

# add sun glare penalties to the graph
G_glare_penalized = add_glare_penalty(G, sun_glare_df)

origin_point = (38.887207850686245, -77.01517876315336)  
destination_point = (38.901044444849354, -77.04488235444373) 

origin_node = nearest_node(G, *origin_point)
destination_node = nearest_node(G, *destination_point)

# fastest route 
fastest_route = nx.shortest_path(G, source=origin_node, target=destination_node, weight="length")

# sun glare avoidance route
glare_avoidance_route = nx.shortest_path(G_glare_penalized, source=origin_node, target=destination_node, weight="weight")

# plot the routes using osmnx
fig, ax = ox.plot_graph_routes(
    G, 
    routes=[fastest_route, glare_avoidance_route], 
    route_colors=["red", "blue"], 
    route_linewidth=4, 
    node_size=0, 
    bgcolor="white",
    save=False
)

# Plot sun glare points as circles on the map manually
glare_points = sun_glare_df[sun_glare_df["has_sun_glare"] == True]
for _, row in glare_points.iterrows():
    ax.scatter(row["long"], row["lat"], color="black", s=100, label="Sun Glare", edgecolor="black", alpha=0.9, zorder=5)

