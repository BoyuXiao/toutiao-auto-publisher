@echo off
REM 后台运行今日头条发布脚本
REM 使用 pythonw.exe 可以在后台运行，不显示窗口

cd /d %~dp0
pythonw.exe main.py --mode publish

REM 如果需要查看日志，可以使用以下命令（会显示窗口但最小化）
REM start /MIN python main.py --mode publish

