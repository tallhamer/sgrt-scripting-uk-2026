"""The cells that unpack a pack's DICOM and say plainly where the files are (notebooks 05, 06, 08).

On Binder and Colab there is no file dialog to pick a file with, so no notebook asks for one: the
same cell works everywhere, prints the full paths, and the code uses them through variables.
"""


def dicom_cells(pack, patient):
    return [
        ("md", f"""\
## The plan and structure set

The session pack for `{patient}` includes the patient's **RT Plan** and **RT Structure Set**, as
anonymized DICOM files. This cell unpacks them and prints where they are:"""),
        ("code", f"""\
from sgrt_workshop import packs

dicom = packs.extract_dicom("{pack}")

print("RT Plan:         ", dicom.plan)
print("RT Structure Set:", dicom.struct)"""),
        ("md", f"""\
**You don't need to find or open these files yourself**: the variables `dicom.plan` and
`dicom.struct` hold their full paths, and the code below uses them. The file names are long
because DICOM files are named by their unique ID.

If you want to look at them:

* **On your own laptop:** they are in the workshop folder, under
  `packs/{pack}-dicom/plan/` and `packs/{pack}-dicom/struct/`. You can open them in any DICOM
  viewer, or use these paths in your own scripts after the course.
* **On Binder:** in the file panel on the left, open `packs`, then `{pack}-dicom`.
* **On Colab:** in the **Files** panel on the left, open `sgrt-scripting-uk-2026`, `packs`, then
  `{pack}-dicom`.

On Binder and Colab the files live only as long as your session."""),
    ]
