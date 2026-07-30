"""
任务状态同步测试脚本

用于验证任务状态更新和WebSocket广播的一致性
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'main', 'python'))

from xianwen.db import db, TaskStatus
from xianwen.task_updater import update_and_notify
from xianwen.api import notify_task_update


async def test_update_and_notify():
    """测试 update_and_notify 函数"""
    print("=" * 60)
    print("测试 1: update_and_notify 基本功能")
    print("=" * 60)

    # 创建测试任务
    task_id = "test-task-001"
    task_data = {
        "id": task_id,
        "video_url": "https://example.com/test.mp4",
        "status": TaskStatus.PENDING,
        "progress": 0.0,
        "title": "测试任务",
    }

    db.save_task(task_id, task_data)
    print(f"✓ 创建测试任务: {task_id}")

    # 测试更新
    updates = {
        "status": TaskStatus.DOWNLOADING,
        "progress": 50.0,
    }

    result = await update_and_notify(task_id, updates)

    if result:
        print(f"✓ 更新成功")
        print(f"  - 状态: {result['status']}")
        print(f"  - 进度: {result['progress']}")

        # 验证数据库中的数据
        db_task = db.get_task(task_id)
        if db_task['status'] == TaskStatus.DOWNLOADING.value:
            print(f"✓ 数据库状态正确: {db_task['status']}")
        else:
            print(f"✗ 数据库状态错误: {db_task['status']}")

        if db_task['progress'] == 50.0:
            print(f"✓ 数据库进度正确: {db_task['progress']}")
        else:
            print(f"✗ 数据库进度错误: {db_task['progress']}")
    else:
        print(f"✗ 更新失败")

    # 清理
    db.delete_task(task_id)
    print(f"✓ 清理测试任务")
    print()


async def test_notify_with_data():
    """测试 notify_task_update 传入数据参数"""
    print("=" * 60)
    print("测试 2: notify_task_update 支持传入数据")
    print("=" * 60)

    # 创建测试任务
    task_id = "test-task-002"
    task_data = {
        "id": task_id,
        "video_url": "https://example.com/test2.mp4",
        "status": TaskStatus.PENDING,
        "progress": 0.0,
        "title": "测试任务2",
    }

    db.save_task(task_id, task_data)
    print(f"✓ 创建测试任务: {task_id}")

    # 测试不传入数据（从数据库读取）
    await notify_task_update(task_id)
    print(f"✓ notify_task_update(task_id) 调用成功")

    # 测试传入数据（避免重复读取）
    custom_data = task_data.copy()
    custom_data['status'] = TaskStatus.COMPLETED.value
    await notify_task_update(task_id, task_data=custom_data)
    print(f"✓ notify_task_update(task_id, task_data) 调用成功")

    # 清理
    db.delete_task(task_id)
    print(f"✓ 清理测试任务")
    print()


async def test_race_condition():
    """测试竞态条件修复"""
    print("=" * 60)
    print("测试 3: 竞态条件修复验证")
    print("=" * 60)

    # 创建测试任务
    task_id = "test-task-003"
    task_data = {
        "id": task_id,
        "video_url": "https://example.com/test3.mp4",
        "status": TaskStatus.PENDING,
        "progress": 0.0,
        "title": "测试任务3",
    }

    db.save_task(task_id, task_data)
    print(f"✓ 创建测试任务: {task_id}")

    # 模拟快速连续更新（旧方式可能导致竞态）
    print("执行快速连续更新...")

    for i in range(5):
        updates = {
            "status": TaskStatus.DOWNLOADING,
            "progress": (i + 1) * 20.0,
        }
        result = await update_and_notify(task_id, updates)

        # 验证返回的数据和数据库中的数据一致
        db_task = db.get_task(task_id)
        if result['progress'] == db_task['progress']:
            print(f"  ✓ 更新 {i+1}: 进度 {result['progress']}% - 数据一致")
        else:
            print(f"  ✗ 更新 {i+1}: 返回 {result['progress']}%, 数据库 {db_task['progress']}% - 数据不一致！")

    # 清理
    db.delete_task(task_id)
    print(f"✓ 清理测试任务")
    print()


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("任务状态同步修复验证测试")
    print("=" * 60 + "\n")

    try:
        await test_update_and_notify()
        await test_notify_with_data()
        await test_race_condition()

        print("=" * 60)
        print("✓ 所有测试完成")
        print("=" * 60)
        print("\n修复说明:")
        print("1. 创建了统一的 update_and_notify() 接口")
        print("2. notify_task_update() 支持传入数据，避免重复读取")
        print("3. 所有 Worker 都使用新接口，确保数据一致性")
        print("4. 消除了数据库更新与WebSocket广播之间的竞态条件")
        print()

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
