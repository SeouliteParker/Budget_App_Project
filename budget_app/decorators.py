"""공통 관심사를 분리한 데코레이터 모음"""
import functools
import os
import sys
import time
from datetime import datetime


def handle_errors(func):
    """예외를 스택트레이스 없이 원인+힌트로 출력하고, 실패 시 sys.exit(1)로 종료한다."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            print(f"[오류] {e}")
            print("[힌트] 입력값 형식과 범위를 다시 확인해주세요.")
            sys.exit(1)
        except FileNotFoundError as e:
            print(f"[오류] 파일을 찾을 수 없습니다: {e}")
            print("[힌트] 경로(--data-dir, --from)가 올바른지 확인해주세요.")
            sys.exit(1)
        except KeyError as e:
            print(f"[오류] 필수 값이 누락되었습니다: {e}")
            print("[힌트] CSV 헤더 또는 입력 항목을 확인해주세요.")
            sys.exit(1)
        except PermissionError as e:
            print(f"[오류] 파일 접근 권한이 없습니다: {e}")
            sys.exit(1)
        except EOFError:
            print("\n[오류] 입력이 중간에 종료되었습니다.")
            print("[힌트] 대화형 입력을 끝까지 완료해주세요.")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n[안내] 사용자에 의해 취소되었습니다.")
            sys.exit(1)
    return wrapper


def log_execution(func):
    """실행 로그를 stderr에 남긴다 (표준 출력과 섞이지 않도록)."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if os.environ.get("BUDGET_APP_VERBOSE"):
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[LOG] {now} - {func.__name__} 실행", file=sys.stderr)
        return func(*args, **kwargs)
    return wrapper


def measure_time(func):
    """실행 시간을 측정해 stderr에 출력한다."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        if os.environ.get("BUDGET_APP_VERBOSE"):
            print(f"[TIME] {func.__name__} 실행시간: {elapsed:.4f}초", file=sys.stderr)
        return result
    return wrapper
