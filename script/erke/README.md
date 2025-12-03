# 鸿星尔克小程序签到脚本

鸿星尔克小程序的自动签到脚本，支持查询积分明细和自动签到功能。

## 功能特性

- ✅ 查询积分明细
- ✅ 自动签到
- ✅ 多账号支持
- ✅ 推送通知
- ✅ 详细日志输出

## 文件说明

```
erke/
├── __init__.py        # 模块初始化文件
├── api.py             # API接口文件（包含签名计算）
├── main.py            # 主程序文件
└── README.md          # 说明文档
```

## 配置说明

### 配置方式

鸿星尔克脚本支持两种配置方式，**优先使用环境变量**，如果环境变量不存在则从 `config/token.json` 文件读取。

### 1. 环境变量配置（推荐）

在青龙面板或系统环境变量中设置 `ERKE_CONFIG` 环境变量：

```bash
export ERKE_CONFIG='{"erke":{"accounts":[{"account_name":"账号1","member_id":"你的会员ID","enterprise_id":"你的企业ID","unionid":"你的unionid","openid":"你的openid","wx_openid":"你的微信openid","user_agent":"自定义UA（可选）"}]}}'
```

或者直接设置 erke 配置部分：

```bash
export ERKE_CONFIG='{"accounts":[{"account_name":"账号1","member_id":"你的会员ID","enterprise_id":"你的企业ID","unionid":"你的unionid","openid":"你的openid","wx_openid":"你的微信openid","user_agent":"自定义UA（可选）"}]}'
```

**青龙面板配置：**
1. 进入青龙面板 → 环境变量
2. 添加环境变量：
   - 名称：`ERKE_CONFIG`
   - 值：`{"erke":{"accounts":[{"account_name":"账号1","member_id":"你的会员ID","enterprise_id":"你的企业ID","unionid":"你的unionid","openid":"你的openid","wx_openid":"你的微信openid","user_agent":"自定义UA（可选）"}]}}`

### 2. 配置文件方式

编辑项目根目录下的 `/config/token.json` 文件，在 `erke` 节点下添加账号信息：

```json
{
  "erke": {
    "accounts": [ 
      {
        "account_name": "账号1",
        "member_id": "你的会员ID",
        "enterprise_id": "你的企业ID",
        "unionid": "你的unionid",
        "openid": "你的openid",
        "wx_openid": "你的微信openid",
        "user_agent": "自定义UA（可选）"
      }
    ]
  }
}
```

### 参数说明
随便找到一个post请求,查看data请求数据即可

| 参数 | 说明 | 必填 | 示例 |
|------|------|------|------|
| account_name | 账号备注名 | 是 | 账号1 |
| member_id | 会员ID | 是 | 8a80a18b9ac5a7cb019ac87bda88530f |
| enterprise_id | 企业ID | 是 | ff8080817d9fbda8017dc20674f47fb6 |
| unionid | 微信unionid | 是 | o36lGwKt-pV1vjXvzb0eWFV-Mfn4 |
| openid | 小程序openid | 是 | oXpsg5YUJ_MJzH3orkR8zKEF2udw |
| wx_openid | 微信openid | 是 | oUIO7jktQKedebu0grkjVdpyLvTI |
| user_agent | 用户代理 | 否 | 自定义UA |

## 使用方法

### 前置条件

确保已在项目根目录的 `/config/token.json` 中配置好账号信息。

### 直接运行

```bash
cd /Users/cat/Projects/python/PrivateProjects/ZaiZaiCat-Checkin/script/erke
python3 main.py
```

### 定时任务

可以使用 crontab 设置定时任务：

```bash
# 每天早上8点执行
0 8 * * * cd /Users/cat/Projects/python/PrivateProjects/ZaiZaiCat-Checkin/script/erke && python3 main.py
```

## 执行流程

1. 读取配置文件中的账号信息
2. 遍历每个账号：
   - 查询积分明细
   - 执行签到操作
3. 输出执行结果统计
4. 发送推送通知

## 输出示例

```
==================================================
开始处理账号: 账号1
==================================================
[账号1] 查询积分明细...
[账号1] 积分明细查询成功
[账号1] 当前积分: 100
[账号1] 执行签到...
[账号1] 签到成功
[账号1] 签到信息: 签到成功，获得10积分

============================================================
执行结果统计
============================================================
总账号数: 1
成功: 1
失败: 0
```

## API 说明

### ErkeAPI 类

#### 初始化参数

```python
api = ErkeAPI(
    member_id="会员ID",
    enterprise_id="企业ID", 
    unionid="unionid",
    openid="openid",
    wx_openid="微信openid",
    appid="wxa1f1fa3785a47c7d",  # 可选，默认值
    user_agent="用户代理"  # 可选
)
```

#### 方法

##### get_integral_record()

获取积分明细

```python
result = api.get_integral_record(
    current_page=1,  # 当前页码
    page_size=20     # 每页大小
)
```

返回格式：
```python
{
    'success': bool,    # 是否成功
    'result': dict,     # 成功时的结果数据
    'error': str        # 失败时的错误信息
}
```

##### member_sign()

会员签到

```python
result = api.member_sign()
```

返回格式：
```python
{
    'success': bool,    # 是否成功
    'result': dict,     # 成功时的结果数据
    'error': str        # 失败时的错误信息
}
```

## 注意事项

1. 请确保配置文件中的信息准确无误
2. 建议不要频繁调用接口，避免被限制
3. 签名算法已内置在 api.py 中，无需单独配置
4. 支持多账号，可在配置文件中添加多个账号

## 常见问题

### Q: 如何获取账号信息？
A: 可以通过抓包小程序请求获取相关参数。

### Q: 签到失败怎么办？
A: 检查 `/config/token.json` 中 erke 节点下的参数是否正确，查看日志中的错误信息。

### Q: 可以添加更多功能吗？
A: 可以，在 api.py 中添加新的接口方法即可。

### Q: 配置文件在哪里？
A: 统一使用项目根目录下的 `/config/token.json` 文件，在 `erke` 节点下配置账号信息。

## 更新日志

### v1.0.0 (2025-11-28)
- 初始版本
- 支持积分明细查询
- 支持自动签到
- 支持多账号
- 支持推送通知

