# Documentación Recon Facial

Este índice centraliza la historia por incremento sin perderla ni convertir
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

- [Estabilización A](./incrementos/0010/0010_ESTABILIZACION_A.md) y
  [pruebas A](./pruebas/ESTABILIZACION_A.md).
- [Macro B: preparación estática](./incrementos/0010/0010_MACRO_B.md) y
  [pruebas B](./pruebas/MACRO_B.md).
- [Backend 0009](./incrementos/0009/backend/INCREMENTO_0009_ESTRUCTURA_UNIFORME.md).
- [0010 P0 dashboard](./incrementos/0010/backend/INCREMENTO_0010_P0.md).
- [0010 P1-B catálogo](./incrementos/0010/backend/INCREMENTO_0010_P1B.md).
- [Frontend 0007-A](./incrementos/0007/frontend/INCREMENTO_0007-A.md) y
  [0007-B](./incrementos/0007/frontend/INCREMENTO_0007-B.md).
- [Frontend 0008 propuesta](./incrementos/0008/frontend/INCREMENTO_0008_BLOQUE1_PROPUESTA.md) y
  [cierre de etapa](./incrementos/0008/frontend/INCREMENTO_0008_BLOQUE3_CIERRE.md).
- [Tratamiento de los respaldos React y candidata](./arquitectura/README.md#respaldos-locales-no-publicados):
  conservados localmente, ignorados y fuera del commit de despliegue.

Los informes, manifiestos y evidencias de ejecución se entregan fuera del repo,
en un ZIP por encargo. Los respaldos privados no se publican en esos ZIP.
G6, Docker y Azure requieren sus puertas independientes; el Incremento 0010
permanece abierto.

## Ajustes finales Macro D

[Alcance, contrato y revisión pendiente](./incrementos/0010/MACRO_D.md). La ubicación física de la historia se consolida por incremento; los informes mantienen su contenido histórico y enlaces relativos actualizados. Incremento 0010 ABIERTO; no publica un commit ni autoriza Azure.

- [Sustentación del código (guion y preguntas)](./arquitectura/GUIA_SUSTENTACION_CODIGO.md).

## Puerta final Macro F

[Alcance y validación del cambio humano Bienvenido](./incrementos/0010/MACRO_F.md). La publicación se acredita en el acta externa F con SHA real; el SHA de Macro C no incluye D/E. Se conservan las reservas y la separación entre Docker probado y Azure preparado.
