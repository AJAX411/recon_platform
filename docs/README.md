# Documentación Recon Facial

Este índice ordena las referencias sin mover documentos anteriores ni convertir
sus resultados históricos en verificaciones actuales. El código describe lo
implementado; OpenAPI describe el contrato HTTP; el Contexto Maestro v1.7 OFICIAL
y las resoluciones aprobadas gobiernan los requisitos por ámbito.

## Lectura vigente

1. [README de presentación](../README.md).
2. [Instrucciones permanentes](../AGENTS.md).
3. [Arquitectura actual y límites](./arquitectura/README.md).
4. [ADR-D0-BE-01 aprobada](../backend/ADR_D0_BE_01_ORGANIZACION_CAPACIDADES.md).
5. [Ensayo Docker funcional y límites](./pruebas/DOCKER_LOCAL_0010.md).
6. [Guía operativa Docker](../deploy/README.md).
7. [Contrato VIGENTE para transferir a Azure](./azure/CONTRATO_DESPLIEGUE.md) y
   [checklist de despliegue y demostración](./azure/CHECKLIST_DESPLIEGUE.md).
8. [OpenAPI](../backend/openapi.json), [backend](../backend/README.md),
   [frontend](../frontend/README.md) y [diseño SPA](../frontend/DESIGN.md).

Las cifras 190/190 frontend, 20/20 adaptador, 87 HTTPS/API, 37 Edge y persistencia
son evidencia histórica del ensayo Docker aprobado. Macro C revisa hashes y
documentación sin repetir esas pruebas si no cambia su ámbito. Publicar código
no acredita Azure, G6 Windows ni cierre del Incremento 0010.

El archivo maestro oficial completo se mantiene en la fuente documental privada
aportada al proyecto: `CONTEXTO_MAESTRO_PROYECTO_RECON_FACIAL_v1.7_OFICIAL.txt`
del paquete de referencias D0. No se sustituye por este índice ni se genera
otra versión. La aprobación Vanilla y ADR-D0-BE-01 refinan sus ámbitos.

## Registros históricos conservados

- [Estabilización A](./incrementos/0010_ESTABILIZACION_A.md) y
  [pruebas A](./pruebas/ESTABILIZACION_A.md).
- [Macro B: preparación estática](./incrementos/0010_MACRO_B.md) y
  [pruebas B](./pruebas/MACRO_B.md).
- [Backend 0009](../backend/INCREMENTO_0009_ESTRUCTURA_UNIFORME.md).
- [0010 P0 dashboard](../backend/INCREMENTO_0010_P0.md).
- [0010 P1-B catálogo](../backend/INCREMENTO_0010_P1B.md).
- [Frontend 0007-A](../frontend/INCREMENTO_0007-A.md) y
  [0007-B](../frontend/INCREMENTO_0007-B.md).
- [Frontend 0008 propuesta](../frontend/INCREMENTO_0008_BLOQUE1_PROPUESTA.md) y
  [cierre de etapa](../frontend/INCREMENTO_0008_BLOQUE3_CIERRE.md).
- [Tratamiento de los respaldos React y candidata](./arquitectura/README.md#respaldos-locales-no-publicados):
  conservados localmente, ignorados y fuera del commit de despliegue.

Los informes, manifiestos y evidencias de ejecución se entregan fuera del repo,
en un ZIP por encargo. Los respaldos privados no se publican en esos ZIP.
G6, Docker y Azure requieren sus puertas independientes; el Incremento 0010
permanece abierto.
