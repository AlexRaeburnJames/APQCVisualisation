import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox, ttk
import pandas as pd
import os
from pyvis.network import Network

# === Load and Build Tree Structure ===
def load_hierarchy_from_csv(csv_path):
    df = pd.read_csv(csv_path)
    nodes = {}

    for _, row in df.iterrows():
        node_id = row['Hierarchy ID'].rstrip('.0') if str(row['Hierarchy ID']).endswith('.0') else str(row['Hierarchy ID'])
        nodes[node_id] = {
            'id': node_id,
            'name': row['Name'],
            'pcf_id': row['PCF ID'],
            'children': []
        }

    for node in nodes.values():
        if '.' in node['id']:
            parent_id = node['id'].rsplit('.', 1)[0]
            if parent_id in nodes:
                nodes[parent_id]['children'].append(node)

    return nodes

# === Recursive Filtering with Flat Node Set ===
def filter_selected_subtree(all_nodes, selected_ids):
    filtered = {}
    for sid in selected_ids:
        if sid in all_nodes:
            node = all_nodes[sid]
            filtered[sid] = {
                'id': node['id'],
                'name': node['name'],
                'pcf_id': node['pcf_id'],
                'children': []
            }

    for nid in filtered:
        parent_id = nid.rsplit('.', 1)[0] if '.' in nid else None
        if parent_id in filtered:
            filtered[parent_id]['children'].append(filtered[nid])

    return [node for node in filtered.values() if node['id'].count('.') == 0 or node['id'].rsplit('.', 1)[0] not in filtered]

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

# === Create Mode Tree Builder with Checkboxes ===
def create_mode(all_nodes):
    selection_window = tk.Toplevel()
    selection_window.title("Select Nodes")

    tree_frame = ttk.Frame(selection_window)
    tree_frame.pack(fill='both', expand=True)

    tree = ttk.Treeview(tree_frame, selectmode='none')
    tree.pack(side='left', fill='both', expand=True)
    tree.heading('#0', text='Hierarchy')

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side='right', fill='y')

    check_vars = {}

    def insert_tree_nodes(parent_tkid, node_id):
        node = all_nodes[node_id]
        var = tk.BooleanVar()
        check_vars[node_id] = var

        def get_display_text():
            return f"[{'x' if var.get() else ' '}] {node_id} - {node['name']}"

        tree.insert(parent_tkid, 'end', iid=node_id, text=get_display_text(), open=False)

        def toggle_checkbox(*_):
            tree.item(node_id, text=get_display_text())

        var.trace_add('write', toggle_checkbox)

        for child in node['children']:
            insert_tree_nodes(node_id, child['id'])

    for rid in [nid for nid in all_nodes if nid.count('.') == 0]:
        insert_tree_nodes('', rid)

    def on_tree_click(event):
        item_id = tree.identify_row(event.y)
        if item_id and item_id in check_vars:
            check_vars[item_id].set(not check_vars[item_id].get())

    tree.bind("<Button-1>", on_tree_click)

    def on_submit():
        selected_ids = [nid for nid, var in check_vars.items() if var.get()]
        filtered_tree = filter_selected_subtree(all_nodes, selected_ids)
        pd.DataFrame(selected_ids).to_csv("selected_subtree_ids.csv", index=False)
        visualize_tree(filtered_tree, filename="create_mode_tree.html")
        selection_window.destroy()

    submit_button = tk.Button(selection_window, text="Generate Tree", command=on_submit)
    submit_button.pack()

# === Mode Selection Popup ===
def choose_mode():
    mode_window = tk.Toplevel()
    mode_window.title("Choose Mode")

    mode_var = tk.StringVar(value="")

    def select_mode():
        selected = mode_var.get()
        mode_window.destroy()
        app_callback(selected)

    ttk.Label(mode_window, text="Select Mode:").pack(pady=5)

    view_rb = ttk.Radiobutton(mode_window, text="View", variable=mode_var, value="view")
    create_rb = ttk.Radiobutton(mode_window, text="Create", variable=mode_var, value="create")
    view_rb.pack(anchor='w', padx=10)
    create_rb.pack(anchor='w', padx=10)

    ttk.Button(mode_window, text="OK", command=select_mode).pack(pady=10)

# === Tkinter App ===
def start_app():
    global app_callback

    def run_mode(selected_mode):
        if selected_mode == 'view':
            filename = filedialog.askopenfilename(title="Select a CSV file", filetypes=[("CSV files", "*.csv")])
            if not filename:
                return
            all_nodes = load_hierarchy_from_csv(filename)

            root_ids = [node_id for node_id in all_nodes if node_id.count('.') == 0]

            selected = simpledialog.askstring("Select Roots", f"Available root nodes: {', '.join(root_ids)}\nEnter comma-separated root IDs:")
            if not selected:
                return

            selected_ids = [s.rstrip('.0').strip() if s.strip().endswith('.0') else s.strip() for s in selected.split(',') if s.strip().rstrip('.0') in root_ids]
            subtree = get_subtree_from_roots(all_nodes, selected_ids)

            visualize_tree(subtree, filename="view_mode_tree.html")

        elif selected_mode == 'create':
            if not os.path.exists("framework.csv"):
                messagebox.showerror("Error", "framework.csv not found")
                return
            all_nodes = load_hierarchy_from_csv("framework.csv")
            create_mode(all_nodes)

    app_callback = run_mode

    root = tk.Tk()
    root.withdraw()
    choose_mode()
    root.mainloop()

if __name__ == "__main__":
    start_app()