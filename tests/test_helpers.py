"""sgrt_workshop: the pack downloader, the DICOM paths, finding the workshop folder."""

import hashlib
import io
import shutil
import socket
import sys

import pytest

from conftest import ROOT
from sgrt_workshop import config, emulator, packs


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def fake_pack(monkeypatch, name, data):
    monkeypatch.setitem(config.PACKS, name, (hashlib.sha256(data).hexdigest(), len(data)))


def test_a_pack_is_downloaded_checked_and_then_left_alone(tmp_path, monkeypatch):
    fake_pack(monkeypatch, "demo", b"zip bytes")
    calls = []

    def opener(url, timeout):
        calls.append(url)
        return FakeResponse(b"zip bytes")

    assert packs.download("demo", tmp_path, opener=opener, base_url="https://example.invalid/r") == "downloaded"
    assert calls == ["https://example.invalid/r/demo.zip"]  # the asset URL itself, not the GitHub API
    assert (tmp_path / "demo.zip").read_bytes() == b"zip bytes"
    assert packs.download("demo", tmp_path, opener=opener) == "present"
    assert len(calls) == 1


def test_a_download_that_does_not_match_is_refused_and_not_kept(tmp_path, monkeypatch):
    fake_pack(monkeypatch, "demo", b"the real pack")
    with pytest.raises(packs.PackError, match="does not match"):
        packs.download("demo", tmp_path, opener=lambda url, timeout: FakeResponse(b"something else"))
    assert list(tmp_path.iterdir()) == []


def test_a_failed_download_leaves_nothing(tmp_path, monkeypatch):
    fake_pack(monkeypatch, "demo", b"x")

    def opener(url, timeout):
        raise OSError("network down")

    with pytest.raises(packs.PackError, match="could not download"):
        packs.download("demo", tmp_path, opener=opener)
    assert list(tmp_path.iterdir()) == []


def test_only_the_workshops_packs_are_fetched(tmp_path):
    with pytest.raises(packs.PackError, match="not one of this workshop's packs"):
        packs.download("hfs-phantom", tmp_path)


def test_every_pack_is_small_enough_for_binder_and_colab():
    assert all(size <= 25_000_000 for _sha, size in config.PACKS.values())


@pytest.mark.parametrize("name", ["lt-lung-sbrt-patient", "srs-patient"])
def test_the_lesson_packs_dicom_unpacks_to_named_paths(name, running_emulator):
    dicom = packs.extract_dicom(name, root=ROOT)
    assert dicom.plan.parent == dicom.folder / "plan" and dicom.plan.name.startswith("RP.")
    assert dicom.struct.parent == dicom.folder / "struct" and dicom.struct.name.startswith("RS.")
    assert dicom.plan.read_bytes()[128:132] == b"DICM"


def test_the_workshop_folder_is_found_from_inside_it(tmp_path, monkeypatch):
    monkeypatch.delenv("SGRT_WORKSHOP_HOME", raising=False)
    assert config.workshop_root(ROOT / "notebooks") == ROOT
    assert config.workshop_root(tmp_path) == tmp_path


def test_the_emulator_runs_on_this_interpreter_with_the_workshops_settings():
    command = emulator.command(scenario="slow", root=ROOT)
    assert command[:3] == [sys.executable, "-m", "maprt_emulator"]
    # relative to the workshop folder, where start() runs it, so the banner's paths fit its box
    assert command[command.index("--packs-dir") + 1] == "packs"
    assert command[command.index("--state-dir") + 1] == ".maprt_emulator"
    assert command[-2:] == ["--scenario", "slow"]
    assert "--lenient-user-agent" not in command  # the User-Agent is taught, not switched off
    assert "--token" not in command  # a fresh token every start, as the README and notebook 01 say


def test_the_token_is_read_from_the_running_emulators_file_each_time(tmp_path, monkeypatch):
    monkeypatch.delenv("MAPRT_EMULATOR_TOKEN", raising=False)
    (tmp_path / ".maprt_emulator").mkdir()
    (tmp_path / ".maprt_emulator" / "token").write_text("first-run\n", encoding="utf-8")
    assert config.token(tmp_path) == "first-run"
    (tmp_path / ".maprt_emulator" / "token").write_text("second-run\n", encoding="utf-8")
    assert config.token(tmp_path) == "second-run"  # never cached
    monkeypatch.setenv("MAPRT_EMULATOR_TOKEN", "from-the-environment")
    assert config.token(tmp_path) == "from-the-environment"


def test_no_token_file_says_how_to_start_the_emulator(tmp_path, monkeypatch):
    monkeypatch.delenv("MAPRT_EMULATOR_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="setup cell"):
        config.token(tmp_path)
    assert config.token(tmp_path, required=False) == ""


def test_each_start_gets_a_new_token(running_emulator):
    first = config.token(ROOT)
    emulator.restart(root=ROOT)
    second = config.token(ROOT)
    assert first and second and first != second
    assert emulator.ping(root=ROOT)["success"]  # the new token works
    assert "Token file  .maprt_emulator/token " in emulator.banner(ROOT) and second in emulator.banner(ROOT)


def test_a_restart_into_any_scenario_neither_hangs_nor_spends_the_scenario(running_emulator):
    """Readiness is a port check, never an API call (a call would hang under `slow`, fail under
    `bad-token`, and use up `throttle`'s two 503s before the student's first request)."""
    import httpx2

    from sgrt_workshop import settings

    try:
        for scenario in ("slow", "bad-token"):
            emulator.restart(scenario=scenario, root=ROOT)
            assert emulator.status(ROOT) == {"running": True, "scenario": scenario, "pid": emulator.status(ROOT)["pid"],
                                             "port": emulator.status(ROOT)["port"]}
        emulator.restart(scenario="throttle", root=ROOT)
        s = settings()
        first = httpx2.get(f"{s.url}/integration/rooms",
                           headers={"Authorization": f"Bearer {s.token}", "User-Agent": s.user_agent})
        assert first.status_code == 503 and first.headers.get("retry-after")
    finally:
        emulator.restart(root=ROOT)


@pytest.mark.parametrize("pack", ["lt-lung-sbrt-patient", "srs-patient"])
def test_requests_built_from_the_plan_are_the_recorded_ones(pack, running_emulator):
    """Lessons 06 and 08 build their requests from the plan. They must be byte-for-byte what was
    recorded (isocenter to 0.01 mm, beam numbers as text, every arc control point), or the
    emulator falls back to computing its own verdicts and the lessons would show other answers."""
    import json
    import zipfile

    from maprt_client import build_beam_delivery_status_request, build_map_request
    from sgrt_workshop import connect, plan

    dicom = packs.extract_dicom(pack, root=ROOT)
    setup = plan.read_setup(dicom.plan)
    beams = plan.read_beams(dicom.plan)
    with zipfile.ZipFile(config.packs_dir(ROOT) / f"{pack}.zip") as archive, connect() as client:
        surface_id, _ = client.get_patient_surfaces(setup.patient_id)[0]
        for name in archive.namelist():
            if not name.endswith("_request.json") or not ("GetMap" in name or "GetBeamDeliveryStatus" in name):
                continue
            recorded = json.loads(archive.read(name))["body"]
            couch, patient = recorded["CouchBuffer"] / 10, recorded["PatientBuffer"] / 10
            if "GetBeamDeliveryStatus" in name:
                _, built = build_beam_delivery_status_request(setup.isocenter, couch, patient, surface_id,
                                                              recorded["TreatmentRoomId"], setup.position,
                                                              plan.beam_list(beams))
                assert built == recorded, name
            elif "GetMap" in name:
                _, (low, high) = build_map_request(setup.isocenter, couch, patient, surface_id,
                                                   recorded["TreatmentRoomId"], "IEC_61217", setup.position)
                assert (high if recorded["HighResolution"] else low) == recorded, name


def test_a_map_chart_is_labeled_by_angle_hovers_and_stays_small(running_emulator):
    """Plotly charts carry their data into the notebook: a per-cell hover label once made one map
    1.7 MB and the capstone's six 10.8 MB. The axes now carry the angles instead."""
    import numpy as np

    from sgrt_workshop import plan
    from sgrt_workshop.plotting import plot_map
    from maprt_client import check_beams

    collision_map = np.ones((360, 181), dtype=int)
    collision_map[100:200, 50:120] = 0
    beams = plan.read_beams(packs.extract_dicom("lt-lung-sbrt-patient", root=ROOT).plan)
    check_beams(beams, (collision_map, None, None), arc_check_resolution=1)
    figure = plot_map(collision_map, title="test", beams=beams)
    heatmap = figure.data[0]
    assert np.asarray(heatmap.z).shape == (360, 181)
    assert list(heatmap.x[:1]) + list(heatmap.x[-1:]) == ["270", "90"] and heatmap.y[0] == "180"
    assert "couch %{x}°, gantry %{y}°" in heatmap.hovertemplate
    arcs = [b for b in beams if b.gantry_rotation != "NONE"]
    named = [t for t in figure.data[1:] if t.hovertemplate and "arc" in t.hovertemplate]
    outlines = [t for t in figure.data[1:] if t.line and t.line.color == "black"]
    assert len(named) >= len(arcs) and len(outlines) == len(named)  # every arc: an outline and a named line
    assert all(len(t.y) > 2 for t in named)  # a point per degree, so hovering anywhere names the beam
    colliding = [t for t in named if "COLLISION" in t.hovertemplate]
    assert colliding and all(t.line.color == "#ff8c00" for t in colliding)  # orange, not red, on red regions
    assert len(figure.to_json()) < 300_000


def test_a_difference_map_shows_each_change_by_angle_and_stays_small():
    """Notebook 05 subtracts a 3 cm map from a 2 cm one: 1 (only the first clear) is orange, 0 pale,
    -1 blue, on the same angle axes as a map; the key is in the hover template, not per cell."""
    import numpy as np

    from sgrt_workshop.plotting import BEAM_COLLISION, CLEAR, plot_difference

    first = np.ones((360, 181), dtype=int)
    second = first.copy()
    second[100:110, 50:60] = 0
    figure = plot_difference(first - second, labels=("clear at 2 cm only", "clear at 3 cm only"))
    heatmap = figure.data[0]
    assert list(heatmap.x[:1]) + list(heatmap.x[-1:]) == ["270", "90"] and heatmap.y[0] == "180"
    assert "clear at 2 cm only" in heatmap.hovertemplate and heatmap.customdata is None
    scale = dict((round(stop, 3), color) for stop, color in heatmap.colorscale)
    # zmin -1.5 .. zmax 1.5: the values -1, 0 and 1 sit at 1/6, 1/2 and 5/6 of the scale
    assert scale[0.0] == "#1f6feb" and scale[0.667] == BEAM_COLLISION and CLEAR in scale.values()
    assert len(figure.to_json()) < 300_000


def test_a_surface_is_dark_magenta_seen_from_the_side_with_scroll_zoom_off(running_emulator, monkeypatch):
    import trimesh

    from sgrt_workshop import surfaces

    mesh = trimesh.creation.box(extents=(2000, 600, 400))
    figure = surfaces.figure_of(mesh, title="box")
    assert figure.data[0].color == "#8B008B" and figure.layout.scene.aspectmode == "data"
    assert figure.layout.scene.dragmode == "orbit"  # free rotation
    assert figure.layout.scene.camera.eye.y < -1 and abs(figure.layout.scene.camera.eye.x) < 0.5  # side-on
    shown = {}
    monkeypatch.setattr(type(figure), "show", lambda self, config=None: shown.update(config=config))
    surfaces.show(mesh)
    assert shown["config"] == {"scrollZoom": False}  # scrolling the page past it must not zoom it


def _free_ports(count):
    """``count`` ports nothing is listening on now (the OS picks them)."""
    sockets = [socket.socket() for _ in range(count)]
    for sock in sockets:
        sock.bind((config.HOST, 0))
    ports = [sock.getsockname()[1] for sock in sockets]
    for sock in sockets:
        sock.close()
    return ports


def _hold(port):
    """Something else listening on ``port``, as a leftover emulator or another program would be."""
    sock = socket.socket()
    sock.bind((config.HOST, port))
    sock.listen()
    return sock


def _second_workshop(tmp_path):
    """Another copy of the workshop folder (a second download, say) with the same packs."""
    (tmp_path / "packs").mkdir()
    for name in config.PACKS:
        shutil.copyfile(config.packs_dir(ROOT) / f"{name}.zip", tmp_path / "packs" / f"{name}.zip")
    return tmp_path


def test_the_url_is_read_from_the_running_emulators_server_json_each_time(tmp_path, monkeypatch):
    monkeypatch.delenv("MAPRT_EMULATOR_URL", raising=False)
    assert config.api_url(tmp_path) == "http://127.0.0.1:8000"  # never started: the usual port
    (tmp_path / ".maprt_emulator").mkdir()
    (tmp_path / ".maprt_emulator" / "server.json").write_text('{"url": "http://127.0.0.1:8003"}', encoding="utf-8")
    assert config.api_url(tmp_path) == "http://127.0.0.1:8003"
    (tmp_path / ".maprt_emulator" / "server.json").write_text("not json", encoding="utf-8")
    assert config.api_url(tmp_path) == "http://127.0.0.1:8000"
    monkeypatch.setenv("MAPRT_EMULATOR_URL", "http://appliance:8000")
    assert config.api_url(tmp_path) == "http://appliance:8000"


def test_a_busy_port_moves_the_emulator_to_the_next_and_the_notebooks_follow(tmp_path, monkeypatch, running_emulator):
    """Seen in the Colab simulation and feared in class: a port held by an emulator left running
    elsewhere, or another program. start() takes the next free port, the notebooks' settings find
    it, a restart keeps it, and stop() leaves the other program alone."""
    from sgrt_workshop import settings

    root = _second_workshop(tmp_path)
    monkeypatch.setenv("SGRT_WORKSHOP_HOME", str(root))
    monkeypatch.delenv("MAPRT_EMULATOR_URL", raising=False)
    busy, free, spare = _free_ports(3)
    monkeypatch.setattr(config, "PORTS", (busy, free, spare))
    monkeypatch.setattr(config, "PORT", busy)
    held = _hold(busy)
    try:
        started = emulator.start(root=root)
        assert started["port"] == free and started["running"]
        assert settings().url == f"http://127.0.0.1:{free}"
        assert emulator.ping(root=root)["success"]
        pid = started["pid"]
        assert emulator.start(root=root)["pid"] == pid  # already up (a closed terminal): used as it is
        held.close()  # the usual port is free again, but a restart stays where clients expect it
        emulator.restart(root=root)
        assert emulator.status(root)["port"] == free and emulator.status(root)["pid"] != pid
        assert emulator.ping(root=root)["success"]
    finally:
        held.close()
        emulator.stop(root=root)
    assert not emulator.listening(port=free)


def test_stop_never_touches_what_holds_the_port_if_it_is_not_ours(tmp_path, monkeypatch):
    (port,) = _free_ports(1)
    monkeypatch.setattr(config, "PORTS", (port,))
    monkeypatch.setattr(config, "PORT", port)
    held = _hold(port)
    try:
        emulator.stop(root=tmp_path)  # nothing of ours: no error, nothing killed
        assert emulator.listening(port=port)
    finally:
        held.close()


def test_every_port_busy_says_so(tmp_path, monkeypatch):
    (port,) = _free_ports(1)
    monkeypatch.setattr(config, "PORTS", (port,))
    (tmp_path / "packs").mkdir()
    (tmp_path / "packs" / "x.zip").write_bytes(b"")
    held = _hold(port)
    try:
        with pytest.raises(emulator.EmulatorError, match="all in use"):
            emulator.start(root=tmp_path)
    finally:
        held.close()
