# 설치 가이드

Claude Code를 이미 사용 중이라면 Claude 로그인은 완료된 상태입니다.  
아래 3단계만 따라하면 됩니다.

---

## 1단계 — Python 설치 확인

터미널을 열고 아래를 입력하세요:

```
python3 --version
```

> 터미널 여는 법: `Command(⌘) + Space` → `터미널` 입력 → Enter

`Python 3.xx.x` 숫자가 나오면 **2단계로 넘어가세요.**

숫자가 안 나오면 https://www.python.org/downloads 에서 Python을 설치하세요.

---

## 2단계 — 파일 다운로드

1. https://github.com/coco-bmf/multi-agent-runner 접속
2. 초록색 `<> Code` 버튼 클릭
3. `Download ZIP` 클릭
4. 다운로드된 zip 파일을 더블클릭해서 압축 풀기

---

## 3단계 — API 키 설정 (선택)

Claude 외에 Codex(OpenAI), Gemini도 함께 쓰고 싶을 때만 필요합니다.  
Claude만 쓸 거라면 건너뛰세요.

압축 푼 폴더 안의 `.env.example` 파일을 복사해 이름을 `.env`로 바꾸고, 텍스트 편집기로 열어서 키를 입력하세요:

```
OPENAI_API_KEY=여기에_OpenAI_키_붙여넣기
GEMINI_API_KEY=여기에_Gemini_키_붙여넣기
```

---

## 실행하기

터미널에서 다운로드한 폴더로 이동합니다:

```
cd ~/Downloads/multi-agent-runner-main
```

실행:

```
python3 run.py "여기에 질문이나 작업 내용을 입력하세요"
```

예시:

```
python3 run.py "파이썬으로 계산기 코드 짜줘"
python3 run.py "이 글 영어로 번역해줘: 안녕하세요"
```

---

## 자주 겪는 오류

| 오류 메시지 | 해결 방법 |
|---|---|
| `python3: command not found` | 1단계로 돌아가서 Python 설치 |
| `Permission denied` | `sudo python3 run.py "..."` 로 재시도 |
