#!/usr/bin/env python3
"""Verificador independiente de recogidas de ALUMABE CASTELLANOS 2011 S.L.

Solo usa la librería estándar de Python 3.8+. No necesita acceso a los sistemas de la empresa.

Uso:
    python verificar_recogida.py <carpeta_de_la_prueba>

La carpeta es el contenido descomprimido de la "prueba de integridad" de una recogida.
Comprueba:
  1. Que el hash del registro se corresponde con sus datos (registro/canonical.txt).
  2. Que la firma y la foto de bultos son exactamente las registradas (SHA-256).
  3. Que el registro está incluido en el anclaje diario (prueba de Merkle).
  4. Que el archivo de anclaje es el que está sellado en el fichero .ots.
El último paso, comprobar que el .ots está anclado en la blockchain de Bitcoin, se hace en
https://opentimestamps.org (arrastrando el .json del anclaje y su .ots) o con `ots verify`.
"""
import hashlib
import json
import os
import sys

OTS_MAGIC = b"\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def leaf(h: str) -> bytes:
    return hashlib.sha256(b"\x00" + bytes.fromhex(h)).digest()


def node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def root_from_proof(record_hash: str, proof: list) -> str:
    h = leaf(record_hash)
    for step in proof:
        sib = bytes.fromhex(step["hash"])
        h = node(sib, h) if step["side"] == "left" else node(h, sib)
    return h.hex()


def ots_file_digest(data: bytes) -> str:
    if not data.startswith(OTS_MAGIC):
        raise ValueError("no es un fichero OpenTimestamps")
    pos = len(OTS_MAGIC)
    pos += 1                      # versión (varuint, 1 byte para la versión 1)
    if data[pos] != 0x08:         # operación SHA-256
        raise ValueError("el .ots no usa SHA-256")
    return data[pos + 1:pos + 33].hex()


def main(folder: str) -> int:
    ok = True

    def check(cond: bool, msg: str):
        nonlocal ok
        print(("  OK    " if cond else "  FALLO ") + msg)
        ok = ok and cond

    def read(*parts):
        with open(os.path.join(folder, *parts), "rb") as f:
            return f.read()

    reg = json.loads(read("registro", "registro.json"))
    canonical = read("registro", "canonical.txt").decode("utf-8")
    data = json.loads(canonical)

    print(f"Registro {data['id']} · {data.get('recipient')} · {data.get('carrier')}")
    print("1) Hash del registro")
    computed = sha256_hex(f"{reg['prev_hash']}\n{canonical}".encode("utf-8"))
    check(computed == reg["record_hash"], f"record_hash = {computed}")

    print("2) Ficheros")
    files = [(data.get("signature_sha256"), "firma.png"), (data.get("photo_sha256"), "bultos.jpg")]
    files += [(h, f"bultos_{i}.jpg") for i, h in enumerate(data.get("extra_photos_sha256") or [], start=2)]
    for expected, name in files:
        path = os.path.join(folder, "registro", name)
        if expected is None:
            print(f"  --    sin {name}")
        elif not os.path.isfile(path):
            check(False, f"falta {name}")
        else:
            check(sha256_hex(read("registro", name)) == expected, f"{name} coincide con su SHA-256")

    print("3) Inclusión en el anclaje diario")
    anchor_dir = os.path.join(folder, "anclaje")
    if not os.path.isdir(anchor_dir):
        print("  --    el día aún no está anclado (se ancla cada noche)")
        return 0 if ok else 1
    anchor_name = next(n for n in os.listdir(anchor_dir) if n.endswith(".json"))
    anchor_bytes = read("anclaje", anchor_name)
    anchor = json.loads(anchor_bytes)
    proof = json.loads(read("anclaje", "merkle_proof.json"))
    check(reg["record_hash"] in anchor.get("record_hashes", []), "el registro aparece en el anclaje")
    check(root_from_proof(reg["record_hash"], proof["proof"]) == anchor["merkle_root"], "la prueba de Merkle lleva a la raíz del anclaje")

    print("4) Sello OpenTimestamps")
    ots_path = os.path.join(anchor_dir, anchor_name + ".ots")
    if os.path.isfile(ots_path):
        check(ots_file_digest(read("anclaje", anchor_name + ".ots")) == sha256_hex(anchor_bytes),
              "el .ots sella exactamente este archivo de anclaje")
        print("  ->    Comprueba el anclaje en Bitcoin en https://opentimestamps.org con "
              f"'{anchor_name}' y '{anchor_name}.ots'")
    else:
        print("  --    sin .ots")

    print("\nRESULTADO:", "VERIFICADO" if ok else "NO VERIFICADO")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
