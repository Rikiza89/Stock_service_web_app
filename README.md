# 🏭 Django 在庫管理サービス

このリポジトリは、**マルチテナント対応の在庫および在庫追跡システム**である **Django 在庫管理サービス** の公式ドキュメントです。

本アプリケーションは、**組織（Society）・ユーザー名・パスワード**を組み合わせた**カスタム認証バックエンド**を採用し、各テナントのデータを安全かつ分離して管理するように設計されています。

---

## 🚀 クイックスタート

以下の手順でアプリケーションをローカル環境にセットアップし、実行することができます。

### 🧩 前提条件

システムに以下のソフトウェアがインストールされている必要があります：

- Python 3.8 以上（推奨）
- pip（Python パッケージマネージャ）

---

## 1️⃣ インストール

### リポジトリのクローン

```bash
git clone https://github.com/Rikiza89/Stock_service_web_app.git
cd Stock_service_web_app
```

### 仮想環境の作成（推奨）

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows
```

### 依存関係のインストール

このアプリケーションは Django と django-import-export を使用しています。  
`requirements.txt` が存在する場合は以下のコマンドで一括インストールしてください。

```bash
pip install -r requirements.txt
```

`requirements.txt` が存在しない場合は、手動で以下をインストールします。

```bash
pip install Django django-import-export
```

---

## 2️⃣ 設定

### settings.py の確認

カスタム認証が正しく機能するためには、Django の設定ファイルに以下の内容が含まれている必要があります。

#### カスタムユーザーモデルの設定

```python
AUTH_USER_MODEL = 'stock_service.User'
```

#### カスタム認証バックエンドの設定

```python
AUTHENTICATION_BACKENDS = [
    'stock_service.backends.SocietyAuthBackend',  # カスタムバックエンド
    'django.contrib.auth.backends.ModelBackend',  # Django標準
]
```

---

## 3️⃣ データベース設定

### マイグレーションの適用

以下のコマンドを実行して、データベースに必要なテーブルを作成します。

```bash
python manage.py makemigrations stock_service
python manage.py migrate
```

### スーパーユーザーの作成

```bash
python manage.py createsuperuser
```

> 💡 **ヒント：** スーパーユーザーは初期セットアップや Django 管理画面へのアクセスに使用します。

---

## ⚙️ サンプルデータのロード（オプション）

初期テスト用データを作成する場合は、以下のコマンドを使用します。

```bash
python manage.py load_sample_data_stock_service
```

このコマンドは以下に定義されています：

```
stock_service/management/commands/load_sample_data_stock_service.py
```

> 🧠 **説明：**  
> このスクリプトはデモ用に Society・User・StockObject などの初期データを自動生成します。  
> 本番運用環境では任意で実行可能です。

---

## 4️⃣ 開発サーバーの実行

以下のコマンドでローカルサーバーを起動します。

```bash
python manage.py runserver
```

アプリケーションは [http://127.0.0.1:8000/](http://127.0.0.1:8000/) で利用できます。  
ログインページは `stock_service/urls.py` で設定された `/login_stock_service/` などの URL からアクセス可能です。

---

## 🔒 デモサイトへのアクセス

| 項目 | 内容 |
|------|------|
| デモサイトURL | [https://rikiza.pythonanywhere.com/stock_service/login_stock_service/](https://rikiza.pythonanywhere.com/stock_service/login_stock_service/) |
| ログインユーザー | `1234` |
| パスワード | `1234` |
| 会社名（Society Name） | `1234` |

---

## 🛠 プロジェクト構成

コアロジックは `stock_service` アプリケーション内にあります。

| ファイル名 | 説明 |
|------------|------|
| **models.py** | `Society`、`User`、`StockObject` など、全てのデータベースモデルを定義します。 |
| **backends.py** | カスタム認証ロジック `SocietyAuthBackend` を実装します。 |
| **forms.py** | 登録・ログイン・管理操作に使用されるフォームを定義します。 |
| **views.py** | ユーザー管理、在庫処理、設定画面のビジネスロジックを担当します。 |
| **urls.py** | 各ビューへのルーティング設定を行います。 |

---

## 📄 ライセンス

© 2025 Rikiza89. All rights reserved.

