# DB Guide
# 워크북 경로
# 노션 → 작업공간/워크북 → DB - MongoDB구축
yaml파일을 내려받고 실행시키기 전에 사전 확인!

master 1개, workernode 3개를 전제로 구성했습니다!

kubectl get no -A

NAME      STATUS   ROLES           AGE     VERSION

master    Ready    control-plane   7d14h   v1.29.0

worker1   Ready    <none>          7d13h   v1.29.0

worker2   Ready    <none>          7d13h   v1.29.0

worker3   Ready    <none>          7d13h   v1.29.0

kubectl get sc

NAME               PROVISIONER        RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION   AGE

openebs-device     openebs.io/local   Delete          WaitForFirstConsumer   false                  4d7h

openebs-hostpath   openebs.io/local   Delete          WaitForFirstConsumer   false                  4d7h

명령어로 storageclass 확인했을시 없을 경우에는 아래의 명령어로 설치!

kubectl apply -f https://openebs.github.io/charts/openebs-operator-lite.yaml

kubectl apply -f https://openebs.github.io/charts/openebs-lite-sc.yaml

# 네임스페이스 생성
kubectl create ns mongodb

# yaml파일 실행
# 네임스페이스 없으면 오류, yaml파일 내에 StatefulSet → template → spec → nodeAffinity안에 values의 node명이 k8s node랑 일치해야 합니다!
kubectl apply -f 1.mongodb-statefulset-openebs.yaml

# 정상 실행 확인
kubectl get pv,pvc,po,svc -A | grep mongodb

# 테스트를 위한 설정
# 여기서 나오는 값을(아마 아래 값과 일치)
kubectl run dns-verify -it --rm --restart=Never --image=busybox -- cat /etc/resolv.conf
nameserver 172.96.0.10

# 여기에 넣자
sudo vi /etc/resolv.conf

# ping 확인
curl mongodb-0.mongodb-svc.mongodb.svc.cluster.local:27017

curl mongodb-1.mongodb-svc.mongodb.svc.cluster.local:27017

curl mongodb-2.mongodb-svc.mongodb.svc.cluster.local:27017

# mongodb 세팅 필요
kubectl exec -it -n mongodb mongodb-0 -- /bin/bash

# mongodb 사용
mongo

# replicaset 구성 명령어
rs.initiate({
  _id: "rs0",
  members: [
    { _id: 0, host: "mongodb-0.mongodb-svc.mongodb.svc.cluster.local:27017", priority: 100},
    { _id: 1, host: "mongodb-1.mongodb-svc.mongodb.svc.cluster.local:27017", priority: 50},
    { _id: 2, host: "mongodb-2.mongodb-svc.mongodb.svc.cluster.local:27017", priority: 50}
  ]
})

# replicaset 구성 확인
rs.status()

# 조금 기다리면 아래와 같이 뜨는거 확인 하고 아래 명령어 실행
rs0:PRIMARY>

# 워크북 경로
# 노션 → 작업공간/워크북 → DB - MongoDB
# 사용할 DB지정
use im

# collection생성
db.createCollection("InterviewMaster")

# 더미 데이터 생성
db.InterviewMaster2.insert(
  {
    "_id":"pji0217@naver.com"
  , "user_info":
      {
          "user_nm":"박종익"
        , "user_nicknm":"jjong"
        , "user_gender":"남"
        , "user_birthday":"1992-02-17"
        , "user_tel":"010-000-0000"
      }
  , "user_history":
      {
          "user_itv_cnt":"3"
      }
  , "itv_info":
      {
          "pji0217@naver_240610_00001":
            {
                "itv_sub":"jjong_자소서_모의면접_001"
              , "itv_text_url":"s3://simulation-userdata/text/test.txt"
              , "itv_cate":"자소서"
              , "itv_job":"시스템 엔지니어"
              , "itv_qs_cnt":"5"
              , "itv_date":"2024-06-10"
              , "qs_info":
                  {
                      "01":
                        {
	                          "qs_content":"자신의 강점에 대해서 설명해보세요."
	                        , "qs_video_url":"s3://simulation-userdata/video/1718263662009test.mp4"
	                        , "qs_audio_url":"s3://simulation-userdata/audio/1718324990967.mp3"
	                        , "qs_text_url":"s3://simulation-userdata/text/test.txt"
	                        , "qs_fb_url":"http://url/..."
                        }
                    , "02":
                        {
	                          "qs_content":"자신의 특별한 경험에 대해서 설명해보세요."
	                        , "qs_video_url":"http://url/..."
	                        , "qs_audio_url":"http://url/..."
	                        , "qs_text_url":"http://url/..."
	                        , "qs_fb_url":"http://url/..."
                        }
                    , "03":
                        {
	                          "qs_content":"이런 상황에서 본인이라면 어떻게 해결할지에 대해서 설명해보세요."
	                        , "qs_video_url":"http://url/..."
	                        , "qs_audio_url":"http://url/..."
	                        , "qs_text_url":"http://url/..."
	                        , "qs_fb_url":"http://url/..."
                        }
                    , "04":
                        {
	                          "qs_content":"자신의 경험 중 힘든일이 무엇있었는지, 어떻게 해결했는지 이야기 해주세요."
	                        , "qs_video_url":"http://url/..."
	                        , "qs_audio_url":"http://url/..."
	                        , "qs_text_url":"http://url/..."
	                        , "qs_fb_url":"http://url/..."
                        }
                    , "05":
                        {
	                          "qs_content":"우리가 당신을 채용해야할 이유에 대해서 설명해보세요."
	                        , "qs_video_url":"http://url/..."
	                        , "qs_audio_url":"http://url/..."
	                        , "qs_text_url":"http://url/..."
	                        , "qs_fb_url":"http://url/..."
                        }
                  }
            }
        , "pji0217@naver_240611_00010":
            {
                "itv_sub":"jjong_자소서_모의면접_002"
              , "itv_text_url":"http://url/..."
              , "itv_cate":"자소서"
              , "itv_job":"DevOps 엔지니어"
              , "itv_qs_cnt":"5"
              , "itv_date":"2024-06-11"
              , "qs_info":
                  {
                      "01":
                        {
	                          "qs_content":"자신의 강점에 대해서 설명해보세요."
	                        , "qs_video_url":"http://url/..."
	                        , "qs_audio_url":"http://url/..."
	                        , "qs_text_url":"http://url/..."
	                        , "qs_fb_url":"http://url/..."
                        }
                    , "02":
                        {
	                          "qs_content":"자신의 특별한 경험에 대해서 설명해보세요."
	                        , "qs_video_url":"http://url/..."
	                        , "qs_audio_url":"http://url/..."
	                        , "qs_text_url":"http://url/..."
	                        , "qs_fb_url":"http://url/..."
                        }
                    , "03":
                        {
	                          "qs_content":"이런 상황에서 본인이라면 어떻게 해결할지에 대해서 설명해보세요."
	                        , "qs_video_url":"http://url/..."
	                        , "qs_audio_url":"http://url/..."
	                        , "qs_text_url":"http://url/..."
	                        , "qs_fb_url":"http://url/..."
                        }
                    , "04":
                        {
	                          "qs_content":"자신의 경험 중 힘든일이 무엇있었는지, 어떻게 해결했는지 이야기 해주세요."
	                        , "qs_video_url":"http://url/..."
	                        , "qs_audio_url":"http://url/..."
	                        , "qs_text_url":"http://url/..."
	                        , "qs_fb_url":"http://url/..."
                        }
                    , "05":
                        {
	                          "qs_content":"우리가 당신을 채용해야할 이유에 대해서 설명해보세요."
	                        , "qs_video_url":"http://url/..."
	                        , "qs_audio_url":"http://url/..."
	                        , "qs_text_url":"http://url/..."
	                        , "qs_fb_url":"http://url/..."
                        }
                  }
            }
        , "pji0217@naver_240612_00014":
            {
                "itv_sub":"jjong_자소서_모의면접_003"
              , "itv_text_url":"http://url/..."
              , "itv_cate":"자소서"
              , "itv_job":"DevOps 엔지니어"
              , "itv_qs_cnt":"5"
              , "itv_date":"2024-06-12"
              , "qs_info":
                  {
                      "01":
                        {
	                          "qs_content":"자신의 강점에 대해서 설명해보세요."
	                        , "qs_video_url":"http://url/..."
	                        , "qs_audio_url":"http://url/..."
	                        , "qs_text_url":"http://url/..."
	                        , "qs_fb_url":"http://url/..."
                        }
                    , "02":
                        {
	                          "qs_content":"자신의 특별한 경험에 대해서 설명해보세요."
	                        , "qs_video_url":"http://url/..."
	                        , "qs_audio_url":"http://url/..."
	                        , "qs_text_url":"http://url/..."
	                        , "qs_fb_url":"http://url/..."
                        }
                    , "03":
                        {
	                          "qs_content":"이런 상황에서 본인이라면 어떻게 해결할지에 대해서 설명해보세요."
	                        , "qs_video_url":"http://url/..."
	                        , "qs_audio_url":"http://url/..."
	                        , "qs_text_url":"http://url/..."
	                        , "qs_fb_url":"http://url/..."
                        }
                    , "04":
                        {
	                          "qs_content":"자신의 경험 중 힘든일이 무엇있었는지, 어떻게 해결했는지 이야기 해주세요."
	                        , "qs_video_url":"http://url/..."
	                        , "qs_audio_url":"http://url/..."
	                        , "qs_text_url":"http://url/..."
	                        , "qs_fb_url":"http://url/..."
                        }
                    , "05":
                        {
	                          "qs_content":"우리가 당신을 채용해야할 이유에 대해서 설명해보세요."
	                        , "qs_video_url":"http://url/..."
	                        , "qs_audio_url":"http://url/..."
	                        , "qs_text_url":"http://url/..."
	                        , "qs_fb_url":"http://url/..."
                        }
                  }
            }
      }
  }
)
