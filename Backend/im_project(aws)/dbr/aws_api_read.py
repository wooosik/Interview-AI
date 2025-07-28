from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from typing import Optional
from pymongo import MongoClient
from pydantic import BaseModel
import os, uuid, requests, logging
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
# uvicorn aws_api_read:app --host 0.0.0.0 --port 8003 --reload

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



##########################
########## test ##########
##########################
# 전체 데이터 조회(테스트용)
@app.get("/dbr/get_data")
async def get_data():
    data = tb_itm.scan().get('Items', [])
    return {"data": data}



# UUID값 조회(테스트용)
@app.get("/dbr/get_uuid")
async def get_uuid():
    unique_id = uuid.uuid4()
    print("UUID 기본값 : ", unique_id, "\nUUID hex값 : ", unique_id.hex)
    return {
        "UUID 기본값": unique_id,
        "UUID hex값": unique_id.hex
    }



# 전화번호 복호화 함수
def decrypt_user_tel(encrypted_tel: str) -> str:
    response = kms.decrypt(
        CiphertextBlob=base64.b64decode(encrypted_tel)
    )
    return response['Plaintext'].decode('utf-8')

# 전화번호 복호화 값 조회
@app.get("/dbr/get_tel/{user_id}")
async def get_tel(user_id: str):
    # info 조회
    itm_user_info = tb_itm.get_item(
        Key={
            'PK': f'u#{user_id}',
            'SK': 'info'
        }
    )
    
    # 전화번호 복호화
    encrypted_user_tel = itm_user_info['Item'].get('user_tel', '')
    decrypted_user_tel = decrypt_user_tel(encrypted_user_tel) if encrypted_user_tel else ''
    
    data = {
        "user_id": user_id,
        "user_info": {
            "user_nm": itm_user_info['Item'].get('user_nm', ''),
            "user_tel": decrypted_user_tel
        }
    }
    return data
    


###########################
########## OAuth ##########
###########################
# kakao Login
# 호출시 auth로 redirect해서 인증 진행
@app.get("/dbr/act/kakao")
def kakao():
    kakao_client_key = os.getenv("KAKAO_CLIENT_KEY")
    if os.getenv("env") == "eks":
        kakao_url = os.getenv("KAKAO_REDIRECT_EKS_URI")
    elif os.getenv("env") == "k8s":
        kakao_url = os.getenv("KAKAO_REDIRECT_K8S_URI")
    else:
        kakao_url = os.getenv("KAKAO_REDIRECT_LOC_URI")
    kakao_scope = os.getenv("KAKAO_SCOPE")
    
    url = f"https://kauth.kakao.com/oauth/authorize?client_id={kakao_client_key}&redirect_uri={kakao_url}&response_type=code&scope={kakao_scope}"
    
    response = RedirectResponse(url)
    return response



# kakao 인증
# {
#   "code": {
#     "access_token": "access_token값",
#     "token_type": "bearer",
#     "refresh_token": "refresh_token값",
#     "id_token": "id_token값",
#     "expires_in": 21599,
#     "scope": "account_email openid profile_nickname",
#     "refresh_token_expires_in": 5183999
#   }
# }
@app.get("/dbr/act/kakao/auth")
async def kakaoAuth(response: Response, code: Optional[str]="NONE"):
    kakao_client_key = os.getenv("KAKAO_CLIENT_KEY")
    kakao_secret_key = os.getenv("KAKAO_SECRET_KEY")
    if os.getenv("env") == "eks":
        kakao_url = os.getenv("KAKAO_REDIRECT_EKS_URI")
        db_check_url = os.getenv("DB_CHECK_EKS_URI")
    elif os.getenv("env") == "k8s":
        kakao_url = os.getenv("KAKAO_REDIRECT_K8S_URI")
        db_check_url = os.getenv("DB_CHECK_K8S_URI")
    else:
        kakao_url = os.getenv("KAKAO_REDIRECT_LOC_URI")
        db_check_url = os.getenv("DB_CHECK_LOC_URI")
    
    url = f'https://kauth.kakao.com/oauth/token?grant_type=authorization_code&client_id={kakao_client_key}&redirect_uri={kakao_url}&code={code}&client_secret={kakao_secret_key}'
    
    res = requests.post(url)
    result = res.json()
    
    print("*****/act/kakao/auth result*****\n", result, "\n********************************")
    access_token = result["access_token"]
    response.set_cookie(key="kakao", value=access_token)
    
    user_info_url = 'https://kapi.kakao.com/v2/user/me'
    # access_token을 이용해서 사용자 정보 받아오기
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    user_info_res = requests.get(user_info_url, headers=headers)
    user_info_result = user_info_res.json()
    print("*****user info result*****\n", user_info_result, "\n**************************")
    
    if 'kakao_account' in user_info_result and 'email' in user_info_result['kakao_account']:
        email = user_info_result['kakao_account']['email']
        
        # DB user체크 부분
        # info 조회
        itm_user_info = tb_itm.get_item(
            Key={
                'PK': f'u#{email}',
                'SK': 'info'
            }
        )
        
        # history 조회
        itm_user_history = tb_itm.get_item(
            Key={
                'PK': f'u#{email}',
                'SK': 'history'
            }
        )
        
        user_info = itm_user_info.get('Item', {})
        user_history = itm_user_history.get('Item', {})
        
        user = {
            "user_id": email,
            "user_info": {
                "user_uuid": user_info.get('user_uuid', ''),
                "user_nm": user_info.get('user_nm', ''),
                "user_nicknm": user_info.get('user_nicknm', ''),
                "user_gender": user_info.get('user_gender', ''),
                "user_birthday": user_info.get('user_birthday', ''),
                "user_tel": user_info.get('user_tel', '')
            },
            "user_history": {
                "user_itv_cnt": user_history.get('user_itv_cnt', 0)
            }
        }
        
        # user정보가 없을 경우에는 false값 넘겨줘서 신규가입 화면으로
        # user정보가 있을 경우에는 true값 넘겨줘서 마이페이지 확인 화면 or 메인페이지로
        if not user_info:
            print("*****user info DB result*****\n신규유저\n ", user, "\n*****************************")
            logger.info(f'카카오 회원가입: {email}, {access_token}')
            url = f"{db_check_url}/auth?email_id={email}&access_token={access_token}&message=new"
        else:
            print("*****user info DB result*****\n기존유저\n ", user, "\n*****************************")
            logger.info(f'카카오 로그인: {email}, {access_token}')
            url = f"{db_check_url}/auth?email_id={email}&access_token={access_token}&message=main"
        
        response = RedirectResponse(url)
        return response
    else:
        return {"error": "Email not available"}



# kakao 로그아웃
# http://192.168.0.66:8002/act/kakao/logout
# access_token받아야 로그아웃 처리 가능
class ItemToken(BaseModel):
    access_token: str

@app.post("/dbr/act/kakao/logout")
def kakaoLogout(item: ItemToken, response: Response):
    try:
        access_token = item.access_token
        
        url = "https://kapi.kakao.com/v1/user/unlink"
        headers = {"Authorization": f"Bearer {access_token}"}
        res = requests.post(url, headers=headers)
        result = res.json()
        
        print("*****Logout result*****\n", result, "\n***********************")
        logger.info(f'로그아웃: {access_token}')
        
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail="Failed to logout from Kakao")
        
        response.delete_cookie(key="kakao")
        return {"logout": "success"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# kakao 로그아웃(강제)
# http://192.168.0.66:8002/act/kakao/kill
# access_token받아야 로그아웃 처리 가능
@app.get("/dbr/act/kakao/kill/{token}")
def kakaokill(token: str, response: Response):
    try:
        # 액세스 토큰(강제 kill)
        access_token = token
        
        url = "https://kapi.kakao.com/v1/user/unlink"
        headers = {"Authorization": f"Bearer {access_token}"}
        res = requests.post(url, headers=headers)
        result = res.json()
        
        print("*****Logout result*****\n", result, "\n***********************")
        logger.info(f'로그아웃: {access_token}')
        
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail="Failed to logout from Kakao")
        
        response.delete_cookie(key="kakao")
        return {"logout": "success"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



###########################
########### DBR ###########
###########################
# 마이페이지(정보) 조회
# get
# 입력값 user_id
# 출력값 user_id, user_inf, user_history
@app.get("/dbr/get_user/{user_id}")
async def get_user(user_id: str):
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
    
    # 전화번호 복호화
    encrypted_user_tel = itm_user_info['Item'].get('user_tel', '')
    decrypted_user_tel = decrypt_user_tel(encrypted_user_tel) if encrypted_user_tel else ''
    
    data = {
        "user_id": user_id,
        "user_info": {
            "user_uuid": itm_user_info['Item'].get('user_uuid', ''),
            "user_nm": itm_user_info['Item'].get('user_nm', ''),
            "user_nicknm": itm_user_info['Item'].get('user_nicknm', ''),
            "user_gender": itm_user_info['Item'].get('user_gender', ''),
            "user_birthday": itm_user_info['Item'].get('user_birthday', ''),
            "user_tel": decrypted_user_tel
        },
        "user_history": {
            "user_itv_cnt": itm_user_history['Item'].get('user_itv_cnt', 0)
        }
    }
    return data



# 신규 면접 번호 생성
# get
# 입력값 user_id
# 출력값 user_itv_cnt
@app.get("/dbr/get_newitvcnt/{user_id}")
async def get_newitvcnt(user_id: str):
    # history 조회
    itm_user_history = tb_itm.get_item(
        Key={
            'PK': f'u#{user_id}',
            'SK': 'history'
        }
    )
    
    data = {
        "new_itv_cnt": itm_user_history['Item'].get('user_itv_cnt', 0)
    }
    return data



# 마이페이지(면접, 질문) 조회
# get
# 입력값 user_id
# 출력값 user_id, user_history, itv_info
@app.get("/dbr/get_itv/{user_id}")
async def get_itv(user_id: str):
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
    
    # itv 조회
    itm_itv_info = tb_itm.query(
            KeyConditionExpression=Key('PK').eq(f'u#{user_id}#itv_info')
    )
    itm_itv_info_list = {}
    
    for itv_item in itm_itv_info.get('Items', []):
        itv_no = itv_item['SK'].replace('i#', '')
        
        # qs 조회
        itm_qs_info = tb_itm.query(
            KeyConditionExpression=Key('PK').eq(itv_item['SK'] + '#qs_info')
        )
        itm_qs_info_list = {}
        
        for qs_item in itm_qs_info.get('Items', []):
            qs_no = qs_item['SK'].replace('q#', '')
            
            itm_qs_info_list[qs_no] = {
                "qs_content": qs_item.get('qs_content', ''),
                "qs_video_url": qs_item.get('qs_video_url', ''),
                "qs_audio_url": qs_item.get('qs_audio_url', ''),
                "qs_text_url": qs_item.get('qs_text_url', '')
            }
        
        itv_data = {
            "itv_sub": itv_item.get('itv_sub', ''),
            "itv_date": itv_item.get('itv_date', ''),
            "itv_cate": itv_item.get('itv_cate', ''),
            "itv_job": itv_item.get('itv_job', ''),
            "itv_text_url": itv_item.get('itv_text_url', ''),
            "itv_fb_url": itv_item.get('itv_fb_url', ''),
            "itv_qs_cnt": itv_item.get('itv_qs_cnt', ''),
            "qs_info": itm_qs_info_list
        }
        itm_itv_info_list[itv_no] = itv_data
    
    data = {
        "user_id": user_id,
        "user_history": {
            "user_itv_cnt": itm_user_history['Item'].get('user_itv_cnt', "0")
        },
        "itv_info": itm_itv_info_list
    }
    return data



# 면접 조회
# get
# 입력값 user_id, itv_no
# 출력값 user_id, user_history, itv_info
@app.get("/dbr/get_itv/{user_id}/{itv_no}")
async def get_itv_detail(user_id: str, itv_no: str):
    logger.info('REPORT 정보 조회')
    
    # info 조회
    itm_user_info = tb_itm.get_item(
        Key={
            'PK': f'u#{user_id}',
            'SK': 'info'
        }
    )
    
    # itv 조회
    itm_user_itv = tb_itm.get_item(
        Key={
            'PK': f'u#{user_id}#itv_info',
            'SK': f'i#{itv_no}'
        }
    )
    
    itv_item = itm_user_itv['Item']
    itv_no = itv_item['SK'].replace('i#', '')
    
    # qs 조회
    itm_qs_info = tb_itm.query(
        KeyConditionExpression=Key('PK').eq(itv_item['SK'] + '#qs_info')
    )
    itm_qs_info_list = {}
    
    for qs_item in itm_qs_info.get('Items', []):
        qs_no = qs_item['SK'].replace('q#', '')
        
        itm_qs_info_list[qs_no] = {
            "qs_content": qs_item.get('qs_content', ''),
            "qs_video_url": qs_item.get('qs_video_url', ''),
            "qs_audio_url": qs_item.get('qs_audio_url', ''),
            "qs_text_url": qs_item.get('qs_text_url', ''),
        }
    
    itv_data = {
        "itv_sub": itv_item.get('itv_sub', ''),
        "itv_date": itv_item.get('itv_date', ''),
        "itv_cate": itv_item.get('itv_cate', ''),
        "itv_job": itv_item.get('itv_job', ''),
        "itv_text_url": itv_item.get('itv_text_url', ''),
        "itv_fb_url": itv_item.get('itv_fb_url', ''),
        "itv_qs_cnt": itv_item.get('itv_qs_cnt', ''),
        "qs_info": itm_qs_info_list
    }
    
    data = {
        "user_id": user_id,
        "itv_info": {
            itv_no: itv_data
        }
    }
    return data

FastAPIInstrumentor.instrument_app(app)
