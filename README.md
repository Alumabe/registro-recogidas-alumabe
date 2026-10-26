# Registro de recogidas — ALUMABE CASTELLANOS 2011 S.L.

Este repositorio publica cada día un **anclaje** de las recogidas de mercancía firmadas por
agencias de transporte en nuestras instalaciones. Sirve para demostrar ante terceros que un
justificante de recogida existía en una fecha y **no ha sido modificado desde entonces**.

No contiene datos personales: solo hashes SHA-256.

## Contenido

```
anchors/AAAA/MM/AAAA-MM-DD.json       anclaje del día
anchors/AAAA/MM/AAAA-MM-DD.json.ots   sello OpenTimestamps (anclado en Bitcoin)
verificar_recogida.py                 verificador independiente
```

Cada anclaje incluye:

| Campo | Significado |
|---|---|
| `record_hashes` | hash de cada recogida registrada ese día |
| `merkle_root` | raíz de Merkle de esos hashes |
| `chain_head` | último hash de la cadena completa de registros al cierre del día |
| `prev_anchor_sha256` | SHA-256 del anclaje del día anterior (los anclajes también forman una cadena) |

Se publican también los días sin recogidas, para que no existan huecos.

## Cómo se construye

1. Cada recogida genera un registro con sus datos, el SHA-256 de la firma y de la foto, y un
   valor aleatorio. Su hash encadena con el registro anterior:
   `record_hash = SHA-256(prev_hash + "\n" + canonical)`.
2. Cada noche se calcula la raíz de Merkle de los registros recibidos ese día
   (hoja = `SHA-256(0x00 || hash)`, nodo = `SHA-256(0x01 || izq || der)`, el nodo impar sube sin duplicarse).
3. El archivo del anclaje se sella con [OpenTimestamps](https://opentimestamps.org), que lo
   ancla en la blockchain de Bitcoin. Ni nosotros ni GitHub podemos falsificar esa fecha.

## Cómo verificar una recogida

Ante una reclamación, ALUMABE entrega la **prueba de integridad** de la recogida (un .zip con el
registro, la firma, la foto, la prueba de Merkle y el anclaje). Con ella:

```
python verificar_recogida.py carpeta_descomprimida
```

y después se comprueba el sello en Bitcoin arrastrando `AAAA-MM-DD.json` y su `.ots` a
<https://opentimestamps.org>. El anclaje debe coincidir con el publicado en este repositorio.
