#!/bin/bash

echo "========================================"
echo "AI Browser 起動スクリプト (Mac/Linux)"
echo "========================================"

# スクリプトがあるディレクトリに移動
cd "$(dirname "$0")" || exit

# 仮想環境の作成
if [ ! -d ".venv" ]; then
    echo "[1/3] Python仮想環境を作成しています..."
    # python3コマンドが存在するかチェック
    if command -v python3 &> /dev/null; then
        python3 -m venv .venv
    elif command -v python &> /dev/null; then
        python -m venv .venv
    else
        echo "[エラー] Pythonが見つかりません。Pythonがインストールされているか確認してください。"
        echo "エンターキーを押して終了します..."
        read -r
        exit 1
    fi
fi

# 仮想環境の有効化とパッケージインストール
echo "[2/3] 必要なパッケージをインストールしています..."
source .venv/bin/activate
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[エラー] パッケージのインストールに失敗しました。"
    echo "エンターキーを押して終了します..."
    read -r
    exit 1
fi

# Playwrightブラウザのインストール
echo "[3/3] ブラウザ (Playwright) を準備しています..."
playwright install chromium
if [ $? -ne 0 ]; then
    echo "[エラー] ブラウザのインストールに失敗しました。"
    echo "エンターキーを押して終了します..."
    read -r
    exit 1
fi

echo ""
echo "========================================"
echo "準備完了。AI Browser を起動します。"
echo "========================================"
python main.py

echo ""
echo "実行が終了しました。ターミナルを閉じてください。"
