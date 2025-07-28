# Backend Guide
# 워크북 경로
# 노션 → 작업공간/워크북 → Backend(FastAPI)
해당 파일을 내려받고 im, im_project가 있는 디렉터리로 이동!
# 가상환경 진입(여기서 작업을 했음)
source im/Scripts/activate

# (참고)가상환경 나오기
deactivate

# im_project 디렉터리내 api_read.py, api_write.py가 있는 디렉터리로 이동!
# app실행 명령어
read : uvicorn api_read:app --reload --port 8000 --reload

write : uvicorn api_write:app --reload --port 8001 --reload

# app접속방법(URL주의!!!!)
read : http://127.0.0.1:8000/docs

write : http://127.0.0.1:8001/docs
