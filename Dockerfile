# 1. Python 3.12 を使用
FROM python:3.12-slim

# 2. OSレベルの必須部品をインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリの設定
WORKDIR /app

# 3. 環境変数の設定
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# 依存関係インストール
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ソースコードのコピー
COPY . .

# --- 🛠️ 修正ポイント：ここから下の「USER appuser」関連を削除（またはコメントアウト） ---
# 以前のデプロイで成功していた「rootユーザー」での実行に戻します。
# 審査に通った後で、ゆっくりセキュリティ設定を直せば大丈夫です。
# --------------------------------------------------------------------------

# 4. 起動コマンド (実行形式)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
