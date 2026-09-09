"""공통 검증/유틸 함수 모듈"""
import re
from datetime import datetime

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")


def validate_date(date_str: str) -> str:
    """YYYY-MM-DD 형식 검증. 실패 시 ValueError."""
    if not date_str or not DATE_PATTERN.match(date_str):
        raise ValueError("날짜 형식이 올바르지 않습니다 (YYYY-MM-DD).")
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError("존재하지 않는 날짜입니다.")
    return date_str


def validate_month(month_str: str) -> str:
    """YYYY-MM 형식 검증."""
    if not month_str or not MONTH_PATTERN.match(month_str):
        raise ValueError("월 형식이 올바르지 않습니다 (YYYY-MM).")
    try:
        datetime.strptime(month_str, "%Y-%m")
    except ValueError:
        raise ValueError("존재하지 않는 월입니다.")
    return month_str


def validate_amount(amount_str: str) -> int:
    """양수 정수 검증."""
    try:
        amount = int(str(amount_str).strip())
    except (ValueError, TypeError):
        raise ValueError("금액은 숫자여야 합니다.")
    if amount <= 0:
        raise ValueError("금액은 0보다 큰 양수여야 합니다.")
    return amount


def validate_type(type_str: str) -> str:
    """income/expense 검증."""
    if type_str not in ("income", "expense"):
        raise ValueError("타입은 income 또는 expense만 가능합니다.")
    return type_str


def parse_tags(raw: str) -> list[str]:
    """쉼표 구분 태그 문자열 -> 리스트"""
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]
