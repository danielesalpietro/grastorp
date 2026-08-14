"""Rilevamento GPU e interfacce di rete dell'host.

Le GPU vengono rilevate tramite `nvidia-smi`. Perché sia visibile dentro il
container del backend, il container deve avere accesso alle GPU dell'host
(richiede l'NVIDIA Container Toolkit sull'host e la relativa reservation nel
docker-compose.yml). Se `nvidia-smi` non è presente o fallisce, l'elenco è
vuoto. La lettura delle NIC reali dell'host non è ancora implementata: da
fare passando per un servizio con accesso privilegiato al network namespace
dell'host.
"""

from __future__ import annotations

import shutil
import subprocess

from app.schemas import GPUDevice, NICDevice

_FULL_FIELDS = (
    "index,name,driver_version,uuid,pci.bus_id,memory.total,memory.used,memory.free,"
    "temperature.gpu,utilization.gpu,power.draw,power.limit,compute_cap"
)
_BASIC_FIELDS = "index,name,memory.total,memory.used"


def _parse_int(value: str) -> int | None:
    value = value.strip()
    if not value or value.upper() in ("N/A", "[N/A]"):
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _parse_float(value: str) -> float | None:
    value = value.strip()
    if not value or value.upper() in ("N/A", "[N/A]"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _query_nvidia_smi(fields: str) -> str | None:
    try:
        return subprocess.check_output(
            ["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"],
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError):
        return None


def list_gpus() -> list[GPUDevice]:
    if shutil.which("nvidia-smi") is None:
        return []

    output = _query_nvidia_smi(_FULL_FIELDS)
    if output is not None:
        gpus: list[GPUDevice] = []
        for line in output.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            (
                index,
                name,
                driver_version,
                uuid,
                pci_bus_id,
                mem_total,
                mem_used,
                mem_free,
                temperature,
                utilization,
                power_draw,
                power_limit,
                compute_cap,
            ) = parts
            gpus.append(
                GPUDevice(
                    index=int(index),
                    name=name,
                    driver_version=driver_version or None,
                    uuid=uuid or None,
                    pci_bus_id=pci_bus_id or None,
                    vram_total_mb=_parse_int(mem_total) or 0,
                    vram_used_mb=_parse_int(mem_used) or 0,
                    vram_free_mb=_parse_int(mem_free),
                    temperature_c=_parse_int(temperature),
                    utilization_percent=_parse_int(utilization),
                    power_draw_w=_parse_float(power_draw),
                    power_limit_w=_parse_float(power_limit),
                    compute_capability=compute_cap or None,
                )
            )
        return gpus

    # nvidia-smi non supporta uno dei campi estesi (driver più vecchio): fallback.
    output = _query_nvidia_smi(_BASIC_FIELDS)
    if output is None:
        return []

    gpus = []
    for line in output.strip().splitlines():
        index, name, total, used = (p.strip() for p in line.split(","))
        gpus.append(
            GPUDevice(
                index=int(index),
                name=name,
                vram_total_mb=_parse_int(total) or 0,
                vram_used_mb=_parse_int(used) or 0,
            )
        )
    return gpus


def list_nics() -> list[NICDevice]:
    # Stub: implementazione reale da fare (es. lettura /sys/class/net dell'host).
    return []
