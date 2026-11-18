"""Reading what MapRT needs from an RT Plan: the setup and the beams.

Notebook 06 writes this code out in full, cell by cell; notebook 08 imports it from here so the
capstone stays short. The two must stay the same (a test checks they agree with the recordings).

The requests are built the way MapRT's own client (MapApp) builds them, so the emulator finds the
recorded answers: the isocenter rounded to 0.01 mm, beam numbers sent as text (as DICOM stores
them), an arc as every one of its control points' gantry angles, a static beam as one.
"""

from types import SimpleNamespace

import pydicom


def read_setup(plan_path):
    """``isocenter`` (mm, 0.01 mm), ``position`` (e.g. ``"HFS"``) and ``patient_id`` from a plan."""
    plan = pydicom.dcmread(plan_path)
    first = plan.BeamSequence[0].ControlPointSequence[0]
    return SimpleNamespace(
        isocenter=[round(float(v), 2) + 0.0 for v in first.IsocenterPosition],  # no -0.0
        position=str(plan.PatientSetupSequence[0].PatientPosition),
        patient_id=str(plan.PatientID),
    )


def read_beams(plan_path):
    """Every beam of the plan, as objects with the fields ``maprt_client.check_beams`` reads.

    Each has ``number`` (text), ``name``, ``delivery_type`` (``"TREATMENT"`` or ``"SETUP"``),
    ``couch``, ``gantry_start``, ``gantry_stop``, ``gantry_rotation`` (``"NONE"`` for a static beam,
    ``"CW"`` or ``"CC"`` for an arc), ``gantry_angles`` (every control point's, or one for a static
    beam) and ``status`` (None until a check sets it).
    """
    beams = []
    for beam in pydicom.dcmread(plan_path).BeamSequence:
        points = beam.ControlPointSequence
        rotation = str(points[0].GantryRotationDirection)
        angles = [float(point.GantryAngle) for point in points if "GantryAngle" in point]
        if rotation == "NONE":
            angles = angles[:1]
        beams.append(SimpleNamespace(
            number=str(beam.BeamNumber), name=str(beam.BeamName),
            delivery_type=str(beam.TreatmentDeliveryType),
            couch=float(points[0].PatientSupportAngle),
            gantry_start=angles[0], gantry_stop=angles[-1], gantry_rotation=rotation,
            gantry_angles=angles, status=None,
        ))
    return beams


def beam_list(beams):
    """The ``BeamList`` of a GetBeamDeliveryStatus request for these beams."""
    from maprt_client import beam_entry

    return [beam_entry(beam.number, [(angle, beam.couch) for angle in beam.gantry_angles]) for beam in beams]
