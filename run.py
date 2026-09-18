#!/usr/bin/env python3
"""multi-agent runner — 3개 에이전트(Claude, Codex, Gemini)에 동시에 프롬프트를 보내고 결과를 취합한다.

Usage:
  python run.py "이 코드의 보안 취약점을 분석해줘"
  python run.py "REST API 설계해줘" --mode judge
  python run.py "리팩토링 방안 제안" --mode summarize --agents claude,gemini
  python run.py "코드 리뷰" --timeout 600 --judge-by gemini
"""
import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
ENV_FILE = SCRIPT_DIR / ".env"


def _load_dotenv() -> dict:
    """간단한 .env 파서. KEY=VALUE 형식만 지원."""
    env = {}
    if not ENV_FILE.exists():
        return env
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            if v:
                env[k.strip()] = v
    return env

# ──────────────────────────────────────────────
# 에이전트 정의
# ──────────────────────────────────────────────

AGENTS = {
    "claude": {
        "cmd": ["claude", "-p", "--output-format", "text"],
        "name": "Claude",
    },
    "codex": {
        "cmd": ["codex", "exec", "--json"],
        "name": "Codex",
        "parse": "codex_json",
    },
    "gemini": {
        "cmd": ["agy", "-p"],
        "name": "Gemini",
    },
}


# ──────────────────────────────────────────────
# 파서
# ──────────────────────────────────────────────

def _parse_codex_jsonl(raw: str) -> str:
    """codex --json JSONL 출력에서 실제 답변 텍스트만 추출한다."""
    parts = []
    for line in raw.splitlines():
        try:
            ev = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        # item.completed 이벤트에서 텍스트 추출
        if ev.get("type") == "item.completed":
            item = ev.get("item", {})
            text = item.get("text", "")
            if text:
                parts.append(text)
                continue
            # content 배열 안에 텍스트가 있는 경우
            for c in item.get("content", []):
                if isinstance(c, dict) and c.get("type") == "text":
                    parts.append(c["text"])
                elif isinstance(c, str):
                    parts.append(c)
        # role=assistant 형식 (이전 버전 호환)
        elif ev.get("role") == "assistant":
            for c in ev.get("content", []):
                if isinstance(c, dict) and c.get("type") == "text":
                    parts.append(c["text"])
                elif isinstance(c, str):
                    parts.append(c)
    return "\n".join(parts) if parts else raw


# ──────────────────────────────────────────────
# 에이전트 실행
# ──────────────────────────────────────────────

async def run_agent(agent_id: str, prompt: str, timeout: int) -> dict:
    """에이전트 CLI를 서브프로세스로 실행하고 결과를 반환한다."""
    config = AGENTS[agent_id]
    binary = config["cmd"][0]

    # CLI 존재 확인
    if not shutil.which(binary):
        return {
            "agent": agent_id,
            "name": config["name"],
            "status": "skip",
            "error": f"'{binary}' CLI가 설치되지 않았거나 PATH에 없음",
            "output": None,
            "elapsed": 0,
        }

    # 특수문자가 포함된 긴 프롬프트는 셸 인자 대신 안전한 방법으로 전달
    needs_safe = len(prompt) > 2000 or any(c in prompt for c in '`"\'{}$\\')
    tmp_file = None
    stdin_data = b""

    if needs_safe and agent_id == "gemini":
        # gemini: stdin으로 프롬프트 전달 + -p에 최소 지시문
        cmd = config["cmd"] + ["위 내용에 답변해줘"]
        stdin_data = prompt.encode("utf-8")
    elif needs_safe:
        # claude, codex는 stdin(-) 지원
        cmd = config["cmd"] + ["-"]
        stdin_data = prompt.encode("utf-8")
    else:
        cmd = config["cmd"] + [prompt]

    start = time.time()

    # 에이전트별 환경변수 + .env 병합
    proc_env = {**os.environ, **_load_dotenv(), **config.get("env", {})}

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=proc_env,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=stdin_data), timeout=timeout
        )
        elapsed = time.time() - start

        stderr_text = stderr.decode("utf-8", errors="replace").strip()
        stdout_text = stdout.decode("utf-8", errors="replace").strip()

        # claude -p는 결과를 stderr에 출력하는 경우가 있음 (returncode=0이지만 stdout 비어있을 때)
        if proc.returncode == 0 and not stdout_text and stderr_text:
            # stderr에 있는 내용이 실제 결과일 수 있음
            stdout_text = stderr_text
            stderr_text = ""

        if proc.returncode != 0:
            return {
                "agent": agent_id,
                "name": config["name"],
                "status": "error",
                "error": f"[exit={proc.returncode}] {stderr_text[:400]}" if stderr_text else f"[exit={proc.returncode}] stdout='{stdout_text[:200]}'",
                "output": None,
                "elapsed": round(elapsed, 1),
            }

        raw = stdout_text
        if not raw and stderr_text:
            return {
                "agent": agent_id,
                "name": config["name"],
                "status": "error",
                "error": stderr_text[:500],
                "output": None,
                "elapsed": round(elapsed, 1),
            }

        # codex --json: JSONL 이벤트에서 assistant 메시지만 추출
        if config.get("parse") == "codex_json":
            raw = _parse_codex_jsonl(raw)

        return {
            "agent": agent_id,
            "name": config["name"],
            "status": "ok",
            "error": None,
            "output": raw,
            "elapsed": round(elapsed, 1),
        }

    except asyncio.TimeoutError:
        elapsed = time.time() - start
        # 타임아웃 시 프로세스 종료
        try:
            proc.terminate()
            await asyncio.sleep(2)
            proc.kill()
        except Exception:
            pass
        return {
            "agent": agent_id,
            "name": config["name"],
            "status": "timeout",
            "error": f"{timeout}초 초과",
            "output": None,
            "elapsed": round(elapsed, 1),
        }
    finally:
        if tmp_file:
            try:
                os.unlink(tmp_file.name)
            except OSError:
                pass


async def run_all_agents(prompt: str, agent_ids: list[str], timeout: int) -> list[dict]:
    """선택된 에이전트들을 병렬로 실행한다."""
    tasks = [run_agent(aid, prompt, timeout) for aid in agent_ids]
    return await asyncio.gather(*tasks)


# ──────────────────────────────────────────────
# 결과 취합
# ──────────────────────────────────────────────

def build_merge_prompt(results: list[dict], mode: str, original_prompt: str) -> str:
    """취합용 프롬프트를 생성한다."""
    ok_results = [r for r in results if r["status"] == "ok"]

    if len(ok_results) < 2:
        return ""

    results_block = ""
    for r in ok_results:
        results_block += f"\n--- {r['name']} (소요: {r['elapsed']}초) ---\n"
        results_block += r["output"]
        results_block += "\n"

    if mode == "summarize":
        return f"""아래는 동일한 프롬프트에 대해 여러 AI 에이전트가 각각 생성한 결과입니다.

[원래 프롬프트]
{original_prompt}

[각 에이전트 결과]
{results_block}

위 결과들을 종합하여 하나의 통합 답변을 작성해주세요.
- 각 에이전트의 좋은 포인트를 모두 포함
- 중복은 제거하고 상충하는 부분은 양쪽 의견을 병기
- 어떤 에이전트의 어떤 포인트를 채택했는지 간단히 표시"""

    else:  # judge
        return f"""아래는 동일한 프롬프트에 대해 여러 AI 에이전트가 각각 생성한 결과입니다.

[원래 프롬프트]
{original_prompt}

[각 에이전트 결과]
{results_block}

심사 기준:
1. 정확성 — 사실 관계가 맞는가
2. 완성도 — 빠진 내용 없이 충분히 다뤘는가
3. 실용성 — 바로 적용할 수 있는가
4. 구조 — 읽기 쉽고 논리적인가

각 에이전트 결과를 위 기준으로 평가하고:
- 각 기준별 점수 (1-5)
- 최종 순위와 선정 이유
- 선정된 결과를 그대로 출력 (수정 없이)"""


async def merge_results(
    results: list[dict], mode: str, original_prompt: str, judge_agent: str, timeout: int
) -> str | None:
    """성공한 결과들을 취합한다."""
    ok_results = [r for r in results if r["status"] == "ok"]

    if len(ok_results) == 0:
        return None
    if len(ok_results) == 1:
        return f"[에이전트 1개만 성공 — {ok_results[0]['name']}의 결과를 그대로 사용]\n\n{ok_results[0]['output']}"

    merge_prompt = build_merge_prompt(results, mode, original_prompt)
    if not merge_prompt:
        return None

    print(f"\n{'='*60}")
    print(f"  취합 중... (심사 에이전트: {judge_agent}, 모드: {mode})")
    print(f"{'='*60}\n")

    judge_result = await run_agent(judge_agent, merge_prompt, timeout)

    if judge_result["status"] == "ok":
        return judge_result["output"]
    else:
        # 심사 에이전트 실패 시 결과만 나란히 보여줘
        fallback = "[심사 에이전트 실패 — 각 결과를 나란히 표시합니다]\n\n"
        for r in ok_results:
            fallback += f"{'='*40}\n  {r['name']} (소요: {r['elapsed']}초)\n{'='*40}\n"
            fallback += r["output"] + "\n\n"
        return fallback


# ──────────────────────────────────────────────
# 결과 저장
# ──────────────────────────────────────────────

def save_results(prompt: str, results: list[dict], merged: str | None, mode: str):
    """결과를 파일로 저장한다."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    run_dir = RESULTS_DIR / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    # 개별 결과 저장
    for r in results:
        status_mark = {"ok": "ok", "error": "err", "skip": "skip", "timeout": "timeout"}
        fname = f"{r['agent']}_{status_mark.get(r['status'], 'unknown')}.md"
        content = r["output"] or r.get("error", "결과 없음")
        (run_dir / fname).write_text(content, encoding="utf-8")

    # 취합 결과 저장
    if merged:
        (run_dir / f"merged_{mode}.md").write_text(merged, encoding="utf-8")

    # 메타 정보
    meta = {
        "prompt": prompt,
        "mode": mode,
        "timestamp": ts,
        "agents": [
            {"agent": r["agent"], "status": r["status"], "elapsed": r["elapsed"]}
            for r in results
        ],
    }
    (run_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return run_dir


# ──────────────────────────────────────────────
# 출력
# ──────────────────────────────────────────────

def print_status(results: list[dict]):
    """각 에이전트 실행 결과 상태를 출력한다."""
    print(f"\n{'='*60}")
    print("  에이전트 실행 결과")
    print(f"{'='*60}")
    for r in results:
        icon = {"ok": "[OK]", "error": "[ERR]", "skip": "[SKIP]", "timeout": "[TIMEOUT]"}
        status = icon.get(r["status"], "[?]")
        elapsed = f"{r['elapsed']}s" if r["elapsed"] else "-"
        detail = ""
        if r["status"] != "ok":
            detail = f" — {r['error']}"
        print(f"  {status:10s} {r['name']:20s} {elapsed:>8s}{detail}")
    print()


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────

async def async_main():
    ap = argparse.ArgumentParser(
        description="3개 에이전트에 동시에 프롬프트를 보내고 결과를 취합한다"
    )
    ap.add_argument("prompt", help="에이전트에 보낼 프롬프트")
    ap.add_argument(
        "--mode", choices=["summarize", "judge"], default="summarize",
        help="취합 모드: summarize(종합 요약) | judge(심사 선택) (기본: summarize)",
    )
    ap.add_argument(
        "--agents", default="claude,codex,gemini",
        help="실행할 에이전트 (쉼표 구분, 기본: claude,codex,gemini)",
    )
    ap.add_argument(
        "--judge-by", default="claude",
        help="취합/심사를 수행할 에이전트 (기본: claude)",
    )
    ap.add_argument(
        "--timeout", type=int, default=300,
        help="에이전트당 타임아웃 초 (기본: 300)",
    )
    ap.add_argument(
        "--no-merge", action="store_true",
        help="취합 없이 개별 결과만 출력",
    )
    args = ap.parse_args()

    agent_ids = [a.strip() for a in args.agents.split(",")]
    invalid = [a for a in agent_ids if a not in AGENTS]
    if invalid:
        print(f"알 수 없는 에이전트: {invalid}")
        print(f"사용 가능: {list(AGENTS.keys())}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Multi-Agent Runner")
    print(f"{'='*60}")
    print(f"  프롬프트 : {args.prompt[:80]}{'...' if len(args.prompt)>80 else ''}")
    print(f"  에이전트 : {', '.join(agent_ids)}")
    print(f"  취합 모드: {args.mode}")
    print(f"  타임아웃 : {args.timeout}초")
    print(f"{'='*60}")
    print(f"\n  에이전트 실행 중...\n")

    # 1. 병렬 실행
    results = await run_all_agents(args.prompt, agent_ids, args.timeout)

    # 2. 상태 출력
    print_status(results)

    # 3. 취합
    merged = None
    if not args.no_merge:
        merged = await merge_results(
            results, args.mode, args.prompt, args.judge_by, args.timeout
        )

    # 4. 저장
    run_dir = save_results(args.prompt, results, merged, args.mode)

    # 5. 최종 출력
    if merged:
        print(f"{'='*60}")
        print(f"  취합 결과 ({args.mode})")
        print(f"{'='*60}\n")
        print(merged)
    else:
        ok_results = [r for r in results if r["status"] == "ok"]
        if ok_results:
            for r in ok_results:
                print(f"{'='*60}")
                print(f"  {r['name']} (소요: {r['elapsed']}초)")
                print(f"{'='*60}\n")
                print(r["output"])
                print()
        else:
            print("성공한 에이전트가 없습니다.")

    print(f"\n  결과 저장: {run_dir}\n")


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
