"""파일 I/O 전담 모듈 (JSONL 저장, 제너레이터 스트리밍, 원자적 교체)"""
import json
import os
import tempfile
from typing import Iterator, Optional

from .models import Transaction, Budget, Category


def _ensure_file(filepath: str) -> None:
    dirpath = os.path.dirname(filepath)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
    if not os.path.exists(filepath):
        open(filepath, "w", encoding="utf-8").close()


def _atomic_rewrite(filepath: str, lines: list[str]) -> None:
    """임시 파일에 쓰고 os.replace로 원자적 교체 (update/delete 안정성 확보)"""
    dirpath = os.path.dirname(filepath) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dirpath)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
        os.replace(tmp_path, filepath)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


class TransactionRepository:
    """거래 내역 저장소 (JSONL, 스트리밍 조회)"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        _ensure_file(filepath)

    def stream_all(self) -> Iterator[Transaction]:
        """파일 전체를 메모리에 올리지 않고 한 줄씩 읽어 yield한다."""
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield Transaction.from_dict(json.loads(line))

    def append(self, tx: Transaction) -> None:
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(tx.to_dict(), ensure_ascii=False) + "\n")

    def next_id(self) -> str:
        max_num = 0
        for tx in self.stream_all():
            try:
                num = int(tx.id.split("-")[-1])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue
        return f"TX-{max_num + 1:06d}"

    def rewrite_all(self, transactions: list[Transaction]) -> None:
        lines = [json.dumps(t.to_dict(), ensure_ascii=False) for t in transactions]
        _atomic_rewrite(self.filepath, lines)


class CategoryRepository:
    """카테고리 저장소 (JSONL, 소량 데이터라 리스트로 관리)"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        _ensure_file(filepath)

    def stream_all(self) -> Iterator[Category]:
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield Category.from_dict(json.loads(line))

    def list_names(self) -> list[str]:
        return [c.name for c in self.stream_all()]

    def add(self, name: str) -> None:
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps({"name": name}, ensure_ascii=False) + "\n")

    def remove(self, name: str) -> bool:
        names = self.list_names()
        if name not in names:
            return False
        remaining = [n for n in names if n != name]
        lines = [json.dumps({"name": n}, ensure_ascii=False) for n in remaining]
        _atomic_rewrite(self.filepath, lines)
        return True


class BudgetRepository:
    """예산 저장소 (월별 1건, JSONL)"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        _ensure_file(filepath)

    def stream_all(self) -> Iterator[Budget]:
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield Budget.from_dict(json.loads(line))

    def get(self, month: str) -> Optional[int]:
        for b in self.stream_all():
            if b.month == month:
                return b.amount
        return None

    def upsert(self, month: str, amount: int) -> None:
        budgets = list(self.stream_all())
        found = False
        for b in budgets:
            if b.month == month:
                b.amount = amount
                found = True
        if not found:
            budgets.append(Budget(month=month, amount=amount))
        lines = [json.dumps(b.to_dict(), ensure_ascii=False) for b in budgets]
        _atomic_rewrite(self.filepath, lines)
