from app.services import gpu_service


def test_parse_int_handles_na_and_numeric():
    assert gpu_service._parse_int("N/A") is None
    assert gpu_service._parse_int("[N/A]") is None
    assert gpu_service._parse_int("") is None
    assert gpu_service._parse_int("42") == 42
    assert gpu_service._parse_int("42.0") == 42


def test_parse_float_handles_na_and_numeric():
    assert gpu_service._parse_float("N/A") is None
    assert gpu_service._parse_float("35.21") == 35.21


def test_list_gpus_empty_without_nvidia_smi(monkeypatch):
    monkeypatch.setattr(gpu_service.shutil, "which", lambda _: None)
    assert gpu_service.list_gpus() == []


def test_list_gpus_parses_full_output(monkeypatch):
    monkeypatch.setattr(gpu_service.shutil, "which", lambda _: "/usr/bin/nvidia-smi")
    csv_line = (
        "0, NVIDIA GeForce RTX 3090, 550.90.07, GPU-uuid, 00000000:01:00.0, "
        "24576, 1024, 23552, 45, 12, 35.21, 350.00, 8.6\n"
    )
    monkeypatch.setattr(gpu_service, "_query_nvidia_smi", lambda fields: csv_line)

    gpus = gpu_service.list_gpus()
    assert len(gpus) == 1

    gpu = gpus[0]
    assert gpu.name == "NVIDIA GeForce RTX 3090"
    assert gpu.vram_total_mb == 24576
    assert gpu.vram_used_mb == 1024
    assert gpu.temperature_c == 45
    assert gpu.utilization_percent == 12
    assert gpu.power_draw_w == 35.21
    assert gpu.compute_capability == "8.6"


def test_list_gpus_parses_multiple_devices(monkeypatch):
    monkeypatch.setattr(gpu_service.shutil, "which", lambda _: "/usr/bin/nvidia-smi")
    lines = "\n".join(
        f"{i}, NVIDIA GeForce RTX 3090, 550.90.07, GPU-uuid-{i}, 00000000:0{i+1}:00.0, "
        f"24576, {i * 500}, {24576 - i * 500}, {40 + i}, {10 + i}, 30.0, 350.00, 8.6"
        for i in range(8)
    )
    monkeypatch.setattr(gpu_service, "_query_nvidia_smi", lambda fields: lines)

    gpus = gpu_service.list_gpus()
    assert len(gpus) == 8
    assert [g.index for g in gpus] == list(range(8))


def test_list_gpus_falls_back_to_basic_fields_on_older_driver(monkeypatch):
    monkeypatch.setattr(gpu_service.shutil, "which", lambda _: "/usr/bin/nvidia-smi")

    def fake_query(fields):
        if fields == gpu_service._FULL_FIELDS:
            return None  # simula un nvidia-smi che non supporta tutti i campi
        return "0, NVIDIA GeForce RTX 3090, 24576, 1024\n"

    monkeypatch.setattr(gpu_service, "_query_nvidia_smi", fake_query)

    gpus = gpu_service.list_gpus()
    assert len(gpus) == 1
    assert gpus[0].vram_total_mb == 24576
    assert gpus[0].vram_used_mb == 1024
    assert gpus[0].driver_version is None
