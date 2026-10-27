#!/usr/bin/env python3
"""Corrige caminhos absolutos internos do runtime Wine/Box64 ARM64.

Os binarios ELF contem um PT_INTERP e RPATH com /data/data/com.winlator.
Mudancas apenas no Java e C nao corrigem esses binarios ja compilados.
Usamos identificador proprio do mesmo tamanho para preservar o layout ELF.
"""
from pathlib import Path
import mmap
import subprocess
import sys
import tarfile
import tempfile

OLD = b"com.winlator"
NEW = b"com.tclwin11"
assert len(OLD) == len(NEW) == 12


def patch(assets: Path):
    archives = sorted(assets.rglob("*.tzst"))
    if not (assets / "rootfs.tzst").is_file():
        raise RuntimeError("rootfs.tzst ausente")
    if not (assets / "box64/box64-0.4.4.tzst").is_file():
        raise RuntimeError("box64-0.4.4.tzst ausente")
    hits = {}
    for archive in archives:
        with tempfile.TemporaryDirectory(prefix="tcl-runtime-") as tmp:
            raw_tar = Path(tmp) / "data.tar"
            with raw_tar.open("wb") as out:
                subprocess.run(["zstd", "-q", "-dc", str(archive)], stdout=out, check=True)
            with tarfile.open(raw_tar, "r:") as tar:
                need_rebuild = any("com.winlator" in m.name or "com.winlator" in m.linkname
                                   for m in tar)
            # Links simbolicos guardam o caminho no HEADER TAR, com checksum.
            # Reconstruir esses headers antes do patch binario evita corromper o TAR.
            if need_rebuild:
                rebuilt = Path(tmp) / "rebuilt.tar"
                with tarfile.open(raw_tar, "r:") as source_tar, tarfile.open(
                    rebuilt, "w:", format=tarfile.GNU_FORMAT
                ) as destination_tar:
                    for member in source_tar:
                        old_name = member.name
                        old_link = member.linkname
                        member.name = old_name.replace("com.winlator", "com.tclwin11")
                        member.linkname = old_link.replace("com.winlator", "com.tclwin11")
                        payload = source_tar.extractfile(member) if member.isfile() else None
                        destination_tar.addfile(member, payload)
                rebuilt.replace(raw_tar)
            count = 0
            with raw_tar.open("r+b") as f, mmap.mmap(f.fileno(), 0) as mm:
                idx = 0
                while True:
                    idx = mm.find(OLD, idx)
                    if idx < 0:
                        break
                    mm[idx:idx + len(OLD)] = NEW
                    count += 1
                    idx += len(OLD)
                mm.flush()
                if mm.find(OLD) >= 0:
                    raise RuntimeError(f"Restaram caminhos antigos em {archive}")
            if count or need_rebuild:
                subprocess.run(["zstd", "-q", "-f", "-T0", "-5", str(raw_tar), "-o", str(archive)],
                               check=True)
                hits[archive.relative_to(assets).as_posix()] = count
                print(f"Caminhos internos corrigidos: {archive.name}: {count} (+header={need_rebuild})", flush=True)
    if hits.get("box64/box64-0.4.4.tzst", 0) < 2:
        raise RuntimeError("O PT_INTERP e RPATH do Box64 nao foram corrigidos")
    if hits.get("rootfs.tzst", 0) < 50:
        raise RuntimeError("As referencias de bibliotecas Wine e Linux nao foram corrigidas")
    print(f"Runtime Wine/Box64: {sum(hits.values())} caminhos corrigidos", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: patch_runtime_assets.py /app/src/main/assets")
    patch(Path(sys.argv[1]).resolve())
