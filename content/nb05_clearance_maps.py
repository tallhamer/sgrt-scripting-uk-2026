"""05 · Clearance maps: building a GetMap request from the plan, and reading the map."""

from ._common import exercise, header
from ._dicom import dicom_cells

CELLS = [
    *header(5, "Clearance maps", "Asking MapRT for a clearance map, and reading it."),
    ("md", """\
## What is a clearance map?

For a single *setup* (that is, a combination of patient surface, treatment room geometry,
isocenter location, patient position, and safety margins), MapRT calculates a **clearance map**. A
**clearance map** is an evaluation of the clearance state for every possible combination of couch
and gantry angle: *clear*, or a *collision* (the gantry would come too close to the patient or the
couch). The results are placed in a 2D grid, with gantry angle on the vertical axis and couch angle
on the horizontal axis, giving the user a *map* of the solution space.

To ask for one, MapRT needs the setup:

* the **patient surface** (notebook 04) and the **treatment room** (notebook 03);
* the **isocenter**, in millimeters, and the **patient position** (head first supine, `HFS`...);
* two safety margins, the **couch buffer** and the **patient buffer**: how close the gantry may
  come, in centimeters.

The **isocenter** and **patient position** come from the treatment plan."""),
    *dicom_cells("hfs-phantom-slim", "ANON-001-SLIM"),
    ("md", """\
## The setup, from the plan

`pydicom` reads DICOM files. The isocenter is stored with each beam (every beam of this plan shares
it); we round it to 0.01 mm, the precision MapRT works to. The patient position is in the plan's
setup section (`+ 0.0` just turns a rounded `-0.0` into a plain `0.0`):"""),
    ("code", """\
import pydicom

plan = pydicom.dcmread(dicom.plan)

isocenter = [round(float(v), 2) + 0.0 for v in plan.BeamSequence[0].ControlPointSequence[0].IsocenterPosition]
position = plan.PatientSetupSequence[0].PatientPosition

print("Patient:   ", plan.PatientID)
print("Isocenter: ", isocenter, "mm")
print("Position:  ", position)"""),
    ("md", """\
The patient's surface and the room come from MapRT:"""),
    ("code", """\
from sgrt_workshop import connect

client = connect()
room_ids = {name: room_id for name, room_id, _ in client.get_treatment_rooms()}
surface_id, _ = client.get_patient_surfaces(plan.PatientID)[0]

room = "Truebeam"
print(room, room_ids[room])
print("surface", surface_id)"""),
    ("md", """\
## Building the API request

`build_map_request` turns the setup information into a MapRT request body. MapRT can compute a
clearance map at **low resolution** (every 5 to 10 degrees, quick) or **high resolution** (every
degree); this gives you both requests, and a short label describing the setup:"""),
    ("code", """\
import json

from maprt_client import build_map_request

label, (low_res, high_res) = build_map_request(
    isocenter=isocenter,
    couch_buffer=2,      # cm
    patient_buffer=2,    # cm
    surface_id=surface_id,
    room_id=room_ids[room],
    room_scale="IEC_61217",
    patient_orientation=position,
)

print("Label:", label)
print()
print("Low-resolution request:")
print(json.dumps(low_res, indent=2))
print()
print("High-resolution request:")
print(json.dumps(high_res, indent=2))"""),
    ("md", """\
The two requests differ only in `HighResolution`. Notice the buffers: you give centimeters, the
request carries millimeters (`20`).

## The reply is not JSON

GetMap is the one MapRT endpoint whose answer isn't the usual envelope. It is plain text, one line
per angle pair. `client.send` shows each reply exactly as it arrives; here are the start and the
end of both:"""),
    ("code", """\
raw_low = client.send("POST", "/integration/GetMap", low_res).text
raw_high = client.send("POST", "/integration/GetMap", high_res).text

for name, raw in (("Low-resolution", raw_low), ("High-resolution", raw_high)):
    lines = raw.split()
    print(f"{name} reply: {len(lines):,} lines")
    print("\\n".join(lines[:5]))
    print("...")
    print("\\n".join(lines[-3:]))
    print()"""),
    ("md", """\
The first line gives the number of couch and gantry angles in the map: `37,36` at low resolution
(a couch angle every 5°, a gantry angle every 10°) and `181,360` at high resolution (every degree),
so the high-resolution reply is about 50 times longer. Each line after that is `couch,gantry,isOK`
(`1` clear, `0` collision), and the last line is `DONE`, which says the map is complete
(notebook 07 shows why that matters).

The lines don't arrive in the order the map is drawn in:

* **Couch:** for each gantry angle, the couch counts *down* from 90° to 0°, then jumps to 355° (359°
  at high resolution) and carries on down to 270°.
* **Gantry:** it starts at 180°, counts up to 359°, wraps to 0° and stops at 179°.

MapRT's own screen draws the map with gantry 180° at the top and couch 270° (= -90°) on the left,
through 0°, to 90° on the right. To get the same picture, the reply has to be turned back into a
grid with both axes put in that order, minding the jumps at couch 0° and gantry 0°. A
low-resolution map also has to be spread out to one value per degree, each sample covering the
angles up to the next one.

The client module's `get_map` method sends the same request and turns the text into a grid of
numbers for you, returning a numpy *array* for convenience:"""),
    ("code", """\
collision_map, _, _ = client.get_map(high_res)
low_res_map, _, _ = client.get_map(low_res)

print("High resolution: shape", collision_map.shape, f"{collision_map.mean():.0%} clear")
print("Low resolution:  shape", low_res_map.shape, f"{low_res_map.mean():.0%} clear")"""),
    ("md", """\
Both have 360 rows, one per **gantry** angle from 180° around to 179°, and 181 columns, one per
**couch** angle from 270° (= -90°) through 0° to 90°. `get_map` spreads the low-resolution map out
to the same grid, so the same code reads either one.

## Drawing it"""),
    ("code", """\
from sgrt_workshop.plotting import plot_maps

plot_maps({
    f"High resolution ({room}, 2 cm buffers)": (collision_map, None),
    f"Low resolution ({room}, 2 cm buffers)": (low_res_map, None),
}, columns=2)"""),
    ("md", """\
Pale is clear, red is a collision. **Hover over a map** to read the couch and gantry angle under
the pointer. The red regions are where the gantry would come too close to the patient or the couch
as it turns, at that couch angle. The low-resolution map is the same picture in coarser blocks (5°
of couch by 10° of gantry): it is quicker to compute, but its edges are less exact.

To look up one pair of angles yourself: row `(gantry - 180) % 360`, column `(couch - 270) % 360`
(`%` is the remainder after division, which wraps angles around the circle):"""),
    ("code", """\
gantry, couch = 90, 0
row, column = (gantry - 180) % 360, (couch - 270) % 360

print(f"gantry {gantry}°, couch {couch}°:", "clear" if collision_map[row, column] else "COLLISION")"""),
    ("md", """\
## Bigger buffers, less room

A larger buffer keeps the gantry farther from the patient, so less of the map is clear. Here are
high-resolution maps with 2 cm and 3 cm buffers, side by side:"""),
    ("code", """\
maps = {}
for buffer in (2, 3):
    _, (_, request) = build_map_request(
        isocenter=isocenter,
        couch_buffer=buffer,      # cm
        patient_buffer=buffer,    # cm
        surface_id=surface_id,
        room_id=room_ids[room],
        room_scale="IEC_61217",
        patient_orientation=position,
    )
    grid, _, _ = client.get_map(request)
    maps[buffer] = grid
    print(f"{buffer} cm buffers: {grid.mean():.1%} clear")

plot_maps({
    "2 cm buffers": (maps[2], None),
    "3 cm buffers": (maps[3], None),
}, columns=2)"""),
    ("md", """\
The two maps are hard to tell apart by eye. Because each map is a numpy array of `1`s and `0`s,
subtracting one from the other shows exactly where they differ: `1` where an angle pair is clear
with 2 cm buffers but a collision with 3 cm, `0` where nothing changed (and `-1` where only the
3 cm map is clear, which a bigger buffer shouldn't give):"""),
    ("code", """\
from sgrt_workshop.plotting import plot_difference

difference = maps[2] - maps[3]
changed = (difference != 0).sum()

print(f"{changed:,} angle pairs changed: {changed / difference.size:.1%} of the map")
plot_difference(difference, title="2 cm minus 3 cm buffers",
                labels=("clear at 2 cm only", "clear at 3 cm only"))"""),
    ("md", """\
Orange marks the angle pairs that the 3 cm buffers take away; they lie along the edges of the
collision regions. The difference is often very small, as it is here. In some cases, though, a
small change in the buffers can make an otherwise passing beam fail: a beam whose arc runs close
to the edge of a collision region can be clear with 2 cm buffers and collide with 3 cm.
Notebook 06 checks a plan's beams against a map."""),
    *exercise(
        """\
        Write a function `is_clear(collision_map, gantry, couch)` that returns `True` if that pair of
        angles is clear. Use it to check gantry 0°, 90°, 180° and 270°, all at couch 0°.""",
        """\
        def is_clear(collision_map, gantry, couch):
            return bool(collision_map[(gantry - 180) % 360, (couch - 270) % 360])

        for gantry in (0, 90, 180, 270):
            print(f"gantry {gantry:3}°, couch 0°:", "clear" if is_clear(collision_map, gantry, 0) else "COLLISION")""",
    ),
]
