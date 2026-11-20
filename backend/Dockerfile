# Base oficial linux/amd64 verificada para el ensayo aislado; sin frontend externo de build.
ARG PYTHON_IMAGE=python:3.14.10-slim-bookworm@sha256:1faf2343e747208b2a36e5f2b5ff908ec3b2d0078a6a7bfe73b535698fe83909
FROM ${PYTHON_IMAGE} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/recon/src:/opt/recon/deploy
WORKDIR /opt/recon
COPY backend/deploy/requirements-runtime.txt backend/deploy/requirements-wsgi.txt /tmp/requirements/
# Instalaciones solo dentro de una futura construcción expresamente autorizada.
# Fallar si falta wheel Linux/CPython 3.14, sin compilar fuentes arbitrarias.
RUN python -m pip install --no-cache-dir --only-binary=:all: \
    -r /tmp/requirements/requirements-runtime.txt -r /tmp/requirements/requirements-wsgi.txt \
    && groupadd --gid 10001 recon && useradd --uid 10001 --gid recon --no-create-home recon
COPY backend/src/ /opt/recon/src/
COPY backend/deploy/app_wsgi.py /opt/recon/deploy/app_wsgi.py
COPY backend/migrations/ /opt/recon/migrations/
USER 10001:10001
EXPOSE 8000
# Liveness de factory/proceso, no disponibilidad del esquema ni login.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/_diagnostico',timeout=3); assert r.status==200"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--worker-class", "sync", "--timeout", "30", "--forwarded-allow-ips", "", "--access-logfile", "/dev/null", "--error-logfile", "-", "--log-level", "warning", "app_wsgi:create_wsgi_app()"]
