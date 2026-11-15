# Incremento 0009 — Estructura uniforme B controlada

**Estado:** IMPLEMENTADO LOCALMENTE, Bloque 2; incremento sin cerrar.
**Ejecución:** 14/11/2026. Autorrevisión local; revisión independiente pendiente.
**Baseline:** Contexto Maestro v1.7 OFICIAL (25/10/2026), resoluciones IAM,
Personas/enrolamiento, Personas/persistencia y EventoAcceso 0006, conservando
sus estados y ámbitos. Esta reorganización no reemplaza el baseline.

## Manifiesto previo U0

- Fuentes indispensables accesibles y leídas íntegramente: AGENTS.md, encargo
  de Bloque 2, definición ampliada B controlada y Contexto Maestro v1.7.
- Autorización: mensaje expreso del responsable en esta sesión. Los estados
  de propuesta de los documentos de definición se conservan como historia.
- Git inicial: `main`, HEAD `2180476cc5bd0b582fff4b793a9b7d9cf1a25feb`,
  árbol e índice limpios; último commit de frontend 0008.
- Alcance: matrices B001–B069, P01–P11, N01–N27, T01–T23, S15, M01,
  NT01/NT02 y D01–D04. Servicios son los casos de uso existentes.
- Criterios: mismos contratos HTTP, siete Blueprints, once clases/tablas,
  metadata, transacciones, seguridad, relojes y privacidad por rol; fuentes
  congeladas intactas. Sin dependencias, endpoints ni reglas nuevas.
- Referencia capturada antes de editar: inventario AST de módulos y
  consumidores, mapa completo de reglas/hooks, firma física SQLAlchemy con
  compilación MySQL sin conexión y corpus de 102 respuestas HTTP ficticias.
- Aislamiento: SQLite exclusivamente en memoria, entorno privado retirado
  del proceso y barrera contra cualquier conexión distinta; sin leer `.env`,
  ejecutar procedimientos operativos, Alembic o bootstrap sobre una base real.
- Línea base ejecutada: 219 unitarias aprobadas; Ruff sin hallazgos;
  82 pruebas frontend aprobadas en ocho archivos.

## Resultado de U1–U5

Se implementó el árbol aprobado: 100 archivos Python de aplicación, de los
cuales 64 contienen funcionalidad y 36 son inicializadores técnicos sin lógica.
Se retiraron los 28 orígenes funcionales y dos inicializadores de aplicación
obsoletos, sin fachadas ni clases duplicadas. El
[README backend](./README.md#rutas-históricas-del-corte-2180476) contiene el cruce
completo de rutas históricas.

- U1: dominio, puertos y servicios conservan los casos de uso y sus cuerpos.
- U2: modelos, repositorios y UoW separados; once modelos/tablas canónicos,
  una instancia `db` y la misma `db.session` por operación.
- U3: siete módulos DTO con funciones de representación y validación de forma.
  Login sigue admitiendo claves adicionales; IAM/Persona/Manual conservan sus
  validaciones y etapas diferentes. Las proyecciones por rol no se rediseñaron.
- U4: siete controladores, seguridad HTTP, utilidad administrativa y ocho
  constructores de composición; relojes y construcción por petición conservados.
- U5: retiradas, imports de consumidores, documentación y pruebas. M01 cambió
  solo imports; S15 cambió un import y no se ejecutó como procedimiento.

## Evidencia ejecutada

| Comprobación | Resultado real |
|---|---|
| Línea base local | 219 unitarias y 82 frontend aprobadas; Ruff sin hallazgos |
| Backend final | 257 aprobadas; 0 fallidas, omitidas o errores |
| Nuevas suites | 32 DTO y 6 de estructura/composición/reloj aprobadas |
| Frontend final | 82 aprobadas en ocho archivos; build y lint con salida 0 |
| Ruff final | Sin hallazgos, selección E4/E7/E9/F, sin correcciones automáticas |
| AST/compilación en memoria | 146 archivos Python, incluidos tests/scripts/revisiones, sin ejecutarlos como procedimientos |
| Equivalencia de cuerpos trasladados U1/U2 | 129 símbolos, sin diferencias salvo ubicación de imports |
| Equivalencia HTTP | 33 operaciones/26 paths, siete Blueprints; 35 reglas totales incluyendo static/diagnóstico, mismos conversores/vistas/métodos/hooks |
| Corpus antes/después | 102 respuestas ficticias equivalentes con tiempos controlados |
| ORM | Once tablas y clases, misma firma física; compilación MySQL sin conexión |
| Fuentes congeladas | OpenAPI, seis revisiones, configuración/dependencias y frontend conservados según alcance |
| Autorrevisión de alcance | 129 entradas Git: 22 modificadas, 30 retiradas, 77 nuevas; ninguna fuera de la matriz |
| Git | `main`, HEAD inicial conservado, índice vacío; diff --check sin hallazgos |

Las unitarias se ejecutaron mediante un envoltorio temporal que retira el
entorno privado y bloquea cualquier conexión distinta de SQLite en memoria:
cero intentos no autorizados. Las pruebas de verificadores operativos usan
dobles; las pruebas de bootstrap usan memoria/SQLite o validan el fallo previo
a persistencia, sin bootstrap operativo. Ninguna función Alembic upgrade o
downgrade se ejecutó. SQLite no demuestra locks, concurrencia o integridad
de una base MySQL real.

Las nuevas [pruebas de estructura](./tests/unit/test_estructura_0009.py)
congelan las firmas de U0 para DDL/índices MySQL compilados y mapa HTTP completo,
verifican primer registro en un proceso limpio, identidad de clases, sesión
compartida y reloj canónico. Las [pruebas DTO](./tests/unit/test_dto_0009.py)
verifican forma, null, fechas, etapas y selección explícita de campos.

| Firma SHA-256 de referencia | Valor conservado |
|---|---|
| Metadata física ampliada | `718892cf4b58b7c2cf7806ae78dfa827317da87e5f13976e13971d1d76388a3d` |
| DDL/índices MySQL compilados | `c429d9b17d888f46f8c6ad03ed72b346b83a61402ea9f0dbd42cf7b5b5e9d934` |
| Reglas/vistas/hooks | `3cd6637c064f3e1c0d92dfb67e9aa39e4c9b2e1d64ab616ec468199653d5d409` |
| Corpus HTTP canónico | `dc16635f6668026296260f1f882bb7fa3c19f8cc22ee13ee55555ca267acdbee` |
| OpenAPI, bytes | `a8d7f663530dc21e79265364baff77a77e431d0fcdf3109e14f679f4bf991ed3` |

La comparación normaliza únicamente valores efímeros de CSRF/cookie a
propiedades de presencia/configuración y el orden no significativo de `Allow`.
El nombre antiguo del hook de transporte se coteja con su renombre aprobado;
no se omiten métodos, cuerpos o políticas. Los cambios de import_name/root_path
de Blueprints son consecuencia del traslado; no hay recursos estáticos o
templates propios configurados que dependan de esas ubicaciones.

Se corrigieron una referencia de monkeypatch a Auditoría retirada y 26 avisos
E402 por ubicación de docstrings en extracciones. El comparador temporal de
snapshots necesitó normalizar tuplas/listas JSON y el orden de `Allow`;
no fueron cambios de contrato. El informe externo detalla también los fallos
de herramientas auxiliares y la secuencia de las verificaciones.

## Riesgos y pendientes de gobierno

V09 MySQL requiere autorización operacional independiente. Bloque 3 y revisión
independiente posteriores; no se declara cerrado ni publicado el incremento.
Git de escritura permanece exclusivamente bajo control del responsable.

Se conservan los acoplamientos de consultas entre capacidades y proyecciones
en infraestructura, y el acceso interno para el contexto de fallo de modo.
No se modificó la política de retención ni se repararon literalmente enlaces
históricos del frontend: se documentó su correspondencia. El docstring histórico
de [env Alembic](./migrations/env.py) no hace seguro importarlo: su cuerpo ejecuta
la selección de migración; se revisó por AST y solo se cambiaron imports.

No hubo lectura o escritura operativa de bases, migraciones, procedimientos
del ZIP, cambios de dependencias, frontend, biometría o Git de escritura.
El resultado local no acredita producción, reconocimiento facial integrado ni
apertura física. Continúan los estados PROVISIONAL, PENDIENTE y EN INVESTIGACIÓN
en sus ámbitos. El Bloque 3 deberá revisar el diff y esta evidencia de manera
independiente antes de decidir validación adicional o publicación.
