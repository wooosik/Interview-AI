from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Optional
from pymongo import MongoClient
from pydantic import BaseModel
from datetime import datetime
import os, uuid, re, logging
import boto3, base64
from boto3.dynamodb.conditions import Key
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

# 테스트 방법
# uvicorn aws_api_write:app --host 0.0.0.0 --port 8004 --reload

app = FastAPI()

# .env파일 읽기
load_dotenv()

# COSRS옵션 부여
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DynamoDB 연결 설정
dynamodb = boto3.resource(
    "dynamodb",
    # aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    # aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)
tb_itm=dynamodb.Table("ITM-PRD-DYN-TBL")

# KMS 연결 설정
kms = boto3.client(
    'kms',
    # aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    # aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)
kms_id=os.getenv("AWS_KMS_ID")

# LOG
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
otel_logging_init()



###########################
########### DBW ###########
###########################
# 신규 사용자 생성(curl로 입력 받아서 생성 되는 기준으로 작성)  
# post
# 입력값 user_id, emial, 성명, 별명, 성별, 생년월일, 연락처
class ItemUser(BaseModel):
    user_id: str
    name: str
    nickname: str
    gender: str
    birthday: str
    tel: str

@app.post("/dbw/create_user")
async def create_user(item: ItemUser):
    user_id = item.user_id
    user_nm = item.name
    user_nicknm = item.nickname
    user_gender = item.gender
    user_birthday = item.birthday
    user_tel = item.tel
    
    try:
        # 필수 필드 검증
        if not all([user_id, user_nm, user_nicknm, user_gender, user_birthday, user_tel]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # 전화번호 암호화
        encrypted_user_tel = base64.b64encode(
            kms.encrypt(KeyId=kms_id, Plaintext=user_tel.encode('utf-8'))['CiphertextBlob']
        ).decode('utf-8')
        
        new_user_info = {
            'PK': f'u#{user_id}',
            'SK': 'info',
            'user_uuid': uuid.uuid4().hex,
            'user_nm': user_nm,
            'user_nicknm': user_nicknm,
            'user_gender': user_gender,
            'user_birthday': user_birthday,
            'user_tel': encrypted_user_tel
        }
        
        new_user_history = {
            'PK': f'u#{user_id}',
            'SK': 'history',
            'user_itv_cnt': 0
        }
        
        tb_itm.put_item(Item=new_user_info)
        tb_itm.put_item(Item=new_user_history)
        
        logger.info(f'회원가입: {user_id}, {user_nm}')
        return {"message": "User added successfully", "user_id": user_id}
        
    except Exception as e:
        logger.error('Failed SIGN UP: %s', str(e))
        raise HTTPException(status_code=500, detail=str(e))



# 마이페이지 수정
# patch
# 필수 입력값 : user_id
# None 허용값 : 성명, 별명, 성별, 생년월일, 연락처

# T1@T1.com
# Faker
# 불사대마왕
# 남
# 1999-09-09
# 010-9999-9999
class ItemUser(BaseModel):
    user_id: str
    name: Optional[str] = None
    nickname: Optional[str] = None
    gender: Optional[str] = None
    birthday: Optional[str] = None
    tel: Optional[str] = None

@app.patch("/dbw/mod_user")
async def mod_user(item: ItemUser):
    user_id = item.user_id
    user_nm = item.name
    user_nicknm = item.nickname
    user_gender = item.gender
    user_birthday = item.birthday
    user_tel = item.tel
    
    try:
        # info 조회
        itm_user_info = tb_itm.get_item(
            Key={
                'PK': f'u#{user_id}',
                'SK': 'info'
            }
        )
        
        data = {
            "user_id": user_id,
            "user_info": {
                "user_uuid": itm_user_info['Item'].get('user_uuid', ''),
                "user_nm": itm_user_info['Item'].get('user_nm', ''),
                "user_nicknm": itm_user_info['Item'].get('user_nicknm', ''),
                "user_gender": itm_user_info['Item'].get('user_gender', ''),
                "user_birthday": itm_user_info['Item'].get('user_birthday', ''),
                "user_tel": itm_user_info['Item'].get('user_tel', '')
            }
        }
        
        if not data:
            raise HTTPException(status_code=404, detail="User not found")
        print("User data:", data)
        
        # 업데이트할 필드들
        update_expression = "SET "
        expression_attribute_values = {}
        expression_attribute_names = {}
        update_fields = {}

        if user_nm is not None and user_nm != data["user_info"].get("user_nm"):
            update_expression += "#user_nm = :user_nm, "
            expression_attribute_values[":user_nm"] = user_nm
            expression_attribute_names["#user_nm"] = "user_nm"
            update_fields["user_nm"] = user_nm
        
        if user_nicknm is not None and user_nicknm != data["user_info"].get("user_nicknm"):
            update_expression += "#user_nicknm = :user_nicknm, "
            expression_attribute_values[":user_nicknm"] = user_nicknm
            expression_attribute_names["#user_nicknm"] = "user_nicknm"
            update_fields["user_nicknm"] = user_nicknm
        
        if user_gender is not None and user_gender != data["user_info"].get("user_gender"):
            update_expression += "#user_gender = :user_gender, "
            expression_attribute_values[":user_gender"] = user_gender
            expression_attribute_names["#user_gender"] = "user_gender"
            update_fields["user_gender"] = user_gender
        
        if user_birthday is not None and user_birthday != data["user_info"].get("user_birthday"):
            update_expression += "#user_birthday = :user_birthday, "
            expression_attribute_values[":user_birthday"] = user_birthday
            expression_attribute_names["#user_birthday"] = "user_birthday"
            update_fields["user_birthday"] = user_birthday
        
        if user_tel is not None and user_tel != data["user_info"].get("user_tel"):
            encrypted_user_tel = base64.b64encode(
                kms.encrypt(KeyId=kms_id, Plaintext=user_tel.encode('utf-8'))['CiphertextBlob']
            ).decode('utf-8')
            update_expression += "#user_tel = :user_tel, "
            expression_attribute_values[":user_tel"] = encrypted_user_tel
            expression_attribute_names["#user_tel"] = "user_tel"
            update_fields["user_tel"] = encrypted_user_tel
        
        # 업데이트할 필드가 있는 경우에만 업데이트 수행
        if update_fields:
            update_expression = update_expression.rstrip(", ")
            
            result = tb_itm.update_item(
                Key={
                    'PK': f'u#{user_id}',
                    'SK': 'info'
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ExpressionAttributeNames=expression_attribute_names,
                ReturnValues="UPDATED_NEW"
            )
            print("Update result:", result)
            
            if result['ResponseMetadata']['HTTPStatusCode'] != 200:
                raise HTTPException(status_code=400, detail="Update failed")
        logger.info(f'회원정보 수정: {user_id}, {user_nm}')
        return {"status": "success", "updated_fields": update_fields}
        
    except Exception as e:
        print("Exception occurred:", str(e))
        raise HTTPException(status_code=500, detail=str(e))



# 면접 생성
# post
# 필수 입력값 : user_id, 자소서 url, 카테고리, 직무
# return값 : new_itv_no

# T1@T1.com
# http://url...
# 자소서
# 프로게이머
class ItemItv(BaseModel):
    user_id: str
    itv_cate: str
    itv_job: str
    itv_text_url: str

@app.post("/dbw/new_itv")
async def new_itv(item: ItemItv):
    user_id = item.user_id
    itv_cate = item.itv_cate
    itv_job = item.itv_job
    itv_text_url = item.itv_text_url
    
    try:
        # info 조회
        itm_user_info = tb_itm.get_item(
            Key={
                'PK': f'u#{user_id}',
                'SK': 'info'
            }
        )
        
        # history 조회
        itm_user_history = tb_itm.get_item(
            Key={
                'PK': f'u#{user_id}',
                'SK': 'history'
            }
        )
        
        # 면접번호생성을 위한 데이터 조회
        # uuid / 오늘 날짜 / user_history에서 면접번호 가져오기
        today_date6 = datetime.today().strftime('%y%m%d')
        today_date8 = datetime.today().strftime('%Y-%m-%d')
        user_uuid = itm_user_info['Item'].get("user_uuid")
        user_nicknm = itm_user_info['Item'].get("user_nicknm")
        user_itv_cnt = itm_user_history.get('Item', {}).get('user_itv_cnt', 0)
        print(f"Current user_id: {user_id}")
        print(f"Current user_itv_cnt: {user_itv_cnt}")
        
        # user_itv_cnt가 None이거나 0이거나 문자열로 된 경우 처리
        if isinstance(user_itv_cnt, str):
            match = re.search(r'\d+$', user_itv_cnt)
            if match:
                user_itv_cnt = int(match.group())
            else:
                user_itv_cnt = 0
        user_itv_cnt += 1
        print(f"New user_itv_cnt: {user_itv_cnt}")
        
        # 면접번호, 면접제목 생성!
        new_itv_no = f"{user_uuid}_{today_date6}_{str(user_itv_cnt).zfill(3)}"
        new_itv_sub = f"{user_nicknm}_{itv_cate}_면접_{str(user_itv_cnt).zfill(3)}"
        print(f"New itv_info key: {new_itv_no}")
        print(f"New itv_info sub: {new_itv_sub}")
        
        # 면접 데이터 생성
        new_itv_info = {
            "itv_sub": new_itv_sub,
            "itv_cate": itv_cate,
            "itv_job": itv_job,
            "itv_text_url": itv_text_url,
            "itv_date": today_date8,
            "itv_qs_cnt": "0"
        }
        
        # 면접 데이터 Upload
        tb_itm.put_item(
            Item={
                'PK': f'u#{user_id}#itv_info',
                'SK': f'i#{new_itv_no}',
                **new_itv_info
            }
        )
        print("Update query:", new_itv_info)
        
        # 인터뷰 카운트 업데이트
        tb_itm.update_item(
            Key={
                'PK': f'u#{user_id}',
                'SK': 'history'
            },
            UpdateExpression="SET user_itv_cnt = :user_itv_cnt",
            ExpressionAttributeValues={
                ":user_itv_cnt": user_itv_cnt
            }
        )
        logger.info(f'면접 시작 {user_id}')
        return {"message": "Update successful", "new_itv_no": new_itv_no}
        
    except Exception as e:
        print("Exception occurred:", str(e))
        raise HTTPException(status_code=500, detail=str(e))



# 질문 종료시 질문정보/결과 저장(n번 수행)
# post
# 필수 입력값 : user_id, 면접번호, 질문번호, 질문내용, 비디오, 오디오, 텍스트 url정보

# T1@T1.com
# T1@T1_240614_001
# 01 ~ n번
# 자신의 강점에 대해서 설명해보세요.
# s3://simulation-userdata/video/1718263662009test.mp4
# s3://simulation-userdata/audio/1718324990967.mp3
# s3://simulation-userdata/text/test.txt
class ItemQs(BaseModel):
    user_id: str
    itv_no: str
    qs_no: int
    qs_content: str
    qs_video_url: str
    qs_audio_url: str
    qs_text_url: str

@app.post("/dbw/new_qs")
async def new_qs(item: ItemQs):
    user_id = item.user_id
    itv_no = item.itv_no
    # qs_no 1~9는 01~09로 처리, 10부터는 그대로 문자열 처리
    qs_no = f"{item.qs_no:02}"
    qs_content = item.qs_content
    qs_video_url = item.qs_video_url
    qs_audio_url = item.qs_audio_url
    qs_text_url = item.qs_text_url
    
    try:
        # 질문번호에 대한 데이터 업데이트
        new_qs_info = {
            "qs_content": qs_content,
            "qs_video_url": qs_video_url,
            "qs_audio_url": qs_audio_url,
            "qs_text_url": qs_text_url
        }
        print("Update user_id :", user_id, "\nUpdate itv_no :", itv_no, "\nUpdate query :", new_qs_info)
        
        # 새로운 질문 정보 추가
        tb_itm.put_item(
            Item={
                'PK': f'i#{itv_no}#qs_info',
                'SK': f'q#{qs_no}',
                **new_qs_info
            }
        )
        return {"status": "success", "updated_fields": new_qs_info}
        
    except Exception as e:
        print("Exception occurred:", str(e))
        raise HTTPException(status_code=500, detail=str(e))



# 면접종료시 결과 반영
# patch
# 필수 입력값 : user_id, 면접번호, 질문개수, 피드백 url정보

# T1@T1.com
# T1@T1_240614_001
# n
# http://url...
class ItemFb(BaseModel):
    user_id: str
    itv_no: str
    itv_qs_cnt: int
    itv_fb_url: str

@app.patch("/dbw/update_fb")
async def update_fb(item: ItemFb):
    user_id = item.user_id
    itv_no = item.itv_no
    itv_qs_cnt = item.itv_qs_cnt
    itv_fb_url = item.itv_fb_url
    
    try:
        # 업데이트 실행
        result = tb_itm.update_item(
            Key={
                'PK': f'u#{user_id}#itv_info',
                'SK': f'i#{itv_no}'
            },
            UpdateExpression="SET itv_qs_cnt = :itv_qs_cnt, itv_fb_url = :itv_fb_url",
            ExpressionAttributeValues={
                ":itv_qs_cnt": itv_qs_cnt,
                ":itv_fb_url": itv_fb_url
            },
            ReturnValues="UPDATED_NEW"
        )
        print("Update user_id :", user_id, "\nUpdate data :", result)
        
        if result['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise HTTPException(status_code=400, detail="Update failed")
        
        return {"status": "success", "updated_fields": result["Attributes"]}
    
    except Exception as e:
        print("Exception occurred:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

FastAPIInstrumentor.instrument_app(app)
