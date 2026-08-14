"""Rilevamento GPU e interfacce di rete dell'host.

Stub: prova a interrogare `nvidia-smi` se disponibile nel container (richiede
NVIDIA Container Toolkit); altrimenti restituisce un elenco vuoto. La lettura
delle NIC reali dell'host non è ancora implementata: da fare passando per
un servizio con accesso privilegiato al network namespace dell'host.
"""

from __future__ import annotations

import shutil
import subprocess

from app.schemas import GPUDevice, NICDevice


def list_gpus() -> list[GPUDevice]:
    if shutil.which("nvidia-smi") is None:
        return []

    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,memory.used",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError):
        return []

    gpus: list[GPUDevice] = []
    for line in output.strip().splitlines():
        index, name, total, used = (part.strip() for part in line.split(","))
        gpus.append(
            GPUDevice(
                index=int(index),
                name=name,
                vram_total_mb=int(float(total)),
                vram_used_mb=int(float(used)),
            )
        )
    return gpus


def list_nics() -> list[NICDevice]:
    # Stub: implementazione reale da fare (es. lettura /sys/class/net dell'host).
    return []
