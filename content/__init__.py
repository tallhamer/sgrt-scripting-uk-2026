"""The notebooks, in order: ``(filename, cells)``. ``scripts/build_notebooks.py`` writes them."""

from . import (
    nb00_start_here,
    nb01_setup_and_token,
    nb02_replies_and_errors,
    nb03_treatment_rooms,
    nb04_patient_surfaces,
    nb05_clearance_maps,
    nb06_beams_and_plans,
    nb07_robustness,
    nb08_capstone,
)

NOTEBOOKS = [
    ("00_start_here.ipynb", nb00_start_here.CELLS),
    ("01_setup_and_token.ipynb", nb01_setup_and_token.CELLS),
    ("02_replies_and_errors.ipynb", nb02_replies_and_errors.CELLS),
    ("03_treatment_rooms.ipynb", nb03_treatment_rooms.CELLS),
    ("04_patient_surfaces.ipynb", nb04_patient_surfaces.CELLS),
    ("05_clearance_maps.ipynb", nb05_clearance_maps.CELLS),
    ("06_beams_and_plans.ipynb", nb06_beams_and_plans.CELLS),
    ("07_robustness.ipynb", nb07_robustness.CELLS),
    ("08_capstone_plan_qa.ipynb", nb08_capstone.CELLS),
]
