"""04 · Patient surfaces: listing, downloading and drawing a patient's surface."""

from ._common import exercise, header

CELLS = [
    *header(4, "Patient surfaces", "A patient's surfaces: listing them, downloading one, and looking at it."),
    ("md", """\
## What a surface is

MapRT checks for collisions between the machine, the **patient**, the **couch** and the
**immobilization devices**, so it needs a model that includes all of them. That model comes from
a **surface**: the 3D outline of the patient, captured by the SGRT cameras. The benefit of
capturing it with the SGRT cameras is that it records both the patient and their immobilization
devices (essentially anything above the CT table top), whether or not that region is inside the
CT scan volume.

The captured surface becomes the **patient model**, which MapRT merges with a room's geometry to
compute its clearance maps. A patient can have more than one surface capture: for example, a new
capture after a new CT for a re-plan, or one per setup position for a patient whose treatment
needs several, such as Head First Supine (HFS) and Feet First Supine (FFS) surfaces when treating
multiple bone metastases in the abdomen and lower extremities."""),
    ("code", """\
from sgrt_workshop import connect

client = connect()
surfaces = client.get_patient_surfaces("ANON-001-SLIM")
surfaces"""),
    ("md", """\
Each surface is `(id, when it was created)`.

## What MapRT sends back

First, the raw reply for the first surface, asked for by hand with `httpx2` as in notebook 02.
The surface itself is in `data`, and it's long, so we show only its first 100 characters:"""),
    ("code", """\
import httpx2
from sgrt_workshop import settings

s = settings()
headers = {"Authorization": f"Bearer {s.token}", "User-Agent": s.user_agent}

surface_id, created = surfaces[0]
reply = httpx2.get(f"{s.url}/integration/surfaces/{surface_id}", headers=headers).json()

{**reply, "data": reply["data"][:100] + "..."}"""),
    ("md", """\
The same envelope as every other reply. `data` is a **data URI**: a short label saying what
follows (`data:application/octet-stream;base64,`: some bytes, base64-encoded), then the file
itself. Base64 writes any bytes as
plain letters and digits so they can travel inside JSON; it makes them about a third larger.

To get the file back, take everything after the comma and decode it:"""),
    ("code", """\
import base64

encoded = reply["data"].split(",")[-1]
by_hand = base64.b64decode(encoded)

print(f"{len(encoded):,} characters of base64 -> {len(by_hand):,} bytes")"""),
    ("md", """\
`client.get_surface` does all of this for you: it sends the request, checks `success`, strips the
label and decodes the base64, and hands back the file's bytes:"""),
    ("code", """\
raw = client.get_surface(surface_id)

print("Same as by hand:", raw == by_hand)
print(f"{len(raw) / 1_000_000:.1f} MB")
print(raw[:150].decode())"""),
    ("md", """\
It's an **OBJ file**, a plain-text 3D format: lines starting `v` are *vertices* (points, x y z in
millimeters) and lines starting `f` are *faces* (triangles joining three vertices).

## Reading the raw mesh file

Reading a 3D file by hand is a chore, so we use one of the many Python libraries that can read
meshes (VTK, Open3D, PyVista, trimesh and others). Here we use **trimesh**, a lighter-weight and
widely used library for 3D meshes, which reads the bytes we downloaded directly:"""),
    ("code", """\
import io
import trimesh

mesh = trimesh.load(io.BytesIO(raw), file_type="obj", process=False)

print(len(mesh.vertices), "vertices")
print(len(mesh.faces), "faces")
print("size (mm):", mesh.extents.round())"""),
    ("md", """\
`extents` is the size of the box the surface fits in, along x, y and z.

## Visualizing the surface

Once a surface is read in, there are many ways to draw it (trimesh has its own viewer, for one).
The convenience function `surfaces.show` below draws it in 3D with **Plotly**, a library for
interactive charts, lit so its shape is easy to read. A surface often has more triangles than a
browser can turn smoothly, so it draws a simplified copy, limited to 40,000 triangles.

To move the view, **drag with the left mouse button** to turn the surface in any direction. To
zoom, pick the magnifier in the view's toolbar (top right) and drag, or drag with the **middle
mouse button**; **double-click** to go back to the start."""),
    ("code", """\
from sgrt_workshop import surfaces

surfaces.show(mesh, title="Phantom ANON-001-SLIM")"""),
    ("md", """\
The axes are in millimeters, in MapRT's coordinates, at their true proportions: what you see is
the phantom where MapRT has it, on the couch.

## A patient's surface

The same for a patient: `ANON-010`, who had lung SBRT (notebook 06 checks this patient's plan)."""),
    ("code", """\
patient_id, _ = client.get_patient_surfaces("ANON-010")[0]
patient_mesh = trimesh.load(io.BytesIO(client.get_surface(patient_id)), file_type="obj", process=False)

print(f"{len(patient_mesh.vertices):,} vertices, size {patient_mesh.extents.round()} mm")
surfaces.show(patient_mesh, title="Patient ANON-010")"""),
    ("md", """\
## A patient with two surfaces

What happens when a patient has two different surfaces? Which one should a script use to generate
a clearance map, or to check that a plan's beams will clear? That question has no simple answer.
For many workflows it can be as simple as using the **newest** surface, and the time each surface
was created tells you which one that is.

Patient `ANON-009` has two surfaces. When you ask the API for a patient's surfaces, you get back a
list of the surfaces and their creation times. Python's **`datetime`** library turns those text
dates into times Python can compare:"""),
    ("code", """\
from datetime import datetime

two = client.get_patient_surfaces("ANON-009")
for surface_id, created in two:
    print(surface_id, created)

newest_id, newest_time = max(two, key=lambda surface: datetime.fromisoformat(surface[1]))
print("\\nNewest:", newest_id, "created", newest_time)"""),
    ("md", """\
`max(..., key=...)` picks the item with the largest *key*: here, the latest creation time."""),
    ("md", """\
<div style="border-left: 6px solid #d1242f; background-color: #fff1f0; color: #82071e; padding: 0.6em 1em;">
<b>⚠️ Warning: when you choose a surface for a real patient, check it with your own eyes as well.
The newest is not always the right one.</b>
</div>"""),
    *exercise(
        """\
        Download **both** of `ANON-009`'s surfaces, and for each print its number of vertices and its
        size in millimeters (`mesh.extents`). Which one is larger?""",
        """\
        for surface_id, created in client.get_patient_surfaces("ANON-009"):
            mesh = trimesh.load(io.BytesIO(client.get_surface(surface_id)), file_type="obj", process=False)
            print(f"{created}: {len(mesh.vertices):,} vertices, size {mesh.extents.round()} mm")""",
        number=1,
    ),
    *exercise(
        """\
        Take one of `ANON-009`'s surfaces from Exercise 1 and draw it with **trimesh's own viewer**
        instead of `surfaces.show`. Three steps:

        1. Simplify it first, as `surfaces.show` does: `mesh.simplify_quadric_decimation(face_count=40_000)`
           (a full surface would put megabytes into the notebook).
        2. Give it a color, so it stands out from the white background:
           `small.visual.vertex_colors = [255, 0, 255, 255]` (red, green, blue, opacity: magenta).
        3. Draw it: `small.show(viewer="jupyter")`.

        How does trimesh's view compare with the Plotly one above?""",
        """\
        surface_id, created = client.get_patient_surfaces("ANON-009")[0]
        mesh = trimesh.load(io.BytesIO(client.get_surface(surface_id)), file_type="obj", process=False)

        small = mesh.simplify_quadric_decimation(face_count=40_000)
        small.visual.vertex_colors = [255, 0, 255, 255]
        small.show(viewer="jupyter")""",
        number=2,
    ),
]
