import asyncio
import os
import sys
import webbrowser
import uvicorn
import socket
from multiprocessing import Process
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from zeroconf import ServiceInfo, Zeroconf

# 将项目根目录添加到 Python 路径
path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, path)

from src.main.python.sheng_wen.transcriber.transcriber import get_transcriber
from src.main.python.sheng_wen.llm.llm import get_llm
from src.main.python.sheng_wen.transcriber.transcriber_worker import TranscriberWorker
from src.main.python.sheng_wen.llm.llm_worker import LLMWorker
from src.main.python.sheng_wen.downloader.video_downloader_worker import VideoDownloaderWorker
from src.main.python.sheng_wen.downloader.file_upload_worker import FileUploadWorker
from src.main.python.sheng_wen.utils.logger import logger
from src.main.python.sheng_wen.db import TaskStatus
from src.main.python.sheng_wen.worker_manager import WorkerManager
from src.main.python.sheng_wen.version import APP_VERSION
import src.main.python.sheng_wen.api as api_module
from src.main.python.sheng_wen.config.settings import config
from datetime import datetime
import uuid

g_worker_manager = None
g_zeroconf = None
g_mdns_info = None


def get_local_ip():
    """获取本机局域网 IP 地址"""
    try:
        # 创建一个 UDP socket 连接到公共 DNS 服务器
        # 这不会实际发送数据，只是用于获取本机 IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        # 如果获取失败，返回 0.0.0.0
        return "0.0.0.0"


def log_access_tips(port: int):
    """输出服务访问提示（本机 + 局域网）"""
    local_ip = get_local_ip()
    logger.info("============================================================")
    logger.info("服务启动完成，可通过浏览器访问：")
    logger.info(f"  本机可通过浏览器访问 http://localhost:{port}/")
    if local_ip != "0.0.0.0":
        logger.info(f"  其它设备可通过浏览器访问 http://{local_ip}:{port}/")
    else:
        logger.info(f"  其它设备可通过浏览器访问 http://<本机局域网IP>:{port}/")
    logger.info("============================================================")


def register_mdns_service(host: str, port: int):
    """注册 mDNS 服务"""
    global g_zeroconf, g_mdns_info
    try:
        g_zeroconf = Zeroconf()
        
        # 创建服务信息
        g_mdns_info = ServiceInfo(
            "_http._tcp.local.",
            "ShengWen._http._tcp.local.",
            addresses=[socket.inet_aton(host)],
            port=port,
            properties={
                b"path": b"/",
                b"description": b"ShengWen - Video Transcription Service",
            },
        )
        
        g_zeroconf.register_service(g_mdns_info)
        logger.info(f"--- [mDNS] 服务已注册: ShengWen.local -> http://{host}:{port} ---")
        logger.info(f"--- [mDNS] 局域网设备可通过 'http://ShengWen.local:{port}' 访问 ---")
    except Exception as e:
        logger.warning(f"--- [mDNS] 服务注册失败: {e} ---")
        logger.warning(f"--- [mDNS] 请确保已安装 Bonjour 服务 (Windows/macOS) 或 avahi-daemon (Linux) ---")


def unregister_mdns_service():
    """注销 mDNS 服务"""
    global g_zeroconf, g_mdns_info
    if g_zeroconf:
        try:
            g_zeroconf.unregister_service(g_mdns_info)
            g_zeroconf.close()
            logger.info("--- [mDNS] 服务已注销 ---")
        except Exception as e:
            logger.warning(f"--- [mDNS] 服务注销失败: {e} ---")
        finally:
            g_zeroconf = None
            g_mdns_info = None


async def run_sidebar_progress_test():
    """
    一个独立的测试函数，用于验证从后端到前端的进度条更新管道。
    """
    logger.info("--- [ProgressTest] 启动侧边栏进度条功能测试 ---")

    test_task_id = f"test-progress-task-{uuid.uuid4()}"
    logger.info(f"--- [ProgressTest] 创建测试任务: {test_task_id} ---")

    # 1. 在数据库中创建一个假的测试任务
    from src.main.python.sheng_wen.db import db
    from src.main.python.sheng_wen.api import notify_task_update
    
    db.save_task(test_task_id, {
        "id": test_task_id,
        "video_url": "https://www.bilibili.com/video/BV1xt411v7zS/", # 示例 URL
        "status": TaskStatus.DOWNLOADING,
        "created_at": datetime.now(),
        "progress": 0.0,
        "title": "进度条功能测试任务"
    })
    await notify_task_update(test_task_id)
    await asyncio.sleep(1)

    # 2. 模拟进度从 0 到 100
    for i in range(101):
        db.update_task(test_task_id, {"progress": float(i)})
        logger.info(f"[ProgressTest] 更新任务 '{test_task_id}' 进度为 {i}%")
        await notify_task_update(test_task_id)
        await asyncio.sleep(0.1) # 模拟工作间隔

    # 3. 模拟任务完成
    db.update_task(test_task_id, {"status": TaskStatus.COMPLETED, "progress": 100.0})
    await notify_task_update(test_task_id)
    logger.info(f"--- [ProgressTest] 测试任务 {test_task_id} 已完成 ---")
    
    # 4. (可选) 几秒后删除任务
    await asyncio.sleep(10)
    db.delete_task(test_task_id)
    await notify_task_update(test_task_id) # 通知前端删除
    logger.info(f"--- [ProgressTest] 测试任务 {test_task_id} 已删除 ---")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    管理应用的生命周期，在启动时初始化工作单元，在关闭时优雅地停止它们。
    """
    global g_worker_manager

    # 启动恢复：把上次异常中断遗留在中间态的任务回收为 FAILED，避免前端永远卡在“处理中”。
    recovered_count = api_module.db.recover_interrupted_tasks()
    if recovered_count > 0:
        logger.warning(
            f"--- [Lifespan] 检测到 {recovered_count} 个中断任务，已自动标记为 FAILED（可手动重试） ---"
        )

    # 配置转录器：统一来自 JSON 配置 + 运行时设置管理器
    whisper_cfg = config.whisper
    runtime_transcription_state = api_module.transcription_settings_manager.get_runtime_state()
    runtime_device = str(runtime_transcription_state.get("device") or whisper_cfg.device).lower()
    if runtime_device not in {"cpu", "cuda"}:
        runtime_device = whisper_cfg.device

    if whisper_cfg.effective_model_path:
        logger.info(f"--- [Transcriber] 使用本地模型路径: {whisper_cfg.effective_model_path} ---")
        transcriber_config = {"model_size_or_path": whisper_cfg.effective_model_path, "device": runtime_device}
    else:
        logger.info(f"--- [Transcriber] 使用模型大小: {whisper_cfg.model_size} ---")
        logger.info("--- [Transcriber] 未指定本地模型路径，若本地缓存不存在将自动下载（首次可能较慢）---")
        transcriber_config = {"model_size": whisper_cfg.model_size, "device": runtime_device}

    # LLM 配置：统一来自 JSON 配置 + 运行时设置管理器
    llm_config = api_module.llm_provider_manager.get_runtime_config()
    prompt_file = config.app.prompt_file

    logger.info("--- [Lifespan] 正在初始化工作单元 ---")
    try:
        logger.info("--- [Lifespan] 1/5 初始化转录器（此阶段可能触发模型下载）... ---")
        transcriber = get_transcriber("fast_whisper", **transcriber_config)
        logger.info("--- [Lifespan] 1/5 转录器初始化完成 ---")

        logger.info("--- [Lifespan] 2/5 初始化 LLM 客户端... ---")
        llm_client = get_llm(llm_config)
        logger.info("--- [Lifespan] 2/5 LLM 客户端初始化完成 ---")

        logger.info("--- [Lifespan] 3/5 创建 Worker 实例... ---")
        llm_worker = LLMWorker(name="LLMWorker", llm_client=llm_client)
        transcriber_worker = TranscriberWorker(name="TranscriberWorker", transcriber=transcriber, next_worker=llm_worker)
        downloader_worker = VideoDownloaderWorker(
            name="VideoDownloaderWorker",
            next_worker=transcriber_worker,
            summary_worker=llm_worker,
            transcription_settings_manager=api_module.transcription_settings_manager,
        )
        file_upload_worker = FileUploadWorker(name="FileUploadWorker", next_worker=transcriber_worker)
        logger.info("--- [Lifespan] 3/5 Worker 实例创建完成 ---")

        logger.info("--- [Lifespan] 4/5 加载系统提示词并注入依赖... ---")
        llm_worker.load_system_prompt(prompt_file)

        # 依赖注入
        api_module.downloader_worker = downloader_worker
        api_module.file_upload_worker = file_upload_worker
        api_module.llm_worker = llm_worker
        api_module.transcriber_worker = transcriber_worker
        api_module.llm_provider_manager.bind_llm_worker(llm_worker)
        api_module.transcription_settings_manager.bind_transcriber_worker(transcriber_worker)

        workers = [downloader_worker, file_upload_worker, transcriber_worker, llm_worker]
        g_worker_manager = WorkerManager(workers=workers)
        logger.info("--- [Lifespan] 4/5 依赖注入完成 ---")

        logger.info("--- [Lifespan] 5/5 启动后台 Worker 循环... ---")
        g_worker_manager.start_all()

        logger.info("--- [Lifespan] 5/5 后台 Worker 启动完成 ---")
        logger.info("--- [Lifespan] 后台工作单元已就绪 ---")
        log_access_tips(config.app.port)

    except Exception as e:
        logger.error(f"--- [Lifespan] 工作单元启动失败: {e}", exc_info=True)

    # 启动进度条测试（如果已启用）
    if config.app.enable_progress_test:
        asyncio.create_task(run_sidebar_progress_test())

    yield

    # Shutdown logic
    if g_worker_manager:
        logger.info("--- [Lifespan] 正在停止工作单元... ---")
        await g_worker_manager.stop_all()
        logger.info("--- [Lifespan] 所有工作单元已停止 ---")
    
    # 注销 mDNS 服务
    unregister_mdns_service()

# 创建一个带有生命周期管理的新 FastAPI 实例
app = FastAPI(
    lifespan=lifespan,
    title="ShengWen API",
    description="视频转录与 AI 总结服务",
    version=APP_VERSION,
)

# 添加中间件 (这部分不会被 include_router 包含)
cors_cfg = config.cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_cfg.origins_list,
    allow_credentials=cors_cfg.allow_credentials,
    allow_methods=cors_cfg.methods_list,
    allow_headers=cors_cfg.headers_list,
)

# 将原始 api.py 中定义的路由挂载到新实例上
app.include_router(api_module.app.router)

# 重新挂载静态文件目录 (这部分不会被 include_router 包含)
dist_dir = config.app.frontend_dist_dir
assets_dir = os.path.join(dist_dir, "assets")

if os.path.exists(dist_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
else:
    logger.warning(f"前端构建目录未找到: {dist_dir}。将无法提供前端页面。")
    logger.warning("请先在 'frontend' 目录下运行 'npm run build'。")


if __name__ == "__main__":
    app_cfg = config.app

    host = app_cfg.host
    port = app_cfg.port

    logger.info(f"--- 声文智汇 - ShengWen v{APP_VERSION} made By smileFAace@outlook.com ---")
    logger.info(f"--- 启动 FastAPI 服务器于 http://{host}:{port} ---")

    # 注册 mDNS 服务
    if app_cfg.enable_mdns:
        # 获取本机局域网 IP
        local_ip = get_local_ip()
        register_mdns_service(local_ip, port)

    # 确保 uvicorn 运行的是我们新创建的 app 实例
    uvicorn.run(app, host=host, port=port)


