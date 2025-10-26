# Development Guide

## セットアップ

### 1. 依存関係のインストール
```bash
uv sync
```

### 2. Pre-commitフックのセットアップ
```bash
uv run setup-hooks
```

これにより、コミット前に自動的にテストが実行されます。

## テスト実行

### 全テスト実行
```bash
uv run test
```

### APIテストのみ実行
```bash
uv run test-api
```

### 手動でpytestを実行
```bash
uv run pytest tests/ -v
```

## アプリケーション実行

### スケジューラー起動（定期実行）
```bash
uv run app
```

### 一回だけ実行
```bash
uv run app-once
```

### API サーバー起動
```bash
uv run api
```

## Git ワークフロー

### Pre-commitフック
コミット前に以下が自動実行されます：
- 全テストの実行
- Python構文チェック
- コードフォーマットチェック
- YAMLファイルチェック
- 大きなファイルのチェック

## トラブルシューティング

### Pre-commitフックをスキップしたい場合
```bash
git commit --no-verify -m "commit message"
```

### Pre-commitフックを再インストール
```bash
uv run pre-commit uninstall
uv run setup-hooks
```

### テストが失敗する場合
1. APIサーバーが既に起動していないか確認
2. ポート8000が使用されていないか確認
3. データベースファイルの権限を確認
