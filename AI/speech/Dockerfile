FROM python:3.10
COPY . /src
WORKDIR /src
RUN apt-get update -y && apt-get install -y xdg-utils
RUN pip install --upgrade pip && pip install -r requirement.txt
RUN opentelemetry-bootstrap -a install
RUN export OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true

EXPOSE 8000
# CMD ["opentelemetry-instrument","--traces_exporter","console","--metrics_exporter","console","--logs_exporter","opentelemetry-collector.istio-system.svc.cluster.local:4317","uvicorn","speech:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["uvicorn","speech:app", "--host", "0.0.0.0", "--port", "8000"]