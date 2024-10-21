#!/usr/bin/env python3
"""
generate_interactive_graph.py

A script to convert a DOT file into an interactive HTML graph using PyVis.
Features:
- Hierarchical layout (Left to Right)
- Colored clusters/groups
- Click to collapse/expand connected nodes
"""

import sys
import os
import networkx as nx
import pydot
from pyvis.network import Network
import json
import random

def parse_dot_file(dot_file_path):
    """
    Parse the DOT file and return a NetworkX graph and clusters.

    Parameters:
    - dot_file_path (str): Path to the DOT file.

    Returns:
    - nx_graph (networkx.DiGraph): The parsed graph.
    - clusters (dict): Mapping of node names to their cluster labels.
    """
    try:
        # Load the DOT file using pydot
        (pydot_graph,) = pydot.graph_from_dot_file(dot_file_path)
        # Convert pydot graph to NetworkX graph
        nx_graph = nx.nx_pydot.from_pydot(pydot_graph)
        
        # Extract clusters (subgraphs)
        clusters = {}
        for subgraph in pydot_graph.get_subgraphs():
            cluster_name = subgraph.get_name().strip('"')
            # Ignore internal cluster names like 'cluster_...'
            if cluster_name.startswith("cluster_"):
                cluster_label = subgraph.get_label()
                # Clean the label by removing quotes
                if isinstance(cluster_label, list):
                    cluster_label = cluster_label[0]
                cluster_label = cluster_label.strip('"') if cluster_label else cluster_name
                for node in subgraph.get_nodes():
                    node_name = node.get_name().strip('"')
                    # Exclude special nodes like 'node [shape=box ...]'
                    if node_name.startswith('"') and node_name.endswith('"'):
                        node_name = node_name[1:-1]
                    clusters[node_name] = cluster_label
        return nx_graph, clusters
    except Exception as e:
        print(f"Error reading DOT file: {e}")
        sys.exit(1)

def clean_attribute(value):
    """
    Clean attribute values by removing surrounding quotes.

    Parameters:
    - value: The attribute value to clean.

    Returns:
    - str: Cleaned attribute value.
    """
    if isinstance(value, str):
        return value.strip('"')
    return value

def generate_group_styles(clusters):
    """
    Generate unique styles for each group based on clusters.

    Parameters:
    - clusters (dict): Mapping of node names to their cluster labels.

    Returns:
    - dict: Styles for each group.
    """
    unique_clusters = set(clusters.values())
    colors = generate_unique_colors(len(unique_clusters))
    group_styles = {}
    for cluster, color in zip(unique_clusters, colors):
        group_styles[cluster] = {
            "color": {
                "background": color,
                "border": "#2B7CE9"  # Default border color
            }
        }
    return group_styles

def generate_unique_colors(n):
    """
    Generate a list of unique hexadecimal colors.

    Parameters:
    - n (int): Number of unique colors to generate.

    Returns:
    - list: List of color strings in HEX format.
    """
    random.seed(42)  # For reproducibility
    colors = []
    for _ in range(n):
        color = "#%06x" % random.randint(0, 0xFFFFFF)
        colors.append(color)
    return colors

def create_interactive_graph(nx_graph, clusters, output_html="interactive_graph.html"):
    """
    Create an interactive graph using PyVis and save it as an HTML file.

    Parameters:
    - nx_graph (networkx.DiGraph): The NetworkX graph.
    - clusters (dict): Mapping of node names to their cluster labels.
    - output_html (str): Output HTML file name.
    """
    # Initialize PyVis network
    net = Network(height="1000px", width="100%", directed=True, bgcolor="#ffffff", font_color="black")
    
    # Set hierarchical layout
    net.barnes_hut()
    
    # Generate group styles
    group_styles = generate_group_styles(clusters)
    
    # Add nodes with attributes
    for node, data in nx_graph.nodes(data=True):
        node_id = node
        label = clean_attribute(data.get('label', node))
        title = clean_attribute(data.get('tooltip', ''))
        url = clean_attribute(data.get('URL', ''))
        color = clean_attribute(data.get('fillcolor', '#97C2FC'))  # Default color
        shape = 'box' if data.get('shape') == 'box' else 'ellipse'
        font = clean_attribute(data.get('fontname', 'Helvetica'))
        fontsize = clean_attribute(data.get('fontsize', '14'))
        
        # Convert fontsize to integer
        try:
            size = int(float(fontsize))
        except ValueError:
            size = 14  # Default size if conversion fails
        
        # Assign color
        node_color = color if 'fillcolor' in data else '#97C2FC'
        
        # Assign group based on cluster
        group = clusters.get(node, 'default')
        
        net.add_node(
            node_id,
            label=label.strip('<>'),
            title=title,
            url=url,
            color=node_color,
            shape=shape,
            font={'face': font, 'size': size},
            group=group
        )
    
    # Add edges with attributes
    for source, target, data in nx_graph.edges(data=True):
        label = clean_attribute(data.get('label', ''))
        title = clean_attribute(data.get('tooltip', ''))
        url = clean_attribute(data.get('URL', ''))
        color = clean_attribute(data.get('color', '#848484'))  # Default color
        arrows = clean_attribute(data.get('arrowhead', 'normal'))
        style = clean_attribute(data.get('style', 'solid'))
        
        # Clean and convert penwidth
        penwidth_str = clean_attribute(data.get('penwidth', '1.0'))
        try:
            width = float(penwidth_str)
        except ValueError:
            width = 1.0  # Default width if conversion fails
        
        net.add_edge(
            source,
            target,
            title=title,
            color=color,
            arrows=arrows,
            width=width,
            dashes=True if style == "dashed" else False,
            smooth=True  # For curved lines
        )
    
    # Define network options
    options = {
        "physics": {
            "barnesHut": {
                "gravitationalConstant": -8000,
                "springConstant": 0.001,
                "springLength": 200
            },
            "minVelocity": 0.75
        },
        "edges": {
            "color": {
                "inherit": True
            },
            "smooth": {
                "type": "continuous"
            }
        },
        "nodes": {
            "font": {
                "size": 14
            }
        },
        "groups": group_styles,  # Include generated group styles
        "layout": {
            "hierarchical": {
                "enabled": True,
                "direction": "LR",  # Left to Right
                "sortMethod": "hubsize"
            }
        }
    }
    
    # Convert options to JSON string
    options_json = json.dumps(options)
    
    # Apply network options
    net.set_options(options_json)
    
    # Generate and save the interactive graph
    try:
        net.show(output_html, notebook=False)
        print(f"Interactive graph generated: {output_html}")
    except AttributeError as e:
        print(f"Error generating interactive graph: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while generating the interactive graph: {e}")
        sys.exit(1)
    
    # Inject custom JavaScript for collapse/expand functionality
    inject_custom_js(output_html)

def inject_custom_js(output_html):
    """
    Inject custom JavaScript into the generated HTML file to add collapse/expand functionality.

    Parameters:
    - output_html (str): The HTML file to modify.
    """
    try:
        with open(output_html, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        # Custom JavaScript for collapse/expand
        custom_js = """
        <script type="text/javascript">
            // Function to toggle visibility of connected nodes
            function toggleNode(nodeId) {
                var connectedNodes = network.getConnectedNodes(nodeId);
                var connectedEdges = network.getConnectedEdges(nodeId);
                
                connectedNodes.forEach(function(n) {
                    var node = nodes.get(n);
                    if (node.hidden === undefined || node.hidden === false) {
                        node.hidden = true;
                        nodes.update(node);
                    } else {
                        node.hidden = false;
                        nodes.update(node);
                    }
                });
                
                connectedEdges.forEach(function(e) {
                    var edge = edges.get(e);
                    if (edge.hidden === undefined || edge.hidden === false) {
                        edge.hidden = true;
                        edges.update(edge);
                    } else {
                        edge.hidden = false;
                        edges.update(edge);
                    }
                });
            }

            // Add event listener for node clicks
            network.on("click", function(params) {
                if (params.nodes.length === 1) {
                    var nodeId = params.nodes[0];
                    toggleNode(nodeId);
                }
            });
        </script>
        """
        
        # Find the position of the closing </body> tag
        insert_position = html_content.rfind("</body>")
        if insert_position == -1:
            print("Error: </body> tag not found in the HTML file.")
            return
        
        # Insert the custom JavaScript before </body>
        html_content = html_content[:insert_position] + custom_js + html_content[insert_position:]
        
        # Write the modified HTML back to the file
        with open(output_html, 'w', encoding='utf-8') as file:
            file.write(html_content)
        
        print("Custom JavaScript injected for collapse/expand functionality.")
    except Exception as e:
        print(f"Error injecting custom JavaScript: {e}")

def main():
    """
    Main function to execute the script.
    """
    if len(sys.argv) != 2:
        print("Usage: python generate_interactive_graph.py <path_to_dot_file>")
        sys.exit(1)
    
    dot_file_path = sys.argv[1]
    
    if not os.path.isfile(dot_file_path):
        print(f"Specified DOT file does not exist: {dot_file_path}")
        sys.exit(1)
    
    # Parse the DOT file and extract clusters
    nx_graph, clusters = parse_dot_file(dot_file_path)
    
    # Create the interactive graph
    create_interactive_graph(nx_graph, clusters)

if __name__ == "__main__":
    main()
