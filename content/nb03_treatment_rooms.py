"""03 · Treatment rooms: listing them, and finding one by machine name."""

from ._common import exercise, header

CELLS = [
    *header(3, "Treatment rooms", "Listing a site's treatment rooms, and finding one by its machine name."),
    ("md", """\
## The rooms on this appliance

In MapRT a **treatment room** is a geometry: a linac with a particular set of accessories (an
imager panel extended to 50 cm, a kV source, an electron applicator...), modelled for collision
checking. One physical linac can have several. Every map and beam check is for one of them."""),
    ("code", """\
from sgrt_workshop import connect

client = connect()
rooms = client.get_treatment_rooms()

print(len(rooms), "rooms")
for name, room_id, coordinate_system in rooms:
    print(f"  {name:28} {room_id}")"""),
    ("md", """\
Each room has a **name** for people and an **id** for programs: a GUID, a long code that is unique
and never changes even if the room is renamed. MapRT's other requests ask for the id. All of them
use the IEC 61217 coordinate system.

A Python *dictionary* turns a name into its id:"""),
    ("code", """\
room_ids = {name: room_id for name, room_id, _ in rooms}

room_ids["Truebeam kV50"]"""),
    ("md", """\
## Finding a room by machine name

MapRT can also look a room up by its **machine name**: the name of the linac it belongs to, as
set up on the appliance. A script that knows which linac a patient is booked on (from the
oncology information system, say) can ask for the room that way. There are three possible
answers, and this appliance has all three.

**1. Several rooms share the name.** Eight room geometries here belong to the machine called
`Truebeam`:"""),
    ("code", """\
from maprt_client import MapRTApiError

try:
    client.get_treatment_room("Truebeam")
except MapRTApiError as error:
    print(error.error_code)"""),
    ("md", """\
`DuplicateKey`: MapRT won't guess which one you meant.

**2. No room has that name.** `Truebeam e10` is a room *name*, not a machine name:"""),
    ("code", """\
reply = client.get_treatment_room("Truebeam e10")
reply"""),
    ("md", """\
This one *succeeds*, and returns an id made of zeros: MapRT's way of saying "none". A script has to
check for it; otherwise it carries on with an id that matches nothing."""),
    ("code", """\
NO_ROOM = "00000000-0000-0000-0000-000000000000"

print("Found a room?", reply["data"] != NO_ROOM)"""),
    ("md", """\
**3. Exactly one room.** On this appliance one machine name is `"Truebeam "`, with a space at the
end. Look up the id it returns among the rooms we listed:"""),
    ("code", """\
reply = client.get_treatment_room("Truebeam ")   # note the space before the closing quote

names_by_id = {room_id: name for name, room_id, _ in rooms}
print(repr(reply["data"]), "->", names_by_id[reply["data"]])"""),
    ("md", """\
That space is real: it's how the machine was named on the appliance these sessions were recorded
on. Machine names are typed in by people, so they can hold spaces, odd capitals or typos.
`"Truebeam"` and `"Truebeam "` are different names to a computer.

You can see every room's machine name in MapRT's raw reply (`maprt-client` keeps only the name, id
and coordinate system). `repr()` shows the quotes, so a trailing space is visible:"""),
    ("code", """\
raw_rooms = client.send("GET", "/integration/rooms").json()["data"]

for room in raw_rooms:
    print(f"  {room['name']:28} machine name {room['machineName']!r}")"""),
    *exercise(
        """\
        Write a function `find_room(client, machine_name)` that returns:

        * the **room name** if exactly one room has that machine name,
        * `None` if no room does (the all-zeros id),
        * the text `"several"` if MapRT answers `DuplicateKey`.

        Try it with `"Truebeam"`, `"Truebeam "` and `"Halcyon"`.""",
        """\
        def find_room(client, machine_name):
            names_by_id = {room_id: name for name, room_id, _ in client.get_treatment_rooms()}
            try:
                room_id = client.get_treatment_room(machine_name)["data"]
            except MapRTApiError as error:
                if error.error_code == "DuplicateKey":
                    return "several"
                raise
            if room_id == NO_ROOM:
                return None
            return names_by_id[room_id]

        for machine_name in ["Truebeam", "Truebeam ", "Halcyon"]:
            print(repr(machine_name), "->", find_room(client, machine_name))""",
        number=1,
    ),
    *exercise(
        """\
        The room names say which accessories each geometry has. Write three functions that each take the
        `client` and return only some of the rooms (as the `(name, id, coordinate system)` tuples
        `get_treatment_rooms()` gives):

        * `get_electron_rooms`: the rooms with an **electron applicator**, whose names end in the
          cone: `e6`, `e10`, `e15`, `e20` or `e25`;
        * `get_triggered_imaging_rooms`: the rooms with only the **kV arms** out, at 50, 60 or 70 cm
          from isocenter (`kV50`, `kV60`, `kV70`);
        * `get_port_film_rooms`: the rooms with the **MV detector** out, at 50, 60 or 70 cm from
          isocenter (`MV50`, `MV60`, `MV70`).

        Print each function's rooms. A hint: Python's `re` module matches text against a pattern.
        `re.search(r" e\\d+$", name)` finds a space, an `e` and one or more digits (`\\d+`) at the
        end of the name (`$`), so it is true for `"Truebeam e10"` and false for
        `"Truebeam Imager 50"`.""",
        """\
        import re

        def get_electron_rooms(client):
            \"\"\"Rooms with an electron applicator: names ending in the cone (e6, e10, e15, e20, e25).\"\"\"
            return [room for room in client.get_treatment_rooms() if re.search(r" e\\d+$", room[0])]

        def get_triggered_imaging_rooms(client):
            \"\"\"Rooms with only the kV arms out, at 50, 60 or 70 cm from isocenter.\"\"\"
            return [room for room in client.get_treatment_rooms() if re.search(r"kV(50|60|70)$", room[0])]

        def get_port_film_rooms(client):
            \"\"\"Rooms with the MV detector out, at 50, 60 or 70 cm from isocenter.\"\"\"
            return [room for room in client.get_treatment_rooms() if re.search(r"MV(50|60|70)$", room[0])]

        for get_rooms in [get_electron_rooms, get_triggered_imaging_rooms, get_port_film_rooms]:
            print(get_rooms.__name__)
            for name, room_id, _ in get_rooms(client):
                print(f"  {name:20} {room_id}")""",
        number=2,
    ),
]
