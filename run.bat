@echo off
chcp 65001 >nul 2>&1
title AI 台股當沖分析系統

echo ====================================
echo  AI 台股當沖分析系統
echo ====================================
echo.

REM 檢查虛擬環境
if not exist "venv" (
    echo [錯誤] 找不到虛擬環境
    echo 請先執行: setup.bat
    pause
    exit /b 1
)

REM 啟動虛擬環境
echo [1/3] 啟動虛擬環境...
call venv\Scripts\activate.bat >nul 2>&1

REM 檢查 .env 檔案
if not exist ".env" (
    echo [警告] 找不到 .env 檔案
    echo.
)

REM 智能套件檢查（只在 requirements.txt 更新時才執行）
echo [2/3] 檢查套件狀態...

REM 檢查是否需要更新
set NEED_UPDATE=0

REM 檢查標記檔案
if not exist ".last_update" (
    set NEED_UPDATE=1
) else (
    REM 比較 requirements.txt 和標記檔案的修改時間
    for %%A in (requirements.txt) do set REQ_TIME=%%~tA
    for %%A in (.last_update) do set UPDATE_TIME=%%~tA
    
    if not "!REQ_TIME!"=="!UPDATE_TIME!" (
        set NEED_UPDATE=1
    )
)

if %NEED_UPDATE%==1 (
    echo 發現套件更新，正在安裝...
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    
    REM 創建標記檔案
    echo. > .last_update
    echo 套件更新完成！
) else (
    echo 套件已是最新版本，跳過更新
)

REM 啟動應用程式
echo [3/3] 啟動應用程式...
echo.
echo 瀏覽器將自動開啟 http://localhost:8501
echo 按 Ctrl+C 可停止程式
echo.

streamlit run main.py

pause
