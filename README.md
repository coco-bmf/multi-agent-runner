# multi-agent-runner

Claude, Codex, Gemini 3개 AI에 동시에 프롬프트를 보내고 결과를 자동으로 취합하는 CLI 도구입니다.

```
              ┌─────────┐
   prompt ───▶│  Claude │
              ├─────────┤
              │  Codex  │──▶ 취합(요약/심사) ──▶ 결과 저장
              ├─────────┤
              │  Gemini │
              └─────────┘
```

## 요구사항

각 CLI가 설치되어 있어야 합니다. 없는 에이전트는 자동으로 건너뜁니다.

| 에이전트 | CLI | 인증 |
|---|---|---|
| Claude | [`claude`](https://claude.ai/code) | `claude` 로그인 (키 불필요) |
| Codex | [`codex`](https://github.com/openai/codex) | `OPENAI_API_KEY` |
| Gemini | [`agy`](https://github.com/agy-cli/agy) | `GEMINI_API_KEY` |

Python 3.10 이상 필요. 외부 패키지 의존성 없음.

## 설치

```bash
git clone https://github.com/coco-bmf/multi-agent-runner.git
cd multi-agent-runner

# API 키 설정 (선택)
cp .env.example .env
# .env 파일에 OPENAI_API_KEY, GEMINI_API_KEY 입력
```

## 사용법

```bash
# 기본 실행 (3개 에이전트 병렬 → Claude가 취합)
python run.py "이 코드의 보안 취약점을 분석해줘"

# 심사 모드 (어떤 에이전트 결과가 가장 좋은지 선정)
python run.py "REST API 설계해줘" --mode judge

# 특정 에이전트만 사용
python run.py "리팩토링 방안 제안" --agents claude,gemini

# 취합 없이 개별 결과만 보기
python run.py "코드 리뷰" --no-merge

# 타임아웃 조정 (기본 300초)
python run.py "긴 작업" --timeout 600
```

## 옵션

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--mode` | `summarize` | `summarize` 종합 요약 / `judge` 심사 후 최선 선정 |
| `--agents` | `claude,codex,gemini` | 실행할 에이전트 (쉼표 구분) |
| `--judge-by` | `claude` | 취합/심사를 수행할 에이전트 |
| `--timeout` | `300` | 에이전트당 타임아웃 (초) |
| `--no-merge` | `false` | 취합 없이 개별 결과만 출력 |

## 결과 저장

실행할 때마다 `results/YYYYMMDD_HHMMSS/` 폴더에 자동 저장됩니다.

```
results/
└── 20260815_090751/
    ├── claude_ok.md       # Claude 결과
    ├── codex_ok.md        # Codex 결과
    ├── gemini_ok.md       # Gemini 결과
    ├── merged_summarize.md  # 취합 결과
    └── meta.json          # 실행 메타 정보
```

에러가 난 에이전트는 `claude_err.md`, 건너뛴 경우 `claude_skip.md`로 저장됩니다.

## 동작 방식

1. 선택된 에이전트를 **병렬**로 실행
2. 성공한 결과가 2개 이상이면 `--judge-by` 에이전트가 취합
3. 1개만 성공하면 그 결과를 그대로 사용
4. 전부 실패하면 에러 메시지 출력

## 라이선스

MIT
