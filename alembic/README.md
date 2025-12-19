# Alembic README

このドキュメントは、Python プロジェクトで **Alembic** を用いてデータベースマイグレーションを管理するための手順と運用ルールをまとめたものです。

---

## インストール

```bash
uv add alembic
```

---

## 初期セットアップ

```bash
alembic init alembic
```

生成される主なファイル／ディレクトリ：

```
.
├─ alembic/
│  ├─ versions/        # マイグレーションファイル
│  ├─ env.py           # 実行環境設定
│  └─ script.py.mako
└─ alembic.ini         # Alembic設定ファイル
```

---

## データベース接続設定

`alembic.ini` を編集し、DB 接続 URL を設定します。

```ini
sqlalchemy.url = postgresql+psycopg2://user:password@localhost:5432/dbname
```

もしくは `env.py` 内で環境変数から読み込むことを推奨します。

---

## モデルとの連携（Autogenerate）

`env.py` で `target_metadata` に SQLAlchemy の `Base.metadata` を設定します。

```python
from app.db.base import Base
target_metadata = Base.metadata
```

---

## マイグレーション作成

### 自動生成

```bash
alembic revision --autogenerate -m "add user table"
```

### 手動生成

```bash
alembic revision -m "manual migration"
```

生成されたファイルは **必ず内容を確認** してください。

---

## マイグレーション適用

最新バージョンまで反映：

```bash
alembic upgrade head
```

特定バージョンまで反映：

```bash
alembic upgrade <revision_id>
```

---

## ロールバック

1 つ前のバージョンへ戻す：

```bash
alembic downgrade -1
```

特定バージョンへ戻す：

```bash
alembic downgrade <revision_id>
```

---

## 現在の状態確認

```bash
alembic current
alembic history
```

---

## 運用ルール（推奨）

- `--autogenerate` 後は必ず差分をレビューする
- 本番環境では **事前にバックアップ** を取得する
- 1 マイグレーション = 1 変更単位
- downgrade が安全に動作することを確認する

---

## よくあるトラブル

### 差分が正しく検出されない

- `target_metadata` が正しく設定されているか確認
- モデルが import されているか確認

### 既存 DB と衝突する

- `alembic stamp head` で現在の状態を同期

---

## 参考リンク

- Alembic 公式ドキュメント
- SQLAlchemy 公式ドキュメント
