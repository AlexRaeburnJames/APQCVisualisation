import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import pandas as pd
import os
from pyvis.network import Network

# === Load and Build Tree Structure ===
def load_hierarchy_from_csv(csv_path):
    df = pd.read_csv(csv_path)
    nodes = {}

    # Create node dictionary
    for _, row in df.iterrows():
        node_id = row['Hierarchy ID'].rstrip('.0') if row['Hierarchy ID'].endswith('.0') else row['Hierarchy ID']
        nodes[node_id] = {
            'id': node_id,
            'name': row['Name'],
            'pcf_id': row['PCF ID'],
            'children': []
        }

    # Assign children based on ID hierarchy
    for node in nodes.values():
        if '.' in node['id']:
            parent_id = node['id'].rsplit('.', 1)[0]
            if parent_id in nodes:
                nodes[parent_id]['children'].append(node)

    return nodes

# === Recursive Filtering ===
def get_subtree_from_roots(all_nodes, selected_root_ids):
    def collect_descendants(node):
        result = {
            'id': node['id'],
            'name': node['name'],
            'pcf_id': node['pcf_id'],
            'children': [collect_descendants(child) for child in node['children']]
        }
        return result

    return [collect_descendants(all_nodes[rid]) for rid in selected_root_ids if rid in all_nodes]

# === Visualization ===
def visualize_tree(tree_roots, filename='tree_view.html'):
    net = Network(directed=True)
    net.set_options("""
    {
      "layout": {
        "hierarchical": {
          "direction": "LR",
          "sortMethod": "directed",
          "levelSeparation": 600
        }
      },
      "interaction": {
        "dragNodes": false,
        "dragView": true
      },
      "physics": {
        "enabled": false
      }
    }
    """)

    def add_nodes(node, parent=None):
        net.add_node(node['id'], label=node['name'], shape='box', color='#000000', font={'color': '#FFFFFF'})
        if parent:
            net.add_edge(parent['id'], node['id'])
        for child in node['children']:
            add_nodes(child, node)

    for root in tree_roots:
        add_nodes(root)

    net.show(filename, notebook=False)

# === Tkinter App ===
def start_app():
    root = tk.Tk()
    root.withdraw()

    filename = filedialog.askopenfilename(title="Select a CSV file", filetypes=[("CSV files", "*.csv")])
    if not filename:
        return

    all_nodes = load_hierarchy_from_csv(filename)

    import json
    print("\n=== Full Tree (Flat JSON Form) ===")
    print(json.dumps(all_nodes, indent=2))
    print("=== End Tree ===\n")

    root_ids = [node_id for node_id in all_nodes if node_id.count('.') == 0]

    selected = simpledialog.askstring("Select Roots", f"Available root nodes (ending in .0): {', '.join(root_ids)}\nEnter comma-separated root IDs:")
    if not selected:
        return

    selected_ids = [s.rstrip('.0').strip() if s.strip().endswith('.0') else s.strip() for s in selected.split(',') if s.strip().rstrip('.0') in root_ids]
    subtree = get_subtree_from_roots(all_nodes, selected_ids)

    visualize_tree(subtree, filename="view_mode_tree.html")

if __name__ == "__main__":
    start_app()
