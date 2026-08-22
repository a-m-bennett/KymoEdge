import os
import tkinter as tk
from collections import deque
from tkinter import filedialog, messagebox, ttk

import matplotlib.patches as patches
import matplotlib.ticker as ticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.widgets import RectangleSelector
import numpy as np
from skimage import color, io

# --- High-Definition / HiDPI Scaling Fix ---
try:
    import ctypes

    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


# This script is designed to be run as a standalone application, not imported as a module.
# PathfinderApp is the main class that encapsulates the GUI and core functionality for kymograph edge detection and pathfinding.
class PathfinderApp:

    def __init__(self, root):
        self.root = root
        self.root.title("KymoEdge")
        self.root.geometry("1200x1000")

        # Core App State Data
        self.raw_image_data = None  # Stores the untouched original image
        self.image_data = None  # Stores the active (potentially rotated) working image
        self.height = 0
        self.width = 0
        self.ban_selections = []  # List of tuples: (ymin, ymax, xmin, xmax)
        self.drawn_patches = []
        self.current_path = None
        self.display_dpi = 150
        self.graph = None  # Graph structure persisted and reused across updates

        # Track number of 90-degree rotations (0, 1, 2, 3)
        self.rotation_count = 0

        # UI Layout Construction
        self.setup_styles()
        self.create_widgets()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Sidebar.TFrame", background="#f0f0f0", relief="groove")
        style.configure("Canvas.TFrame", background="#ffffff")
        style.configure("Action.TButton", font=("Helvetica", 10, "bold"), padding=6)
        style.configure(
            "Status.TLabel", font=("Helvetica", 10, "italic"), foreground="#555555"
        )

    def create_widgets(self):
        self.sidebar = ttk.Frame(self.root, width=280, style="Sidebar.TFrame")
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        self.sidebar.pack_propagate(False)

        self.canvas_frame = ttk.Frame(self.root, style="Canvas.TFrame")
        self.canvas_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=5, pady=5)

        lbl_title = ttk.Label(
            self.sidebar, text="Configuration Panel", font=("Helvetica", 12, "bold")
        )
        lbl_title.pack(anchor=tk.W, padx=5, pady=10)

        # --- File Selection Options ---
        lbl_source = ttk.Label(self.sidebar, text="Image Data Source:")
        lbl_source.pack(anchor=tk.W, padx=5, pady=2)

        self.file_source_var = tk.StringVar(value="Browse Local File...")
        self.cbo_file_source = ttk.Combobox(
            self.sidebar,
            textvariable=self.file_source_var,
            values=[
                "Browse Local File...",
                "Demo1",
                "Demo2",
            ],
            state="readonly",
        )
        self.cbo_file_source.pack(fill=tk.X, padx=5, pady=2)
        self.cbo_file_source.bind("<<ComboboxSelected>>", self.on_file_source_change)

        file_frame = ttk.Frame(self.sidebar)
        file_frame.pack(fill=tk.X, padx=5, pady=2)

        self.ent_filename = ttk.Entry(file_frame)
        self.ent_filename.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        self.btn_browse = ttk.Button(
            file_frame, text="Browse...", command=self.browse_file
        )
        self.btn_browse.pack(side=tk.RIGHT)
        self.btn_load = ttk.Button(
            self.sidebar,
            text="Load Image",
            style="Action.TButton",
            command=self.load_image_engine,
        )
        self.btn_load.pack(fill=tk.X, padx=5, pady=4)

        self.btn_rotate = ttk.Button(
            self.sidebar, text="Rotate Image 90°", command=self.rotate_image_90
        )
        self.btn_rotate.pack(fill=tk.X, padx=5, pady=4)
        self.btn_rotate.config(state=tk.DISABLED)

        # --- Display Options (Grid & Scales) ---
        ttk.Separator(self.sidebar, orient="horizontal").pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(
            self.sidebar,
            text="Display Overlay Options:",
            font=("Helvetica", 9, "bold"),
        ).pack(anchor=tk.W, padx=5, pady=2)

        self.var_show_bans = tk.BooleanVar(value=True)
        chk_show_bans = ttk.Checkbutton(
            self.sidebar,
            text="Show Ban Regions Box overlays",
            variable=self.var_show_bans,
            command=self.refresh_display_canvas,
        )
        chk_show_bans.pack(anchor=tk.W, padx=5, pady=2)

        lbl_tick_freq = ttk.Label(self.sidebar, text="Grid Tick Frequency (px):")
        lbl_tick_freq.pack(anchor=tk.W, padx=5, pady=2)
        self.ent_tick_freq = ttk.Entry(self.sidebar)
        self.ent_tick_freq.insert(0, "100")
        self.ent_tick_freq.pack(fill=tk.X, padx=5, pady=2)
        self.ent_tick_freq.bind("<Return>", lambda e: self.refresh_display_canvas())

        # --- Pathfinding Jumping ---
        ttk.Separator(self.sidebar, orient="horizontal").pack(fill=tk.X, padx=5, pady=5)

        lbl_above = ttk.Label(self.sidebar, text="Jump ABOVE:")
        lbl_above.pack(anchor=tk.W, padx=5, pady=2)
        self.ent_above = ttk.Spinbox(self.sidebar, from_=1, to=5, width=5)
        self.ent_above.insert(0, "3")
        self.ent_above.pack(fill=tk.X, padx=5, pady=2)

        lbl_below = ttk.Label(self.sidebar, text="Jump BELOW:")
        lbl_below.pack(anchor=tk.W, padx=5, pady=2)
        self.ent_below = ttk.Spinbox(self.sidebar, from_=1, to=5, width=5)
        self.ent_below.insert(0, "3")
        self.ent_below.pack(fill=tk.X, padx=5, pady=2)

        # --- Export Calibration Parameters ---
        ttk.Separator(self.sidebar, orient="horizontal").pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(
            self.sidebar,
            text="Export Calibration Settings:",
            font=("Helvetica", 9, "bold"),
        ).pack(anchor=tk.W, padx=5, pady=2)

        lbl_tpp = ttk.Label(self.sidebar, text="Time per pixel (s):")
        lbl_tpp.pack(anchor=tk.W, padx=5, pady=2)
        self.ent_tpp = ttk.Entry(self.sidebar)
        self.ent_tpp.insert(0, "0.3")
        self.ent_tpp.pack(fill=tk.X, padx=5, pady=2)

        lbl_npp = ttk.Label(self.sidebar, text="Distance per pixel (nm):")
        lbl_npp.pack(anchor=tk.W, padx=5, pady=2)
        self.ent_npp = ttk.Entry(self.sidebar)
        self.ent_npp.insert(0, "1700.0")
        self.ent_npp.pack(fill=tk.X, padx=5, pady=2)

        lbl_nps = ttk.Label(self.sidebar, text="Nanometers per subunit length:")
        lbl_nps.pack(anchor=tk.W, padx=5, pady=2)
        self.ent_nps = ttk.Entry(self.sidebar)
        self.ent_nps.insert(0, "4.0")
        self.ent_nps.pack(fill=tk.X, padx=5, pady=2)

        ttk.Separator(self.sidebar, orient="horizontal").pack(
            fill=tk.X, padx=5, pady=10
        )

        # --- Actions & Status ---
        self.lbl_status = ttk.Label(
            self.sidebar,
            text="Status: Select an image source to begin.",
            wraplength=250,
            style="Status.TLabel",
        )
        self.lbl_status.pack(anchor=tk.W, padx=5, pady=5)

        self.btn_update = ttk.Button(
            self.sidebar,
            text="Compute / Update Path",
            style="Action.TButton",
            command=self.update_path_engine,
        )
        self.btn_update.pack(fill=tk.X, padx=5, pady=4)
        self.btn_update.config(state=tk.DISABLED)

        self.btn_undo_ban = ttk.Button(
            self.sidebar, text="Undo Last Ban", command=self.undo_last_ban
        )
        self.btn_undo_ban.pack(fill=tk.X, padx=5, pady=4)
        self.btn_undo_ban.config(state=tk.DISABLED)

        self.btn_clear = ttk.Button(
            self.sidebar, text="Clear All Bans", command=self.clear_all_bans
        )
        self.btn_clear.pack(fill=tk.X, padx=5, pady=4)
        self.btn_clear.config(state=tk.DISABLED)

        self.btn_export = ttk.Button(
            self.sidebar, text="Export Path Data", command=self.export_data
        )
        self.btn_export.pack(fill=tk.X, padx=5, pady=4)
        self.btn_export.config(state=tk.DISABLED)

        # --- Canvas Setup ---
        self.fig = Figure(dpi=self.display_dpi)
        self.ax = self.fig.add_subplot(111)
        self.ax.text(0.5, 0.5, "Image will load here", ha="center", va="center")
        self.ax.axis("off")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.canvas_frame)
        self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)

        self.fig.canvas.mpl_connect("button_press_event", self.on_canvas_click)

    def on_file_source_change(self, event=None):
        """Disables manual entry elements if a built-in demo configuration is picked."""
        if self.file_source_var.get() != "Browse Local File...":
            self.ent_filename.config(state=tk.DISABLED)
            self.btn_browse.config(state=tk.DISABLED)
        else:
            self.ent_filename.config(state=tk.NORMAL)
            self.btn_browse.config(state=tk.NORMAL)

    def browse_file(self):
        self.file_source_var.set("Browse Local File...")
        self.on_file_source_change()
        filepath = filedialog.askopenfilename(
            filetypes=[("TIFF Files", "*.tif;*.tiff"), ("All Files", "*.*")]
        )
        if filepath:
            self.ent_filename.config(state=tk.NORMAL)
            self.ent_filename.delete(0, tk.END)
            self.ent_filename.insert(0, filepath)

    def _resolve_demo_path(self, base_name):
        """Helper to find either .tif or .tiff variation in the directory."""
        for ext in [".tif", ".tiff"]:
            test_path = "demoFiles/" + base_name + ext
            if os.path.exists(test_path):
                return test_path
        return base_name + ".tif"  # Default fallback if neither exists

    def load_image_engine(self):
        selection = self.file_source_var.get()

        try:
            if selection in ["Demo1", "Demo2"]:
                filepath = self._resolve_demo_path(selection)
                if not os.path.exists(filepath):
                    messagebox.showerror(
                        "File Not Found",
                        f"Could not find local demo file target: '{filepath}'\n"
                        f"Please ensure it is placed in this script's folder directory.",
                    )
                    return

                self.raw_image_data = load_tiff_direct(filepath)
                self.ent_filename.config(state=tk.NORMAL)
                self.ent_filename.delete(0, tk.END)
                self.ent_filename.insert(0, filepath)
                self.ent_filename.config(state=tk.DISABLED)
            else:
                filepath = self.ent_filename.get()
                if not filepath or not os.path.exists(filepath):
                    messagebox.showerror("Error", "Invalid image file path specified.")
                    return
                self.raw_image_data = load_tiff_direct(filepath)

            # Reset the rotation count for a newly loaded image
            self.rotation_count = 0
            self.apply_image_orientation()

        except Exception as e:
            messagebox.showerror(
                "Loading Exception",
                f"Failed to successfully parse image file structure:\n{str(e)}",
            )

    def rotate_image_90(self):
        self.rotation_count = (self.rotation_count + 1) % 4
        self.apply_image_orientation()

    def apply_image_orientation(self):
        if self.raw_image_data is None:
            return

        self.image_data = np.rot90(
            self.raw_image_data, k=self.rotation_count, axes=(0, 1)
        )
        self.height, self.width = self.image_data.shape[:2]

        self.ban_selections.clear()
        self.drawn_patches.clear()
        self.current_path = None

        self.graph = create_graph_adjacency(self.image_data, max_jump=10)
        self.refresh_display_canvas()

        self.btn_rotate.config(state=tk.NORMAL)
        self.btn_update.config(state=tk.NORMAL)
        self.btn_clear.config(state=tk.NORMAL)
        self.btn_undo_ban.config(state=tk.DISABLED)
        self.btn_export.config(state=tk.DISABLED)
        self.lbl_status.config(
            text="Status: Image loaded. Rotate orientation if necessary, set jump limits, draw bans, then update path."
        )

    def refresh_display_canvas(self):
        self.fig.clear()
        self.ax = self.fig.add_subplot(111)

        display_img = np.copy(self.image_data)

        if self.current_path is not None:
            for loc in self.current_path:
                if 0 <= loc[0] < self.height and 0 <= loc[1] < self.width:
                    display_img[loc[0], loc[1]] = [0.0, 1.0, 0.0]

        self.ax.imshow(display_img, interpolation="nearest")

        try:
            tick_freq = int(self.ent_tick_freq.get())
            if tick_freq <= 0:
                tick_freq = 100
        except ValueError:
            tick_freq = 100

        self.ax.xaxis.set_major_locator(ticker.MultipleLocator(tick_freq))
        self.ax.yaxis.set_major_locator(ticker.MultipleLocator(tick_freq))

        if getattr(self, "var_show_grid", tk.BooleanVar(value=False)).get():
            self.ax.grid(color="white", linestyle="--", linewidth=0.5, alpha=0.7)

        self.ax.set_axis_on()
        self.drawn_patches.clear()

        if self.var_show_bans.get():
            for ymin, ymax, xmin, xmax in self.ban_selections:
                rect = patches.Rectangle(
                    (xmin, ymin),
                    xmax - xmin,
                    ymax - ymin,
                    linewidth=1.5,
                    edgecolor="r",
                    facecolor="none",
                )
                self.ax.add_patch(rect)
                self.drawn_patches.append(rect)

                self.ax.text(
                    xmax,
                    ymin,
                    "×",
                    color="white",
                    fontsize=9,
                    weight="bold",
                    ha="center",
                    va="center",
                    bbox=dict(
                        facecolor="red",
                        edgecolor="black",
                        boxstyle="circle,pad=0.15",
                        lw=0.5,
                    ),
                )

        self.rs = RectangleSelector(
            self.ax,
            self.on_region_select,
            useblit=True,
            button=[1],
            minspanx=5,
            minspany=5,
            spancoords="pixels",
            interactive=False,
        )

        self.fig.tight_layout()
        self.canvas.draw()

    # --- Event Handlers for Canvas Interactions ---
    def on_region_select(self, eclick, erelease):
        if self.image_data is None:
            return

        if (
            eclick.xdata is None
            or eclick.ydata is None
            or erelease.xdata is None
            or erelease.ydata is None
        ):
            return

        x1, y1 = int(eclick.xdata), int(eclick.ydata)
        x2, y2 = int(erelease.xdata), int(erelease.ydata)

        ymin, ymax = min(y1, y2), max(y1, y2)
        xmin, xmax = min(x1, x2), max(x1, x2)

        self.ban_selections.append((ymin, ymax, xmin, xmax))
        self.btn_undo_ban.config(state=tk.NORMAL)

        if self.var_show_bans.get():
            rect = patches.Rectangle(
                (xmin, ymin),
                xmax - xmin,
                ymax - ymin,
                linewidth=1.5,
                edgecolor="r",
                facecolor="none",
            )
            self.ax.add_patch(rect)
            self.drawn_patches.append(rect)

            self.ax.text(
                xmax,
                ymin,
                "×",
                color="white",
                fontsize=9,
                weight="bold",
                ha="center",
                va="center",
                bbox=dict(
                    facecolor="red",
                    edgecolor="black",
                    boxstyle="circle,pad=0.15",
                    lw=0.5,
                ),
            )
            self.canvas.draw_idle()
        else:
            self.refresh_display_canvas()

    def on_canvas_click(self, event):
        if self.image_data is None or event.x is None or event.y is None:
            return

        if event.button == 1 and (event.key is None or event.key != "control"):
            click_x_pix, click_y_pix = event.x, event.y
            target_index = -1

            for idx, (ymin, ymax, xmin, xmax) in reversed(
                list(enumerate(self.ban_selections))
            ):
                btn_x_pix, btn_y_pix = self.ax.transData.transform((xmax, ymin))

                if (click_x_pix - btn_x_pix) ** 2 + (
                    click_y_pix - btn_y_pix
                ) ** 2 <= 225:
                    target_index = idx
                    break

            if target_index != -1:
                self.ban_selections.pop(target_index)
                if len(self.ban_selections) == 0:
                    self.btn_undo_ban.config(state=tk.DISABLED)

                self.lbl_status.config(
                    text="Status: Ban region removed via close button. Click 'Compute / Update Path' to update path calculations."
                )
                self.refresh_display_canvas()
                return

        if event.button == 3 or (event.button == 1 and event.key == "control"):
            if event.xdata is None or event.ydata is None:
                return
            click_x, click_y = int(event.xdata), int(event.ydata)

            target_index = -1
            for idx, (ymin, ymax, xmin, xmax) in reversed(
                list(enumerate(self.ban_selections))
            ):
                if ymin <= click_y <= ymax and xmin <= click_x <= xmax:
                    target_index = idx
                    break

            if target_index != -1:
                self.ban_selections.pop(target_index)

                if len(self.ban_selections) == 0:
                    self.btn_undo_ban.config(state=tk.DISABLED)

                self.lbl_status.config(
                    text="Status: Ban region removed. Click 'Compute / Update Path' to update path calculations."
                )
                self.refresh_display_canvas()

    def undo_last_ban(self):
        if self.ban_selections:
            self.ban_selections.pop()
            if len(self.ban_selections) == 0:
                self.btn_undo_ban.config(state=tk.DISABLED)
            self.lbl_status.config(
                text="Status: Last ban region removed. Click 'Compute / Update Path' to update."
            )
            self.refresh_display_canvas()

    def clear_all_bans(self):
        self.ban_selections.clear()
        self.btn_undo_ban.config(state=tk.DISABLED)
        self.refresh_display_canvas()

    # --- Pathfinding Engine
    def update_path_engine(self):
        try:
            jump_above = int(self.ent_above.get())
            jump_below = int(self.ent_below.get())
            if jump_above < 0 or jump_below < 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror(
                "Validation Error", "Jump steps must be non-negative integers."
            )
            return

        self.lbl_status.config(text="Status: Re-routing optimized track network...")
        self.root.update_idletasks()

        self.graph = ban_nodes_in_regions(self.graph, self.ban_selections, self.width)
        self.current_path = path(self.graph, jump_above, jump_below)
        self.refresh_display_canvas()
        self.btn_export.config(state=tk.NORMAL)
        self.lbl_status.config(
            text=f"Status: Path updated (Above: {jump_above} | Below: {jump_below})."
        )

    # --- Data Export Engine
    def export_data(self):
        try:
            tpp = float(self.ent_tpp.get())
            npp = float(self.ent_npp.get())
            nps = float(self.ent_nps.get())
        except ValueError:
            messagebox.showerror("Error", "Calibration values must be valid numbers.")
            return

        base_suggested = os.path.splitext(self.ent_filename.get())[0] + "_refined"
        save_path = filedialog.asksaveasfilename(
            initialfile=os.path.basename(base_suggested),
            defaultextension=".txt",
            filetypes=[
                ("Text Matrix", "*.txt"),
                ("Data File", "*.dat"),
                ("CSV Comma Delimited", "*.csv"),
            ],
        )
        if save_path:
            ext = os.path.splitext(save_path)[1]
            to_output_format(
                self.current_path,
                os.path.splitext(save_path)[0],
                ext,
                time_per_pixel=tpp,
                nm_per_pixel=npp,
                nm_per_subunit=nps,
            )
            messagebox.showinfo("Success", "Data exported.")


# --- Graph & Calculation Core Engines ---


# Reads a TIFF image file and converts it to a normalized grey format suitable for processing.
def load_tiff_direct(file_path):
    img = io.imread(file_path)
    if img.ndim == 3:
        if img.shape[-1] == 4:
            img = color.rgba2rgb(img)
        gray = color.rgb2gray(img)
    else:
        gray = img.astype(np.float64)

    img = np.stack([gray] * 3, axis=-1)
    img = img.astype(np.float64)
    img = (img - img.min()) / (img.max() - img.min())
    img = np.clip(img, 0.0, 1.0)
    return img


# Create a directed graph representation of the image for pathfinding.
# Each pixel is a node, and edges connect to the next column's pixels within the jump constraints.
# Each node stores its [[neighbors], weight (intensity difference), id, position, and ban status].
def create_graph_adjacency(image_data: np.ndarray, max_jump: int = 5):
    height, width, _ = image_data.shape
    keys = [-1, -2]
    source_information = [[], 0, 0, (-1, -1), False]
    sink_information = [[], 0, height, (height, width), False]
    node_information = []

    for i in range(height):
        for j in range(width):
            node_id = i * width + j
            info_list = [[], 0, (1 + 2 * max_jump), (i, j), False]

            if j == 0:
                source_information[0].append((node_id, 0))

            if j + 1 < width:
                info_list[0].append((i * width + (j + 1), 0))

                for k in range(1, max_jump + 1):
                    if i - k >= 0:
                        info_list[0].append(((i - k) * width + (j + 1), -k))

                for k in range(1, max_jump + 1):
                    if i + k < height:
                        info_list[0].append(((i + k) * width + (j + 1), k))
            else:
                info_list[0].append((-2, 0))

            if i == height - 1 or i == height - 2 or i == 0:
                weight = 0
            else:
                dif = abs(image_data[i][j] - image_data[i + 1][j])
                weight = dif[0]

            info_list[1] = weight
            keys.append(node_id)
            node_information.append(info_list)

    all_node_information = [
        source_information,
        sink_information,
    ] + node_information
    return dict(zip(keys, all_node_information))


# Function to compute the longest path in a directed acyclic graph (DAG) using topological sorting and dynamic programming.
# First calculates the indegree of each node, then performs a topological sort using Kahn's algorithm.
# After obtaining the topological order, it iterates through each node to update the longest path weights and predecessors based on the graph's edges and weights.
# Finally, it reconstructs the longest path from the sink node back to the source using the predecessor mapping and returns the path as a list
def path(graph: dict, jump_above: int, jump_below: int):
    weight = {node_id: -float("inf") for node_id in graph}
    predecessor = {node_id: None for node_id in graph}
    weight[-1] = 0

    # Compute indegrees for topological sorting
    indegrees = {node_id: 0 for node_id in graph}
    for node_id, info in graph.items():
        for nbr, row_delta in info[0]:
            if row_delta < 0 and abs(row_delta) > jump_above:
                continue
            if row_delta > 0 and row_delta > jump_below:
                continue
            if nbr not in indegrees:
                indegrees[nbr] = 0
            indegrees[nbr] += 1

    # Perform topological sort using Kahn's algorithm
    queue = deque([n for n, d in indegrees.items() if d == 0])
    topological_order = []
    while queue:
        n = queue.popleft()
        topological_order.append(n)
        for nbr, row_delta in graph[n][0]:
            if row_delta < 0 and abs(row_delta) > jump_above:
                continue
            if row_delta > 0 and row_delta > jump_below:
                continue
            indegrees[nbr] -= 1
            if indegrees[nbr] == 0:
                queue.append(nbr)

    # Use the topological order to compute the longest path
    for node in topological_order:
        if weight[node] == -float("inf") or graph[node][4]:
            continue
        for neighbor, row_delta in graph[node][0]:
            if row_delta < 0 and abs(row_delta) > jump_above:
                continue
            if row_delta > 0 and row_delta > jump_below:
                continue
            if graph[neighbor][4]:
                continue
            candidate = weight[node] + graph[neighbor][1]
            if weight[neighbor] < candidate:
                weight[neighbor] = candidate
                predecessor[neighbor] = node

    # Reconstruct the path from the sink node back to the source
    path = []
    current_node = -2
    while current_node is not None:
        path.append(graph[current_node][3])
        current_node = predecessor[current_node]
    path.reverse()
    return path


# Applies the ban selections to the graph, marking nodes as banned based on the user specified rectangular regions.
def ban_nodes_in_regions(graph, selections, width):
    for node_id in graph:
        graph[node_id][4] = False

    for ymin, ymax, xmin, xmax in selections:
        for i in range(ymin, ymax):
            for j in range(xmin, xmax):
                node_id = i * width + j
                if node_id in graph:
                    graph[node_id][4] = True
    return graph


# Performs the final conversion of the path data into a user-friendly output format,
# applying the specified calibration parameters for time and distance.
def to_output_format(
    path: list,
    file_name: str,
    file_type: str,
    time_per_pixel,
    nm_per_pixel,
    nm_per_subunit,
):
    output_file = f"{file_name}{file_type}"
    with open(output_file, "w") as f:
        for y, x in path:
            if y == -1:
                continue

            time_val = time_per_pixel * x
            distance_nm = nm_per_pixel * y
            subunits = distance_nm / nm_per_subunit

            f.write(f"{time_val} {subunits}\n")


if __name__ == "__main__":
    main_root = tk.Tk()
    app = PathfinderApp(main_root)
    main_root.mainloop()
