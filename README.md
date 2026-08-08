# BilibiliExtractor

根据 BV 号提取 B 站视频的音频 / 视频文件的命令行工具。基于 B 站网页端公开的
`view` / `playurl` 接口解析 DASH 音视频流，使用 `ffmpeg` 完成封装/合并。

## 依赖

- Python >= 3.9
- [ffmpeg](https://ffmpeg.org/)（需在 `PATH` 中可用）

## 安装

```bash
pip install -e .
```

## 使用

### 登录（可选，但推荐）

不登录默认只能获取到 480P 左右的画质。扫码登录后可解锁 1080P、4K 等更高画质
（取决于账号是否为大会员）。

```bash
bilibili-extractor login
```

登录信息会保存在 `~/.bilibili_extractor/cookies.json`。清除登录状态：

```bash
bilibili-extractor logout
```

### 下载

```bash
# 自动选择最高可用画质，视频+音频合并为 mp4
bilibili-extractor download BV13J3R6MEkE

# 指定输出目录
bilibili-extractor download BV13J3R6MEkE -o ~/Downloads

# 只提取音频（输出 .m4a）
bilibili-extractor download BV13J3R6MEkE --audio-only

# 只提取无声视频（输出 .mp4）
bilibili-extractor download BV13J3R6MEkE --video-only

# 指定画质（qn 值，如 80=1080P，64=720P，32=480P）
bilibili-extractor download BV13J3R6MEkE -q 80

# 多P视频，指定第几P（默认第1P）
bilibili-extractor download BV13J3R6MEkE -p 2

# 批量下载多P视频的所有分P
bilibili-extractor download BV13J3R6MEkE -a
```

### 从 txt 文件批量下载

`batch` 会读取整个文本文件，自动提取出所有出现过的 BV 号（纯号、完整视频链接、
混在其他文字里都可以，重复的会自动去重），然后逐个下载。参数与 `download` 基本一致。

```bash
# list.txt 内容随意，每行一个 BV 号或视频链接均可
bilibili-extractor batch list.txt -o ~/Downloads

# 批量下载，只要音频，且每个视频的所有分P都要
bilibili-extractor batch list.txt --audio-only -a
```

某个 BV 号下载失败不会中断其余任务，结束后会汇总列出失败的 BV 号。

### 音质说明

音频优先级：**Hi-Res 无损（FLAC）> 192K AAC > 132K > 64K**。

- 普通账号 / 未开通 Hi-Res 无损包：最高只能拿到 192K AAC（输出 `.m4a`），这是
  B 站常规音轨的上限，`.m4a` 只是容器，不代表"最高音质"。
- 大会员且开通了 Hi-Res 无损包：工具会自动识别并优先下载无损 FLAC 音轨
  （输出 `.flac`；若同时下载视频，容器会自动改为 `.mkv`，因为 MP4 不支持
  封装 FLAC 音轨）。
- 具体某个视频是否提供 Hi-Res 音源取决于 UP 主上传时提供的源文件，并非所有
  视频都有。

`bvid` 参数既可以是纯 BV 号，也可以是包含 BV 号的完整视频链接。

## 已知限制

- 仅支持返回标准 DASH 流的普通视频；番剧、互动视频等特殊类型暂不支持。
- 请遵守 B 站相关服务条款，仅用于个人学习或已获授权的用途。
