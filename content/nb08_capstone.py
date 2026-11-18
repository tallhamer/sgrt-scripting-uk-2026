"""08 · Capstone: plan QA across every room."""

from ._common import exercise, header
from ._dicom import dicom_cells

CELLS = [
    *header(8, "Capstone: plan QA across rooms",
            "Everything together: check every beam of a plan in every room, and report."),
    ("md", """\
Patient `ANON-012` has an SRS plan. Before treatment you want to know: **in which treatment rooms
can every beam of this plan be delivered without a collision?** That's a check across many rooms,
which is where a script beats clicking.

The steps are all from earlier notebooks:

1. read the setup and the beams from the plan (05 and 06);
2. for each room: get the clearance map (05), check the beams yourself (06), and ask MapRT (06);
3. report."""),
    *dicom_cells("srs-patient", "ANON-012"),
    ("md", """\
## 1. The setup and the beams

Notebook 06 wrote out `read_beams` in full. The same code, with a `read_setup` for the isocenter
and position, lives in `sgrt_workshop.plan`, so this notebook can stay short:"""),
    ("code", """\
from sgrt_workshop import plan

setup = plan.read_setup(dicom.plan)
print("Patient:  ", setup.patient_id)
print("Isocenter:", setup.isocenter, "mm")
print("Position: ", setup.position)

for beam in plan.read_beams(dicom.plan):
    kind = "static" if beam.gantry_rotation == "NONE" else f"arc {beam.gantry_rotation}"
    print(f"  beam {beam.number:5} {beam.delivery_type:9} {kind:7} couch {beam.couch:5.1f}°")"""),
    ("md", """\
## 2. Which rooms

A real appliance computes a map for any room. **The emulator can only replay what was recorded**,
and this patient's session was recorded in six rooms; for any other room it would substitute a map
recorded elsewhere. So the check covers those six. (On a real appliance you would loop over every
room in `client.get_treatment_rooms()`.)"""),
    ("code", """\
from sgrt_workshop import connect, packs

client = connect()
names_by_id = {room_id: name for name, room_id, _ in client.get_treatment_rooms()}
surface_id, _ = client.get_patient_surfaces(setup.patient_id)[0]

rooms = sorted(names_by_id[room_id] for room_id in packs.recorded_rooms("srs-patient"))
room_ids = {names_by_id[room_id]: room_id for room_id in packs.recorded_rooms("srs-patient")}
rooms"""),
    ("md", """\
## 3. Check every room

For each room: generate a clearance map, perform your own check of the plan's beams, and then ask
MapRT to check the beams to confirm. The results are kept in a dictionary, by room, so we can report
on them afterwards. (Six maps at about one second each on the emulator: give it a few seconds. On a
real appliance, where a map may take many seconds to over a minute, expect it to take longer.)"""),
    ("code", """\
from maprt_client import build_beam_delivery_status_request, build_map_request, check_beams

BUFFER = 2   # cm, couch and patient

results = {}
for room in rooms:
    _, (_, map_request) = build_map_request(
        isocenter=setup.isocenter,
        couch_buffer=BUFFER,      # cm
        patient_buffer=BUFFER,    # cm
        surface_id=surface_id,
        room_id=room_ids[room],
        room_scale="IEC_61217",
        patient_orientation=setup.position,
    )
    collision_map, _, _ = client.get_map(map_request)

    beams = plan.read_beams(dicom.plan)
    check_beams(beams, (collision_map, None, None), arc_check_resolution=1)

    _, beams_request = build_beam_delivery_status_request(
        isocenter=setup.isocenter,
        couch_buffer=BUFFER,      # cm
        patient_buffer=BUFFER,    # cm
        surface_id=surface_id,
        room_id=room_ids[room],
        patient_orientation=setup.position,
        beam_list=plan.beam_list(beams),
    )
    maprt_says = {str(number): safe for number, safe in client.get_beam_delivery_status(beams_request)}

    results[room] = {"map": collision_map, "beams": beams, "maprt": maprt_says}
    print(f"{room}: done")"""),
    ("md", """\
## 4. The report

One row per beam, one column per room: `✓` safe, `✗` not. Where your check and MapRT's disagree,
the cell shows `?`: a disagreement is always worth a closer look."""),
    ("code", """\
beam_names = [beam.name for beam in plan.read_beams(dicom.plan)]
short = {room: room.replace("Truebeam", "TB").strip() for room in rooms}   # shorter column headings

print(f"{'beam':8}{'type':11}" + "".join(f"{short[room]:>14}" for room in rooms))
for index, name in enumerate(beam_names):
    first = results[rooms[0]]["beams"][index]
    row = f"{name:8}{first.delivery_type:11}"
    for room in rooms:
        beam = results[room]["beams"][index]
        maprt = results[room]["maprt"][beam.number]
        mark = "?" if beam.status != maprt else ("✓" if maprt else "✗")
        row += f"{mark:>14}"
    print(row)"""),
    ("code", """\
print("Room by room, according to MapRT:")
for room in rooms:
    unsafe = [beam.name for beam in results[room]["beams"] if not results[room]["maprt"][beam.number]]
    print(f"  {room:20}", "all safe" if not unsafe else "unsafe: " + ", ".join(unsafe))"""),
    ("md", """\
## 5. The maps side by side"""),
    ("code", """\
from sgrt_workshop.plotting import plot_maps

plot_maps({room: (results[room]["map"], results[room]["beams"]) for room in rooms})"""),
    ("md", """\
Hover over a beam to see which one it is, or over the map to read the angles."""),
    ("md", """\
## What it tells you

No room clears **every** beam: the `G090` setup field (gantry 90°, couch 0°) collides in all six.
That's a setup imaging field, so the fix is to image from another angle, not to change the
treatment. In most rooms some **treatment** arcs collide too; only one room clears them all. A
report like this, run before the plan is approved, turns a collision found at the machine into a
decision made at the desk.

As always: this is a teaching tool. A clinical check needs a validated system and your
department's own procedures."""),
    *exercise(
        """\
        Ignore the setup fields: write a function `treatable_rooms(results)` that returns the rooms
        where every **TREATMENT** beam is safe according to MapRT. Print them.""",
        """\
        def treatable_rooms(results):
            treatable = []
            for room, result in results.items():
                treatment = [beam for beam in result["beams"] if beam.delivery_type == "TREATMENT"]
                if all(result["maprt"][beam.number] for beam in treatment):
                    treatable.append(room)
            return treatable

        print("Every treatment beam safe in:", treatable_rooms(results))""",
    ),
]
