# MediaExtractor

多平台音视频提取命令行工具，统一入口 `media-extractor`，按平台分子命令：

- `media-extractor bilibili ...` — 根据 BV 号提取 B 站视频/音频
- `media-extractor netease ...` — 根据歌曲/歌单 ID 或链接提取网易云音乐

两个平台都基于对应网页端公开接口解析播放地址实现，均支持扫码登录以解锁更高
画质/音质。

## 依赖

- Python >= 3.9
- [ffmpeg](https://ffmpeg.org/)（需在 `PATH` 中可用；仅 B 站视频下载需要，用于
  音视频合并/封装，网易云音乐下载不需要）

## 安装

```bash
pip install -e .
```

## B 站视频/音频

### 登录（可选，但推荐）

不登录默认只能获取到 480P 左右的画质。扫码登录后可解锁 1080P、4K 等更高画质
（取决于账号是否为大会员）。

```bash
media-extractor bilibili login
media-extractor bilibili logout   # 清除登录状态
```

### 下载

```bash
# 自动选择最高可用画质，视频+音频合并为 mp4
media-extractor bilibili download BV13J3R6MEkE

# 指定输出目录
media-extractor bilibili download BV13J3R6MEkE -o ~/Downloads

# 只提取音频（输出 .m4a，账号有 Hi-Res 无损包时自动升级为 .flac）
media-extractor bilibili download BV13J3R6MEkE --audio-only

# 只提取无声视频（输出 .mp4）
media-extractor bilibili download BV13J3R6MEkE --video-only

# 指定画质（qn 值，如 80=1080P，64=720P，32=480P）
media-extractor bilibili download BV13J3R6MEkE -q 80

# 多P视频，指定第几P（默认第1P），或 -a 下载所有分P
media-extractor bilibili download BV13J3R6MEkE -p 2
media-extractor bilibili download BV13J3R6MEkE -a
```

### 从 txt 文件批量下载

`batch` 会读取整个文本文件，自动提取出所有出现过的 BV 号（纯号、完整视频链接、
混在其他文字里都可以，重复的会自动去重），然后逐个下载。参数与 `download` 基本一致。

```bash
media-extractor bilibili batch list.txt -o ~/Downloads
media-extractor bilibili batch list.txt --audio-only -a
```

某个 BV 号下载失败不会中断其余任务，结束后会汇总列出失败的 BV 号。

### 音质说明

音频优先级：**Hi-Res 无损（FLAC）> 192K AAC > 132K > 64K**。普通账号 / 未开通
Hi-Res 无损包最高只能拿到 192K AAC（`.m4a` 只是容器，不代表"最高音质"）；大会员
且开通 Hi-Res 无损包时会自动优先下载无损 FLAC（若同时下载视频，容器自动改为
`.mkv`，因为 MP4 不支持封装 FLAC）。具体某个视频是否提供 Hi-Res 音源取决于 UP
主上传时的源文件，并非所有视频都有。

## 网易云音乐

### 登录（可选）

不登录只能下载部分免费歌曲，且音质有限；扫码登录后可解锁无损/Hi-Res 等音质，
以及更多需要 VIP 权限的歌曲。

```bash
media-extractor netease login
media-extractor netease logout
```

网易云对扫码登录接口有比较严格的风控，如果长时间卡在“已扫描，请在手机上点击
『确认登录』”，多半是被判定为风险请求。这种情况下可以改用手动导入 Cookie：
在浏览器里登录网页版 [music.163.com](https://music.163.com)，打开开发者工具的
Network 面板，随便找一个 `music.163.com` 的请求，复制其请求头里完整的
`Cookie` 字符串，然后：

```bash
media-extractor netease login --cookie "MUSIC_U=xxx; __csrf=xxx; ..."
```

### 下载

`target` 可以是歌曲/歌单的纯数字 ID，也可以是网易云音乐链接
（如 `https://music.163.com/#/song?id=xxx` 或 `.../playlist?id=xxx`）。

```bash
# 下载单曲，自动选账号能拿到的最高音质
media-extractor netease download 1901371647
media-extractor netease download "https://music.163.com/#/song?id=1901371647"

# 下载整个歌单（自动建同名子文件夹存放）
media-extractor netease download "https://music.163.com/#/playlist?id=xxxxx"

# 纯数字 ID 默认按歌曲处理；如果这个 ID 其实是歌单，用 --type 指明
media-extractor netease download 123456 --type playlist

# 指定音质
media-extractor netease download 1901371647 -q exhigher
```

音质从高到低：`jymaster`(超清母带) > `sky`(沉浸环绕声) > `jyeffect`(高清环绕声)
> `hires`(Hi-Res) > `lossless`(无损) > `exhigher`(320k) > `higher`(192k) >
`standard`(128k)，不指定 `-q` 时会自动从高到低尝试，取账号能拿到的最高音质。

### 从 txt 文件批量下载

```bash
# 每行一个歌曲/歌单 ID 或链接均可
media-extractor netease batch list.txt -o ~/Downloads
```

## 已知限制

- B 站：仅支持返回标准 DASH 流的普通视频；番剧、互动视频等特殊类型暂不支持。
- 网易云音乐：部分歌曲因版权方限制无法获取播放地址，即使登录大会员也可能
  无法下载；这是平台侧的限制，不是工具本身的 bug。
- 请遵守各平台相关服务条款，仅用于个人学习或已获授权的用途。
