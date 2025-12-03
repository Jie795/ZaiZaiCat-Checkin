"""
Ole 签到主程序
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from api import OleAPI

# 添加项目根目录到Python路径以导入notification模块
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

from notify import send


def load_config():
    """从环境变量或配置文件加载配置"""
    # 优先从环境变量读取配置
    env_config = os.getenv('HUARUNTONG_OLE_CONFIG')
    if env_config:
        try:
            print("从环境变量读取Ole配置")
            config = json.loads(env_config)
            # 如果环境变量是完整的配置对象
            if 'huaruntong' in config:
                return config
            else:
                # 如果环境变量直接是 ole 配置，包装成完整格式
                return {'huaruntong': {'ole': config}}
        except json.JSONDecodeError as e:
            print(f"环境变量配置JSON解析失败: {e}，将尝试从文件读取")
        except Exception as e:
            print(f"读取环境变量配置失败: {e}，将尝试从文件读取")
    
    # 如果环境变量没有配置或解析失败，从文件读取
    # 使用统一的 token.json 配置文件
    # 从当前文件位置向上三级到达项目根目录，然后进入 config 目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, '..', '..', '..', 'config', 'token.json')
    print(f"从配置文件读取: {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def process_account(account_config):
    """处理单个账号的签到"""
    account_name = account_config.get('account_name', '未知账号')

    # 初始化结果
    result_info = {
        'account_name': account_name,
        'device_name': account_config["device_name"],
        'success': False,
        'error': None,
        'message': None
    }

    # 初始化 API
    api = OleAPI(
        session_id=account_config["session_id"],
        device_name=account_config["device_name"],
        unique=account_config["unique"],
        ole_wx_open_id=account_config["ole_wx_open_id"],
        shop_code=account_config["shop_code"],
        city_id=account_config["city_id"],
        user_agent=account_config.get("user_agent")
    )

    print("=" * 50)
    print(f"账号: {account_name} ({account_config['device_name']})")
    print("=" * 50)

    # 执行签到
    print("\n开始签到...")
    result = api.sign_in()

    # 处理签到结果
    if "error" in result:
        error_msg = result['error']
        print(f"❌ 签到失败: {error_msg}")
        result_info['error'] = error_msg
    else:
        print(f"✅ 签到成功!")
        print(f"响应数据: {result}")
        result_info['success'] = True
        result_info['message'] = "签到成功"

    print("\n" + "=" * 50)
    return result_info


def send_notification_summary(all_results, start_time, end_time):
    """
    发送任务执行结果的推送通知

    Args:
        all_results: 所有账号的执行结果列表
        start_time: 任务开始时间
        end_time: 任务结束时间
    """
    try:
        duration = (end_time - start_time).total_seconds()

        # 统计结果
        total_count = len(all_results)
        success_count = sum(1 for r in all_results if r.get('success'))
        failed_count = total_count - success_count

        # 构建通知标题
        if failed_count == 0:
            title = "Ole签到成功 ✅"
        elif success_count == 0:
            title = "Ole签到失败 ❌"
        else:
            title = "Ole签到部分成功 ⚠️"

        # 构建通知内容
        content_parts = [
            "📊 执行统计:",
            f"✅ 成功: {success_count} 个账号",
            f"❌ 失败: {failed_count} 个账号",
            f"📈 总计: {total_count} 个账号",
            "",
            "📝 详情:"
        ]

        for result in all_results:
            account_name = result.get('account_name', '未知账号')
            if result.get('success'):
                content_parts.append(f"  ✅ [{account_name}] 签到成功")
            else:
                error = result.get('error', '未知错误')
                if len(error) > 30:
                    error = error[:30] + "..."
                content_parts.append(f"  ❌ [{account_name}] {error}")

        content_parts.append("")
        content_parts.append(f"⏱️ 执行耗时: {int(duration)}秒")
        content_parts.append(f"🕐 完成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        content = "\n".join(content_parts)

        # 发送通知
        send(title, content)
        print("✅ 推送通知发送成功")

    except Exception as e:
        print(f"❌ 推送通知失败: {str(e)}")


def main():
    """主函数"""
    # 记录开始时间
    start_time = datetime.now()
    print(f"\n{'='*60}")
    print(f"## Ole签到任务开始")
    print(f"## 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # 加载配置
    config = load_config()
    accounts = config.get('huaruntong', {}).get('ole', {}).get('accounts', [])

    if not accounts:
        print("❌ 配置文件中没有找到账号信息")
        return

    # 收集所有账号的结果
    all_results = []

    # 遍历所有账号
    for account in accounts:
        if not account.get('session_id'):
            print(f"⚠️  跳过账号 {account.get('account_name', '未知')}: session_id 为空")
            print("=" * 50)
            all_results.append({
                'account_name': account.get('account_name', '未知'),
                'success': False,
                'error': 'session_id为空'
            })
            continue

        result = process_account(account)
        all_results.append(result)
        print("\n")

    # 记录结束时间
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n{'='*60}")
    print(f"## Ole签到任务完成")
    print(f"## 结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"## 执行耗时: {int(duration)} 秒")
    print(f"{'='*60}\n")

    # 发送推送通知
    send_notification_summary(all_results, start_time, end_time)


if __name__ == "__main__":
    main()
