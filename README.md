# 🏭 Django 在庫管理サービス 

このリポジトリは、**マルチテナント対応の在庫および在庫追跡システム**である **Django 在庫管理サービス** のドキュメントです。

本アプリケーションは、**組織/会社名、ユーザー名、パスワード**を組み合わせた**カスタム認証バックエンド**を利用して、各テナント（社会）のデータを分離して管理するように設計されています。

---

## 🚀 クイックスタート (アプリケーションの実行)

以下の手順に従って、アプリケーションをローカルでセットアップし、実行してください。

---

### 🧩 前提条件

システムに以下のソフトウェアがインストールされている必要があります。

- Python (3.8+ 推奨)
- pip (Python パッケージインストーラ)

---

## 1️⃣ インストール

### リポジトリのクローン:

```bash
git clone https://github.com/Rikiza89/Stock_service_web_app.git
cd Stock_service_web_app
```

### 仮想環境の作成 (推奨):

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS の場合
# venv\Scripts\activate   # Windows の場合
```

### 依存関係のインストール:

このアプリケーションを実行するには、主に Django と django-import-export が必要です。

プロジェクトルートに `requirements.txt` が存在することを想定しています。

```bash
pip install -r requirements.txt
```

もし `requirements.txt` がない場合は、以下を手動でインストールしてください。

```bash
pip install Django django-import-export
```

---

## 2️⃣ 設定 (settings.py の確認)

カスタム認証が正しく機能するように、メインの Django `settings.py` ファイルに以下の設定が含まれていることを確認してください。

### カスタムユーザーモデルの設定:

```python
AUTH_USER_MODEL = 'stock_service.User'
```

### カスタム認証バックエンドの設定:

ログイン時に「社会名」「ユーザー名」「パスワード」を処理するカスタムバックエンドを有効にします。

```python
AUTHENTICATION_BACKENDS = [
    # カスタムバックエンドのパス (必須)
    'stock_service.backends.SocietyAuthBackend',
    # Djangoのデフォルトバックエンド (Adminサイトへのアクセスなどに必要)
    'django.contrib.auth.backends.ModelBackend',
]
```

---

## 3️⃣ データベース設定

### マイグレーションの適用:

Society、User、StockObjectなどの必要なテーブルをデータベースに作成します。

```bash
python manage.py makemigrations stock_service
python manage.py migrate
```

### スーパーユーザーの作成 (Adminアクセス用):

```bash
python manage.py createsuperuser
```

> 💡 **注:** スーパーユーザーは、初期セットアップや Django Admin サイトでの管理のために使用されます。

---

## ⚙️ オプション設定: サンプルデータのロード (Optional Sample Data Loading)

初期状態でテスト用のデータを作成する場合は、以下のコマンドを使用してサンプルデータを読み込むことができます。

```bash
python manage.py load_sample_data_stock_service
```

このコマンドは以下の場所に定義されています:

```
stock_service/management/commands/load_sample_data_stock_service.py
```

> 🧠 **説明:**  
> このスクリプトは、デモ用にSociety・User・StockObjectなどの初期データを自動で生成します。  
> 実運用時にはこのコマンドの利用は任意です。

---


## 4️⃣ 開発サーバーの実行

以下の標準的な Django コマンドを使用してアプリケーションを起動します。

```bash
python manage.py runserver
```

アプリケーションは [http://127.0.0.1:8000/](http://127.0.0.1:8000/) で実行されます。  
カスタムログインページは、`stock_service/urls.py` で設定された URL（例: `/login_stock_service/`）からアクセスできます。

---

## 🔒 デモサイトへのアクセス (Demo Site Access)

| 項目 | 詳細 |
|------|------|
| デモサイトリンク | **[デモサイト](https://rikiza.pythonanywhere.com/stock_service/login_stock_service/)** |
| ログインユーザー | `1234` |
| パスワード | `1234` |
| 会社名 (Society Name) | `1234` |

---

## 🛠 プロジェクト構成 (Project Structure)

コアロジックは、`stock_service` Django アプリケーション内にあります。

| ファイル | 説明 |
|-----------|------|
| **models.py** | `Society`、`User`、`StockObject`、および各種トランザクションモデルを含むデータベーススキーマを定義します。 |
| **backends.py** | カスタムログインロジックを担う `SocietyAuthBackend` を含みます。 |
| **forms.py** | 登録、ログイン、およびモデル管理用のカスタムフォーム。 |
| **views.py** | ユーザー管理、在庫操作、および設定に関するビジネスロジックとレンダリングを処理します。 |
| **urls.py** | アプリケーションの URL ルートを定義します。 |

---

© 2025 Rikiza89. All rights reserved.



