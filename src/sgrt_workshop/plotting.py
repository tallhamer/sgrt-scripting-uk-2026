"""Drawing a collision map, with a plan's beams on it (Plotly: hover shows the angles and verdicts)."""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

#: Collision dark red, clear pale gray: readable for every kind of color vision, and in print.
COLLISION, CLEAR = "#a3262a", "#eef0f2"
#: A beam that is clear (green), and one that isn't (orange: it stands out on the red collision
#: regions, where a red beam would disappear).
BEAM_CLEAR, BEAM_COLLISION = "#1a7f37", "#ff8c00"


def couch_label(column):
    """A map column's couch angle: columns run from couch 270° through 0° to 90°."""
    return (270 + column) % 360


def gantry_label(row):
    """A map row's gantry angle: rows run from gantry 180° all the way round to 179°."""
    return (180 + row) % 360


def _map_traces(collision_map, beams=None):
    """The heatmap, then each beam drawn on it (one at a time from ``check_beams``, so what is drawn
    is exactly what was checked). The axes are the angles themselves (as labels), so hovering
    reads them directly and the chart carries no per-cell text: a map stays ~0.2 MB."""
    from maprt_client import check_beams

    collision_map = np.asarray(collision_map)
    rows, columns = collision_map.shape
    couch = [f"{couch_label(c)}" for c in range(columns)]
    gantry = [f"{gantry_label(r)}" for r in range(rows)]
    traces = [go.Heatmap(
        z=collision_map, x=couch, y=gantry,
        colorscale=[[0, COLLISION], [0.5, COLLISION], [0.5, CLEAR], [1, CLEAR]], zmin=0, zmax=1,
        showscale=False,
        hovertemplate="couch %{x}°, gantry %{y}°: %{z} (1 clear, 0 collision)<extra></extra>",
    )]
    for beam in beams or []:
        status = beam.status
        _, arcs, statics = check_beams([beam], (collision_map, None, None), arc_check_resolution=1)
        if status is not None:
            beam.status = status
        color = BEAM_CLEAR if beam.status else BEAM_COLLISION
        label = f"beam {getattr(beam, 'name', '')}: <b>{'clear' if beam.status else 'COLLISION'}</b>"
        for segment in arcs:
            # A point at every gantry angle the arc covers, so hovering anywhere on it names the beam;
            # a black line under the colored one keeps it visible on red and on pale alike.
            low, high = sorted((segment.start, segment.stop))
            ys = [gantry[r] for r in range(low, high + 1)]
            xs = [couch[segment.couch]] * len(ys)
            traces.append(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="black", width=7),
                                     hoverinfo="skip", showlegend=False))
            traces.append(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=4),
                                     hovertemplate=label + "<extra>arc</extra>", showlegend=False))
        for point in statics:
            traces.append(go.Scatter(x=[couch[point.couch]], y=[gantry[point.gantry]], mode="markers",
                                     marker=dict(color=color, size=10, line=dict(color="black", width=1)),
                                     hovertemplate=label + "<extra>static beam</extra>", showlegend=False))
    return traces


def _label_axes(figure, shape, row=None, col=None):
    rows, columns = shape
    figure.update_xaxes(title_text="Couch angle", type="category",
                        tickvals=[f"{couch_label(c)}" for c in range(0, columns, 30)],
                        ticktext=[f"{couch_label(c)}°" for c in range(0, columns, 30)], row=row, col=col)
    figure.update_yaxes(title_text="Gantry angle", type="category", autorange="reversed",  # gantry 180° at the top
                        tickvals=[f"{gantry_label(r)}" for r in range(0, rows, 30)],
                        ticktext=[f"{gantry_label(r)}°" for r in range(0, rows, 30)], row=row, col=col)


def plot_map(collision_map, title=None, beams=None):
    """A collision map: couch angle across, gantry angle down; clear pale, collision red. Hover over
    it to read the angles. ``beams`` (optional; run ``maprt_client.check_beams`` first) are drawn on
    it: an arc as a line along the gantry angles it sweeps, a static beam as a dot, green if clear
    and orange if not; hover over one to see which beam it is."""
    figure = go.Figure(_map_traces(collision_map, beams))
    _label_axes(figure, np.asarray(collision_map).shape)
    figure.update_layout(title=title, width=560, height=640, margin=dict(l=70, r=20, t=50, b=60),
                         plot_bgcolor="white")
    return figure


def plot_difference(difference, title=None, labels=("clear in the first map only", "clear in the second map only")):
    """The difference of two collision maps (``first - second``): ``1`` where only the first map is
    clear (orange), ``-1`` where only the second is (blue), ``0`` where they agree (pale). Hover
    reads the angles and the value (the key is in the hover box, not per cell, so the chart stays
    small)."""
    difference = np.asarray(difference)
    rows, columns = difference.shape
    key = f"1 {labels[0]}, 0 no change, -1 {labels[1]}"
    figure = go.Figure(go.Heatmap(
        z=difference,
        x=[f"{couch_label(c)}" for c in range(columns)],
        y=[f"{gantry_label(r)}" for r in range(rows)],
        colorscale=[[0, "#1f6feb"], [1 / 3, "#1f6feb"], [1 / 3, CLEAR], [2 / 3, CLEAR],
                    [2 / 3, BEAM_COLLISION], [1, BEAM_COLLISION]],
        zmin=-1.5, zmax=1.5, showscale=False,
        hovertemplate=f"couch %{{x}}°, gantry %{{y}}°: %{{z}}<br>({key})<extra></extra>",
    ))
    _label_axes(figure, difference.shape)
    figure.update_layout(title=title, width=560, height=640, margin=dict(l=70, r=20, t=50, b=60),
                         plot_bgcolor="white")
    return figure


def plot_maps(panels, columns=3):
    """Several maps side by side: ``panels`` maps a title to ``(collision_map, beams)``."""
    titles = list(panels)
    rows = -(-len(titles) // columns)
    figure = make_subplots(rows=rows, cols=columns, subplot_titles=titles,
                           horizontal_spacing=0.07, vertical_spacing=0.08)
    for index, title in enumerate(titles):
        collision_map, beams = panels[title]
        row, col = index // columns + 1, index % columns + 1
        for trace in _map_traces(collision_map, beams):
            figure.add_trace(trace, row=row, col=col)
        _label_axes(figure, np.asarray(collision_map).shape, row=row, col=col)
    figure.update_layout(height=560 * rows, margin=dict(l=60, r=20, t=60, b=40), plot_bgcolor="white")  # the notebook's width
    return figure
