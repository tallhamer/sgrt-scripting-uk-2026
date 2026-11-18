"""06 · Beams and plans: checking a plan's beams against a map, and asking MapRT."""

from ._common import exercise, header
from ._dicom import dicom_cells

CELLS = [
    *header(6, "Beams and plans",
            "Checking a treatment plan's beams against a clearance map, and asking MapRT to check them."),
    ("md", """\
A clearance map says which angles are clear. A **plan** says which angles the beams use. Put them
together and you know whether the plan can be delivered without a collision. There are two ways to
find out, and we'll do both:

1. check the beams **yourself**, against the map;
2. ask **MapRT** (its GetBeamDeliveryStatus request).

This patient, `ANON-010`, had lung SBRT."""),
    *dicom_cells("lt-lung-sbrt-patient", "ANON-010"),
    ("md", """\
## The plan's beams"""),
    ("code", """\
import pydicom

plan = pydicom.dcmread(dicom.plan)

for beam in plan.BeamSequence:
    first = beam.ControlPointSequence[0]
    print(f"beam {beam.BeamNumber:>2}  {beam.BeamName:6} {beam.TreatmentDeliveryType:9} "
          f"rotation {first.GantryRotationDirection:4}  gantry {float(first.GantryAngle):5.1f}°  "
          f"couch {float(first.PatientSupportAngle):5.1f}°")"""),
    ("md", """\
Some beams are **static** (rotation `NONE`: one gantry angle) and some are **arcs** (`CW`
clockwise or `CC` counter-clockwise: the gantry sweeps while the beam is on). The `SETUP` beams
are imaging fields used to position the patient; they need clearance too.

An arc's gantry angles are listed in its *control points*: one per step of the sweep. This turns
each beam into a small record with what a collision check needs:"""),
    ("code", """\
from types import SimpleNamespace


def read_beams(plan):
    beams = []
    for beam in plan.BeamSequence:
        points = beam.ControlPointSequence
        rotation = points[0].GantryRotationDirection
        angles = [float(point.GantryAngle) for point in points if "GantryAngle" in point]
        if rotation == "NONE":
            angles = angles[:1]                     # a static beam: one angle
        beams.append(SimpleNamespace(
            number=str(beam.BeamNumber), name=beam.BeamName,
            delivery_type=beam.TreatmentDeliveryType,
            couch=float(points[0].PatientSupportAngle),
            gantry_start=angles[0], gantry_stop=angles[-1], gantry_rotation=rotation,
            gantry_angles=angles, status=None,
        ))
    return beams


beams = read_beams(plan)
for beam in beams:
    print(f"beam {beam.number}: {len(beam.gantry_angles):3} gantry angle(s), {beam.gantry_start}° to {beam.gantry_stop}°")"""),
    ("md", """\
## The map for this setup

As in notebook 05, in the room `Truebeam kV50` (a TrueBeam with its kV imager extended):"""),
    ("code", """\
from maprt_client import build_map_request
from sgrt_workshop import connect

client = connect()
room_ids = {name: room_id for name, room_id, _ in client.get_treatment_rooms()}
surface_id, _ = client.get_patient_surfaces(plan.PatientID)[0]

isocenter = [round(float(v), 2) + 0.0 for v in plan.BeamSequence[0].ControlPointSequence[0].IsocenterPosition]
position = plan.PatientSetupSequence[0].PatientPosition
room = "Truebeam kV50"

_, (_, high_res) = build_map_request(
    isocenter=isocenter,
    couch_buffer=2,      # cm
    patient_buffer=2,    # cm
    surface_id=surface_id,
    room_id=room_ids[room],
    room_scale="IEC_61217",
    patient_orientation=position,
)
collision_map, _, _ = client.get_map(high_res)"""),
    ("md", """\
## 1. Checking the beams yourself

The `check_beams` convenience function looks up the gantry angle(s) each beam uses, at its
respective couch angle, and sets the beam's `status`: `True` if every one is clear.
(`arc_check_resolution=1` checks every degree of an arc.)"""),
    ("code", """\
from maprt_client import check_beams

check_beams(beams, (collision_map, None, None), arc_check_resolution=1)

for beam in beams:
    print(f"beam {beam.number} ({beam.name}):", "clear" if beam.status else "COLLISION")"""),
    ("code", """\
from sgrt_workshop.plotting import plot_map

plot_map(collision_map, title=f"{plan.PatientID}, {room}, 2 cm buffers", beams=beams)"""),
    ("md", """\
Each arc is drawn as a line along the gantry angles it sweeps, at its couch angle; each static beam
as a dot. Green is clear, orange runs into a collision region. Hover over one to see which beam it is.

## 2. Asking MapRT

GetBeamDeliveryStatus sends the setup information and the beam settings (i.e., the beam number,
gantry angle, and couch angle) for every control point to the MapRT API as a list for evaluation.
Beam numbers are sent as text, the way DICOM stores them:"""),
    ("code", """\
from maprt_client import beam_entry, build_beam_delivery_status_request

beam_list = [beam_entry(beam.number, [(angle, beam.couch) for angle in beam.gantry_angles]) for beam in beams]

_, request = build_beam_delivery_status_request(
    isocenter=isocenter,
    couch_buffer=2,      # cm
    patient_buffer=2,    # cm
    surface_id=surface_id,
    room_id=room_ids[room],
    patient_orientation=position,
    beam_list=beam_list,
)
verdicts = client.get_beam_delivery_status(request)
verdicts"""),
    ("md", """\
MapRT answers `(beam number, is it safe)` for each beam. The numbers come back as numbers even
though we sent text, so compare them as text:"""),
    ("code", """\
maprt_says = {str(number): safe for number, safe in verdicts}

print(f"{'beam':6}{'yours':>12}{'MapRT':>12}")
for beam in beams:
    yours = "clear" if beam.status else "COLLISION"
    theirs = "safe" if maprt_says[beam.number] else "UNSAFE"
    print(f"{beam.number:6}{yours:>12}{theirs:>12}")"""),
    ("md", """\
They agree: in this room both arcs would collide. GetBeamDeliveryStatus is a **licensed** feature:
an appliance without the license answers `FeatureNotLicensed` (a `license` error), and that means
"I won't tell you", never "unsafe" (notebook 07)."""),
    *exercise(
        """\
        Check the same beams in the room `"Truebeam"` instead of `"Truebeam kV50"`: get its map, run
        `check_beams` on a fresh `read_beams(plan)`, and print which beams' verdict differs from the
        kV50 room.""",
        """\
        _, (_, request) = build_map_request(
            isocenter=isocenter,
            couch_buffer=2,      # cm
            patient_buffer=2,    # cm
            surface_id=surface_id,
            room_id=room_ids["Truebeam"],
            room_scale="IEC_61217",
            patient_orientation=position,
        )
        truebeam_map, _, _ = client.get_map(request)

        in_truebeam = read_beams(plan)
        check_beams(in_truebeam, (truebeam_map, None, None), arc_check_resolution=1)

        for here, there in zip(beams, in_truebeam):
            if here.status != there.status:
                print(f"beam {here.number}: {room} {'clear' if here.status else 'COLLISION'}, "
                      f"Truebeam {'clear' if there.status else 'COLLISION'}")""",
    ),
]
