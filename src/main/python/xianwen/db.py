import json
import os
import base64
import hashlib
import secrets
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Float,
    Integer,
    BigInteger,
    Text,
    DateTime,
    Boolean,
    Enum as SQLEnum,
    UniqueConstraint,
    inspect,
    or_,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from Cryptodome.Cipher import AES
from .config.settings import config
from .utils.logger import logger
from .utils.project_root import get_project_root

Base = declarative_base()

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    UPLOADING = "UPLOADING"
    TRANSCRIBING = "TRANSCRIBING"
    SUMMARIZING = "SUMMARIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class TaskModel(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    video_url = Column(String, nullable=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    latest_modified_at = Column(DateTime, default=datetime.utcnow)
    progress = Column(Float, default=0.0)
    title = Column(String, nullable=True)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    audio_duration = Column(Float, nullable=True)
    transcription_time = Column(Float, nullable=True)
    topic = Column(String, nullable=True)
    author_name = Column(String, nullable=True)
    author_url = Column(String, nullable=True)
    summary_mode = Column(String, nullable=True)
    summary_chunk_total = Column(Integer, nullable=True)
    summary_chunk_done = Column(Integer, nullable=True)
    summary_meta = Column(Text, nullable=True)
    folder_id = Column(String, nullable=True)
    source_type = Column(String, nullable=False, default="video")
    source_url = Column(Text, nullable=True)
    source_meta = Column(Text, nullable=True)
    library_visible = Column(Boolean, nullable=False, default=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "video_url": self.video_url,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "created_at": self.created_at.isoformat() + 'Z' if self.created_at else None,
            "latest_modified_at": self.latest_modified_at.isoformat() + 'Z' if self.latest_modified_at else None,
            "progress": self.progress,
            "title": self.title,
            "transcript": self.transcript,
            "summary": self.summary,
            "error_message": self.error_message,
            "audio_duration": self.audio_duration,
            "transcription_time": self.transcription_time,
            "topic": self.topic,
            "author_name": self.author_name,
            "author_url": self.author_url,
            "summary_mode": self.summary_mode,
            "summary_chunk_total": self.summary_chunk_total,
            "summary_chunk_done": self.summary_chunk_done,
            "summary_meta": self.summary_meta,
            "folder_id": self.folder_id,
            "source_type": self.source_type or "video",
            "source_url": self.source_url or self.video_url,
            "source_meta": self.source_meta,
            "library_visible": self.library_visible is not False,
        }


class ContentAssetModel(Base):
    """与任务关联、由先闻继学管理的持久内容物料。"""

    __tablename__ = "content_assets"
    __table_args__ = (
        UniqueConstraint("task_id", "relative_path", name="uq_content_asset_task_path"),
    )

    id = Column(String, primary_key=True)
    task_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False, index=True)
    asset_type = Column(String, nullable=False, index=True)
    relative_path = Column(Text, nullable=False)
    original_filename = Column(Text, nullable=True)
    content_type = Column(String, nullable=True)
    sha256 = Column(String, nullable=False)
    size_bytes = Column(BigInteger, nullable=False, default=0)
    source_url = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="available", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "role": self.role,
            "asset_type": self.asset_type,
            "relative_path": self.relative_path,
            "original_filename": self.original_filename,
            "content_type": self.content_type,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "source_url": self.source_url,
            "status": self.status,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }


class FolderModel(Base):
    __tablename__ = "folders"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    parent_id = Column(String, nullable=True)
    folder_type = Column(String, default="manual")
    source_video_url = Column(String, nullable=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "folder_type": self.folder_type,
            "source_video_url": self.source_video_url,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() + 'Z' if self.created_at else None,
        }


class CredentialSecretModel(Base):
    __tablename__ = "credential_secrets"

    id = Column(String, primary_key=True)
    encrypted_payload = Column(Text, nullable=False)
    key_version = Column(String, default="dev-v1")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ConnectedAccountModel(Base):
    __tablename__ = "connected_accounts"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=True)
    credential_type = Column(String, nullable=False)
    secret_id = Column(String, nullable=False)
    secret_masked = Column(String, nullable=True)
    domain_scope = Column(String, nullable=True)
    status = Column(String, default="connected", index=True)
    last_verified_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "display_name": self.display_name,
            "credential_type": self.credential_type,
            "secret_masked": self.secret_masked,
            "domain_scope": self.domain_scope,
            "status": self.status,
            "last_verified_at": self.last_verified_at.isoformat() + "Z" if self.last_verified_at else None,
            "last_used_at": self.last_used_at.isoformat() + "Z" if self.last_used_at else None,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }


class CollectionJobModel(Base):
    __tablename__ = "collection_jobs"

    id = Column(String, primary_key=True)
    provider = Column(String, nullable=False, index=True)
    source_type = Column(String, nullable=False)
    source_url = Column(Text, nullable=True)
    title = Column(String, nullable=False)
    folder_id = Column(String, nullable=True)
    status = Column(String, default="PENDING", index=True)
    total_items = Column(Integer, default=0)
    completed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    aggregate_markdown = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "provider": self.provider,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "title": self.title,
            "folder_id": self.folder_id,
            "status": self.status,
            "total_items": self.total_items,
            "completed_items": self.completed_items,
            "failed_items": self.failed_items,
            "aggregate_markdown": self.aggregate_markdown,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }


class CollectionItemModel(Base):
    __tablename__ = "collection_items"

    id = Column(String, primary_key=True)
    job_id = Column(String, nullable=False, index=True)
    sort_order = Column(Integer, default=0)
    provider = Column(String, nullable=False, index=True)
    source_url = Column(Text, nullable=False)
    title = Column(String, nullable=False)
    part_index = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True)
    task_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "sort_order": self.sort_order,
            "provider": self.provider,
            "source_url": self.source_url,
            "title": self.title,
            "part_index": self.part_index,
            "duration": self.duration,
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }


class ContentSubscriptionModel(Base):
    __tablename__ = "content_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "provider",
            "source_type",
            "external_source_id",
            name="uq_content_subscription_source",
        ),
    )

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)
    source_type = Column(String, nullable=False)
    source_url = Column(Text, nullable=False)
    external_source_id = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    connected_account_id = Column(String, nullable=False)
    folder_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="ACTIVE", index=True)
    poll_interval_minutes = Column(Integer, nullable=False, default=15)
    active_window_start = Column(String, nullable=False, default="08:30")
    active_window_end = Column(String, nullable=False, default="18:30")
    digest_time = Column(String, nullable=False, default="20:30")
    timezone = Column(String, nullable=False, default="Asia/Shanghai")
    initial_sync_mode = Column(String, nullable=False, default="from_now")
    last_cursor = Column(Text, nullable=True)
    last_polled_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    next_poll_at = Column(DateTime, nullable=True, index=True)
    last_digest_date = Column(String, nullable=True)
    last_digest_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    lease_owner = Column(String, nullable=True)
    lease_expires_at = Column(DateTime, nullable=True, index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "external_source_id": self.external_source_id,
            "display_name": self.display_name,
            "connected_account_id": self.connected_account_id,
            "folder_id": self.folder_id,
            "status": self.status,
            "poll_interval_minutes": self.poll_interval_minutes,
            "active_window_start": self.active_window_start,
            "active_window_end": self.active_window_end,
            "digest_time": self.digest_time,
            "timezone": self.timezone,
            "initial_sync_mode": self.initial_sync_mode,
            "last_cursor": self.last_cursor,
            "last_polled_at": self.last_polled_at.isoformat() + "Z" if self.last_polled_at else None,
            "last_success_at": self.last_success_at.isoformat() + "Z" if self.last_success_at else None,
            "next_poll_at": self.next_poll_at.isoformat() + "Z" if self.next_poll_at else None,
            "last_digest_date": self.last_digest_date,
            "last_digest_at": self.last_digest_at.isoformat() + "Z" if self.last_digest_at else None,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures or 0,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }


class SubscriptionItemModel(Base):
    __tablename__ = "subscription_items"
    __table_args__ = (
        UniqueConstraint(
            "subscription_id",
            "external_item_id",
            name="uq_subscription_item_external_id",
        ),
    )

    id = Column(String, primary_key=True)
    subscription_id = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False, index=True)
    external_item_id = Column(String, nullable=False, index=True)
    source_url = Column(Text, nullable=False)
    published_at = Column(DateTime, nullable=False, index=True)
    source_updated_at = Column(DateTime, nullable=True)
    first_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    captured_at = Column(DateTime, nullable=True)
    content_hash = Column(String, nullable=True)
    preview_text = Column(Text, nullable=True)
    raw_html = Column(Text, nullable=True)
    raw_markdown = Column(Text, nullable=True)
    image_manifest = Column(Text, nullable=True)
    source_meta = Column(Text, nullable=True)
    access_scope = Column(String, nullable=False, default="unknown")
    capture_status = Column(String, nullable=False, default="DISCOVERED", index=True)
    failure_code = Column(String, nullable=True)
    failure_detail = Column(Text, nullable=True)
    digest_date = Column(String, nullable=False, index=True)
    digest_task_id = Column(String, nullable=True, index=True)
    source_missing_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    @staticmethod
    def _json_value(raw: str | None, fallback: Any) -> Any:
        if not raw:
            return fallback
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return fallback

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "subscription_id": self.subscription_id,
            "provider": self.provider,
            "external_item_id": self.external_item_id,
            "source_url": self.source_url,
            "published_at": self.published_at.isoformat() + "Z" if self.published_at else None,
            "source_updated_at": self.source_updated_at.isoformat() + "Z" if self.source_updated_at else None,
            "first_seen_at": self.first_seen_at.isoformat() + "Z" if self.first_seen_at else None,
            "last_seen_at": self.last_seen_at.isoformat() + "Z" if self.last_seen_at else None,
            "captured_at": self.captured_at.isoformat() + "Z" if self.captured_at else None,
            "content_hash": self.content_hash,
            "preview_text": self.preview_text or "",
            "raw_html": self.raw_html,
            "raw_markdown": self.raw_markdown,
            "image_manifest": self._json_value(self.image_manifest, []),
            "source_meta": self._json_value(self.source_meta, {}),
            "access_scope": self.access_scope,
            "capture_status": self.capture_status,
            "failure_code": self.failure_code,
            "failure_detail": self.failure_detail,
            "digest_date": self.digest_date,
            "digest_task_id": self.digest_task_id,
            "source_missing_at": self.source_missing_at.isoformat() + "Z" if self.source_missing_at else None,
            "created_at": self.created_at.isoformat() + "Z" if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + "Z" if self.updated_at else None,
        }


class SubscriptionRunModel(Base):
    __tablename__ = "subscription_runs"

    id = Column(String, primary_key=True)
    subscription_id = Column(String, nullable=False, index=True)
    trigger = Column(String, nullable=False)
    status = Column(String, nullable=False, default="RUNNING", index=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    discovered_count = Column(Integer, nullable=False, default=0)
    captured_count = Column(Integer, nullable=False, default=0)
    updated_count = Column(Integer, nullable=False, default=0)
    locked_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    cursor_before = Column(Text, nullable=True)
    cursor_after = Column(Text, nullable=True)
    error_code = Column(String, nullable=True)
    error_detail = Column(Text, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "subscription_id": self.subscription_id,
            "trigger": self.trigger,
            "status": self.status,
            "started_at": self.started_at.isoformat() + "Z" if self.started_at else None,
            "finished_at": self.finished_at.isoformat() + "Z" if self.finished_at else None,
            "discovered_count": self.discovered_count or 0,
            "captured_count": self.captured_count or 0,
            "updated_count": self.updated_count or 0,
            "locked_count": self.locked_count or 0,
            "failed_count": self.failed_count or 0,
            "cursor_before": self.cursor_before,
            "cursor_after": self.cursor_after,
            "error_code": self.error_code,
            "error_detail": self.error_detail,
        }


def _credential_key() -> bytes:
    raw = os.getenv("XIANWEN_CREDENTIAL_SECRET")
    if not raw:
        key_file = Path(
            os.getenv("XIANWEN_CREDENTIAL_SECRET_FILE")
            or (get_project_root() / "config" / ".credential_secret")
        )
        try:
            key_file.parent.mkdir(parents=True, exist_ok=True)
            if key_file.exists():
                raw = key_file.read_text(encoding="utf-8").strip()
            else:
                raw = secrets.token_urlsafe(48)
                key_file.write_text(raw, encoding="utf-8")
                try:
                    key_file.chmod(0o600)
                except OSError:
                    pass
        except OSError as exc:
            raise RuntimeError(
                "无法创建本地凭据加密密钥，请设置 XIANWEN_CREDENTIAL_SECRET"
            ) from exc
    if not raw:
        raise RuntimeError("凭据加密密钥不能为空")
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _encrypt_secret_payload(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    cipher = AES.new(_credential_key(), AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(raw)
    packed = cipher.nonce + tag + ciphertext
    return "v1:" + base64.b64encode(packed).decode("ascii")


def _decrypt_secret_payload(encrypted_payload: str) -> Dict[str, Any]:
    if not encrypted_payload.startswith("v1:"):
        raise ValueError("Unsupported credential secret format")
    packed = base64.b64decode(encrypted_payload[3:].encode("ascii"))
    nonce, tag, ciphertext = packed[:16], packed[16:32], packed[32:]
    cipher = AES.new(_credential_key(), AES.MODE_GCM, nonce=nonce)
    raw = cipher.decrypt_and_verify(ciphertext, tag)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Credential payload must be a JSON object")
    return payload


def _mask_secret_value(value: Any) -> str:
    text_value = str(value or "")
    if len(text_value) <= 8:
        return "****" if text_value else ""
    return f"{text_value[:4]}****{text_value[-4:]}"


def _mask_secret_payload(payload: Dict[str, Any]) -> str:
    for key in ("SESSDATA", "cookie_header", "web_qtstr", "access_token", "token"):
        if payload.get(key):
            label = "Cookie" if key == "cookie_header" else key
            return f"{label}={_mask_secret_value(payload[key])}"
    for key, value in payload.items():
        if value:
            return f"{key}={_mask_secret_value(value)}"
    return ""


class TaskDB:
    def __init__(
        self,
        file_path: str = "tasks.json",
        sqlite_path: str | None = None,
        database_url: str | None = None,
    ):
        self.file_path = file_path
        self.use_db = False
        configured_database_url = database_url or os.getenv("XIANWEN_DATABASE_URL")
        if not configured_database_url and sqlite_path is None:
            configured_database_url = getattr(config.database, "url", "")
        resolved_sqlite_path = sqlite_path or getattr(config.database, "sqlite_path", "xianwen.db")

        try:
            self.database_url = configured_database_url or f"sqlite:///{resolved_sqlite_path}"
            self.engine = create_engine(self.database_url, echo=False)
            Base.metadata.create_all(self.engine)
            self._ensure_schema()
            self.SessionLocal = sessionmaker(bind=self.engine)
            self.use_db = True
            logger.info(
                "Using database: "
                + self.engine.url.render_as_string(hide_password=True)
            )
            self._migrate_from_file_if_needed()
        except Exception as e:
            if configured_database_url:
                raise RuntimeError(
                    "配置的数据库不可用；为避免写入错误的数据源，先闻继学已停止启动"
                ) from e
            logger.error(f"Failed to initialize database: {e}. Falling back to JSON file storage.")
            self.use_db = False
            self._load_from_file()

    def _ensure_schema(self):
        """Add backward-compatible columns for existing databases."""
        try:
            inspector = inspect(self.engine)
            # Ensure folders table exists
            if not inspector.has_table("folders"):
                FolderModel.__table__.create(self.engine)
                logger.info("Database schema updated: created folders table")

            columns = {col["name"] for col in inspector.get_columns("tasks")}
            has_latest_modified_at = "latest_modified_at" in columns
            has_author_name = "author_name" in columns
            has_author_url = "author_url" in columns
            has_summary_mode = "summary_mode" in columns
            has_summary_chunk_total = "summary_chunk_total" in columns
            has_summary_chunk_done = "summary_chunk_done" in columns
            has_summary_meta = "summary_meta" in columns
            has_folder_id = "folder_id" in columns
            has_source_type = "source_type" in columns
            has_source_url = "source_url" in columns
            has_source_meta = "source_meta" in columns
            has_library_visible = "library_visible" in columns
            if (
                has_latest_modified_at
                and has_author_name
                and has_author_url
                and has_summary_mode
                and has_summary_chunk_total
                and has_summary_chunk_done
                and has_summary_meta
                and has_folder_id
                and has_source_type
                and has_source_url
                and has_source_meta
                and has_library_visible
            ):
                return

            with self.engine.begin() as conn:
                if not has_latest_modified_at:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN latest_modified_at DATETIME"))
                    conn.execute(text("UPDATE tasks SET latest_modified_at = created_at WHERE latest_modified_at IS NULL"))
                    logger.info("Database schema updated: added tasks.latest_modified_at")
                if not has_author_name:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN author_name VARCHAR"))
                    logger.info("Database schema updated: added tasks.author_name")
                if not has_author_url:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN author_url VARCHAR"))
                    logger.info("Database schema updated: added tasks.author_url")
                if not has_summary_mode:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN summary_mode VARCHAR"))
                    logger.info("Database schema updated: added tasks.summary_mode")
                if not has_summary_chunk_total:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN summary_chunk_total INTEGER"))
                    logger.info("Database schema updated: added tasks.summary_chunk_total")
                if not has_summary_chunk_done:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN summary_chunk_done INTEGER"))
                    logger.info("Database schema updated: added tasks.summary_chunk_done")
                if not has_summary_meta:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN summary_meta TEXT"))
                    logger.info("Database schema updated: added tasks.summary_meta")
                if not has_folder_id:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN folder_id VARCHAR"))
                    logger.info("Database schema updated: added tasks.folder_id")
                if not has_source_type:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN source_type VARCHAR"))
                    conn.execute(text("UPDATE tasks SET source_type = 'video' WHERE source_type IS NULL"))
                    logger.info("Database schema updated: added tasks.source_type")
                if not has_source_url:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN source_url TEXT"))
                    conn.execute(text("UPDATE tasks SET source_url = video_url WHERE source_url IS NULL"))
                    logger.info("Database schema updated: added tasks.source_url")
                if not has_source_meta:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN source_meta TEXT"))
                    logger.info("Database schema updated: added tasks.source_meta")
                if not has_library_visible:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN library_visible BOOLEAN"))
                    conn.execute(text("UPDATE tasks SET library_visible = TRUE WHERE library_visible IS NULL"))
                    logger.info("Database schema updated: added tasks.library_visible")
        except Exception as e:
            logger.error(f"Failed to ensure database schema: {e}")

    def _load_from_file(self):
        self._memory_db: Dict[str, str] = {}
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self._memory_db = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load tasks from file: {e}")

    def _save_to_file(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self._memory_db, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tasks to file: {e}")

    def _migrate_from_file_if_needed(self):
        """Migrate data from tasks.json to SQLite if file exists and DB is empty"""
        if not os.path.exists(self.file_path):
            return
        
        session: Session = self.SessionLocal()
        try:
            count = session.query(TaskModel).count()
            if count > 0:
                return  # Already has data, skip migration
            
            with open(self.file_path, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
            
            for task_id, task_json in file_data.items():
                task_data = json.loads(task_json)
                task = TaskModel(
                    id=task_data.get("id", task_id),
                    video_url=task_data["video_url"],
                    status=TaskStatus(task_data.get("status", "PENDING")),
                    created_at=datetime.fromisoformat(task_data["created_at"]) if task_data.get("created_at") else datetime.utcnow(),
                    latest_modified_at=datetime.fromisoformat(task_data["latest_modified_at"]) if task_data.get("latest_modified_at") else datetime.fromisoformat(task_data["created_at"]) if task_data.get("created_at") else datetime.utcnow(),
                    progress=task_data.get("progress", 0.0),
                    title=task_data.get("title"),
                    transcript=task_data.get("transcript"),
                    summary=task_data.get("summary"),
                    error_message=task_data.get("error_message"),
                    audio_duration=task_data.get("audio_duration"),
                    transcription_time=task_data.get("transcription_time"),
                    topic=task_data.get("topic"),
                    author_name=task_data.get("author_name"),
                    author_url=task_data.get("author_url"),
                    summary_mode=task_data.get("summary_mode"),
                    summary_chunk_total=task_data.get("summary_chunk_total"),
                    summary_chunk_done=task_data.get("summary_chunk_done"),
                    summary_meta=task_data.get("summary_meta"),
                    source_type=task_data.get("source_type") or "video",
                    source_url=task_data.get("source_url") or task_data.get("video_url"),
                    source_meta=task_data.get("source_meta"),
                    library_visible=task_data.get("library_visible", True) is not False,
                )
                session.add(task)
            
            session.commit()
            logger.info(f"Migrated {len(file_data)} tasks from {self.file_path} to database")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to migrate data from file: {e}")
        finally:
            session.close()

    def _serialize_task(self, task_data: Dict[str, Any]) -> str:
        data = task_data.copy()
        if isinstance(data.get("created_at"), datetime):
            data["created_at"] = data["created_at"].isoformat()
        if isinstance(data.get("latest_modified_at"), datetime):
            data["latest_modified_at"] = data["latest_modified_at"].isoformat()
        return json.dumps(data)

    def _deserialize_task(self, task_json: str) -> Dict[str, Any]:
        data = json.loads(task_json)
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("latest_modified_at"):
            data["latest_modified_at"] = datetime.fromisoformat(data["latest_modified_at"])
        elif data.get("created_at"):
            data["latest_modified_at"] = data["created_at"]
        data.setdefault("source_type", "video")
        data.setdefault("source_url", data.get("video_url"))
        data.setdefault("source_meta", None)
        data.setdefault("library_visible", True)
        return data

    def save_task(self, task_id: str, task_data: Dict[str, Any]):
        if self.use_db:
            session: Session = self.SessionLocal()
            try:
                task = session.query(TaskModel).filter(TaskModel.id == task_id).first()
                if task:
                    for key, value in task_data.items():
                        if key == "status" and isinstance(value, str):
                            value = TaskStatus(value)
                        elif key == "created_at" and isinstance(value, str):
                            value = datetime.fromisoformat(value)
                        elif key == "latest_modified_at" and isinstance(value, str):
                            value = datetime.fromisoformat(value)
                        setattr(task, key, value)
                else:
                    task_data_copy = task_data.copy()
                    if "status" in task_data_copy and isinstance(task_data_copy["status"], str):
                        task_data_copy["status"] = TaskStatus(task_data_copy["status"])
                    if "created_at" in task_data_copy and isinstance(task_data_copy["created_at"], str):
                        task_data_copy["created_at"] = datetime.fromisoformat(task_data_copy["created_at"])
                    if "latest_modified_at" in task_data_copy and isinstance(task_data_copy["latest_modified_at"], str):
                        task_data_copy["latest_modified_at"] = datetime.fromisoformat(task_data_copy["latest_modified_at"])
                    if "latest_modified_at" not in task_data_copy:
                        task_data_copy["latest_modified_at"] = task_data_copy.get("created_at", datetime.utcnow())
                    task_data_copy.setdefault("source_type", "video")
                    task_data_copy.setdefault("source_url", task_data_copy.get("video_url"))
                    task_data_copy.setdefault("source_meta", None)
                    task_data_copy.setdefault("library_visible", True)
                    
                    # 确保 'id' 不在 task_data_copy 中，因为它已经作为关键字参数传递
                    task_data_copy.pop('id', None)
                    
                    task = TaskModel(id=task_id, **task_data_copy)
                    session.add(task)
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save task to database: {e}")
            finally:
                session.close()
        else:
            serialized = self._serialize_task(task_data)
            self._memory_db[task_id] = serialized
            self._save_to_file()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        if self.use_db:
            session: Session = self.SessionLocal()
            try:
                task = session.query(TaskModel).filter(TaskModel.id == task_id).first()
                return task.to_dict() if task else None
            finally:
                session.close()
        else:
            serialized = self._memory_db.get(task_id)
            if serialized:
                return self._deserialize_task(serialized)
            return None

    def upsert_content_asset(self, asset_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.use_db:
            return None
        task_id = str(asset_data.get("task_id") or "").strip()
        relative_path = str(asset_data.get("relative_path") or "").strip()
        if not task_id or not relative_path:
            raise ValueError("内容物料必须包含 task_id 和 relative_path")

        session: Session = self.SessionLocal()
        try:
            asset = (
                session.query(ContentAssetModel)
                .filter(
                    ContentAssetModel.task_id == task_id,
                    ContentAssetModel.relative_path == relative_path,
                )
                .first()
            )
            now = datetime.utcnow()
            payload = {
                key: value
                for key, value in asset_data.items()
                if hasattr(ContentAssetModel, key)
            }
            if asset:
                for key, value in payload.items():
                    if key not in {"id", "task_id", "created_at"}:
                        setattr(asset, key, value)
                asset.updated_at = now
            else:
                payload.setdefault("id", uuid.uuid4().hex)
                payload.setdefault("created_at", now)
                payload.setdefault("updated_at", now)
                asset = ContentAssetModel(**payload)
                session.add(asset)
            session.commit()
            session.refresh(asset)
            return asset.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_content_assets(
        self,
        task_id: str,
        *,
        role: Optional[str] = None,
        status: Optional[str] = "available",
    ) -> List[Dict[str, Any]]:
        if not self.use_db:
            return []
        session: Session = self.SessionLocal()
        try:
            query = session.query(ContentAssetModel).filter(ContentAssetModel.task_id == task_id)
            if role:
                query = query.filter(ContentAssetModel.role == role)
            if status:
                query = query.filter(ContentAssetModel.status == status)
            return [asset.to_dict() for asset in query.order_by(ContentAssetModel.created_at.asc()).all()]
        finally:
            session.close()

    def delete_content_assets(
        self,
        task_id: str,
        *,
        relative_path_prefix: Optional[str] = None,
    ) -> int:
        """删除任务下已明确废弃的物料索引；未指定前缀时删除该任务的全部索引。"""
        if not self.use_db:
            return 0
        session: Session = self.SessionLocal()
        try:
            query = session.query(ContentAssetModel).filter(ContentAssetModel.task_id == task_id)
            if relative_path_prefix:
                query = query.filter(ContentAssetModel.relative_path.startswith(relative_path_prefix))
            deleted = query.delete(synchronize_session=False)
            session.commit()
            return int(deleted or 0)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_tasks(self) -> List[Dict[str, Any]]:
        if self.use_db:
            session: Session = self.SessionLocal()
            try:
                tasks = session.query(TaskModel).order_by(TaskModel.created_at.desc()).all()
                return [task.to_dict() for task in tasks]
            finally:
                session.close()
        else:
            all_tasks = self._memory_db.values()
            return [self._deserialize_task(t) for t in all_tasks]

    def list_library_documents(self) -> List[Dict[str, Any]]:
        """Return the editorial document view used by the library and Git publisher."""
        return [
            task
            for task in self.list_tasks()
            if task.get("library_visible", True) is not False
            and (
                str(task.get("source_type") or "") == "manual"
                or bool(str(task.get("summary") or "").strip())
                or bool(str(task.get("transcript") or "").strip())
            )
        ]

    def delete_task(self, task_id: str):
        if self.use_db:
            session: Session = self.SessionLocal()
            try:
                task = session.query(TaskModel).filter(TaskModel.id == task_id).first()
                if task:
                    session.delete(task)
                    session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to delete task from database: {e}")
            finally:
                session.close()
        else:
            if task_id in self._memory_db:
                del self._memory_db[task_id]
                self._save_to_file()

    def update_task(self, task_id: str, updates: Dict[str, Any]):
        task = self.get_task(task_id)
        if task:
            task.update(updates)
            # 进度更新频繁，不纳入“最新修改时间”；其他字段更新都视为一次修改。
            if any(key != "progress" for key in updates.keys()):
                task["latest_modified_at"] = datetime.utcnow()
            self.save_task(task_id, task)
            return task
        return None

    def recover_interrupted_tasks(self) -> int:
        """
        启动恢复：将上次异常中断遗留在中间态的任务标记为 FAILED。
        返回变更数量。
        """
        interrupted_statuses = {
            TaskStatus.DOWNLOADING.value,
            TaskStatus.UPLOADING.value,
            TaskStatus.TRANSCRIBING.value,
            TaskStatus.SUMMARIZING.value,
        }
        recover_msg = "服务重启导致任务中断，请重试（可使用重新转录/重新总结）。"

        updated = 0
        for task in self.list_tasks():
            status = str(task.get("status") or "").upper()
            if status in interrupted_statuses:
                self.update_task(
                    task["id"],
                    {
                        "status": TaskStatus.FAILED,
                        "error_message": recover_msg,
                    },
                )
                updated += 1

        return updated

    # ── Folder CRUD ──

    def create_folder(self, folder_data: Dict[str, Any]) -> Dict[str, Any]:
        session: Session = self.SessionLocal()
        try:
            folder = FolderModel(**folder_data)
            session.add(folder)
            session.commit()
            session.refresh(folder)
            return folder.to_dict()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create folder: {e}")
            raise
        finally:
            session.close()

    def get_folder(self, folder_id: str) -> Optional[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            folder = session.query(FolderModel).filter(FolderModel.id == folder_id).first()
            return folder.to_dict() if folder else None
        finally:
            session.close()

    def list_folders(self) -> List[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            folders = session.query(FolderModel).order_by(FolderModel.sort_order, FolderModel.created_at).all()
            return [f.to_dict() for f in folders]
        finally:
            session.close()

    def ensure_folder_path(
        self,
        names: List[str],
        *,
        folder_type: str = "auto",
        source_url: str | None = None,
    ) -> Optional[str]:
        """Return the leaf folder id, creating only missing path components."""
        clean_names = [str(name or "").strip() for name in names if str(name or "").strip()]
        if not clean_names:
            return None

        session: Session = self.SessionLocal()
        try:
            parent_id: str | None = None
            for index, name in enumerate(clean_names):
                query = session.query(FolderModel).filter(FolderModel.name == name)
                if parent_id is None:
                    query = query.filter(FolderModel.parent_id.is_(None))
                else:
                    query = query.filter(FolderModel.parent_id == parent_id)
                folder = query.order_by(FolderModel.created_at.asc()).first()
                if not folder:
                    folder = FolderModel(
                        id=uuid.uuid4().hex,
                        name=name,
                        parent_id=parent_id,
                        folder_type=folder_type,
                        source_video_url=source_url if index == len(clean_names) - 1 else None,
                        sort_order=0,
                    )
                    session.add(folder)
                    session.flush()
                parent_id = folder.id
            session.commit()
            return parent_id
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to ensure folder path: {e}")
            raise
        finally:
            session.close()

    def ensure_child_folder(
        self,
        parent_id: str,
        name: str,
        *,
        folder_type: str = "auto",
        source_url: str | None = None,
        sort_order: int = 0,
    ) -> str:
        """Return a stable child folder without rebuilding the parent's full path."""
        clean_parent_id = str(parent_id or "").strip()
        clean_name = str(name or "").strip()
        if not clean_parent_id or not clean_name:
            raise ValueError("子目录必须包含父目录和名称")

        session: Session = self.SessionLocal()
        try:
            parent = session.query(FolderModel).filter(FolderModel.id == clean_parent_id).first()
            if not parent:
                raise ValueError("父目录不存在")
            folder = (
                session.query(FolderModel)
                .filter(
                    FolderModel.parent_id == clean_parent_id,
                    FolderModel.name == clean_name,
                )
                .order_by(FolderModel.created_at.asc())
                .first()
            )
            if not folder:
                folder = FolderModel(
                    id=uuid.uuid4().hex,
                    name=clean_name,
                    parent_id=clean_parent_id,
                    folder_type=folder_type,
                    source_video_url=source_url,
                    sort_order=sort_order,
                )
                session.add(folder)
            elif folder.folder_type == "auto":
                folder.sort_order = sort_order
                if source_url:
                    folder.source_video_url = source_url
            session.commit()
            session.refresh(folder)
            return str(folder.id)
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to ensure child folder: {e}")
            raise
        finally:
            session.close()

    def update_folder(self, folder_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            folder = session.query(FolderModel).filter(FolderModel.id == folder_id).first()
            if not folder:
                return None
            for key, value in updates.items():
                setattr(folder, key, value)
            session.commit()
            session.refresh(folder)
            return folder.to_dict()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update folder: {e}")
            raise
        finally:
            session.close()

    def folder_move_would_create_cycle(self, folder_id: str, parent_id: Optional[str]) -> bool:
        if not parent_id:
            return False
        if folder_id == parent_id:
            return True

        folders = {folder["id"]: folder for folder in self.list_folders()}
        cursor = parent_id
        visited: set[str] = set()
        while cursor:
            if cursor == folder_id:
                return True
            if cursor in visited:
                return True
            visited.add(cursor)
            parent = folders.get(cursor)
            cursor = str(parent.get("parent_id") or "") if parent else ""
        return False

    def delete_folder(self, folder_id: str) -> None:
        session: Session = self.SessionLocal()
        try:
            # Move sub-folders up to parent level
            folder = session.query(FolderModel).filter(FolderModel.id == folder_id).first()
            parent_id = folder.parent_id if folder else None
            session.query(FolderModel).filter(FolderModel.parent_id == folder_id).update({"parent_id": parent_id})
            # Unassign all tasks in this folder
            session.query(TaskModel).filter(TaskModel.folder_id == folder_id).update({"folder_id": None})
            # Delete the folder
            session.delete(folder)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete folder: {e}")
            raise
        finally:
            session.close()

    def assign_task_to_folder(self, task_id: str, folder_id: Optional[str]) -> None:
        session: Session = self.SessionLocal()
        try:
            task = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            if task:
                task.folder_id = folder_id
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to assign task to folder: {e}")
            raise
        finally:
            session.close()

    def list_tasks_in_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            tasks = session.query(TaskModel).filter(TaskModel.folder_id == folder_id).order_by(TaskModel.created_at.desc()).all()
            return [t.to_dict() for t in tasks]
        finally:
            session.close()

    # ── Collection jobs ──

    def _collection_counts_from_items(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(items)
        completed = 0
        failed = 0
        running = 0
        linked = 0
        running_statuses = {
            TaskStatus.DOWNLOADING.value,
            TaskStatus.UPLOADING.value,
            TaskStatus.TRANSCRIBING.value,
            TaskStatus.SUMMARIZING.value,
        }

        for item in items:
            task = item.get("task") or {}
            status = str(task.get("status") or "PENDING")
            if item.get("task_id") or task:
                linked += 1
            if status == TaskStatus.COMPLETED.value:
                completed += 1
            elif status == TaskStatus.FAILED.value:
                failed += 1
            elif status in running_statuses:
                running += 1

        if total > 0 and completed == total:
            status = "COMPLETED"
        elif total > 0 and failed > 0 and completed + failed == total:
            status = "FAILED"
        elif running > 0 or linked > 0:
            status = "RUNNING"
        else:
            status = "PENDING"

        return {
            "status": status,
            "total_items": total,
            "completed_items": completed,
            "failed_items": failed,
            "running_items": running,
        }

    def _collection_item_to_dict(self, session: Session, item: CollectionItemModel) -> Dict[str, Any]:
        data = item.to_dict()
        task = None
        if item.task_id:
            task_model = session.query(TaskModel).filter(TaskModel.id == item.task_id).first()
            task = task_model.to_dict() if task_model else None
        data["task"] = task
        data["status"] = str((task or {}).get("status") or "PENDING")
        return data

    def create_collection_job(self, job_data: Dict[str, Any], items_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        session: Session = self.SessionLocal()
        try:
            job_payload = dict(job_data)
            job_payload["total_items"] = len(items_data)
            job_payload.setdefault("completed_items", 0)
            job_payload.setdefault("failed_items", 0)
            job_payload.setdefault("status", "PENDING")
            job = CollectionJobModel(**job_payload)
            session.add(job)
            for index, item_data in enumerate(items_data):
                item_payload = dict(item_data)
                item_payload.setdefault("job_id", job.id)
                item_payload.setdefault("sort_order", index)
                session.add(CollectionItemModel(**item_payload))
            session.commit()
            return self.get_collection_job(job.id, include_items=True) or job.to_dict()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create collection job: {e}")
            raise
        finally:
            session.close()

    def get_collection_job(self, job_id: str, include_items: bool = False) -> Optional[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            job = session.query(CollectionJobModel).filter(CollectionJobModel.id == job_id).first()
            if not job:
                return None
            data = job.to_dict()
            item_models = (
                session.query(CollectionItemModel)
                .filter(CollectionItemModel.job_id == job_id)
                .order_by(CollectionItemModel.sort_order, CollectionItemModel.created_at)
                .all()
            )
            items = [self._collection_item_to_dict(session, item) for item in item_models]
            data.update(self._collection_counts_from_items(items))
            if include_items:
                data["items"] = items
            return data
        finally:
            session.close()

    def list_collection_jobs(self, include_items: bool = False) -> List[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            jobs = session.query(CollectionJobModel).order_by(CollectionJobModel.created_at.desc()).all()
            result = []
            for job in jobs:
                data = job.to_dict()
                item_models = (
                    session.query(CollectionItemModel)
                    .filter(CollectionItemModel.job_id == job.id)
                    .order_by(CollectionItemModel.sort_order, CollectionItemModel.created_at)
                    .all()
                )
                items = [self._collection_item_to_dict(session, item) for item in item_models]
                data.update(self._collection_counts_from_items(items))
                if include_items:
                    data["items"] = items
                result.append(data)
            return result
        finally:
            session.close()

    def list_collection_items(self, job_id: str) -> List[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            items = (
                session.query(CollectionItemModel)
                .filter(CollectionItemModel.job_id == job_id)
                .order_by(CollectionItemModel.sort_order, CollectionItemModel.created_at)
                .all()
            )
            return [self._collection_item_to_dict(session, item) for item in items]
        finally:
            session.close()

    def link_collection_item_task(self, item_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            item = session.query(CollectionItemModel).filter(CollectionItemModel.id == item_id).first()
            if not item:
                return None
            item.task_id = task_id
            item.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(item)
            return self._collection_item_to_dict(session, item)
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to link collection item task: {e}")
            raise
        finally:
            session.close()

    def update_collection_job(self, job_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            job = session.query(CollectionJobModel).filter(CollectionJobModel.id == job_id).first()
            if not job:
                return None
            for key, value in updates.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            job.updated_at = datetime.utcnow()
            session.commit()
            return self.get_collection_job(job_id, include_items=True)
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update collection job: {e}")
            raise
        finally:
            session.close()

    # ── Content subscriptions ──

    def create_content_subscription(self, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.use_db:
            raise RuntimeError("Content subscriptions require database storage")

        session: Session = self.SessionLocal()
        try:
            existing = (
                session.query(ContentSubscriptionModel)
                .filter(
                    ContentSubscriptionModel.user_id == subscription_data["user_id"],
                    ContentSubscriptionModel.provider == subscription_data["provider"],
                    ContentSubscriptionModel.source_type == subscription_data["source_type"],
                    ContentSubscriptionModel.external_source_id == subscription_data["external_source_id"],
                )
                .first()
            )
            if existing and existing.deleted_at is None:
                raise ValueError("该内容来源已经订阅")

            now = datetime.utcnow()
            if existing:
                for key, value in subscription_data.items():
                    if key != "id" and hasattr(existing, key):
                        setattr(existing, key, value)
                existing.deleted_at = None
                existing.status = "ACTIVE"
                existing.last_error = None
                existing.consecutive_failures = 0
                existing.next_poll_at = subscription_data.get("next_poll_at") or now
                existing.updated_at = now
                subscription = existing
            else:
                payload = dict(subscription_data)
                payload.setdefault("id", uuid.uuid4().hex)
                payload.setdefault("status", "ACTIVE")
                payload.setdefault("next_poll_at", now)
                payload.setdefault("created_at", now)
                payload.setdefault("updated_at", now)
                subscription = ContentSubscriptionModel(**payload)
                session.add(subscription)

            session.commit()
            session.refresh(subscription)
            return subscription.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_content_subscription(
        self,
        subscription_id: str,
        *,
        user_id: str | None = None,
        include_deleted: bool = False,
    ) -> Optional[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            query = session.query(ContentSubscriptionModel).filter(ContentSubscriptionModel.id == subscription_id)
            if user_id is not None:
                query = query.filter(ContentSubscriptionModel.user_id == user_id)
            if not include_deleted:
                query = query.filter(ContentSubscriptionModel.deleted_at.is_(None))
            subscription = query.first()
            return subscription.to_dict() if subscription else None
        finally:
            session.close()

    def list_content_subscriptions(self, user_id: str) -> List[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            subscriptions = (
                session.query(ContentSubscriptionModel)
                .filter(
                    ContentSubscriptionModel.user_id == user_id,
                    ContentSubscriptionModel.deleted_at.is_(None),
                )
                .order_by(ContentSubscriptionModel.created_at.asc())
                .all()
            )
            return [subscription.to_dict() for subscription in subscriptions]
        finally:
            session.close()

    def update_content_subscription(
        self,
        subscription_id: str,
        updates: Dict[str, Any],
        *,
        user_id: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            query = session.query(ContentSubscriptionModel).filter(
                ContentSubscriptionModel.id == subscription_id,
                ContentSubscriptionModel.deleted_at.is_(None),
            )
            if user_id is not None:
                query = query.filter(ContentSubscriptionModel.user_id == user_id)
            subscription = query.first()
            if not subscription:
                return None
            protected = {"id", "user_id", "provider", "source_type", "external_source_id", "created_at"}
            for key, value in updates.items():
                if key not in protected and hasattr(subscription, key):
                    setattr(subscription, key, value)
            subscription.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(subscription)
            return subscription.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def cancel_content_subscription(self, subscription_id: str, user_id: str) -> bool:
        session: Session = self.SessionLocal()
        try:
            subscription = (
                session.query(ContentSubscriptionModel)
                .filter(
                    ContentSubscriptionModel.id == subscription_id,
                    ContentSubscriptionModel.user_id == user_id,
                    ContentSubscriptionModel.deleted_at.is_(None),
                )
                .first()
            )
            if not subscription:
                return False
            now = datetime.utcnow()
            subscription.status = "PAUSED"
            subscription.deleted_at = now
            subscription.next_poll_at = None
            subscription.lease_owner = None
            subscription.lease_expires_at = None
            subscription.updated_at = now
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_subscription_item(
        self,
        subscription_id: str,
        external_item_id: str,
    ) -> Optional[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            item = (
                session.query(SubscriptionItemModel)
                .filter(
                    SubscriptionItemModel.subscription_id == subscription_id,
                    SubscriptionItemModel.external_item_id == external_item_id,
                )
                .first()
            )
            return item.to_dict() if item else None
        finally:
            session.close()

    def upsert_subscription_item(
        self,
        subscription_id: str,
        item_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        session: Session = self.SessionLocal()
        try:
            item = (
                session.query(SubscriptionItemModel)
                .filter(
                    SubscriptionItemModel.subscription_id == subscription_id,
                    SubscriptionItemModel.external_item_id == item_data["external_item_id"],
                )
                .first()
            )
            now = datetime.utcnow()
            created = item is None
            previous_hash = item.content_hash if item else None
            previous_status = item.capture_status if item else None
            payload = dict(item_data)
            if isinstance(payload.get("image_manifest"), (list, dict)):
                payload["image_manifest"] = json.dumps(payload["image_manifest"], ensure_ascii=False)
            if isinstance(payload.get("source_meta"), (list, dict)):
                payload["source_meta"] = json.dumps(payload["source_meta"], ensure_ascii=False)

            if item:
                for key, value in payload.items():
                    if key not in {"id", "subscription_id", "first_seen_at", "created_at"} and hasattr(item, key):
                        setattr(item, key, value)
                item.last_seen_at = now
                item.updated_at = now
            else:
                payload.setdefault("id", uuid.uuid4().hex)
                payload["subscription_id"] = subscription_id
                payload.setdefault("first_seen_at", now)
                payload.setdefault("last_seen_at", now)
                payload.setdefault("created_at", now)
                payload.setdefault("updated_at", now)
                item = SubscriptionItemModel(**payload)
                session.add(item)

            session.commit()
            session.refresh(item)
            changed = created or previous_hash != item.content_hash or previous_status != item.capture_status
            return {"item": item.to_dict(), "created": created, "changed": changed}
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_subscription_items(
        self,
        subscription_id: str,
        *,
        digest_date: str | None = None,
        limit: int | None = None,
    ) -> List[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            query = session.query(SubscriptionItemModel).filter(
                SubscriptionItemModel.subscription_id == subscription_id
            )
            if digest_date is not None:
                query = query.filter(SubscriptionItemModel.digest_date == digest_date)
            query = query.order_by(SubscriptionItemModel.published_at.asc(), SubscriptionItemModel.external_item_id.asc())
            if limit is not None:
                query = query.limit(max(1, int(limit)))
            return [item.to_dict() for item in query.all()]
        finally:
            session.close()

    def count_subscription_items(
        self,
        subscription_id: str,
        *,
        digest_date: str | None = None,
        capture_statuses: List[str] | None = None,
    ) -> int:
        session: Session = self.SessionLocal()
        try:
            query = session.query(SubscriptionItemModel).filter(
                SubscriptionItemModel.subscription_id == subscription_id
            )
            if digest_date is not None:
                query = query.filter(SubscriptionItemModel.digest_date == digest_date)
            if capture_statuses:
                query = query.filter(SubscriptionItemModel.capture_status.in_(capture_statuses))
            return int(query.count())
        finally:
            session.close()

    def mark_subscription_items_digested(
        self,
        subscription_id: str,
        digest_date: str,
        task_id: str,
    ) -> None:
        session: Session = self.SessionLocal()
        try:
            session.query(SubscriptionItemModel).filter(
                SubscriptionItemModel.subscription_id == subscription_id,
                SubscriptionItemModel.digest_date == digest_date,
                SubscriptionItemModel.capture_status.in_(["CAPTURED", "CAPTURED_UPDATED"]),
            ).update({"digest_task_id": task_id}, synchronize_session=False)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_subscription_run(
        self,
        subscription_id: str,
        trigger: str,
        *,
        cursor_before: str | None = None,
    ) -> Dict[str, Any]:
        session: Session = self.SessionLocal()
        try:
            run = SubscriptionRunModel(
                id=uuid.uuid4().hex,
                subscription_id=subscription_id,
                trigger=trigger,
                status="RUNNING",
                cursor_before=cursor_before,
                started_at=datetime.utcnow(),
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return run.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_subscription_run(self, run_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            run = session.query(SubscriptionRunModel).filter(SubscriptionRunModel.id == run_id).first()
            if not run:
                return None
            for key, value in updates.items():
                if key != "id" and hasattr(run, key):
                    setattr(run, key, value)
            session.commit()
            session.refresh(run)
            return run.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_subscription_runs(self, subscription_id: str, *, limit: int = 30) -> List[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            runs = (
                session.query(SubscriptionRunModel)
                .filter(SubscriptionRunModel.subscription_id == subscription_id)
                .order_by(SubscriptionRunModel.started_at.desc())
                .limit(max(1, min(int(limit), 100)))
                .all()
            )
            return [run.to_dict() for run in runs]
        finally:
            session.close()

    def claim_due_content_subscriptions(
        self,
        owner: str,
        now: datetime,
        *,
        lease_seconds: int = 300,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        session: Session = self.SessionLocal()
        try:
            candidates = (
                session.query(ContentSubscriptionModel.id)
                .filter(
                    ContentSubscriptionModel.deleted_at.is_(None),
                    ContentSubscriptionModel.status.in_(["ACTIVE", "DEGRADED", "ERROR"]),
                    ContentSubscriptionModel.next_poll_at.is_not(None),
                    ContentSubscriptionModel.next_poll_at <= now,
                    or_(
                        ContentSubscriptionModel.lease_expires_at.is_(None),
                        ContentSubscriptionModel.lease_expires_at <= now,
                    ),
                )
                .order_by(ContentSubscriptionModel.next_poll_at.asc())
                .limit(max(1, int(limit)))
                .all()
            )
            lease_until = now + timedelta(seconds=max(30, lease_seconds))
            claimed_ids: list[str] = []
            for (subscription_id,) in candidates:
                updated = (
                    session.query(ContentSubscriptionModel)
                    .filter(
                        ContentSubscriptionModel.id == subscription_id,
                        ContentSubscriptionModel.deleted_at.is_(None),
                        ContentSubscriptionModel.status.in_(["ACTIVE", "DEGRADED", "ERROR"]),
                        ContentSubscriptionModel.next_poll_at <= now,
                        or_(
                            ContentSubscriptionModel.lease_expires_at.is_(None),
                            ContentSubscriptionModel.lease_expires_at <= now,
                        ),
                    )
                    .update(
                        {"lease_owner": owner, "lease_expires_at": lease_until},
                        synchronize_session=False,
                    )
                )
                if updated:
                    claimed_ids.append(subscription_id)
            session.commit()
            return [
                item
                for subscription_id in claimed_ids
                if (item := self.get_content_subscription(subscription_id)) is not None
            ]
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def release_content_subscription_lease(self, subscription_id: str, owner: str) -> None:
        session: Session = self.SessionLocal()
        try:
            session.query(ContentSubscriptionModel).filter(
                ContentSubscriptionModel.id == subscription_id,
                ContentSubscriptionModel.lease_owner == owner,
            ).update(
                {"lease_owner": None, "lease_expires_at": None},
                synchronize_session=False,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ── Connected account credential CRUD ──

    def upsert_connected_account(
        self,
        *,
        user_id: str,
        account_id: str | None = None,
        provider: str,
        credential_type: str,
        secret_payload: Dict[str, Any],
        display_name: str | None = None,
        domain_scope: str | None = None,
    ) -> Dict[str, Any]:
        if not self.use_db:
            raise RuntimeError("Connected accounts require database storage")

        now = datetime.utcnow()
        session: Session = self.SessionLocal()
        try:
            if account_id:
                account = (
                    session.query(ConnectedAccountModel)
                    .filter(
                        ConnectedAccountModel.id == account_id,
                        ConnectedAccountModel.user_id == user_id,
                        ConnectedAccountModel.provider == provider,
                        ConnectedAccountModel.status != "revoked",
                    )
                    .first()
                )
            else:
                account = (
                    session.query(ConnectedAccountModel)
                    .filter(
                        ConnectedAccountModel.user_id == user_id,
                        ConnectedAccountModel.provider == provider,
                        ConnectedAccountModel.credential_type == credential_type,
                        ConnectedAccountModel.domain_scope == domain_scope,
                        ConnectedAccountModel.status != "revoked",
                    )
                    .first()
                )
            encrypted_payload = _encrypt_secret_payload(secret_payload)
            secret_masked = _mask_secret_payload(secret_payload)

            if account:
                secret = session.query(CredentialSecretModel).filter(CredentialSecretModel.id == account.secret_id).first()
                if not secret:
                    secret = CredentialSecretModel(id=uuid.uuid4().hex, encrypted_payload=encrypted_payload)
                    session.add(secret)
                    account.secret_id = secret.id
                else:
                    secret.encrypted_payload = encrypted_payload
                    secret.updated_at = now
                account.display_name = display_name or account.display_name
                account.credential_type = credential_type
                account.domain_scope = domain_scope
                account.secret_masked = secret_masked
                account.status = "connected"
                account.last_error = None
                account.updated_at = now
            else:
                secret = CredentialSecretModel(id=uuid.uuid4().hex, encrypted_payload=encrypted_payload)
                account = ConnectedAccountModel(
                    id=uuid.uuid4().hex,
                    user_id=user_id,
                    provider=provider,
                    display_name=display_name,
                    credential_type=credential_type,
                    secret_id=secret.id,
                    secret_masked=secret_masked,
                    domain_scope=domain_scope,
                    status="connected",
                    created_at=now,
                    updated_at=now,
                )
                session.add(secret)
                session.add(account)

            session.commit()
            session.refresh(account)
            return account.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_connected_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        if not self.use_db:
            return []

        session: Session = self.SessionLocal()
        try:
            accounts = (
                session.query(ConnectedAccountModel)
                .filter(
                    ConnectedAccountModel.user_id == user_id,
                    ConnectedAccountModel.status != "revoked",
                )
                .order_by(ConnectedAccountModel.created_at.asc())
                .all()
            )
            return [account.to_dict() for account in accounts]
        finally:
            session.close()

    def get_connected_account_by_provider(self, user_id: str, provider: str) -> Optional[Dict[str, Any]]:
        if not self.use_db:
            return None

        session: Session = self.SessionLocal()
        try:
            account = (
                session.query(ConnectedAccountModel)
                .filter(
                    ConnectedAccountModel.user_id == user_id,
                    ConnectedAccountModel.provider == provider,
                    ConnectedAccountModel.status != "revoked",
                )
                .order_by(ConnectedAccountModel.updated_at.desc())
                .first()
            )
            return account.to_dict() if account else None
        finally:
            session.close()

    def get_connected_account_secret(self, user_id: str, account_id: str) -> Optional[Dict[str, Any]]:
        if not self.use_db:
            return None

        session: Session = self.SessionLocal()
        try:
            account = (
                session.query(ConnectedAccountModel)
                .filter(
                    ConnectedAccountModel.id == account_id,
                    ConnectedAccountModel.user_id == user_id,
                    ConnectedAccountModel.status != "revoked",
                )
                .first()
            )
            if not account:
                return None
            secret = session.query(CredentialSecretModel).filter(CredentialSecretModel.id == account.secret_id).first()
            if not secret:
                return None
            return _decrypt_secret_payload(secret.encrypted_payload)
        finally:
            session.close()

    def delete_connected_account(self, user_id: str, account_id: str) -> bool:
        if not self.use_db:
            return False

        session: Session = self.SessionLocal()
        try:
            account = (
                session.query(ConnectedAccountModel)
                .filter(
                    ConnectedAccountModel.id == account_id,
                    ConnectedAccountModel.user_id == user_id,
                )
                .first()
            )
            if not account:
                return False
            secret = session.query(CredentialSecretModel).filter(CredentialSecretModel.id == account.secret_id).first()
            if secret:
                session.delete(secret)
            session.delete(account)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_connected_account_runtime(
        self,
        user_id: str,
        account_id: str,
        *,
        status: Optional[str] = None,
        last_error: Optional[str] = None,
        verified: bool = False,
        used: bool = False,
    ) -> Optional[Dict[str, Any]]:
        if not self.use_db:
            return None

        session: Session = self.SessionLocal()
        try:
            account = (
                session.query(ConnectedAccountModel)
                .filter(
                    ConnectedAccountModel.id == account_id,
                    ConnectedAccountModel.user_id == user_id,
                )
                .first()
            )
            if not account:
                return None
            now = datetime.utcnow()
            if status is not None:
                account.status = status
            account.last_error = last_error
            if verified:
                account.last_verified_at = now
            if used:
                account.last_used_at = now
            account.updated_at = now
            session.commit()
            session.refresh(account)
            return account.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

# Global instance
db = TaskDB(
    file_path=config.database.json_file_path,
    sqlite_path=config.database.sqlite_path,
    database_url=config.database.url,
)
