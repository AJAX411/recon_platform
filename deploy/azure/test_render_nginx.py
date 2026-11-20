"""Pruebas offline del renderizador de configuración; no inician servicios."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from render_nginx import main, render


class RenderNginxTests(unittest.TestCase):
    def test_fqdn_exacto_y_tls_externo(self):
        config = render("Recon-Static.Example.Test")
        self.assertIn("server_name recon-static.example.test;", config)
        self.assertIn("if ($host != recon-static.example.test)", config)
        self.assertIn("ssl_certificate_key /run/secrets/tls_private_key;", config)
        self.assertNotIn("__RECON_FQDN__", config)

    def test_rechaza_inyeccion_wildcard_puerto_url_e_ip(self):
        for fqdn in ["*.example.test", "example.test:443", "https://example.test",
                     "example.test; return 200;", "example.test\n}", "localhost",
                     "127.0.0.1", "-a.example.test", "a..test", "a." + "b" * 64 + ".test"]:
            with self.subTest(fqdn=fqdn), self.assertRaises(ValueError):
                render(fqdn)

    def test_cli_no_sobrescribe_y_guarda_fuera_del_repo(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "nginx.conf"
            args = ["render_nginx.py", "--fqdn", "recon-static.example.test", "--output", str(target)]
            with patch.object(sys, "argv", args):
                main()
                original = target.read_bytes()
                with self.assertRaises(FileExistsError):
                    main()
                self.assertEqual(original, target.read_bytes())

    def test_cli_rechaza_destino_dentro_del_repo(self):
        target = Path(__file__).with_name("NO_CREAR.conf")
        args = ["render_nginx.py", "--fqdn", "recon-static.example.test", "--output", str(target)]
        with patch.object(sys, "argv", args), self.assertRaises(ValueError):
            main()
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
