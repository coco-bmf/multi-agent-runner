# 설치 가이드 (비개발자용)

컴퓨터에 명령어를 입력하는 방식으로 동작합니다. 처음이라도 순서대로 따라하면 됩니다.

> Mac 기준으로 작성되어 있습니다.

---

## 1단계 — 터미널 열기

터미널은 컴퓨터에 명령을 내리는 창입니다.

1. 키보드에서 `Command(⌘) + Space` 누르기
2. `터미널` 또는 `Terminal` 입력 후 Enter

검은(또는 흰) 창이 뜨면 성공입니다.

---

## 2단계 — Python 설치 확인

터미널에 아래를 입력하고 Enter:

```
python3 --version
```

`Python 3.xx.x` 같은 숫자가 나오면 이미 설치된 것입니다. **3단계로 넘어가세요.**

숫자가 안 나오면 https://www.python.org/downloads 에서 Python을 설치하세요.

---

## 3단계 — Claude CLI 설치

Claude는 별도 API 키 없이 로그인만 하면 됩니다.

터미널에 아래를 순서대로 입력하세요 (한 줄씩 Enter):

```
npm install -g @anthropic-ai/claude-code
```

> `npm`이 없다는 오류가 나오면: https://nodejs.org 에서 Node.js를 먼저 설치하세요.

설치 후 로그인:

```
claude
```

브라우저가 열리면 Anthropic 계정으로 로그인하면 됩니다.

---

## 4단계 — 파일 다운로드

1. https://github.com/coco-bmf/multi-agent-runner 접속
2. 초록색 `<> Code` 버튼 클릭
3. `Download ZIP` 클릭
4. 다운로드된 zip 파일을 더블클릭해서 압축 풀기

---

## 5단계 — API 키 설정 (Codex, Gemini 사용 시)

Claude만 쓸 거라면 이 단계는 건너뛰어도 됩니다.

압축 푼 폴더 안에 `.env.example` 파일이 있습니다.

1. `.env.example` 파일을 복사해서 이름을 `.env`로 바꾸기
2. 텍스트 편집기(메모장, TextEdit 등)로 열기
3. 아래처럼 키 입력 후 저장:

```
OPENAI_API_KEY=여기에_OpenAI_키_붙여넣기
GEMINI_API_KEY=여기에_Gemini_키_붙여넣기
```

---

## 6단계 — 실행하기

터미널에서 다운로드한 폴더로 이동합니다.

```
cd ~/Downloads/multi-agent-runner-main
```

> 폴더 이름이 다를 수 있습니다. `multi-agent-runner`로 시작하는 폴더명으로 입력하세요.

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

## 결과 확인

실행하면 터미널에 각 AI의 답변과 최종 취합 결과가 출력됩니다.  
동시에 `results/` 폴더 안에 날짜별로 파일이 저장됩니다.

---

## 자주 겪는 오류

| 오류 메시지 | 해결 방법 |
|---|---|
| `python3: command not found` | 2단계로 돌아가서 Python 설치 |
| `npm: command not found` | Node.js 설치 후 3단계 재시도 |
| `'claude' CLI가 설치되지 않았거나 PATH에 없음` | 3단계 Claude CLI 설치 확인 |
| `Permission denied` | `sudo python3 run.py "..."` 로 재시도 |
