# Binance Historical Data Downloader

这是一个用于下载币安(Binance)历史K线数据的Python脚本。支持下载从2017年1月至今的所有K线数据，包括daily和monthly两种类型。

## 功能特点

- 支持daily和monthly两种数据类型
- 自动并发下载（默认5个并发）
- 支持增量和全量下载模式
- 自动跳过已下载的文件
- 详细的进度显示和下载统计
- 完整的日志记录

## 环境配置

### 创建conda环境

```bash
# 创建名为binance_klines_syncer的新环境
conda create -n binance_klines_syncer python=3.10

# 激活环境
conda activate binance_klines_syncer
```

### 安装依赖

```bash
pip install aiohttp
```

## 使用方法

### 基本用法

1. 下载daily数据：
```bash
python sync.py --type daily
```

2. 下载monthly数据：
```bash
python sync.py --type monthly
```

### 增量下载

只下载缺失的文件：
```bash
python sync.py --type daily --incr
python sync.py --type monthly --incr
```

### 下载其他交易对

默认下载BTCUSDT，可以指定其他交易对：
```bash
python sync.py --type monthly --symbol ETHUSDT
```

### 快速启动脚本

使用提供的shell脚本快速启动下载（使用source命令以保持在conda环境中）：
```bash
source sync_monthly.sh  # 下载monthly数据
source sync_daily.sh    # 下载daily数据
```

注意：使用`source`命令（或`.`命令）执行脚本，这样可以保持在conda环境中。不要直接使用`./sync_monthly.sh`的方式执行。

## 支持的时间周期

### Daily数据
- 1s（秒级）
- 1m, 3m, 5m, 15m, 30m（分钟级）
- 1h, 2h, 4h, 6h, 8h, 12h（小时级）

### Monthly数据
- 1m, 3m, 5m, 15m, 30m（分钟级）
- 1h, 2h, 4h, 6h, 8h, 12h（小时级）
- 1d, 3d（天级）
- 1w（周级）
- 1mo（月级）

## 数据存储结构

```
binance_data/
├── daily/
│   ├── 1m/
│   ├── 3m/
│   └── ...
└── monthly/
    ├── 1m/
    ├── 3m/
    └── ...

logs/
└── binance_[mode]_[date].log
```

## 日志记录

- 日志文件保存在 `logs` 目录
- 包含详细的下载记录和错误信息
- 每次运行生成独立的日志文件

## 注意事项

1. 首次运行会下载大量数据，请确保有足够的磁盘空间
2. 下载速度受网络条件和币安服务器限制
3. 程序会自动创建必要的目录结构
4. 下载失败的文件会在日志中记录，可以后续重试

## 错误处理

- 自动重试失败的下载（最多3次）
- 详细的错误日志记录
- 下载完成后显示失败文件列表

## 性能优化

- 使用异步IO进行并发下载
- 自动跳过已存在的文件
- 下载完成后自动清理临时文件

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 许可证

MIT License