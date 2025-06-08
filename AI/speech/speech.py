from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from boto3 import Session
from botocore.exceptions import BotoCoreError, ClientError
from contextlib import closing
import os
import sys
import subprocess
from datetime import datetime
from tempfile import gettempdir
from pydantic import BaseModel
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv
from transformers import PreTrainedTokenizerFast, BartForConditionalGeneration
import logging
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler 
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry._logs import (
    SeverityNumber,
    get_logger,
    get_logger_provider,
    std_to_otel,
    set_logger_provider
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
otel_endpoint_url = os.getenv("OTEL_ENDPOINT_URL", 'http://opentelemetry-collector.istio-system.svc.cluster.local:4317')

class FormattedLoggingHandler(LoggingHandler):
    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        record.msg = msg
        record.args = None
        self._logger.emit(self._translate(record))

def otel_logging_init():
    # ------------Logging
    # Set logging level
    # CRITICAL = 50
    # ERROR = 40
    # WARNING = 30
    # INFO = 20
    # DEBUG = 10
    # NOTSET = 0
    # default = WARNING
    
    # ------------ Opentelemetry loging initialization
    logger_provider = LoggerProvider(
        resource=Resource.create({})
    )
    set_logger_provider(logger_provider)
    otlp_log_exporter = OTLPLogExporter(endpoint=otel_endpoint_url)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_log_exporter))
    otel_log_handler = FormattedLoggingHandler(logger_provider=logger_provider)
    LoggingInstrumentor().instrument()
    logFormatter = logging.Formatter(os.getenv("OTEL_PYTHON_LOG_FORMAT", None))
    otel_log_handler.setFormatter(logFormatter)
    logging.getLogger().addHandler(otel_log_handler)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
otel_logging_init()

bucket = os.environ["bucket"]
session = Session(
    aws_access_key_id=os.getenv("aws_access_key_id",None),
    aws_secret_access_key=os.getenv("aws_secret_access_key",None),
    region_name="ap-northeast-2")
polly = session.client("polly")
s3 = session.client("s3")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY",None))

class Item(BaseModel):
    user_id: str
    text: str
class SttItem(BaseModel):
    user_uuid: str
    itv_cnt: str
    file_path: str
class TextItem(BaseModel):
    text: str

@app.post("/speech/stt", status_code=200)
async def stt(item: SttItem):
    start_time = datetime.now()
    file_path = item.file_path.replace('s3://'+bucket+'/','')
    local_file_path = item.user_uuid+item.itv_cnt+".mp3"
    s3.download_file( 
        bucket,
        file_path,
        local_file_path
    )
    
    with open(local_file_path,"rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file, 
            response_format="text"
        )
    os.remove(local_file_path)
    date_file = str(start_time.timestamp()).replace('.','')
    original_file_name = f'{item.user_uuid}/{item.itv_cnt}/{date_file}.txt'
    end_time = datetime.now()
    elapsed_time = end_time - start_time
    logger.info(f'STT SEC:{elapsed_time.total_seconds()}')
    
    s3.put_object(
        Body = transcript,
        Bucket = bucket,
        Key = original_file_name
    )
    return {"s3_file_path":'s3://'+bucket+'/'+original_file_name}
FastAPIInstrumentor.instrument_app(app)