# MIT License
#
# Copyright (c) 2018-2019 Tskit Developers
# Copyright (c) 2015-2017 University of Oxford
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
Module responsible for visualisations.
"""
import collections
import numbers

import numpy as np
import svgwrite

from _tskit import NULL

LEFT = "left"
RIGHT = "right"
TOP = "top"
BOTTOM = "bottom"


def check_orientation(orientation):
    if orientation is None:
        orientation = TOP
    else:
        orientation = orientation.lower()
        orientations = [LEFT, RIGHT, TOP, BOTTOM]
        if orientation not in orientations:
            raise ValueError(f"Unknown orientiation: choose from {orientations}")
    return orientation


def check_max_tree_height(max_tree_height, allow_numeric=True):
    if max_tree_height is None:
        max_tree_height = "tree"
    is_numeric = isinstance(max_tree_height, numbers.Real)
    if max_tree_height not in ["tree", "ts"] and not allow_numeric:
        raise ValueError("max_tree_height must be 'tree' or 'ts'")
    if max_tree_height not in ["tree", "ts"] and (allow_numeric and not is_numeric):
        raise ValueError(
            "max_tree_height must be a numeric value or one of 'tree' or 'ts'"
        )
    return max_tree_height


def check_tree_height_scale(tree_height_scale):
    if tree_height_scale is None:
        tree_height_scale = "time"
    if tree_height_scale not in ["time", "log_time", "rank"]:
        raise ValueError("tree_height_scale must be 'time', 'log_time' or 'rank'")
    return tree_height_scale


def check_format(format):  # noqa A002
    if format is None:
        format = "SVG"  # noqa A001
    fmt = format.lower()
    supported_formats = ["svg", "ascii", "unicode"]
    if fmt not in supported_formats:
        raise ValueError(
            "Unknown format '{}'. Supported formats are {}".format(
                format, supported_formats
            )
        )
    return fmt


def check_order(order):
    """
    Checks the specified drawing order is valid and returns the corresponding
    tree traversal order.
    """
    if order is None:
        order = "minlex"
    traversal_orders = {
        "minlex": "minlex_postorder",
        "tree": "postorder",
    }
    if order not in traversal_orders:
        raise ValueError(
            f"Unknown display order '{order}'. "
            f"Supported orders are {list(traversal_orders.keys())}"
        )
    return traversal_orders[order]


def check_x_scale(x_scale):
    """
    Checks the specified x_scale is valid and sets default if None
    """
    if x_scale is None:
        x_scale = "physical"
    x_scales = ["physical", "treewise"]
    if x_scale not in x_scales:
        raise ValueError(
            f"Unknown display x_scale '{x_scale}'. " f"Supported orders are {x_scales}"
        )
    return x_scale


def add_text_in_group(dwg, elem, x, y, text, **kwargs):
    """
    Add the text to the elem within a group. This allows text rotations to work smoothly
    """
    grp = elem.add(dwg.g(transform=f"translate({x}, {y})"))
    grp.add(dwg.text(text, **kwargs))


def draw_tree(
    tree,
    width=None,
    height=None,
    node_labels=None,
    node_colours=None,
    mutation_labels=None,
    mutation_colours=None,
    format=None,  # noqa A002
    edge_colours=None,
    tree_height_scale=None,
    max_tree_height=None,
    order=None,
):

    # See tree.draw() for documentation on these arguments.
    fmt = check_format(format)
    if fmt == "svg":
        if width is None:
            width = 200
        if height is None:
            height = 200

        def remap(original_map, new_key, none_value):
            if original_map is None:
                return None
            new_map = {}
            for key, value in original_map.items():
                if value is None:
                    new_map[key] = none_value
                else:
                    new_map[key] = {new_key: value}
            return new_map

        # Old semantics were to not draw the node if colour is None.
        # Setting opacity to zero has the same effect.
        node_attrs = remap(node_colours, "fill", {"opacity": 0})
        edge_attrs = remap(edge_colours, "stroke", {"opacity": 0})
        mutation_attrs = remap(mutation_colours, "fill", {"opacity": 0})

        node_label_attrs = None
        tree = SvgTree(
            tree,
            (width, height),
            node_labels=node_labels,
            mutation_labels=mutation_labels,
            tree_height_scale=tree_height_scale,
            max_tree_height=max_tree_height,
            node_attrs=node_attrs,
            edge_attrs=edge_attrs,
            node_label_attrs=node_label_attrs,
            mutation_attrs=mutation_attrs,
            order=order,
        )
        return tree.drawing.tostring()

    else:
        if width is not None:
            raise ValueError("Text trees do not support width")
        if height is not None:
            raise ValueError("Text trees do not support height")
        if mutation_labels is not None:
            raise ValueError("Text trees do not support mutation_labels")
        if mutation_colours is not None:
            raise ValueError("Text trees do not support mutation_colours")
        if node_colours is not None:
            raise ValueError("Text trees do not support node_colours")
        if edge_colours is not None:
            raise ValueError("Text trees do not support edge_colours")
        if tree_height_scale is not None:
            raise ValueError("Text trees do not support tree_height_scale")

        use_ascii = fmt == "ascii"
        text_tree = VerticalTextTree(
            tree,
            node_labels=node_labels,
            max_tree_height=max_tree_height,
            use_ascii=use_ascii,
            orientation=TOP,
            order=order,
        )
        return str(text_tree)


class SvgTreeSequence:
    """
    A class to draw a tree sequence in SVG format.

    See :meth:`TreeSequence.draw_svg` for a description of usage and parameters.
    """

    def __init__(
        self,
        ts,
        size=None,
        x_scale=None,
        tree_height_scale=None,
        max_tree_height=None,
        node_labels=None,
        mutation_labels=None,
        node_attrs=None,
        mutation_attrs=None,
        edge_attrs=None,
        node_label_attrs=None,
        mutation_label_attrs=None,
        root_svg_attributes=None,
        style=None,
        order=None,
    ):
        self.ts = ts
        if size is None:
            size = (200 * ts.num_trees, 200)
        x_scale = check_x_scale(x_scale)
        if root_svg_attributes is None:
            root_svg_attributes = {}
        if max_tree_height is None:
            max_tree_height = "ts"
        self.image_size = size
        self.drawing = svgwrite.Drawing(
            size=self.image_size, debug=True, **root_svg_attributes
        )
        dwg = self.drawing
        if style is not None:
            dwg.defs.add(dwg.style(style))
        root_group = dwg.add(dwg.g(class_="tree-sequence"))
        if x_scale == "physical":
            background = root_group.add(dwg.g(class_="background"))
            axis_top_padding = 20
            tick_len = (0, 5)
        else:
            axis_top_padding = 5
            tick_len = (5, 5)

        self.node_labels = {u: str(u) for u in range(ts.num_nodes)}
        # TODO add general padding arguments following matplotlib's terminology.
        self.axes_x_offset = 15
        self.axes_y_offset = 10
        self.treebox_x_offset = self.axes_x_offset + 5
        self.treebox_y_offset = self.axes_y_offset + axis_top_padding
        treebox_width = size[0] - 2 * self.treebox_x_offset
        treebox_height = size[1] - 2 * self.treebox_y_offset
        tree_width = treebox_width / ts.num_trees
        svg_trees = [
            SvgTree(
                tree,
                (tree_width, treebox_height),
                node_labels=node_labels,
                mutation_labels=mutation_labels,
                tree_height_scale=tree_height_scale,
                max_tree_height=max_tree_height,
                node_attrs=node_attrs,
                edge_attrs=edge_attrs,
                node_label_attrs=node_label_attrs,
                mutation_attrs=mutation_attrs,
                mutation_label_attrs=mutation_label_attrs,
                order=order,
            )
            for tree in ts.trees()
        ]

        ticks = []  # svg_x_pos of drawn trees, svg_x_pos of breakpoints, & labels
        y = self.treebox_y_offset
        trees = root_group.add(dwg.g(class_="trees"))
        drawing_scale = float(tree_width * ts.num_trees) / ts.sequence_length
        tree_x = self.treebox_x_offset
        break_x = self.treebox_x_offset

        for svg_tree, tree in zip(svg_trees, ts.trees()):
            svg_tree.root_group["transform"] = f"translate({tree_x} {y})"
            trees.add(svg_tree.root_group)
            ticks.append((tree_x, break_x, tree.interval[0]))
            tree_x += tree_width
            break_x += tree.span * drawing_scale
        ticks.append((tree_x, break_x, ts.sequence_length))

        # TODO - add the ability to show the commented section below as a flag
        # # Debug --- draw the tree and axes boxes
        # w = self.image_size[0] - 2 * self.treebox_x_offset
        # h = self.image_size[1] - 2 * self.treebox_y_offset
        # dwg.add(dwg.rect((self.treebox_x_offset, self.treebox_y_offset), (w, h),
        #     fill="white", fill_opacity=0, stroke="black", stroke_dasharray="15,15"))
        # w = self.image_size[0] - 2 * self.axes_x_offset
        # h = self.image_size[1] - 2 * self.axes_y_offset
        # dwg.add(dwg.rect((self.axes_x_offset, self.axes_y_offset), (w, h),
        #     fill="white", fill_opacity=0, stroke="black", stroke_dasharray="5,5"))

        axes_left = self.treebox_x_offset
        axes_right = self.image_size[0] - self.treebox_x_offset
        y = self.image_size[1] - 2 * self.axes_y_offset
        axis = root_group.add(dwg.g(class_="axis"))
        axis.add(dwg.line((axes_left, y), (axes_right, y), stroke="black"))
        integer_ticks = all(round(label) == label for _, _, label in ticks)
        label_precision = 0 if integer_ticks else 2

        for i, tick in enumerate(ticks):
            tree_x, break_x, genome_coord = tick
            if x_scale == "treewise":
                x = tree_x
            elif x_scale == "physical":
                x = break_x
                if i > 0 and i % 2 == 1:
                    # draw an alternating grey background
                    prev_tree_x, prev_break_x, _ = ticks[i - 1]
                    background.add(
                        dwg.polygon(
                            [
                                (prev_break_x, y + tick_len[1]),
                                (prev_break_x, y),
                                (prev_tree_x, y - axis_top_padding),
                                (prev_tree_x, 0),
                                (tree_x, 0),
                                (tree_x, y - axis_top_padding),
                                (break_x, y),
                                (break_x, y + tick_len[1]),
                            ],
                            fill="#F1F1F1",
                        )
                    )

            axis.add(
                dwg.line((x, y - tick_len[0]), (x, y + tick_len[1]), stroke="black")
            )
            add_text_in_group(
                dwg,
                axis,
                x,
                y + 20,
                f"{genome_coord:.{label_precision}f}",
                font_size=14,
                text_anchor="middle",
                font_weight="bold",
            )


class SvgTree:
    """
    A class to draw a tree in SVG format.

    See :meth:`Tree.draw_svg` for a description of usage and parameters.
    """

    def __init__(
        self,
        tree,
        size=None,
        tree_height_scale=None,
        max_tree_height=None,
        node_labels=None,
        mutation_labels=None,
        node_attrs=None,
        mutation_attrs=None,
        edge_attrs=None,
        node_label_attrs=None,
        mutation_label_attrs=None,
        root_svg_attributes=None,
        style=None,
        order=None,
    ):
        self.tree = tree
        self.traversal_order = check_order(order)
        if size is None:
            size = (200, 200)
        self.image_size = size
        if root_svg_attributes is None:
            root_svg_attributes = {}
        self.root_svg_attributes = root_svg_attributes
        self.drawing = self.setup_drawing()
        if style is not None:
            self.drawing.defs.add(self.drawing.style(style))
        self.treebox_x_offset = 10
        self.treebox_y_offset = 10
        self.treebox_width = size[0] - 2 * self.treebox_x_offset
        self.assign_y_coordinates(tree_height_scale, max_tree_height)
        self.node_x_coord_map = self.assign_x_coordinates(
            tree, self.treebox_x_offset, self.treebox_width
        )

        self.edge_attrs = {}
        self.node_attrs = {}
        self.node_label_attrs = {}
        for u in tree.nodes():
            self.edge_attrs[u] = {}
            if edge_attrs is not None and u in edge_attrs:
                self.edge_attrs[u].update(edge_attrs[u])
            self.node_attrs[u] = {"r": 3}
            if node_attrs is not None and u in node_attrs:
                self.node_attrs[u].update(node_attrs[u])
            label = ""
            if node_labels is None:
                label = str(u)
            elif u in node_labels:
                label = str(node_labels[u])
            self.node_label_attrs[u] = {"text": label}
            if node_label_attrs is not None and u in node_label_attrs:
                self.node_label_attrs[u].update(node_label_attrs[u])

        self.mutation_attrs = {}
        self.mutation_label_attrs = {}
        for site in tree.sites():
            for mutation in site.mutations:
                m = mutation.id
                # We need to offset the rectangle so that it's centred
                self.mutation_attrs[m] = {
                    "size": (6, 6),
                    "transform": "translate(-3 -3)",
                }
                if mutation_attrs is not None and m in mutation_attrs:
                    self.mutation_attrs[m].update(mutation_attrs[m])
                label = ""
                if mutation_labels is None:
                    label = str(m)
                elif mutation.id in mutation_labels:
                    label = str(mutation_labels[m])
                self.mutation_label_attrs[m] = {"text": label}
                if mutation_label_attrs is not None and m in mutation_label_attrs:
                    self.mutation_label_attrs[m].update(mutation_label_attrs[m])

        self.draw()

    def setup_drawing(self):
        "Return an svgwrite.Drawing object for further use"
        dwg = svgwrite.Drawing(
            size=self.image_size, debug=True, **self.root_svg_attributes
        )
        tree_class = f"tree t{self.tree.index}"
        self.root_group = dwg.add(dwg.g(class_=tree_class))
        self.edges = self.root_group.add(
            dwg.g(class_="edges", stroke="black", fill="none")
        )
        self.symbols = self.root_group.add(dwg.g(class_="symbols"))
        self.nodes = self.symbols.add(dwg.g(class_="nodes"))
        self.mutations = self.symbols.add(dwg.g(class_="mutations", fill="red"))
        self.labels = self.root_group.add(
            dwg.g(class_="labels", font_size=14, dominant_baseline="middle")
        )
        self.node_labels = self.labels.add(dwg.g(class_="nodes"))
        self.mutation_labels = self.labels.add(
            dwg.g(class_="mutations", font_style="italic")
        )
        self.left_labels = self.node_labels.add(dwg.g(text_anchor="start"))
        self.mid_labels = self.node_labels.add(dwg.g(text_anchor="middle"))
        self.right_labels = self.node_labels.add(dwg.g(text_anchor="end"))
        self.mutation_left_labels = self.mutation_labels.add(dwg.g(text_anchor="start"))
        self.mutation_right_labels = self.mutation_labels.add(dwg.g(text_anchor="end"))
        return dwg

    def assign_y_coordinates(self, tree_height_scale, max_tree_height):
        tree_height_scale = check_tree_height_scale(tree_height_scale)
        max_tree_height = check_max_tree_height(
            max_tree_height, tree_height_scale != "rank"
        )
        ts = self.tree.tree_sequence
        node_time = ts.tables.nodes.time

        if tree_height_scale == "rank":
            assert tree_height_scale == "rank"
            if max_tree_height == "tree":
                # We only rank the times within the tree in this case.
                t = np.zeros_like(node_time) + node_time[self.tree.left_root]
                for u in self.tree.nodes():
                    t[u] = node_time[u]
                node_time = t
            depth = {t: 2 * j for j, t in enumerate(np.unique(node_time))}
            node_height = [depth[node_time[u]] for u in range(ts.num_nodes)]
            max_tree_height = max(depth.values())
        else:
            assert tree_height_scale in ["time", "log_time"]
            if max_tree_height == "tree":
                max_tree_height = max(self.tree.time(root) for root in self.tree.roots)
            elif max_tree_height == "ts":
                max_tree_height = ts.max_root_time

            if tree_height_scale == "log_time":
                # add 1 so that don't reach log(0) = -inf error.
                # just shifts entire timeset by 1 year so shouldn't affect anything
                node_height = np.log(ts.tables.nodes.time + 1)
            elif tree_height_scale == "time":
                node_height = node_time

        assert float(max_tree_height) == max_tree_height

        # In pathological cases, all the roots are at 0
        if max_tree_height == 0:
            max_tree_height = 1

        # TODO should make this a parameter somewhere. This is padding to keep the
        # node labels within the treebox
        label_padding = 10
        y_padding = self.treebox_y_offset + 2 * label_padding
        mutations_over_root = any(
            any(tree.parent(mut.node) == NULL for mut in tree.mutations())
            for tree in ts.trees()
        )
        root_branch_length = 0
        height = self.image_size[1]
        if mutations_over_root:
            # Allocate a fixed about of space to show the mutations on the
            # 'root branch'
            root_branch_length = height / 10  # FIXME just draw branch??
        # y scaling
        padding_numerator = height - root_branch_length - 2 * y_padding
        if tree_height_scale == "log_time":
            # again shift time by 1 in log(max_tree_height), so consistent
            y_scale = padding_numerator / (np.log(max_tree_height + 1))
        else:
            y_scale = padding_numerator / max_tree_height
        self.node_y_coord_map = [
            height - y_scale * node_height[u] - y_padding for u in range(ts.num_nodes)
        ]

    def assign_x_coordinates(self, tree, x_start, width):
        num_leaves = len(list(tree.leaves()))
        x_scale = width / (num_leaves + 1)
        node_x_coord_map = {}
        leaf_x = x_start
        for root in tree.roots:
            for u in tree.nodes(root, order=self.traversal_order):
                if tree.is_leaf(u):
                    leaf_x += x_scale
                    node_x_coord_map[u] = leaf_x
                else:
                    child_coords = [node_x_coord_map[c] for c in tree.children(u)]
                    if len(child_coords) == 1:
                        node_x_coord_map[u] = child_coords[0]
                    else:
                        a = min(child_coords)
                        b = max(child_coords)
                        node_x_coord_map[u] = a + (b - a) / 2
        return node_x_coord_map

    def draw(self):
        dwg = self.drawing
        node_x_coord_map = self.node_x_coord_map
        node_y_coord_map = self.node_y_coord_map
        tree = self.tree

        node_mutations = collections.defaultdict(list)
        for site in tree.sites():
            for mutation in site.mutations:
                node_mutations[mutation.node].append(mutation)

        for u in tree.nodes():
            pu = node_x_coord_map[u], node_y_coord_map[u]
            node_class = f"n{u}"
            if tree.is_sample(u):
                node_class += " sample"
            self.nodes.add(
                dwg.circle(center=pu, class_=node_class, **self.node_attrs[u])
            )
            dx = 0
            dy = -5
            labels = self.mid_labels
            if tree.is_leaf(u):
                dy = 20
            elif tree.parent(u) != NULL:
                dx = 5
                if tree.left_sib(u) == NULL:
                    dx *= -1
                    labels = self.right_labels
                else:
                    labels = self.left_labels
            # TODO get rid of these manual positioning tweaks and add them
            # as offsets the user can access via a transform or something.
            add_text_in_group(
                dwg,
                labels,
                pu[0] + dx,
                pu[1] + dy,
                class_=node_class,
                **self.node_label_attrs[u],
            )
            v = tree.parent(u)
            if v != NULL:
                edge_class = f"p{v} c{u}"
                pv = node_x_coord_map[v], node_y_coord_map[v]
                path = dwg.path(
                    [("M", pu), ("V", pv[1]), ("H", pv[0])],
                    class_=edge_class,
                    **self.edge_attrs[u],
                )
                self.edges.add(path)
            else:
                # FIXME this is pretty crappy for spacing mutations over a root.
                pv = (pu[0], pu[1] - 20)

            num_mutations = len(node_mutations[u])
            delta = (pv[1] - pu[1]) / (num_mutations + 1)
            x = pu[0]
            y = pv[1] - delta
            for mutation in reversed(node_mutations[u]):
                mutation_class = f"m{mutation.id} s{mutation.site} n{u}"
                self.mutations.add(
                    dwg.rect(
                        insert=(x, y),
                        class_=mutation_class,
                        **self.mutation_attrs[mutation.id],
                    )
                )
                dx = 5
                if tree.left_sib(mutation.node) == NULL:
                    dx *= -1
                    labels = self.mutation_right_labels
                else:
                    labels = self.mutation_left_labels
                # TODO get rid of these manual positioning tweaks and add them
                # as offsets the user can access via a transform or something.
                dy = 4
                add_text_in_group(
                    dwg,
                    labels,
                    x + dx,
                    y + dy,
                    class_=mutation_class,
                    **self.mutation_label_attrs[mutation.id],
                )
                y -= delta


class TextTreeSequence:
    """
    Draw a tree sequence as horizontal line of trees.
    """

    def __init__(
        self,
        ts,
        node_labels=None,
        use_ascii=False,
        time_label_format=None,
        position_label_format=None,
        order=None,
    ):
        self.ts = ts

        time_label_format = "{:.2f}" if time_label_format is None else time_label_format
        position_label_format = (
            "{:.2f}" if position_label_format is None else position_label_format
        )

        time = ts.tables.nodes.time
        time_scale_labels = [
            time_label_format.format(time[u]) for u in range(ts.num_nodes)
        ]
        position_scale_labels = [
            position_label_format.format(x) for x in ts.breakpoints()
        ]
        trees = [
            VerticalTextTree(
                tree,
                max_tree_height="ts",
                node_labels=node_labels,
                use_ascii=use_ascii,
                order=order,
            )
            for tree in self.ts.trees()
        ]

        self.height = 1 + max(tree.height for tree in trees)
        self.width = sum(tree.width + 2 for tree in trees) - 1
        max_time_scale_label_len = max(map(len, time_scale_labels))
        self.width += 3 + max_time_scale_label_len + len(position_scale_labels[-1]) // 2

        self.canvas = np.zeros((self.height, self.width), dtype=str)
        self.canvas[:] = " "

        vertical_sep = "|" if use_ascii else "┊"
        x = 0
        time_position = trees[0].time_position
        for u, label in enumerate(map(to_np_unicode, time_scale_labels)):
            y = time_position[u]
            self.canvas[y, 0 : label.shape[0]] = label
        self.canvas[:, max_time_scale_label_len] = vertical_sep
        x = 2 + max_time_scale_label_len

        for j, tree in enumerate(trees):
            pos_label = to_np_unicode(position_scale_labels[j])
            k = len(pos_label)
            label_x = max(x - k // 2 - 2, 0)
            self.canvas[-1, label_x : label_x + k] = pos_label
            h, w = tree.canvas.shape
            self.canvas[-h - 1 : -1, x : x + w - 1] = tree.canvas[:, :-1]
            x += w
            self.canvas[:, x] = vertical_sep
            x += 2

        pos_label = to_np_unicode(position_scale_labels[-1])
        k = len(pos_label)
        label_x = max(x - k // 2 - 2, 0)
        self.canvas[-1, label_x : label_x + k] = pos_label
        self.canvas[:, -1] = "\n"

    def __str__(self):
        return "".join(self.canvas.reshape(self.width * self.height))


def to_np_unicode(string):
    """
    Converts the specified string to a numpy unicode array.
    """
    # TODO: what's the clean of doing this with numpy?
    # It really wants to create a zero-d Un array here
    # which breaks the assignment below and we end up
    # with n copies of the first char.
    n = len(string)
    np_string = np.zeros(n, dtype="U")
    for j in range(n):
        np_string[j] = string[j]
    return np_string


def get_left_neighbour(tree, traversal_order):
    """
    Returns the left-most neighbour of each node in the tree according to the
    specified traversal order. The left neighbour is the closest node in terms
    of path distance to the left of a given node.
    """
    # The traversal order will define the order of children and roots.
    # Root order is defined by this traversal, and the roots are
    # the children of -1
    children = collections.defaultdict(list)
    for u in tree.nodes(order=traversal_order):
        children[tree.parent(u)].append(u)

    left_neighbour = np.full(tree.num_nodes + 1, NULL, dtype=int)

    def find_neighbours(u, neighbour):
        left_neighbour[u] = neighbour
        for v in children[u]:
            find_neighbours(v, neighbour)
            neighbour = v

    # The children of -1 are the roots and the neighbour of all left-most
    # nodes in the tree is also -1 (NULL)
    find_neighbours(-1, -1)

    return left_neighbour[:-1]


def node_time_depth(tree, min_branch_length=None, max_tree_height="tree"):
    """
    Returns a dictionary mapping nodes in the specified tree to their depth
    in the specified tree (from the root direction). If min_branch_len is
    provided, it specifies the minimum length of each branch. If not specified,
    default to 1.
    """
    if min_branch_length is None:
        min_branch_length = {u: 1 for u in range(tree.tree_sequence.num_nodes)}
    time_node_map = collections.defaultdict(list)
    current_depth = 0
    depth = {}
    # TODO this is basically the same code for the two cases. Refactor so that
    # we use the same code.
    if max_tree_height == "tree":
        for u in tree.nodes():
            time_node_map[tree.time(u)].append(u)
        for t in sorted(time_node_map.keys()):
            for u in time_node_map[t]:
                for v in tree.children(u):
                    current_depth = max(current_depth, depth[v] + min_branch_length[v])
            for u in time_node_map[t]:
                depth[u] = current_depth
            current_depth += 2
        for root in tree.roots:
            current_depth = max(current_depth, depth[root] + min_branch_length[root])
    else:
        assert max_tree_height == "ts"
        ts = tree.tree_sequence
        for node in ts.nodes():
            time_node_map[node.time].append(node.id)
        node_edges = collections.defaultdict(list)
        for edge in ts.edges():
            node_edges[edge.parent].append(edge)

        for t in sorted(time_node_map.keys()):
            for u in time_node_map[t]:
                for edge in node_edges[u]:
                    v = edge.child
                    current_depth = max(current_depth, depth[v] + min_branch_length[v])
            for u in time_node_map[t]:
                depth[u] = current_depth
            current_depth += 2

    return depth, current_depth


class TextTree:
    """
    Draws a reprentation of a tree using unicode drawing characters written
    to a 2D array.
    """

    def __init__(
        self,
        tree,
        node_labels=None,
        max_tree_height=None,
        use_ascii=False,
        orientation=None,
        order=None,
    ):
        self.tree = tree
        self.traversal_order = check_order(order)
        self.max_tree_height = check_max_tree_height(
            max_tree_height, allow_numeric=False
        )
        self.use_ascii = use_ascii
        self.orientation = check_orientation(orientation)
        self.horizontal_line_char = "━"
        self.vertical_line_char = "┃"
        if use_ascii:
            self.horizontal_line_char = "-"
            self.vertical_line_char = "|"
        # These are set below by the placement algorithms.
        self.width = None
        self.height = None
        self.canvas = None
        # Placement of nodes in the 2D space. Nodes are positioned in one
        # dimension based on traversal ordering and by their time in the
        # other dimension. These are mapped to x and y coordinates according
        # to the orientation.
        self.traversal_position = {}  # Position of nodes in traversal space
        self.time_position = {}
        # Labels for nodes
        self.node_labels = {}

        # Set the node labels
        for u in tree.nodes():
            if node_labels is None:
                # If we don't specify node_labels, default to node ID
                self.node_labels[u] = str(u)
            else:
                # If we do specify node_labels, default an empty line
                self.node_labels[u] = self.default_node_label
        if node_labels is not None:
            for node, label in node_labels.items():
                self.node_labels[node] = label

        self._assign_time_positions()
        self._assign_traversal_positions()
        self.canvas = np.zeros((self.height, self.width), dtype=str)
        self.canvas[:] = " "
        self._draw()
        self.canvas[:, -1] = "\n"

    def __str__(self):
        return "".join(self.canvas.reshape(self.width * self.height))


class VerticalTextTree(TextTree):
    """
    Text tree rendering where root nodes are at the top and time goes downwards
    into the present.
    """

    @property
    def default_node_label(self):
        return self.vertical_line_char

    def _assign_time_positions(self):
        tree = self.tree
        # TODO when we add mutations to the text tree we'll need to take it into
        # account here. Presumably we need to get the maximum number of mutations
        # per branch.
        self.time_position, total_depth = node_time_depth(
            tree, max_tree_height=self.max_tree_height
        )
        self.height = total_depth - 1

    def _assign_traversal_positions(self):
        self.label_x = {}
        left_neighbour = get_left_neighbour(self.tree, self.traversal_order)
        x = 0
        for u in self.tree.nodes(order=self.traversal_order):
            label_size = len(self.node_labels[u])
            if self.tree.is_leaf(u):
                self.traversal_position[u] = x + label_size // 2
                self.label_x[u] = x
                x += label_size + 1
            else:
                coords = [self.traversal_position[c] for c in self.tree.children(u)]
                if len(coords) == 1:
                    self.traversal_position[u] = coords[0]
                else:
                    a = min(coords)
                    b = max(coords)
                    child_mid = int(round(a + (b - a) / 2))
                    self.traversal_position[u] = child_mid
                self.label_x[u] = self.traversal_position[u] - label_size // 2
                neighbour_x = -1
                neighbour = left_neighbour[u]
                if neighbour != NULL:
                    neighbour_x = self.traversal_position[neighbour]
                self.label_x[u] = max(neighbour_x + 1, self.label_x[u])
                x = max(x, self.label_x[u] + label_size + 1)
            assert self.label_x[u] >= 0
        self.width = x

    def _draw(self):
        if self.use_ascii:
            left_child = "+"
            right_child = "+"
            mid_parent = "+"
            mid_parent_child = "+"
            mid_child = "+"
        elif self.orientation == TOP:
            left_child = "┏"
            right_child = "┓"
            mid_parent = "┻"
            mid_parent_child = "╋"
            mid_child = "┳"
        else:
            left_child = "┗"
            right_child = "┛"
            mid_parent = "┳"
            mid_parent_child = "╋"
            mid_child = "┻"

        for u in self.tree.nodes():
            xu = self.traversal_position[u]
            yu = self.time_position[u]
            label = to_np_unicode(self.node_labels[u])
            label_len = label.shape[0]
            label_x = self.label_x[u]
            assert label_x >= 0
            self.canvas[yu, label_x : label_x + label_len] = label
            children = self.tree.children(u)
            if len(children) > 0:
                if len(children) == 1:
                    yv = self.time_position[children[0]]
                    self.canvas[yv:yu, xu] = self.vertical_line_char
                else:
                    left = min(self.traversal_position[v] for v in children)
                    right = max(self.traversal_position[v] for v in children)
                    y = yu - 1
                    self.canvas[y, left + 1 : right] = self.horizontal_line_char
                    self.canvas[y, xu] = mid_parent
                    for v in children:
                        xv = self.traversal_position[v]
                        yv = self.time_position[v]
                        self.canvas[yv:yu, xv] = self.vertical_line_char
                        mid_char = mid_parent_child if xv == xu else mid_child
                        self.canvas[y, xv] = mid_char
                    self.canvas[y, left] = left_child
                    self.canvas[y, right] = right_child
        # print(self.canvas)
        if self.orientation == TOP:
            self.canvas = np.flip(self.canvas, axis=0)
            # Reverse the time positions so that we can use them in the tree
            # sequence drawing as well.
            flipped_time_position = {
                u: self.height - y - 1 for u, y in self.time_position.items()
            }
            self.time_position = flipped_time_position


class HorizontalTextTree(TextTree):
    """
    Text tree rendering where root nodes are at the left and time goes
    rightwards into the present.
    """

    @property
    def default_node_label(self):
        return self.horizontal_line_char

    def _assign_time_positions(self):
        # TODO when we add mutations to the text tree we'll need to take it into
        # account here. Presumably we need to get the maximum number of mutations
        # per branch.
        self.time_position, total_depth = node_time_depth(
            self.tree, {u: 1 + len(self.node_labels[u]) for u in self.tree.nodes()}
        )
        self.width = total_depth

    def _assign_traversal_positions(self):
        y = 0
        for root in self.tree.roots:
            for u in self.tree.nodes(root, order=self.traversal_order):
                if self.tree.is_leaf(u):
                    self.traversal_position[u] = y
                    y += 2
                else:
                    coords = [self.traversal_position[c] for c in self.tree.children(u)]
                    if len(coords) == 1:
                        self.traversal_position[u] = coords[0]
                    else:
                        a = min(coords)
                        b = max(coords)
                        child_mid = int(round(a + (b - a) / 2))
                        self.traversal_position[u] = child_mid
            y += 1
        self.height = y - 2

    def _draw(self):
        if self.use_ascii:
            top_across = "+"
            bot_across = "+"
            mid_parent = "+"
            mid_parent_child = "+"
            mid_child = "+"
        elif self.orientation == LEFT:
            top_across = "┏"
            bot_across = "┗"
            mid_parent = "┫"
            mid_parent_child = "╋"
            mid_child = "┣"
        else:
            top_across = "┓"
            bot_across = "┛"
            mid_parent = "┣"
            mid_parent_child = "╋"
            mid_child = "┫"

        # Draw in root-right mode as the coordinates go in the expected direction.
        for u in self.tree.nodes():
            yu = self.traversal_position[u]
            xu = self.time_position[u]
            label = to_np_unicode(self.node_labels[u])
            if self.orientation == LEFT:
                # We flip the array at the end so need to reverse the label.
                label = label[::-1]
            label_len = label.shape[0]
            self.canvas[yu, xu : xu + label_len] = label
            children = self.tree.children(u)
            if len(children) > 0:
                if len(children) == 1:
                    xv = self.time_position[children[0]]
                    self.canvas[yu, xv:xu] = self.horizontal_line_char
                else:
                    bot = min(self.traversal_position[v] for v in children)
                    top = max(self.traversal_position[v] for v in children)
                    x = xu - 1
                    self.canvas[bot + 1 : top, x] = self.vertical_line_char
                    self.canvas[yu, x] = mid_parent
                    for v in children:
                        yv = self.traversal_position[v]
                        xv = self.time_position[v]
                        self.canvas[yv, xv:x] = self.horizontal_line_char
                        mid_char = mid_parent_child if yv == yu else mid_child
                        self.canvas[yv, x] = mid_char
                    self.canvas[bot, x] = top_across
                    self.canvas[top, x] = bot_across
        if self.orientation == LEFT:
            self.canvas = np.flip(self.canvas, axis=1)
            # Move the padding to the left.
            self.canvas[:, :-1] = self.canvas[:, 1:]
            self.canvas[:, -1] = " "
        # print(self.canvas)
