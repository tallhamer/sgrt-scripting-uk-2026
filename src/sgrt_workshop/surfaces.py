"""Showing a patient surface in the notebook: shaded, in 3D, with Plotly.

The surface is drawn in millimeters in MapRT's coordinates (the axes keep their true proportions),
lit so its shape is easy to read. Drag to turn it (freely, in any direction); to zoom, pick the magnifier in the view's
toolbar and drag; double-click to reset. Scrolling is left to the notebook: with Plotly's default,
scrolling the page past a 3D view zooms the view instead.
"""

import plotly.graph_objects as go

#: The surface color: dark magenta, #8B008B (RGB 139, 0, 139).
DARK_MAGENTA = "#8B008B"


def figure_of(mesh, title=None, face_count=40_000, color=DARK_MAGENTA):
    """The Plotly figure of a ``trimesh`` surface (:func:`show` displays it). Surfaces have
    hundreds of thousands of triangles, more than a browser turns smoothly, so it is first
    simplified to ``face_count``."""
    if len(mesh.faces) > face_count:
        mesh = mesh.simplify_quadric_decimation(face_count=face_count)
    x, y, z = mesh.vertices.T
    i, j, k = mesh.faces.T
    figure = go.Figure(go.Mesh3d(
        x=x, y=y, z=z, i=i, j=j, k=k, color=color, flatshading=False,
        lighting=dict(ambient=0.45, diffuse=0.8, specular=0.15, roughness=0.6, fresnel=0.1),
        lightposition=dict(x=0, y=-2000, z=3000),
        hoverinfo="skip",
    ))
    axis = dict(showbackground=False, gridcolor="#d0d4da", zerolinecolor="#d0d4da")
    figure.update_layout(
        title=title, height=650, margin=dict(l=0, r=0, t=50, b=0),
        scene=dict(aspectmode="data", xaxis=dict(axis, title="x (mm)"), yaxis=dict(axis, title="y (mm)"),
                   zaxis=dict(axis, title="z (mm)"),
                   camera=dict(eye=dict(x=0.35, y=-1.55, z=0.85)),  # from the side, a little above
                   dragmode="orbit"),  # turn freely in any direction (Plotly's default keeps z upright)
    )
    return figure


def show(mesh, title=None, face_count=40_000, color=DARK_MAGENTA):
    """Show a 3D view of a ``trimesh`` surface in the notebook, with scroll-to-zoom off."""
    figure_of(mesh, title, face_count, color).show(config={"scrollZoom": False})
