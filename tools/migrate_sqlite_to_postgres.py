#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SRC = PROJECT_ROOT / "src" / "main" / "python"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PYTHON_SRC) not in sys.path:
    sys.path.insert(0, str(PYTHON_SRC))

from xianwen.db import (  # noqa: E402
    CollectionItemModel,
    CollectionJobModel,
    ConnectedAccountModel,
    CredentialSecretModel,
    FolderModel,
    TaskDB,
    TaskModel,
)


MODELS = [
    FolderModel,
    TaskModel,
    CredentialSecretModel,
    ConnectedAccountModel,
    CollectionJobModel,
    CollectionItemModel,
]


def copy_model(source: TaskDB, destination: TaskDB, model: type) -> tuple[int, int]:
    source_session = source.SessionLocal()
    destination_session = destination.SessionLocal()
    inserted = 0
    updated = 0
    try:
        for row in source_session.query(model).all():
            values = {column.name: getattr(row, column.name) for column in model.__table__.columns}
            identity = values.get("id")
            existing = destination_session.get(model, identity)
            if existing:
                updated += 1
            else:
                inserted += 1
            destination_session.merge(model(**values))
        destination_session.commit()
        return inserted, updated
    except Exception:
        destination_session.rollback()
        raise
    finally:
        source_session.close()
        destination_session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="把先闻继学 SQLite 数据合并迁移到 PostgreSQL")
    parser.add_argument(
        "--sqlite",
        default=str(PROJECT_ROOT / "xianwen.db"),
        help="SQLite 文件路径",
    )
    parser.add_argument(
        "--postgres-url",
        default=os.getenv("XIANWEN_DATABASE_URL", ""),
        help="PostgreSQL SQLAlchemy URL；默认读取 XIANWEN_DATABASE_URL",
    )
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite).expanduser().resolve()
    if not sqlite_path.is_file():
        parser.error(f"SQLite 文件不存在：{sqlite_path}")
    if not args.postgres_url.startswith(("postgresql://", "postgresql+psycopg://")):
        parser.error("请通过 --postgres-url 提供 PostgreSQL URL")

    source = TaskDB(
        file_path=str(PROJECT_ROOT / "__migration_source_tasks__.json"),
        database_url=f"sqlite:///{sqlite_path}",
    )
    destination = TaskDB(
        file_path=str(PROJECT_ROOT / "__migration_destination_tasks__.json"),
        database_url=args.postgres_url,
    )

    print("先闻继学数据库迁移")
    total_inserted = 0
    total_updated = 0
    for model in MODELS:
        inserted, updated = copy_model(source, destination, model)
        total_inserted += inserted
        total_updated += updated
        print(f"- {model.__tablename__}: inserted={inserted}, updated={updated}")
    print(f"完成: inserted={total_inserted}, updated={total_updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
