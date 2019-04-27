# Watch-with-You 使用说明
## 简单介绍
这是一个实现两用户在异地同步播放本地电影的Python程序，主要适用场景是异地恋需要体验一下“一起看个电影”的时候。现有些插件网络插件可以同步网络视频播放，但是网络上还未看到播放本地视频的程序，但是很多电影不一定能在线播放。
一个理想的使用场景是异地恋双方一边视频聊天，一边通过WatchwithYou看电影。
本程序主要实现两客户端播放进度的实时控制。
本程序使用[@MPV](https://mpv.io/)作为播放器，并利用[@siikamiika](https://github.com/siikamiika)实现的MPV接口[mpv-python-ipc](https://github.com/siikamiika/mpv-python-ipc)实现和播放器交互。

该程序使用 python3, 客户端依赖 requests 和 base64，服务端依赖 flask 和 pymongodb。服务器需要运行mongodb服务。


## 程序说明
主要通过心跳包实现两MPV播放器播放进度同步，分别是暂停动作和快进动作。以客户端暂停后另一客户端不能取消暂停，快进同理。
本程序通过视频文件文件名进行用户间的房间配对,如需要配对则请将两客户端播放的视频文件名保持一致。

本程序客户端可以直接使用,现已在默认服务器地址上开启了服务端程序，尽请体验。
## 文件说明

MPV  MPV播放器
mpv_python_ipc mpv-python-ipc包
client.py 客户端
server.py 服务端
config.ini 配置文件，修改服务器地址