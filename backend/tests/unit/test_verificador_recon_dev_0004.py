"""Barreras de recon_dev/0004 con dobles: nunca abre una conexión MySQL."""

import importlib
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url


@pytest.fixture
def verificador(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("verificar_recon_dev_0004")


@pytest.fixture
def verificador_objetos(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    return importlib.import_module("verificar_objetos_recon_dev_0004")


def test_destino_y_etapa_fallan_antes_de_crear_motor(verificador, monkeypatch):
    monkeypatch.setattr(verificador, "create_engine",
                        lambda *_args, **_kwargs: pytest.fail("No debe conectar"))
    for nombre in verificador.VARIABLES:
        monkeypatch.setenv(nombre, "ficticio")
    monkeypatch.setattr(verificador, "obtener_uri_mysql", lambda **_kwargs:
                        "mysql+pymysql://recon_dev_app:ficticia@127.0.0.1:3306/recon_tests")
    with pytest.raises(verificador.VerificacionFallida, match="destino"):
        verificador.verificar("antes")
    with pytest.raises(verificador.VerificacionFallida, match="estado previo"):
        verificador.verificar("despues")
    with pytest.raises(verificador.VerificacionFallida, match="Etapa"):
        verificador.verificar("otra")
    verificador.validar_destino(make_url(
        "mysql+pymysql://recon_dev_app:ficticia@127.0.0.1:3306/recon_dev"))
    for url in (
        "mysql+pymysql://recon_test_app:ficticia@127.0.0.1:3306/recon_dev",
        "mysql+pymysql://recon_dev_app:ficticia@192.0.2.1:3306/recon_dev",
        "mysql+pymysql://recon_dev_app:ficticia@127.0.0.1:3306/recon_tests",
    ):
        with pytest.raises(verificador.VerificacionFallida):
            verificador.validar_destino(make_url(url))


class ResultadoFalso:
    def __init__(self, filas):
        self.filas = filas

    def one(self):
        return self.filas[0]

    def all(self):
        return self.filas

    def scalars(self):
        return self

    def __iter__(self):
        return iter(self.filas)


class ConexionFalsa:
    def __init__(self, verificador):
        self.tablas = verificador.TABLAS_PREVIAS.copy()
        self.revision = "0003_sesiones_iam"
        self.base = "recon_dev"
        self.borrados = [("fk_sesion_usuario_cuenta", "RESTRICT")]
        self.filas = {tabla: [(1, "valor privado ficticio")]
                      for tabla in verificador.CLAVES_DATOS}
        self.auditorias_personas = 0

    def execute(self, consulta):
        sql = str(consulta)
        if "CURRENT_USER()" in sql:
            return ResultadoFalso([(self.base, "recon_dev_app@localhost",
                                    "recon_dev_app@localhost", 3306)])
        if "information_schema.TABLES" in sql:
            return ResultadoFalso([(tabla, "InnoDB") for tabla in self.tablas])
        if "version_num FROM alembic_version" in sql:
            return ResultadoFalso([self.revision])
        if "REFERENTIAL_CONSTRAINTS" in sql:
            return ResultadoFalso(self.borrados)
        if sql.startswith("SELECT * FROM `"):
            tabla = sql.split("`", 2)[1]
            return ResultadoFalso(self.filas[tabla])
        raise AssertionError("Consulta inesperada")

    def scalar(self, consulta):
        assert "COUNT(*) FROM auditoria_personas" in str(consulta)
        return self.auditorias_personas


class MotorFalso:
    def __init__(self, conexion):
        self.conexion = conexion
        self.liberado = False

    def connect(self):
        return self

    def __enter__(self):
        return self.conexion

    def __exit__(self, *_args):
        return False

    def dispose(self):
        self.liberado = True


def preparar_motor_falso(verificador, monkeypatch):
    conexion = ConexionFalsa(verificador)
    motor = MotorFalso(conexion)
    for nombre in verificador.VARIABLES:
        monkeypatch.setenv(nombre, "ficticio")
    monkeypatch.setattr(verificador, "obtener_uri_mysql", lambda **_kwargs:
                        "mysql+pymysql://recon_dev_app:ficticia@127.0.0.1:3306/recon_dev")
    monkeypatch.setattr(verificador, "create_engine", lambda *_args, **_kwargs: motor)
    monkeypatch.setattr(verificador, "verificar_esquema", lambda _conexion: None)
    monkeypatch.setattr(verificador, "verificar_datos_previos", lambda _conexion: None)
    monkeypatch.setattr(verificador, "verificar_sesion_nueva", lambda *_args, **_kwargs: None)
    return conexion, motor


def test_identidad_revision_tablas_y_fk_incorrectas_se_rechazan(verificador):
    conexion = ConexionFalsa(verificador)
    verificador.validar_identidad(conexion)
    verificador.validar_tablas_y_revision(conexion, "antes")
    conexion.base = "recon_tests"
    with pytest.raises(verificador.VerificacionFallida, match="identidad real"):
        verificador.validar_identidad(conexion)
    conexion.base = "recon_dev"
    conexion.revision = "0004_auditoria_personas"
    with pytest.raises(verificador.VerificacionFallida, match="revisión"):
        verificador.validar_tablas_y_revision(conexion, "antes")
    conexion.revision = "0003_sesiones_iam"
    conexion.tablas.add("auditoria_personas")
    with pytest.raises(verificador.VerificacionFallida, match="Tablas"):
        verificador.validar_tablas_y_revision(conexion, "antes")


def test_estado_privado_detecta_cambios_y_no_se_sobrescribe(verificador, tmp_path):
    conexion = ConexionFalsa(verificador)
    estado = verificador.huellas_datos(conexion)
    ruta = tmp_path / "estado.json"
    verificador.guardar_estado(ruta, estado)
    assert "valor privado ficticio" not in ruta.read_text(encoding="utf-8")
    verificador.comparar_estado(ruta, estado)
    with pytest.raises(verificador.VerificacionFallida, match="ya existe"):
        verificador.guardar_estado(ruta, estado)
    conexion.filas["persona"] = [(1, "dato cambiado")]
    with pytest.raises(verificador.VerificacionFallida, match="datos previos cambiaron"):
        verificador.comparar_estado(ruta, verificador.huellas_datos(conexion))
    ruta.write_text("contenido inválido", encoding="utf-8")
    with pytest.raises(verificador.VerificacionFallida, match="estado privado"):
        verificador.comparar_estado(ruta, estado)


def test_estado_privado_usa_exclusividad_y_reporta_fallos_de_escritura(
    verificador, monkeypatch, tmp_path
):
    ruta = tmp_path / "estado.json"
    apertura_original = verificador.os.open
    aperturas = []

    def abrir(ruta_recibida, banderas, modo):
        aperturas.append((ruta_recibida, banderas, modo))
        return apertura_original(ruta_recibida, banderas, modo)

    monkeypatch.setattr(verificador.os, "open", abrir)
    verificador.guardar_estado(ruta, {"persona": {"filas": 0, "huella": "ficticia"}})
    assert aperturas == [(ruta, verificador.os.O_WRONLY | verificador.os.O_CREAT |
                           verificador.os.O_EXCL, 0o600)]
    with pytest.raises(verificador.VerificacionFallida, match="ya existe"):
        verificador.guardar_estado(ruta, {})
    assert ruta.is_file()

    ruta_ausente = tmp_path / "carpeta_ausente" / "estado.json"
    with pytest.raises(verificador.VerificacionFallida, match="escribir el JSON privado"):
        verificador.guardar_estado(ruta_ausente, {})
    assert not ruta_ausente.exists()


def test_error_de_escritura_no_expone_detalle_del_sistema(verificador, monkeypatch, tmp_path):
    secreto = "ruta-y-dato-privado-ficticios"

    def apertura_fallida(*_args, **_kwargs):
        raise PermissionError(secreto)

    monkeypatch.setattr(verificador.os, "open", apertura_fallida)
    ruta = tmp_path / "estado.json"
    with pytest.raises(verificador.VerificacionFallida) as capturado:
        verificador.guardar_estado(ruta, {})
    assert "escribir el JSON privado" in str(capturado.value)
    assert secreto not in str(capturado.value)
    assert not ruta.exists()


def test_flujo_antes_y_despues_valida_0004_y_preserva_datos(
    verificador, monkeypatch, tmp_path
):
    conexion, motor = preparar_motor_falso(verificador, monkeypatch)
    llamadas = []
    monkeypatch.setattr(verificador, "validar_0004", lambda _conexion: llamadas.append("0004"))
    ruta = tmp_path / "estado.json"
    verificador.verificar("antes", guardar=ruta)
    assert motor.liberado
    verificador.verificar("antes", comparar=ruta)
    conexion.revision = "0004_auditoria_personas"
    conexion.tablas.add("auditoria_personas")
    verificador.verificar("despues", comparar=ruta)
    assert llamadas == ["0004"]
    conexion.auditorias_personas = 1
    with pytest.raises(verificador.VerificacionFallida, match="debe estar vacía"):
        verificador.verificar("despues", comparar=ruta)
    conexion.auditorias_personas = 0
    conexion.borrados = [("fk_sesion_usuario_cuenta", "CASCADE")]
    with pytest.raises(verificador.VerificacionFallida, match="política de borrado"):
        verificador.verificar("despues", comparar=ruta)
    conexion.borrados = [("fk_sesion_usuario_cuenta", "RESTRICT")]

    def check_incorrecto(_conexion):
        raise verificador.Check0004Fallido("El CHECK de acciones no coincide.")

    monkeypatch.setattr(verificador, "validar_0004", check_incorrecto)
    with pytest.raises(verificador.VerificacionFallida, match="CHECK de acciones"):
        verificador.verificar("despues", comparar=ruta)


@pytest.mark.parametrize("fase,esperado", [
    ("conexion", "conexión MySQL"),
    ("validacion", "validación de esquema/datos"),
    ("escritura", "escribir el JSON privado"),
])
def test_fallos_se_distinguen_sin_revelar_detalles(
    verificador, monkeypatch, tmp_path, capsys, fase, esperado
):
    _conexion, motor = preparar_motor_falso(verificador, monkeypatch)
    ruta = tmp_path / "estado.json"
    secreto = "clave-y-dato-personal-ficticios"

    def fallar(*_args, **_kwargs):
        raise RuntimeError(secreto)

    if fase == "conexion":
        monkeypatch.setattr(motor, "connect", fallar)
    elif fase == "validacion":
        monkeypatch.setattr(verificador, "verificar_esquema", fallar)
    else:
        ruta = tmp_path / "carpeta_ausente" / "estado.json"

    monkeypatch.setattr(verificador.sys, "argv", [
        "verificar_recon_dev_0004.py", "--antes", "--guardar-estado", str(ruta)
    ])
    assert verificador.main() == 1
    salida = capsys.readouterr()
    assert esperado in salida.err
    assert secreto not in salida.err + salida.out
    assert not ruta.exists()
    assert motor.liberado


def test_script_exige_autorizacion_y_orden_de_barreras():
    script = (Path(__file__).resolve().parents[2] / "scripts" /
              "aplicar_0004_recon_dev.sh").read_text(encoding="utf-8")
    assert "RECON_AUTORIZAR_MIGRACION_0004_RECON_DEV" in script
    assert "APLICAR_0004_RECON_DEV" in script
    assert "--user=recon_dev_app" in script and "--result-file=" in script
    assert "--skip-routines --skip-events --skip-triggers" in script
    assert script.count("scripts/verificar_objetos_recon_dev_0004.py") == 2
    administrativa = script.index("scripts/verificar_objetos_recon_dev_0004.py")
    primera = script.index("--antes --guardar-estado")
    respaldo = script.index("--result-file=")
    confirmacion = script.index("[[ \"$confirmacion\" != APLICAR_0004_RECON_DEV ]]")
    segunda_administrativa = script.rindex("scripts/verificar_objetos_recon_dev_0004.py")
    segunda = script.index("--antes --comparar-estado")
    migracion = script.index("db upgrade 0004_auditoria_personas")
    posterior = script.index("--despues --comparar-estado")
    assert administrativa < primera < respaldo < confirmacion < segunda_administrativa
    assert segunda_administrativa < segunda < migracion < posterior


@pytest.mark.parametrize("grants,apto", [
    ([], False),
    (["GRANT EVENT ON `recon_dev`.* TO `admin`@`localhost`"], False),
    (["GRANT SHOW_ROUTINE ON *.* TO `admin`@`localhost`"], False),
    (["GRANT SELECT ON *.* TO `admin`@`localhost`",
      "GRANT EVENT ON `recon_dev`.* TO `admin`@`localhost`"], False),
    (["GRANT SELECT, EVENT ON *.* TO `admin`@`localhost`",
      "GRANT TRIGGER ON `recon_dev`.`persona` TO `admin`@`localhost`"], False),
    (["GRANT SELECT ON *.* TO `admin`@`localhost`",
      "GRANT EVENT, TRIGGER ON `recon_dev`.* TO `admin`@`localhost`"], True),
    (["GRANT SHOW_ROUTINE ON *.* TO `admin`@`localhost`",
      "GRANT EVENT, TRIGGER ON `recon_dev`.* TO `admin`@`localhost`"], True),
    (["GRANT ALL PRIVILEGES ON *.* TO `admin`@`localhost` WITH GRANT OPTION"], True),
    (["GRANT SELECT, EVENT, TRIGGER ON *.* TO `admin`@`localhost`",
      "REVOKE SELECT, EVENT ON `recon_dev`.* FROM `admin`@`localhost`"], False),
    (["GRANT `rol_admin`@`localhost` TO `admin`@`localhost`"], False),
])
def test_visibilidad_administrativa_exige_concesiones_directas(
    verificador_objetos, grants, apto
):
    assert verificador_objetos.privilegios_suficientes(grants) is apto


class ConexionObjetosFalsa:
    def __init__(self):
        self.base = "recon_dev"
        self.cuenta = "admin@localhost"
        self.usuario = "admin@localhost"
        self.puerto = 3306
        self.grants = ["GRANT ALL PRIVILEGES ON *.* TO `admin`@`localhost`"]
        self.eventos = 0
        self.rutinas = 0
        self.triggers = 0
        self.consultas_conteo = 0

    def execute(self, consulta):
        sql = str(consulta)
        if "SHOW GRANTS" in sql:
            return ResultadoFalso([(grant,) for grant in self.grants])
        if "CURRENT_USER()" in sql:
            return ResultadoFalso([(self.base, self.cuenta, self.usuario, self.puerto)])
        raise AssertionError("Consulta inesperada")

    def scalar(self, consulta):
        self.consultas_conteo += 1
        sql = str(consulta)
        if "information_schema.EVENTS" in sql:
            return self.eventos
        if "information_schema.ROUTINES" in sql:
            return self.rutinas
        if "information_schema.TRIGGERS" in sql:
            return self.triggers
        raise AssertionError("Consulta inesperada")


def test_cero_objetos_solo_con_identidad_y_privilegios_suficientes(verificador_objetos):
    conexion = ConexionObjetosFalsa()
    verificador_objetos.verificar_conexion(conexion, "admin")
    assert conexion.consultas_conteo == 3
    conexion.base = "recon_tests"
    with pytest.raises(verificador_objetos.VerificacionFallida, match="identidad real"):
        verificador_objetos.verificar_conexion(conexion, "admin")
    conexion.base = "recon_dev"
    conexion.cuenta = "recon_dev_app@localhost"
    with pytest.raises(verificador_objetos.VerificacionFallida, match="identidad real"):
        verificador_objetos.verificar_conexion(conexion, "admin")
    conexion.cuenta = "admin@localhost"
    conexion.grants = ["GRANT USAGE ON *.* TO `admin`@`localhost`"]
    conexion.consultas_conteo = 0
    with pytest.raises(verificador_objetos.VerificacionFallida, match="visibilidad"):
        verificador_objetos.verificar_conexion(conexion, "admin")
    assert conexion.consultas_conteo == 0
    conexion.grants = [None]
    with pytest.raises(verificador_objetos.VerificacionFallida, match="visibilidad"):
        verificador_objetos.verificar_conexion(conexion, "admin")
    conexion.grants = ["GRANT ALL PRIVILEGES ON *.* TO `admin`@`localhost`"]
    conexion.eventos = 1
    with pytest.raises(verificador_objetos.VerificacionFallida, match="respaldo"):
        verificador_objetos.verificar_conexion(conexion, "admin")
    conexion.eventos = 0
    conexion.rutinas = 1
    with pytest.raises(verificador_objetos.VerificacionFallida, match="respaldo"):
        verificador_objetos.verificar_conexion(conexion, "admin")
    conexion.rutinas = 0
    conexion.triggers = 1
    with pytest.raises(verificador_objetos.VerificacionFallida, match="respaldo"):
        verificador_objetos.verificar_conexion(conexion, "admin")


@pytest.mark.parametrize("conteo", [None, "0", False, -1])
def test_conteo_ambiguo_falla_cerrado(verificador_objetos, conteo):
    conexion = ConexionObjetosFalsa()
    conexion.triggers = conteo
    with pytest.raises(verificador_objetos.VerificacionFallida, match="no son concluyentes"):
        verificador_objetos.verificar_conexion(conexion, "admin")


def test_cuenta_administrativa_distinta_antes_de_crear_motor(verificador_objetos, monkeypatch):
    monkeypatch.setattr(verificador_objetos, "create_engine",
                        lambda *_args, **_kwargs: pytest.fail("No debe conectar"))
    monkeypatch.setenv("RECON_BACKUP_ADMIN_USER", "recon_dev_app")
    monkeypatch.setenv("RECON_BACKUP_ADMIN_PASSWORD", "ficticia")
    with pytest.raises(verificador_objetos.VerificacionFallida, match="distinta"):
        verificador_objetos.verificar()


def test_cuenta_administrativa_usa_solo_destino_fijo(verificador_objetos, monkeypatch):
    conexion = ConexionObjetosFalsa()
    motor = MotorFalso(conexion)
    destinos = []

    def crear_motor(url, **_kwargs):
        destinos.append(url)
        return motor

    monkeypatch.setenv("RECON_BACKUP_ADMIN_USER", "admin")
    monkeypatch.setenv("RECON_BACKUP_ADMIN_PASSWORD", "ficticia")
    monkeypatch.setattr(verificador_objetos, "create_engine", crear_motor)
    verificador_objetos.verificar()
    assert motor.liberado
    assert len(destinos) == 1
    assert (destinos[0].host, destinos[0].port, destinos[0].database,
            destinos[0].username) == ("127.0.0.1", 3306, "recon_dev", "admin")


def test_error_inesperado_no_expone_detalles(verificador_objetos, monkeypatch, capsys):
    def fallo():
        raise RuntimeError("dato privado ficticio")

    monkeypatch.setattr(verificador_objetos.sys, "argv", ["verificador"])
    monkeypatch.setattr(verificador_objetos, "verificar", fallo)
    assert verificador_objetos.main() == 1
    salida = capsys.readouterr()
    assert "dato privado ficticio" not in salida.err
    assert "NO APTO" in salida.err
