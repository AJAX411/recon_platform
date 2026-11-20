"""Renderiza Host/FQDN exacto para Nginx; no genera TLS, conecta o despliega."""

import argparse
from pathlib import Path
import re


def render(fqdn: str) -> str:
    """Rechaza comodines e inyección; inserta solo un nombre DNS ASCII completo."""
    fqdn = fqdn.lower()
    labels = fqdn.split(".")
    if (len(fqdn) > 253 or len(labels) < 2
            or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                       for label in labels)
            or labels[-1].isdigit()):
        raise ValueError("Se requiere un FQDN exacto sin protocolo, puerto o comodines.")
    template = Path(__file__).with_name("nginx.conf.template").read_text(encoding="utf-8")
    if template.count("__RECON_FQDN__") != 2:
        raise ValueError("La plantilla no coincide con el contrato de renderizado.")
    return template.replace("__RECON_FQDN__", fqdn)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fqdn", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    content = render(args.fqdn)
    # Exclusivo: no sobrescribir configuración existente ni escribir en el repo.
    root = Path(__file__).resolve().parents[2]
    target = args.output.resolve()
    if target.is_relative_to(root):
        raise ValueError("La configuración renderizada se guarda fuera del repositorio.")
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


if __name__ == "__main__":
    main()
