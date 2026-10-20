# Módulo Personas — Proyecto Recon Facial

## 1. Propósito

Este módulo será responsable de la información funcional de
las personas relacionadas con el reconocimiento facial y
el control de acceso físico.

Su diseño se fundamenta en el Contexto Maestro v1.5.

## 2. Estado arquitectónico

PROVISIONAL.

Se utiliza la arquitectura monolítica modular por capas
adoptada provisionalmente para la plataforma web.

## 3. Separación de responsabilidades

Persona y UsuarioPlataforma son conceptos diferentes.

- Persona representa al individuo relacionado con el
  reconocimiento facial y el control de acceso.
- UsuarioPlataforma representa una cuenta autorizada para
  utilizar la aplicación web.

La administración de cuentas, sesiones y roles corresponde
al módulo Identidad.

## 4. Decisiones provisionales relevantes

- Cada Persona tiene un TipoPersona principal actual.
- Una Persona puede existir sin una cuenta web.
- La vinculación futura entre Persona y UsuarioPlataforma y su cardinalidad siguen PENDIENTES. El prototipo no crea FK ni vínculo automático.
- El catálogo inicial TipoPersona sigue el Contexto Maestro v1.5.

Estas decisiones pueden evolucionar mediante el proceso
formal de arquitectura del proyecto.

## 5. Organización interna

API:
Recibirá solicitudes HTTP y gestionará la entrada y salida
de datos según el contrato aprobado.

Aplicación:
Coordinará los casos de uso y sus transacciones.

Dominio:
Representará las entidades y reglas de negocio.

Infraestructura:
Implementará la persistencia y las adaptaciones externas.

El incremento HTTP administrativo incorpora rutas, casos de uso y auditoría
persistente propios de Personas.

## 6. Capacidades funcionales candidatas

Se analizarán progresivamente:

- Registrar personas.
- Actualizar información de personas.
- Desactivar personas.
- Consultar información de personas.

Su implementación dependerá de los requisitos, casos de uso,
historias de usuario y criterios de aceptación vigentes.

## 7. Decisiones todavía abiertas

La persistencia inicial se preparó conforme a la resolución puntual
Registro de Personas y Persistencia MySQL. Continúan abiertos:

- Catálogo definitivo de tipos documentales y reglas avanzadas de formato.
- Obligatoriedad del identificador institucional para SERVICIOS_GENERALES.
- Reglas exactas de activación y desactivación más allá del estado inicial.
- Permisos y contrato HTTP: las reglas de este incremento son PROVISIONALES y
  requieren revisión independiente antes de su aplicación en MySQL.
- Relación operativa con el enrolamiento biométrico.
- Validación de la migración en MySQL; el modelo físico permanece provisional.

No se implementarán reglas ficticias para cerrar los demás puntos.

## API administrativa provisional

`GET /api/v1/personas/tipos`, `GET /api/v1/personas`,
`GET /api/v1/personas/{id_persona}`, `POST /api/v1/personas`,
`PATCH /api/v1/personas/{id_persona}` y
`PATCH /api/v1/personas/{id_persona}/estado` requieren sesión activa y rol
SUPERADMIN o ADMINISTRADOR. POST y PATCH exigen CSRF. El listado tiene límite
predeterminado 50, máximo 100, y filtros exactos por documento, identificador,
TipoPersona y estado. OPERADOR no recibe datos detallados por estas rutas.

Las escrituras registran actor, Persona, operación y fecha UTC en
`auditoria_personas` dentro de la misma transacción. La migración
`0004_auditoria_personas` está preparada y **no aplicada** en este incremento.
La tabla referencia la cuenta actora para integridad de auditoría; no vincula
Persona con UsuarioPlataforma. El estado ACTIVO/INACTIVO no altera biometría.
Este incremento no completa CU-03 ni incluye enrolamiento.

Esta auditoría especializada registra solo escrituras humanas exitosas de
Personas. Es una solución **PROVISIONAL** para este incremento, no la
implementación física definitiva de `EventoAuditoria` del Contexto Maestro
v1.5. La entidad lógica general también contempla eventos automáticos con
actor nullable; su catálogo, retención y modelo físico continúan PENDIENTES.

## 8. Seguridad y biometría

Este módulo no realiza reconocimiento facial.

No se decide aquí el almacenamiento de embeddings,
imágenes o plantillas biométricas.

Las responsabilidades biométricas deben mantenerse
separadas de la administración funcional de personas.
