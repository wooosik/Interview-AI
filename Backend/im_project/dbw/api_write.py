from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Optional
from pymongo import MongoClient
from pydantic import BaseModel
from datetime import datetime
import os, uuid, re, logging, json
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

# 테스트 방법(외부)
# 192.168.0.66:8001/docs
# uvicorn api_write:app --host 0.0.0.0 --port 8001 --reload

# get : 조회 / 파라미터가 url에 유출됨(body에 못 담음)
# post : 업데이트, 생성 / 파라미터가 url에 유출이 안됨(body에 담아서 보내니까)

app = FastAPI()

# .env파일 읽기
load_dotenv()

# COSRS옵션 부여
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 어느곳에서 접근을 허용할 것이냐
    allow_credentials=True,
    allow_methods=["*"], # 어떤 메서드에 대해서 허용할 것이냐("GET", "POST")
    allow_headers=["*"], 
)

# MongoDB 연결 설정(쓰기속도 특화)
if os.getenv("env") == "k8s":
    connection_string = os.getenv("DB_WRITE_K8S_URI")
else:
    connection_string = os.getenv("DB_WRITE_LOC_URI")
client = MongoClient(connection_string)
db = client["im"]
collection = db["InterviewMaster"]

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

        # 이메일을 _id로 사용하여 새 사용자 데이터 생성
        new_user = {
            "_id": user_id,
            "user_info": {
                "user_nm": user_nm,
                "user_nicknm": user_nicknm,
                "user_gender": user_gender,
                "user_birthday": user_birthday,
                "user_tel": user_tel,
                # 유저의 고유한 값을 생성하기 위해서 uuid4사용(그 중 16진수 hex값 사용)
                "user_uuid": uuid.uuid4().hex
            },
            "user_history": {
                "user_itv_cnt": 0
            },
            "itv_info": {}
        }
        
        # MongoDB에 새 사용자 데이터 삽입
        result = collection.insert_one(new_user)
        
        if result.inserted_id:
            logger.info('SIGN UP')
            return {"message": "User created successfully", "user_id": result.inserted_id}
        else:
            logger.error('Failed SIGN UP')
            raise HTTPException(status_code=400, detail="User creation failed")

    except Exception as e:
        print("Exception occurred:", str(e))
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
        # user_id에 해당하는 값 가져오기
        user = collection.find_one({"_id": user_id})

        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        print("User data:", user)
        
        # 업데이트할 필드들
        update_fields = {}

        if user_nm is not None and user_nm != user.get("user_info", {}).get("user_nm"):
            update_fields["user_info.user_nm"] = user_nm    
        if user_nicknm is not None and user_nicknm != user.get("user_info", {}).get("user_nicknm"):
            update_fields["user_info.user_nicknm"] = user_nicknm
        if user_gender is not None and user_gender != user.get("user_info", {}).get("user_gender"):
            update_fields["user_info.user_gender"] = user_gender
        if user_birthday is not None and user_birthday != user.get("user_info", {}).get("user_birthday"):
            update_fields["user_info.user_birthday"] = user_birthday
        if user_tel is not None and user_tel != user.get("user_info", {}).get("user_tel"):
            update_fields["user_info.user_tel"] = user_tel

        # 업데이트할 필드가 있는 경우에만 업데이트 수행
        if update_fields:
            result = collection.update_one({"_id": user_id}, {"$set": update_fields})
            if result.modified_count == 0:
                raise HTTPException(status_code=400, detail="Update failed")
        logger.info('회원정보 수정')
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
    itv_text_url: str
    itv_cate: str
    itv_job: str

@app.post("/dbw/new_itv")
async def new_itv(item: ItemItv):
    user_id = item.user_id
    itv_text_url = item.itv_text_url
    itv_cate = item.itv_cate
    itv_job = item.itv_job
    
    try:
        # user_id에 해당하는 값 가져오기
        user = collection.find_one({"_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # 면접번호생성을 위한 데이터 조회
        # 오늘 날짜 / email에서 .뒤부분 잘라내기 / user_history에서 면접번호 가져오기
        today_date6 = datetime.today().strftime('%y%m%d')
        today_date8 = datetime.today().strftime('%Y-%m-%d')
        user_id = user.get("_id",{})
        # user_short_id = user.get("_id",{}).split('.')[0]
        user_history = user.get("user_history", {})
        user_itv_cnt = user_history.get("user_itv_cnt")
        print(f"Current user_id: {user_id}")
        print(f"Current user_itv_cnt: {user_itv_cnt}")
        
        # user_itv_cnt가 None이거나 0이거나 문자열로 된 경우 처리
        if user_itv_cnt is None or user_itv_cnt == 0:
            user_itv_cnt = 1
        else:
            # 문자열에서 정수 추출
            if isinstance(user_itv_cnt, str):
                match = re.search(r'\d+$', user_itv_cnt)
                if match:
                    user_itv_cnt = int(match.group())
                else:
                    user_itv_cnt = 0
            user_itv_cnt += 1
        print(f"New user_itv_cnt: {user_itv_cnt}")
        
        # 면접번호, 면접제목 생성!
        # new_itv_no = f"{user_short_id}_{today_date6}_{str(user_itv_cnt).zfill(3)}"
        new_itv_no = f"{user.get("user_info", {}).get("user_uuid")}_{today_date6}_{str(user_itv_cnt).zfill(3)}"
        new_itv_sub = f"{user.get("user_info", {}).get("user_nicknm")}_{itv_cate}_모의면접_{str(user_itv_cnt).zfill(3)}"
        print(f"New itv_info key: {new_itv_no}")
        print(f"New itv_info sub: {new_itv_sub}")

        # 면접 데이터 생성
        new_itv_info = {
            new_itv_no: {
                "itv_sub": new_itv_sub,
                "itv_text_url": itv_text_url,
                "itv_fb_url": "",
                "itv_cate": itv_cate,
                "itv_job": itv_job,
                "itv_qs_cnt": "0",
                "itv_date": today_date8,
                "qs_info": {}
            }
        }

        # update문 생성
        update_query = {
            "$set": {
                "user_history.user_itv_cnt": user_itv_cnt,
                f"itv_info.{new_itv_no}": new_itv_info[new_itv_no]
            }
        }
        print("Update query:", update_query)
        
        # update실행!
        result = collection.update_one({"_id": user_id}, update_query)

        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Update failed")
        logger.info('면접 시작')
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
    logger.info(f'ITV_NO:{item.itv_no} QnA:{item.qs_no} 종료')
    user_id = item.user_id
    itv_no = item.itv_no
    # qs_no 1 ~ 9 : 문자열 01 ~ 09처리
    # qs_no 10 ~  : 문자열 처리
    if 1 <= item.qs_no <= 9:
        qs_no = f"0{item.qs_no}"
    elif 10 <= item.qs_no :
        qs_no = f"{item.qs_no}"
    qs_content = item.qs_content
    qs_video_url = item.qs_video_url
    qs_audio_url = item.qs_audio_url
    qs_text_url = item.qs_text_url

    try:
        # user_id에 해당하는 값 가져오기
        user = collection.find_one({"_id": user_id})
        if not user:
            raise HTTPException(status_code=400, detail="User not found")

        # 질문번호에 대한 데이터 업데이트
        new_qs_info = {
            "qs_content": qs_content,
            "qs_video_url": qs_video_url,
            "qs_audio_url": qs_audio_url,
            "qs_text_url": qs_text_url
        }

        # update문 생성
        update_query = {
            "$set": {
                f"itv_info.{itv_no}.qs_info.{qs_no}": new_qs_info
            }
        }
        print("Update query:", update_query)
        
        # update실행!
        result = collection.update_one({"_id": user_id}, update_query)
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Update failed")

        return {"status": "success", "updated_fields": new_qs_info}

    except Exception as e:
        print("Exception occurred:", str(e))
        raise HTTPException(status_code=500, detail=str(e))



# 면접종료시 결과 반영
# patch
# 필수 입력값 : user_id, 면접번호, 질문개수, 피드백 url정보

# T1@T1.com
# T1@T1_240614_001
# n개
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
        # itv_fb_url을 JSON 형식으로 파싱
        itv_fb_url = json.loads(item.itv_fb_url)

        # user_id에 해당하는 값 가져오기
        user = collection.find_one({"_id": user_id})
        if not user:
            raise HTTPException(status_code=400, detail="User not found")

        # update문 생성
        update_query = {
            "$set": {
                f"itv_info.{itv_no}.itv_qs_cnt": itv_qs_cnt,
                f"itv_info.{itv_no}.itv_fb_url": itv_fb_url
            }
        }
        print("Update query:", update_query)
        
        # update실행!
        result = collection.update_one({"_id": user_id}, update_query)
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Update failed")

        return {"status": "success", "updated_fields": update_query}

    except Exception as e:
        print("Exception occurred:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

FastAPIInstrumentor.instrument_app(app)
