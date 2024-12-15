import osmnx as ox
import networkx as nx
import pandas as pd
from geopy.distance import geodesic
import os
import matplotlib.pyplot as plt

# Load sun glare data

name = "fredericksburg"
script_dir = os.path.dirname(os.path.abspath(__file__))
base_directory = os.path.join(script_dir, "../data", name)
date_string = "2024_12_12_21_00_00" 
sun_glare_data_path = f"{base_directory}/fredericksburg_sun_glare_dataset_{date_string}.csv"
sun_glare_df = pd.read_csv(sun_glare_data_path)
# sun_glare_df = pd.read_csv(data)


# Step 1: Load Road Network
place_name = "Fredericksburg, Virginia, USA"  # Replace with your desired location
G = ox.graph_from_place(place_name, network_type="drive")

# Step 2: Add Sun Glare Penalty
GLARE_PENALTY = 1000  # High cost for glare-prone segments


# Function to find nearest node
def nearest_node(graph, lat, lon):
    return ox.distance.nearest_nodes(graph, lon, lat)

# Mark edges with glare risk
def add_glare_penalty(graph, glare_df):
    for _, row in glare_df.iterrows():
        node = nearest_node(graph, row["lat"], row["long"])
        for _, _, data in graph.edges(node, data=True):
            if row["has_sun_glare"]:
                # Add a large penalty weight for edges with glare
                data["weight"] = data.get("weight", 1) * 10  # Increase weight by 10x
            else:
                data["weight"] = data.get("weight", 1)
    return graph

# Add sun glare penalties to the graph
G_glare_penalized = add_glare_penalty(G, sun_glare_df)

# Define start and end points
origin_point = (38.29671, -77.505704)  # Start lat, long
destination_point = (38.3190391, -77.4716462)  # End lat, long

origin_node = nearest_node(G, *origin_point)
destination_node = nearest_node(G, *destination_point)

# Fastest route (normal weight)
fastest_route = nx.shortest_path(G, source=origin_node, target=destination_node, weight="length")

# Sun glare avoidance route (penalized weight)
glare_avoidance_route = nx.shortest_path(G_glare_penalized, source=origin_node, target=destination_node, weight="weight")

# Plot the routes using osmnx
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

