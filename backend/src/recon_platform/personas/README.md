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
- Una Persona puede tener como máximo una cuenta web.
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

Actualmente existen dominio, aplicación e infraestructura; la API se
incorporará cuando sus contratos, autenticación y permisos sean aprobados.

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
- Permisos de cada rol para administrar personas.
- Contratos HTTP y validaciones de entrada.
- Relación operativa con el enrolamiento biométrico.
- Validación de la migración en MySQL; el modelo físico permanece provisional.

No se implementarán reglas ficticias para cerrar estos puntos.

## 8. Seguridad y biometría

Este módulo no realiza reconocimiento facial.

No se decide aquí el almacenamiento de embeddings,
imágenes o plantillas biométricas.

Las responsabilidades biométricas deben mantenerse
separadas de la administración funcional de personas.
