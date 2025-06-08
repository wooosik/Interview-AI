# 표준 라이브러리 임포트
import os # 운영 체제와 사옿작용하기 위한 모듈
import json # JSON 데이터 처리
import logging # 로깅 설정 및 사용
import io # 입출력 관련 기능
from datetime import datetime # 날짜와 시간 처리

# 타사 라이브러리 임포트
from fastapi import FastAPI # FASTAPI 웹 프레임워크 및 CORS 미들웨어
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel # 데이터 검증 및 설정을 위한 Pydantic 모델
from dotenv import load_dotenv # 파일에서 환경 변수 로드
from PyPDF2 import PdfReader # PDF 및 DOCS 파일 처리
from docx import Document 
import boto3 # AWS 서비스와의 상호작용
import redis # Redis 클라이언트
from anthropic import AnthropicBedrock # Anthropic Bedrock API 클라이언트
# from llama_index.readers.file import HWPReader # llama HWP 파일 처리

# 트레이싱 관련 임포트
from opentelemetry import trace # OpenTelemetry 기본 트레이싱 API 접근 모듈
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor # FastApi 애플리케이션을 자동으로 트레이싱하기 위한 인스트루먼테이션 모듈
from opentelemetry.sdk.trace import TracerProvider # 트레이서 제공자를 설정하기 위한 모듈(트레이서를 생성하고 구성하기 위한 기본 설정을 제공)
from opentelemetry.sdk.resources import Resource # 리소스를 정의하기 위한 모듈(서비스 이름, 환경 등과 같은 메타 데이터를 트레이싱 데이터에 추가)
from opentelemetry.sdk.trace.export import BatchSpanProcessor # 스팬을 배치로 처리하여 내보내는 프로세서
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter # OTLP 형식으로 스팬 데이터를 gRPC를 통해 내보내는 Exporter
## 로깅 관련 임포트
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter # 
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler 
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
# from opentelemetry.instrumentation.logging import LoggingInstrumentor
# from opentelemetry._logs import (
#     SeverityNumber,
#     get_logger,
#     get_logger_provider,
#     std_to_otel,
#     set_logger_provider
# )

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
    # set_logger_provider(logger_provider)
    otlp_log_exporter = OTLPLogExporter(endpoint=otel_endpoint_url)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_log_exporter))
    otel_log_handler = FormattedLoggingHandler(logger_provider=logger_provider)
    # LoggingInstrumentor().instrument()
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


# 환경 변수 가져오기
OPEN_API_KEY = os.getenv('OPEN_API_KEY')
AWS_REGION = os.getenv('AWS_REGION')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
ASSISTANT_ID = os.getenv('ASSISTANT_ID')
CHATBOT_ASSISTANT_ID = os.getenv('CHATBOT_ASSISTANT_ID')
AWS_BEDROCK_REGION = os.getenv('AWS_BEDROCK_REGION')
SYSTEM_COVERLETTER = os.getenv('SYSTEM_COVERLETTER')
SYSTEM_BASIC_CHAT = os.getenv('SYSTEM_BASIC_CHAT')
SYSTEM_EXPERIENCE_CHAT = os.getenv('SYSTEM_EXPERIENCE_CHAT')
SYSTEM_SOLVING_CHAT = os.getenv('SYSTEM_SOLVING_CHAT')
SYSTEM_PERSONALITY_CHAT = os.getenv('SYSTEM_PERSONALITY_CHAT')
SYSTEM_CHAT = os.getenv('SYSTEM_CHAT')
SYSTEM_REPORT = os.getenv('SYSTEM_REPORT')
AWS_ELASTICACHE_REDIS_ENDPOINT = os.getenv('AWS_ELASTICACHE_REDIS_ENDPOINT')
AWS_ELASTICACHE_REDIS_USER = os.getenv('AWS_ELASTICACHE_REDIS_USER')
AWS_ELASTICACHE_REDIS_PASSWORD = os.getenv('AWS_ELASTICACHE_REDIS_PASSWORD')

s3_client = boto3.client(
    's3',
    aws_access_key_id= AWS_ACCESS_KEY_ID,
    aws_secret_access_key= AWS_SECRET_ACCESS_KEY,
    region_name= AWS_REGION
)

bedrock_client = AnthropicBedrock(
    aws_access_key= AWS_ACCESS_KEY_ID,
    aws_secret_key= AWS_SECRET_ACCESS_KEY,
    aws_region= AWS_BEDROCK_REGION,
)

# redis_client = redis.Redis(host='192.168.56.200', port=6379, decode_responses=True)
redis_client = redis.Redis(host='192.168.0.22', port=30637, password='k8spass#')
# redis_client = redis.Redis(host=AWS_ELASTICACHE_REDIS_ENDPOINT, port=6379, ssl=True, username=AWS_ELASTICACHE_REDIS_USER, password=AWS_ELASTICACHE_REDIS_PASSWORD)

class coverletterItem(BaseModel):
    coverletter_url: str
    position: str
    itv_no: str
class chatItem(BaseModel):
    answer_url: str
    itv_no: str
    question_number: int
class reportItem(BaseModel):
    itv_no: str
    question_number: int

async def store_history_redis(hash_name,field,value):
    try:
        # 질문 데이터를 JSON 문자열로 변환
        value_json = json.dumps(value)
        
        # Redis 리스트에 데이터 추가
        redis_client.hset(hash_name,field,value_json)

        print("Data successfully stored in Redis.")
    except Exception as e:
        print(f"Error storing data in Redis: {e}")

async def get_history_redis(hash_name,field):
    try:
        # HGET 명령어를 사용하여 데이터 가져오기
        value = redis_client.hget(hash_name, field)
        
        if value:
            # 값이 JSON 문자열이면 파이썬 객체로 변환
            value = json.loads(value.decode('utf-8'))
            return value
        else:
            print(f"No data found in Redis for {hash_name} -> {field}")
            return None
    except Exception as e:
        print(f"Error retrieving data from Redis: {e}")
        return None
    
async def getall_history_redis(hash_name):
    try:
        # HGETALL 명령어를 사용하여 데이터 가져오기
        value = redis_client.hgetall(hash_name)
        
        if value:
            # 값이 JSON 문자열이면 파이썬 객체로 변환
            decoded_value = {k.decode('utf-8'): json.loads(v.decode('utf-8')) for k, v in value.items()}
            return decoded_value
        else:
            print(f"No data found in Redis for {hash_name}")
            return None
    except Exception as e:
        print(f"Error retrieving data from Redis: {e}")
        return None
async def parsing(url):
    async def extract_text_from_pdf(pdf_content):
        try:
            pdf_reader = PdfReader(io.BytesIO(pdf_content))
            text = ''
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except:
            logging.error('PDF File Parsing Error')
            return 'PDF File Parsing Error'
    
    async def extract_text_from_docx(docx_content):
        try:
            doc = Document(io.BytesIO(docx_content))
            text_set = set()
            text_list = []
            # 문서의 단락을 처리
            for para in doc.paragraphs:
                if para.text not in text_set:
                    text_set.add(para.text)
                    text_list.append(para.text)
            # 문서의 표를 처리
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text not in text_set:
                            text_set.add(cell.text)
                            text_list.append(cell.text)
            return '\n'.join(text_list)
        except:
            logging.error('DOCX File Parsing Error')
            return ''
    
    async def extract_text_from_txt(txt_content):
        try:
            return txt_content.decode('utf-8')
        except:
            logging.error('TXT File Parsing Error')
            return 'TXT File Parsing Error'
    
    # async def extract_text_from_hwp(file_url):
    #     try:
    #         reader = HWPReader()
    #         documents = reader.load_data(file=file_url)
    #         return documents[0].text
    #     except:
    #         logging.error('HWP File Parsing Error')
    #         return 'HWP File Parsing Error'
        
    # async def extract_text_from_hwp(hwp_content):
    #     doc = HWPReader()
    #     encoded_text = ''
    #     for para in doc.load_data(hwp_content).values():
    #         encoded_text += para
    #     decoded_text = encoded_text.decode('utf-16')
    #     return decoded_text

    async def parse_s3_url(url):
        if url.startswith('s3://'):
            url = url[5:]  # "s3://" 부분 제거
            parts = url.split('/', 1) # 한 번만 분할
            bucket_name = parts[0]
            key = parts[1] if len(parts) > 1 else ''
        else:
            logging.error('Unsupported URL format')
            raise ValueError('Unsupported URL format')      
        return bucket_name, key
    
    bucket_name, key = await parse_s3_url(url)
    file_obj = s3_client.get_object(Bucket=bucket_name, Key=key)
    file_content = file_obj["Body"].read().strip()

    if key.endswith('.pdf'):
        logger.info('PDF Parsing')
        text = await extract_text_from_pdf(file_content)
    elif key.endswith('.docx'):
        logger.info('DOCX Parsing')
        text = await extract_text_from_docx(file_content)
    elif key.endswith('.txt'):
        logger.info('TXT Parsing')
        text = await extract_text_from_txt(file_content)
    # elif key.endswith('.hwp'):
    #     file_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".hwp"
    #     bucket = bucket_name
    #     key = key
    #     s3_client.download_file(bucket, key, file_name)
    #     text = await extract_text_from_hwp(file_name)
    #     os.remove(file_name)
    else:
        logging.error('Unsupported file type')
        raise ValueError('Unsupported file type')
    return text

@app.post("/question/coverletter", status_code=200)
async def coverletter(item: coverletterItem):
    start_time1 = datetime.now()
    coverletter_url = item.coverletter_url
    position = item.position
    itv_no = item.itv_no
    logging.info(f'자기소개서 API 호출 itv_no: {itv_no}')
  
    if not coverletter_url :
        return {'response': 'coverletter_urls are missing'}
    print(coverletter_url)
    logger.info(f'자기소개서 URL: {coverletter_url}, 직무: {position}')
    coverletter_text = await parsing(coverletter_url)
    end_time1 = datetime.now()
    elapsed_time = end_time1 - start_time1
    logger.info(f'자기소개서 Parsing SEC:{elapsed_time.total_seconds()}')
    
    prompt = f"자기소개서: {coverletter_text}\n직무: {position}"
    start_time = datetime.now()
    message = bedrock_client.messages.create(
        model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        max_tokens=4096,
        temperature=1,
        system= SYSTEM_COVERLETTER,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ]
            }
        ]
    )
    message_content = message.content[0].text
    # print(message_content)
    start_index = message_content.find('{')
    end_index = message_content.rfind('}') + 1
    response1_text = message_content[start_index:end_index] 
    # print("Response Text:", response1_text)

    end_time = datetime.now()
    elapsed_time = end_time - start_time
    logger.info(f'Bedrock 첫 질문 생성 SEC:{elapsed_time.total_seconds()}')
    input_tokens = message.usage.input_tokens
    output_tokens = message.usage.output_tokens
    cost = round((input_tokens * 0.000003 + output_tokens * 0.000015) * 1381, 3)
    logger.info(f'Bedrock cost:{cost}')

    try:
        response = json.loads(response1_text).get("question")
        response_intent = json.loads(response1_text).get("intent")
        response_type = json.loads(response1_text).get("question_type")
        await store_history_redis(itv_no,"coverletter",prompt)
        await store_history_redis(itv_no,"question-1",response)
        await store_history_redis(itv_no,"question_type",response_type)
        
    except json.JSONDecodeError as e:
        logging.error('JSONDecodeError')
        print("JSONDecodeError:", e)
        response = None
    if response_intent:
        if response_intent=="relevant_coverletter":
            if response:
                end_time = datetime.now()
                elapsed_time = end_time - start_time
                coverletter = await get_history_redis(itv_no,"coverletter")
                initial_question = await get_history_redis(itv_no,"question-1")
                question_type = await get_history_redis(itv_no,"question_type")
                print("Complete history from Redis:")
                print(coverletter)
                print(initial_question)
                print(question_type)
                logger.info(f'질문 생성 후 Redis 업데이트 SEC:{elapsed_time.total_seconds()}')
                logger.info(f'첫 질문: {initial_question}')
                return {'response': response, 'status':200}
            else:
                logger.error('자기소개서 json parsing 실패')
                return{
                        'response': 'LLM 질문 생성 오류',
                        'status':401
                      }
        elif response_intent=="lack_of_relevance":
            logger.error('자기소개서가 직무와 무관한 내용입니다.')
            return{
                    'response': '자기소개서가 직무와 무관한 내용입니다.',
                    'status':410
                  }
        elif response_intent=="negative":
            logger.error('자기소개서가 부정적인 내용만 포함되어있습니다.')
            return{
                    'response': '자기소개서가 부정적인 내용만 포함되어있습니다.',
                    'status':420
                  }
        elif response_intent=="lack_of_content":
            logger.error('자기소개서 내용이 매우 부족합니다.')
            return{
                    'response': '자기소개서 내용이 매우 부족합니다.',
                    'status':430
                  }
        elif response_intent=="others":
            logger.error('해당 내용은 자기소개서가 아닙니다.')
            return{
                    'response': '해당 내용은 자기소개서가 아닙니다.',
                    'status':440
                  }
    else:
        logger.error('자기소개서를 판별할 수 없습니다.')
        return{
                'response': '자기소개서를 판별할 수 없습니다.',
                'status':450
              }

@app.post("/question/chat", status_code=200)
async def chat(item: chatItem):
    answer_url = item.answer_url
    itv_no = item.itv_no
    question_number = item.question_number 
    logger.info(f'질문 생성 API 호출 itv_no: {itv_no}')
    
    answer_text = await parsing(answer_url)
    logger.info('STT File Parsing 완료')

    # 질문과 답변 저장을 위한 리스트 초기화
    questions = []
    answers = []
    await store_history_redis(itv_no,f"answer-{question_number-1}",answer_text)
    logger.info('Redis 저장 완료')
    print(answer_text)
    # 반복문을 사용하여 질문과 답변 생성
    cover_letter = await get_history_redis(itv_no, "coverletter")
    question_type = await get_history_redis(itv_no, "question_type")
    print(question_type)

    if question_type == "experience":
        system_chat = SYSTEM_EXPERIENCE_CHAT
    elif question_type == "basic":
        system_chat = SYSTEM_BASIC_CHAT
    elif question_type == "solving":
        system_chat = SYSTEM_SOLVING_CHAT
    elif question_type == "personality":
        system_chat = SYSTEM_PERSONALITY_CHAT
    else: system_chat = SYSTEM_CHAT
    
    for i in range(1, question_number):
        question = await get_history_redis(itv_no, f"question-{i}")
        answer = await get_history_redis(itv_no, f"answer-{i}")
        questions.append(question)
        answers.append(answer)

        prompt = f"대답: {answer_text}"
    logger.info('이전 질문 및 답변 Redis에서 GET 완료')
    
    ## 꼬리 질문 생성
    start_time = datetime.now()
    if question_number ==2:
        response2 = bedrock_client.messages.create(
        model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        max_tokens=4096,
        temperature=1,
        system= SYSTEM_CHAT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": cover_letter,
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[0],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ]
            }
        ]
    )
        print(response2)
        message_content = response2.content[0].text
        start_index = message_content.find('{')
        end_index = message_content.rfind('}') + 1
        response2_text = message_content[start_index:end_index]
        
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        logger.info(f'Bedrock 질문 생성 SEC:{elapsed_time.total_seconds()}')
        input_tokens = response2.usage.input_tokens
        output_tokens = response2.usage.output_tokens
        cost = round((input_tokens * 0.000003 + output_tokens * 0.000015) * 1381, 3)
        logger.info(f'Bedrock cost:{cost}')
        # print("Response Text:", response2_text)
        try:
            response = json.loads(response2_text).get("question")
            # print("Response:", response)

        except json.JSONDecodeError as e:
            print("JSONDecodeError:", e)
            response = None
        
        await store_history_redis(itv_no,f"question-{question_number}",response)
        print("Complete history from Redis:")
        print(response)

        if response:
            # tts, question = self.extract_question(response)
            logger.info(f'질문: {response}')
            return {'response': response}
        else:
            logger.error('질문 생성 실패')
            return {'response': message_content}
        
    elif question_number == 3:
        response3 = bedrock_client.messages.create(
        model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        max_tokens=4096,
        temperature=1,
        system= SYSTEM_CHAT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": cover_letter,
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[0],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[0],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[1],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ]
            }
        ]
    )
        print(response3)
        message_content = response3.content[0].text
        start_index = message_content.find('{')
        end_index = message_content.rfind('}') + 1
        response3_text = message_content[start_index:end_index]
        
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        logger.info(f'Bedrock 질문 생성 SEC:{elapsed_time.total_seconds()}')
        
        try:
            response = json.loads(response3_text).get("question")
            # print("Response:", response)

        except json.JSONDecodeError as e:
            print("JSONDecodeError:", e)
            response = None
        await store_history_redis(itv_no,f"question-{question_number}",response)
        print("Complete history from Redis:")
        print(response)

        if response:
            # tts, question = self.extract_question(response)
            logger.info(f'질문: {response}')
            return {'response': response}
        else:
            logger.error('질문 생성 실패')
            return {'response': message_content}

    elif question_number == 4:
        response4 = bedrock_client.messages.create(
        model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        max_tokens=4096,
        temperature=1,
        system= SYSTEM_CHAT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": cover_letter,
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[0],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[0],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[1],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[1],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[2],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ]
            }
        ]
    )
        print(response4)
        message_content = response4.content[0].text
        start_index = message_content.find('{')
        end_index = message_content.rfind('}') + 1
        response4_text = message_content[start_index:end_index]

        end_time = datetime.now()
        elapsed_time = end_time - start_time
        logger.info(f'Bedrock 질문 생성 SEC:{elapsed_time.total_seconds()}')
        input_tokens = response4.usage.input_tokens
        output_tokens = response4.usage.output_tokens
        cost = round((input_tokens * 0.000003 + output_tokens * 0.000015) * 1381, 3)
        logger.info(f'Bedrock cost :{cost}')
        
        try:
            response = json.loads(response4_text).get("question")
            # print("Response:", response)

        except json.JSONDecodeError as e:
            print("JSONDecodeError:", e)
            response = None
        await store_history_redis(itv_no,f"question-{question_number}",response)
        print("Complete history from Redis:")
        print(response)

        if response:
            # tts, question = self.extract_question(response)
            logger.info(f'질문: {response}')
            return {'response': response}
        else:
            logger.error('질문 생성 실패')
            return {'response': message_content}
        
    elif question_number == 5:
        response5 = bedrock_client.messages.create(
        model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        max_tokens=4096,
        temperature=1,
        system= SYSTEM_CHAT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": cover_letter,
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[0],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[0],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[1],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[1],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[2],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[2],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[3],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ]
            }
        ]
    )
        print(response5)
        message_content = response5.content[0].text
        start_index = message_content.find('{')
        end_index = message_content.rfind('}') + 1
        response5_text = message_content[start_index:end_index]
        
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        logger.info(f'Bedrock 질문 생성 SEC:{elapsed_time.total_seconds()}')
        input_tokens = response5.usage.input_tokens
        output_tokens = response5.usage.output_tokens
        cost = round((input_tokens * 0.000003 + output_tokens * 0.000015) * 1381, 3)
        logger.info(f'Bedrock cost :{cost}')
        
        try:
            response = json.loads(response5_text).get("question")
            # print("Response:", response)

        except json.JSONDecodeError as e:
            print("JSONDecodeError:", e)
            response = None
        await store_history_redis(itv_no,f"question-{question_number}",response)
        print("Complete history from Redis:")
        print(response)

        if response:
            # tts, question = self.extract_question(response)
            logger.info(f'질문: {response}')
            return {'response': response}
        else:
            logger.error('질문 생성 실패')
            return {'response': message_content}
    elif question_number == 6:
        response6 = bedrock_client.messages.create(
        model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        max_tokens=4096,
        temperature=1,
        top_k=500,
        top_p= 1,
        system= SYSTEM_CHAT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": cover_letter,
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[0],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[0],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[1],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[1],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[2],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[2],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[3],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[3],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[4],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ]
            }
        ]
    )
        print(response6)
        message_content = response6.content[0].text
        start_index = message_content.find('{')
        end_index = message_content.rfind('}') + 1
        response6_text = message_content[start_index:end_index]
        
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        logger.info(f'Bedrock 질문 생성 SEC:{elapsed_time.total_seconds()}')
        input_tokens = response6.usage.input_tokens
        output_tokens = response6.usage.output_tokens
        cost = round((input_tokens * 0.000003 + output_tokens * 0.000015) * 1381, 3)
        logger.info(f'Bedrock cost :{cost}')
        try:
            response = json.loads(response6_text).get("question")
            # print("Response:", response)

        except json.JSONDecodeError as e:
            print("JSONDecodeError:", e)
            response = None
        await store_history_redis(itv_no,f"question-{question_number}",response)
        print("Complete history from Redis:")
        print(response)

        if response:
            # tts, question = self.extract_question(response)
            logger.info(f'질문: {response}')
            return {'response': response}
        else:
            logger.error('질문 생성 실패')
            return {'response': message_content}
            
    elif question_number == 7:
        response7 = bedrock_client.messages.create(
        model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        max_tokens=4096,
        temperature=1,
        system= SYSTEM_CHAT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": cover_letter,
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[0],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[0],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[1],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[1],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[2],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[2],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[3],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[3],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[4],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[4],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[5],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ]
            }
        ]
    )
        print(response7)
        message_content = response7.content[0].text
        start_index = message_content.find('{')
        end_index = message_content.rfind('}') + 1
        response7_text = message_content[start_index:end_index]
        
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        logger.info(f'Bedrock 질문 생성 SEC:{elapsed_time.total_seconds()}')
        input_tokens = response7.usage.input_tokens
        output_tokens = response7.usage.output_tokens
        cost = round((input_tokens * 0.000003 + output_tokens * 0.000015) * 1381, 3)
        logger.info(f'Bedrock cost:{cost}')
        try:
            response = json.loads(response7_text).get("question")
            # print("Response:", response)

        except json.JSONDecodeError as e:
            print("JSONDecodeError:", e)
            response = None
        await store_history_redis(itv_no,f"question-{question_number}",response)
        print("Complete history from Redis:")
        print(response)

        if response:
            # tts, question = self.extract_question(response)
            logger.info(f'질문: {response}')
            return {'response': response}
        else:
            logger.error('질문 생성 실패')
            return {'response': message_content}
            
    elif question_number == 8:
        response8 = bedrock_client.messages.create(
        model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        max_tokens=4096,
        temperature=1,
        system= SYSTEM_CHAT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": cover_letter,
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[0],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[0],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[1],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[1],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[2],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[2],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[3],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[3],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[4],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[4],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[5],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[5],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[6],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ]
            }
        ]
    )
        print(response8)
        message_content = response8.content[0].text
        start_index = message_content.find('{')
        end_index = message_content.rfind('}') + 1
        response8_text = message_content[start_index:end_index]
        
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        logger.info(f'Bedrock 질문 생성 SEC:{elapsed_time.total_seconds()}')
        input_tokens = response8.usage.input_tokens
        output_tokens = response8.usage.output_tokens
        cost = round((input_tokens * 0.000003 + output_tokens * 0.000015) * 1381, 3)
        logger.info(f'Bedrock cost:{cost}')
        try:
            response = json.loads(response8_text).get("question")
            # print("Response:", response)

        except json.JSONDecodeError as e:
            print("JSONDecodeError:", e)
            response = None
        await store_history_redis(itv_no,f"question-{question_number}",response)
        print("Complete history from Redis:")
        print(response)

        if response:
            # tts, question = self.extract_question(response)
            logger.info(f'질문: {response}')
            return {'response': response}
        else:
            logger.error('질문 생성 실패')
            return {'response': message_content}
    elif question_number == 9:
        response9 = bedrock_client.messages.create(
        model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        max_tokens=4096,
        temperature=1,
        system= SYSTEM_CHAT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": cover_letter,
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[0],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[0],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[1],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[1],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[2],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[2],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[3],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[3],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[4],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[4],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[5],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[5],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[6],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[6],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[7],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ]
            }
        ]
    )
        message_content = response9.content[0].text
        start_index = message_content.find('{')
        end_index = message_content.rfind('}') + 1
        response9_text = message_content[start_index:end_index]
        
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        logger.info(f'Bedrock 질문 생성 SEC:{elapsed_time.total_seconds()}')
        input_tokens = response9.usage.input_tokens
        output_tokens = response9.usage.output_tokens
        cost = round((input_tokens * 0.000003 + output_tokens * 0.000015) * 1381, 3)
        logger.info(f'Bedrock cost:{cost}')
        try:
            response = json.loads(response9_text).get("question")
            # print("Response:", response)

        except json.JSONDecodeError as e:
            print("JSONDecodeError:", e)
            response = None
        await store_history_redis(itv_no,f"question-{question_number}",response)
        print("Complete history from Redis:")
        print(response)

        if response:
            # tts, question = self.extract_question(response)
            logger.info(f'질문: {response}')
            return {'response': response}
        else:
            logger.error('질문 생성 실패')
            return {'response': message_content}
    elif question_number == 10:
        response10 = bedrock_client.messages.create(
        model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        max_tokens=4096,
        temperature=1,
        system= SYSTEM_CHAT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": cover_letter,
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[0],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[0],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[1],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[1],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[2],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[2],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[3],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[3],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[4],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[4],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[5],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[5],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[6],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[6],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[7],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": answers[7],
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": questions[8],
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ]
            }
        ]
    )
        print(response10)
        message_content = response10.content[0].text
        start_index = message_content.find('{')
        end_index = message_content.rfind('}') + 1
        response10_text = message_content[start_index:end_index]
        
        end_time = datetime.now()
        elapsed_time = end_time - start_time
        logger.info(f'Bedrock 질문 생성 SEC:{elapsed_time.total_seconds()}')
        input_tokens = response10.usage.input_tokens
        output_tokens = response10.usage.output_tokens
        cost = round((input_tokens * 0.000003 + output_tokens * 0.000015) * 1381, 3)
        logger.info(f'Bedrock cost:{cost}')
        response10_text = response10.content[0].text
        try:
            response = json.loads(response10_text).get("question")
            # print("Response:", response)

        except json.JSONDecodeError as e:
            print("JSONDecodeError:", e)
            response = None
        await store_history_redis(itv_no,f"question-{question_number}",response)
        print("Complete history from Redis:")
        print(response)

        if response:
            # tts, question = self.extract_question(response)
            logger.info(f'질문: {response}')
            return {'response': response}
        else:
            logger.error('질문 생성 실패')
            return {'response': message_content}
        
@app.post("/question/report", status_code=200)
async def report(item: reportItem):
    itv_no = item.itv_no
    question_number = int(item.question_number)
    
    logger.info( f'Report API 호출 itv_no: {itv_no}')
    # combined_history =  await getall_history_redis(itv_no)
    print(itv_no)
    print(question_number)
    # prompt = f"대답: {combined_history}"
    # 질문과 답변 저장을 위한 리스트 초기화
    questions = []
    answers = []
    question_answer_pairs = []

    # report 부분에 coverletter 사용 여부 확인
    cover_letter = await get_history_redis(itv_no, "coverletter")
    logger.info('Redis에서 History GET 완료')
    
    for i in range(1, question_number + 1):
        question = await get_history_redis(itv_no, f"question-{i}")
        answer = await get_history_redis(itv_no, f"answer-{i}")
        questions.append(question)
        answers.append(answer)
        question_answer_pairs.append((question, answer))
    print("question_answer_pairs : ", question_answer_pairs)

    message_text = ""
    for question, answer in question_answer_pairs:
        message_text += f"Question: {question}, Answer: {answer}\n"
    print("message_text : ",message_text)

    ## 꼬리 질문 생성
    start_time = datetime.now()
    message = bedrock_client.messages.create(
        model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        max_tokens=10000,
        temperature=1,
        system= SYSTEM_REPORT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": message_text,
                    }
                ]
            }
        ]
    )
    print(message)
    message_content = message.content[0].text
    start_index = message_content.find('{')
    end_index = message_content.rfind('}') + 1
    response_text = message_content[start_index:end_index]
    
    end_time = datetime.now()
    elapsed_time = end_time - start_time
    logger.info(f'Bedrock Report 생성 SEC:{elapsed_time.total_seconds()}')
    input_tokens = message.usage.input_tokens
    output_tokens = message.usage.output_tokens
    cost = round((input_tokens * 0.000003 + output_tokens * 0.000015) * 1381, 3)
    logger.info(f'Bedrock cost:{cost}')

    try:
        relevant_experience = json.loads(response_text).get("relevant_experience")
        problem_solving = json.loads(response_text).get("problem_solving")
        communication_skills = json.loads(response_text).get("communication_skills")
        initiative = json.loads(response_text).get("initiative")
        situation = json.loads(response_text).get("situation")
        task = json.loads(response_text).get("task")
        action = json.loads(response_text).get("action")
        result = json.loads(response_text).get("result")
        overall_score = json.loads(response_text).get("overall_score")
        encouragement = json.loads(response_text).get("encouragement")
        # print(relevant_experience)
        
        # print("Response:", response)

    except json.JSONDecodeError as e:
        logger.error('JSONDecodeError')
        print("JSONDecodeError:", e)
        response = None
        # noanswer = str(json.loads(response_text))

    if response_text:
        # tts, question = self.extract_question(response)
        return {
                'relevant_experience': relevant_experience,
                'problem_solving': problem_solving,
                'communication_skills': communication_skills,
                'initiative': initiative,
                'situation': situation,
                'task': task,
                'action': action,
                'result': result,
                'overall_score': overall_score,
                'encouragement': encouragement
                }
    else:
        return {'response': message_content}

FastAPIInstrumentor.instrument_app(app)