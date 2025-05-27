import os
import webbrowser
import csv
from pyvis.network import Network
import tkinter as tk
from tkinter import simpledialog

# --- Get Parent ID Function ---
def get_parent_id(hier_id):
    parts = hier_id.split('.')
    if len(parts) == 1:
        return None
    return '.'.join(parts[:-1])

# --- Load CSV Data ---
nodes = {}
edges = []
long_labels = {}

with open('framework.csv', newline='', encoding='utf-8-sig') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        node_id = row['Hierarchy ID'].strip()
        label = row['PCF ID'].strip()
        long_label = row['Name'].strip()
        nodes[node_id] = label
        long_labels[node_id] = long_label

# --- Identify Root Nodes ---
def is_root(node_id):
    return get_parent_id(node_id) not in nodes

root_nodes = {nid: long_labels[nid] for nid in nodes if is_root(nid)}

# --- Tkinter Dialog for Root Selection ---
root = tk.Tk()
root.withdraw()

root_titles = list(root_nodes.values())
root_ids = list(root_nodes.keys())

class MultiSelectDialog(simpledialog.Dialog):
    def body(self, master):
        tk.Label(master, text="Select root nodes to include:").pack()
        frame = tk.Frame(master)
        frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(frame, height=300)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self.check_frame = tk.Frame(canvas)
        canvas.create_window((0, 0), window=self.check_frame, anchor='nw')
        self.vars = []
        for title in root_titles:
            var = tk.IntVar()
            cb = tk.Checkbutton(self.check_frame, text=title, variable=var, anchor="w", justify="left")
            cb.pack(fill="x", anchor="w")
            self.vars.append(var)
        return None

    def apply(self):
        self.result = [root_ids[i] for i, var in enumerate(self.vars) if var.get() == 1]

dialog = MultiSelectDialog(root)
selected_roots = dialog.result or []
if not selected_roots:
    print("No roots selected. Exiting.")
    exit()

# --- Filter Descendants ---
def is_descendant_of_root(node_id, roots):
    return any(node_id == root_id or node_id.startswith(root_id + '.') for root_id in roots)

filtered_nodes = {
    nid: (nodes[nid], long_labels[nid])
    for nid in nodes if is_descendant_of_root(nid, selected_roots)
}
filtered_edges = []

for nid in filtered_nodes:
    parent_id = get_parent_id(nid)
    if parent_id and parent_id in filtered_nodes:
        filtered_edges.append((parent_id, nid))

# --- Build Graph ---
net = Network(directed=True, height="100vh", width="calc(100vw - 320px)")

for nid, (label, long_label) in filtered_nodes.items():
    net.add_node(
        nid,
        label=label,
        title=long_label,
        shape='box',
        color={
            'background': 'black',
            'border': 'black',
            'highlight': {
                'background': 'white',
                'border': 'black'
            },
            'hover': {
                'background': 'white',
                'border': 'black'
            }
        },
        font={
            'color': 'white',
            'align': 'center',
            'highlight': {
                'color': 'black'
            }
        }
    )

for parent, child in filtered_edges:
    net.add_edge(parent, child)

net.set_options('''{
  "layout": {
    "hierarchical": {
      "enabled": true,
      "direction": "LR",
      "sortMethod": "directed",
      "levelSeparation": 300,
      "nodeSpacing": 75,
      "treeSpacing": 200
    }
  },
  "edges": {
    "color": {
      "color": "black",
      "highlight": "black",
      "hover": "black"
    },
    "width": 1,
    "hoverWidth": 3,
    "selectionWidth": 3,
    "smooth": false,
    "arrows": {
      "to": {
        "enabled": true,
        "scaleFactor": 1.5
      }
    }
  },
  "nodes": {
    "shape": "box",
    "font": {
      "face": "Arial",
      "color": "white",
      "align": "center"
    },
    "color": {
      "background": "black",
      "border": "black",
      "highlight": {
        "background": "white",
        "border": "black"
      },
      "hover": {
        "background": "white",
        "border": "black"
      }
    }
  },
  "interaction": {
    "hover": true,
    "navigationButtons": true
  },
  "physics": {
    "enabled": true
  }
}''')

# --- Export HTML ---
output_file = os.path.abspath("top_down_tree.html")
net.write_html(output_file)

# --- Fix table row generation and inject sidebar with search ---
table_rows = "".join(
    f"<tr onclick=\"highlightNodePath('{nid}'); this.classList.add('active-row');" +
    "Array.from(this.parentElement.children).forEach(row => row !== this && row.classList.remove('active-row'))\" " +
    f"style='height: 3em;'><td>{label}</td><td>{long_label}</td></tr>"
    for nid, (label, long_label) in filtered_nodes.items()
)
table_html = f"""
<style>
.active-row {{ background-color: black; color: white; }}
td {{ padding: 5px; }}
</style>
<div id='sidebar' style='position: fixed; right: 0; top: 0; width: 300px; height: 100%; overflow-y: auto; background: #f5f5f5; border-left: 1px solid #ccc; padding: 10px;'>
  <h3>Node Details</h3>
  <input type='text' id='searchInput' onkeyup='filterTable()' placeholder='Search for names..' style='width:100%;margin-bottom:10px;padding:5px;'>
  <table id='nodeTable' border='1' style='width: 100%; border-collapse: collapse;'>
    <thead>
      <tr><th>Label</th><th>Name</th></tr>
    </thead>
    <tbody>
      {table_rows}
    </tbody>
  </table>
</div>
<script>
function filterTable() {{
  var input = document.getElementById("searchInput");
  var filter = input.value.toLowerCase();
  var table = document.getElementById("nodeTable");
  var tr = table.getElementsByTagName("tr");
  for (var i = 1; i < tr.length; i++) {{
    var td1 = tr[i].getElementsByTagName("td")[0];
    var td2 = tr[i].getElementsByTagName("td")[1];
    if (td1 && td2) {{
      var txtValue = td1.textContent || td1.innerText;
      var txtValue2 = td2.textContent || td2.innerText;
      if (txtValue.toLowerCase().indexOf(filter) > -1 || txtValue2.toLowerCase().indexOf(filter) > -1) {{
        tr[i].style.display = "";
      }} else {{
        tr[i].style.display = "none";
      }}
    }}
  }}
}}
</script>
"""

with open(output_file, 'r', encoding='utf-8') as f:
    html = f.read()

# Inject sidebar before </body>
html = html.replace("</body>", table_html + "</body>")

# Inject JS
js_code = """
// JavaScript injection replacement
function highlightNodePath(nodeId) {
    var nodesToHighlight = new Set();
    var edgesToHighlight = new Set();

    function findParents(nid) {
        nodesToHighlight.add(nid);
        var connectedEdges = network.getConnectedEdges(nid);
        for (var i = 0; i < connectedEdges.length; i++) {
            var edge = network.body.data.edges.get(connectedEdges[i]);
            if (edge.to === nid) {
                edgesToHighlight.add(edge.id);
                findParents(edge.from);
            }
        }
    }

    findParents(nodeId);

    network.selectNodes([nodeId]);
    network.focus(nodeId, {
        scale: 1.0,
        animation: {
            duration: 500,
            easingFunction: "easeInOutQuad"
        }
    });

    network.body.data.nodes.update(
        network.body.data.nodes.get().map(function(node) {
            if (nodesToHighlight.has(node.id)) {
                return {
                    id: node.id,
                    color: {
                        background: 'white',
                        border: 'black'
                    },
                    font: { color: 'black' }
                };
            } else {
                return {
                    id: node.id,
                    color: {
                        background: 'black',
                        border: 'black'
                    },
                    font: { color: 'white' }
                };
            }
        })
    );

    network.body.data.edges.update(
        network.body.data.edges.get().map(function(edge) {
            if (edgesToHighlight.has(edge.id)) {
                return {
                    id: edge.id,
                    color: 'black',
                    width: 3
                };
            } else {
                return {
                    id: edge.id,
                    color: 'gray',
                    width: 1
                };
            }
        })
    );
}

network.on("selectNode", function(params) {
    if (params.nodes.length > 0) {
        highlightNodePath(params.nodes[0]);
    }
});

network.on("deselectNode", function(params) {
    network.body.data.nodes.update(
        network.body.data.nodes.get().map(function(node) {
            return {
                id: node.id,
                color: {
                    background: 'black',
                    border: 'black'
                },
                font: { color: 'white' }
            };
        })
    );

    network.body.data.edges.update(
        network.body.data.edges.get().map(function(edge) {
            return {
                id: edge.id,
                color: 'black',
                width: 1
            };
        })
    );
});
"""

insert_pos = html.rfind("</script>")
if insert_pos != -1:
    html = html[:insert_pos] + js_code + html[insert_pos:]

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html)

# --- Open in Browser ---
webbrowser.open(f"file://{output_file}")
