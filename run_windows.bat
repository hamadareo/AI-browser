@echo off
chcp 65001 > nul
echo ========================================
echo AI Browser 起動スクリプト (Windows)
echo ========================================

cd /d "%~dp0"

:: Pythonがインストールされているか確認
python --version >nul 2>&1
if errorlevel 1 goto error_python

IF EXIST ".venv\Scripts\activate.bat" goto skip_venv
echo [1/3] Python仮想環境を作成しています...
python -m venv .venv
if errorlevel 1 goto error_venv
:skip_venv

echo [2/3] 必要なパッケージをインストールしています...
call .venv\Scripts\activate.bat
if errorlevel 1 goto error_activate

pip install -r requirements.txt
if errorlevel 1 goto error_pip

echo [3/3] ブラウザ (Playwright) を準備しています...
python -m playwright install chromium
if errorlevel 1 goto error_playwright

echo.
echo ========================================
echo 準備完了。AI Browser を起動します。
echo ========================================
python main.py

if errorlevel 1 goto error_main
goto end

:error_python
echo [エラー] Pythonが見つかりません。
echo Pythonがインストールされているか、インストール時に「Add python.exe to PATH」にチェックを入れたか確認してください。
echo ※Microsoft Storeが開いてしまう場合は、Windowsの設定から「アプリ実行エイリアス」を開き、Pythonをオフにしてください。
pause
exit /b 1

:error_venv
echo [エラー] 仮想環境の作成に失敗しました。
pause
exit /b 1

:error_activate
echo [エラー] 仮想環境の有効化に失敗しました。
pause
exit /b 1

:error_pip
echo [エラー] パッケージのインストールに失敗しました。
pause
exit /b 1

:error_playwright
echo [エラー] ブラウザのインストールに失敗しました。
pause
exit /b 1

:error_main
echo [エラー] AI Browserの実行中にエラーが発生しました。
pause
exit /b 1

:end
pause
