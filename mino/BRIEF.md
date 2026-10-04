---
workflow: general-video
flow: companion
storyboard: no
message: "아이디어 한 줄이면 대본, 디자인, 영상까지 — MINO"
aspect: "9:16 (1080x1920)"
fps: 60
length: "30.5s"
language: ko
audio: none
---

## Intent
가상의 AI 콘텐츠 제작 플랫폼 MINO의 30초 브랜드 광고 모션그래픽(콘셉트 영상).
장면표(01–10)와 디자인 문법은 사용자가 직접 지정했고, 순서와 시간을 그대로 지킨다.

## Review plan (user-specified)
1. 03(대시보드), 08(폰+채팅)만 먼저 `renders/test-03.mp4`, `renders/test-08.mp4` + 정지 PNG로 렌더.
2. 프레임을 직접 열어 글자 잘림·겹침·화면 밖 패널·빈 프레임 점검 후 수정.
3. 사용자 OK 후 나머지 장면을 만들어 `renders/preview.mp4`.

## Notes
- 폰트: Pretendard Regular/SemiBold/ExtraBold (npm `pretendard`, OFL), 모노는 IBM Plex Mono.
- 장면 테스트는 `tests/tNN/` 미니 프로젝트로 렌더한다 (`tests/sync.sh`로 공용 폴더 복사).
