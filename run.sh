#!/bin/bash
sudo chmod 777 /dev/ttyACM0 
# 启动 HTTP 服务器
echo "Starting Flask server..."
python http_server/server.py


