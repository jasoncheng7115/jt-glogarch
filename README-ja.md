# jt-glogarch v1.18.1

**Language**: [English](README.md) | [繁體中文](README-zh_TW.md) | **日本語**  
**Website**: <https://jasoncheng7115.github.io/jt-glogarch/>

**Graylog Open Archive** — Graylog Open（6.x / 7.x）向けのログのアーカイブ・リストアツール

[![License](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.18.1-green.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()

> **作者：** Jason Cheng（[Jason Tools](https://github.com/jasoncheng7115)）
> **ライセンス：** AGPL-3.0-or-later
>
> 本書は日本語版の概要・運用ガイドです。すべての設定項目や詳細な挙動は英語版の
> [README.md](README.md)、[CONFIG.md](CONFIG.md)、[AUDIT-OPERATIONS.md](AUDIT-OPERATIONS.md)
> を参照してください。内容に差異がある場合は英語版が優先されます。

---

## 目次

- [概要](#概要)
- [主な機能](#主な機能)
- [対応環境・機能サポート表](#対応環境機能サポート表)
- [動作要件](#動作要件)
- [インストール](#インストール)
- [オフライン（閉域）環境へのインストール](#オフライン閉域環境へのインストール)
- [アップグレード](#アップグレード)
- [アンインストール](#アンインストール)
- [初期設定](#初期設定)
- [主要設定](#主要設定)
- [操作監査のセットアップ（nginx）](#操作監査のセットアップnginx)
- [運用ガイド](#運用ガイド)
  - [スケジュール運用](#スケジュール運用)
  - [アーカイブ失敗時の対応](#アーカイブ失敗時の対応)
  - [リストア手順とリストア訓練](#リストア手順とリストア訓練)
  - [通知](#通知)
- [完全性と監査の範囲（できること・できないこと）](#完全性と監査の範囲できることできないこと)
- [パフォーマンスとサイジング](#パフォーマンスとサイジング)
- [CLI リファレンス（抜粋）](#cli-リファレンス抜粋)
- [FAQ](#faq)
- [ライセンス](#ライセンス)

---

## 概要

Graylog Open には、Enterprise 版にあるアーカイブ機能が含まれていません。
**jt-glogarch** はこの不足を補うツールで、Graylog Open（6.x / 7.x）のログを圧縮アーカイブ
（`.json.gz`）として長期保存し、必要なときに Graylog へ戻す（リストアする）までの一連の流れを、
Web UI・スケジューラー・CLI で提供します。

- 既存の Graylog 環境をそのまま使います。ログの収集・解析・検索基盤を作り直す必要はありません。
- アーカイブは SHA256 で完全性を検証でき、オプションで鍵付き HMAC による改ざん検知も利用できます。
- Graylog に対して「誰が何をしたか」を記録する操作監査機能を備えています。
- インターネットに接続できない閉域環境へのインストール・アップグレードにも対応しています。

ライセンスは **AGPL-3.0-or-later** です。

```
+-----------------+     +------------------+     +------------------+
|  Graylog Open   |     |   jt-glogarch    |     |  Graylog Open    |
|  (Production)   |     |                  |     |  (Query / DR)    |
|                 |     |  +------------+  |     |                  |
|  Logs --------->|---->|  | .json.gz   |  |---->|  Restored Logs   |
|                 | API |  | Archives   |  | GELF|                  |
|  OpenSearch     | or  |  | + SHA256   |  |  or |  Searchable in   |
|  Indices        | OS  |  +------------+  | Bulk|  Graylog UI      |
+-----------------+     +------------------+     +------------------+
      Export (API          Storage + DB             Import (GELF TCP
      or OpenSearch)       + Web UI + CLI           or OS Bulk)
```

---

## 主な機能

### アーカイブ内のレコード検索（リストア不要でまず検索・CSV/JSON ダウンロード）

v1.14.0 から、アーカイブファイルを **Graylog にインポートし直さずに、そのまま中を検索** できます。
「半年前にあのホストで何が起きていたか」のような単発の調査では、期間全体を再インポートすると
数十分かかるところを、数秒〜数分で確認できます。

- **時間範囲の指定は必須です。** アーカイブにはインデックスがないため、開くファイルを絞り込めるのは
  時間範囲だけです。アーカイブのタイムラインをドラッグするか、開始・終了時刻を入力します。
- **キーワード** — レコード内のどこかに一致する自由テキスト（大文字・小文字を区別しません）。
  `firewall deny` は両方を含むレコード、`"connection refused"` はフレーズとして一致します。
- **フィールドフィルター** — 指定したフィールドの完全一致です（例：`source=fw01 level=4`）。
- **検索前に負荷の目安を表示します**（対象アーカイブ数、概算レコード数、所要時間の見積もり）。
- 一致箇所は結果一覧と展開表示の両方で強調表示されます。
- **一致した全レコードをダウンロード** できます。CSV（UTF-8 BOM 付きで Excel でも文字化けしません）
  または JSON Lines（全フィールド）で、表示中のページだけでなく全ページ分をディスクへストリーミング
  出力します。件数が多くてもメモリ使用量は増えません。
- エクスポートやインポートの実行中は、検索側が速度を落として処理を譲り、その旨を画面に表示します。

> **これはクエリエンジンではありません。** ダッシュボード、グラフ、集計、クエリ言語、ワイルドカード、
> 正規表現、OR / NOT、フィールドによる並べ替えには対応していません。本格的な分析が必要な場合は、
> その期間を Graylog にインポートし、Graylog の検索機能を使ってください。

### 2 つのエクスポートモード

| 項目 | Graylog API | OpenSearch 直接 |
|---|---|---|
| 速度（既定設定での参考値） | 約 730 レコード/秒 | 約 3,300 レコード/秒 |
| ページング | 時間ウィンドウ方式（10,000 件の offset 上限を回避） | `search_after`（上限なし） |
| ストリーム単位の絞り込み | ✅ 可 | ❌ 不可（インデックス単位） |
| 必要な認証情報 | Graylog API トークン | OpenSearch の認証情報 |
| Graylog 7 Data Node | ✅ 対応 | ❌ 非対応（[サポート表](#対応環境機能サポート表)参照） |
| 向いている用途 | ストリーム単位の保存、OpenSearch に直接接続できない環境 | 大量の過去データの一括保存 |

- **重複排除** — すでにアーカイブ済みの時間範囲は自動的にスキップします。API モードと OpenSearch
  モードを切り替えても、同じログを二重に保存しません。
- **中断からの再開** — 完了したチャンク（1 時間単位）は再エクスポートされません。
- **負荷に応じた自動一時停止** — エクスポートは本番の Graylog / OpenSearch に負荷をかけるため、
  Graylog の JVM ヒープ、ディスクジャーナル、各バッファを定期的に確認し、負荷が高いと一時停止して、
  回復すると自動的に再開します（API モード・OpenSearch 直接モードの両方）。ヒープは GC メトリクスで
  判断し、API モードでは GC 後のヒープが 70% を超えるとページごとに速度を落とします。

### 2 つのインポート（リストア）モード

| モード | 経路 | 向いている用途 |
|---|---|---|
| **GELF**（既定） | Graylog Input → 処理 → OpenSearch | パイプライン、エクストラクター、ストリームルーティング、アラートを適用したい場合 |
| **OpenSearch Bulk** | OpenSearch の `_bulk` API に直接書き込み（GELF の約 5〜10 倍高速） | 処理済みの過去データをそのまま高速に戻したい場合 |

どちらのモードも、元の `timestamp`、`source`、`level`、`facility` とすべてのカスタムフィールドを保持し、
送信前にプリフライトチェックを、送信後に照合（reconciliation）を行います。詳細は
[リストア手順とリストア訓練](#リストア手順とリストア訓練) を参照してください。

### オープンなアーカイブ形式（`.json.gz`）

アーカイブは gzip 圧縮した JSON ファイルで、各ファイルの横に `.sha256` ファイルが置かれます。
独自のバイナリ形式ではないため、長期保存後も jt-glogarch 以外のツールで読み取り・加工できます。
ファイルは設定したサイズ（既定 50 MB）で自動分割され、書き込みはストリーミングで行われるため、
全メッセージをメモリに保持することはありません。

### 複数の Graylog ソース

`servers:` に複数の Graylog を登録し、それぞれに専用の OpenSearch クラスターを設定できます。
サーバーごとにエクスポートスケジュールを作成することで、複数拠点や複数システムのログを 1 台で
アーカイブできます（[主要設定](#主要設定) 参照）。

### スケジュール

- **エクスポート** — cron 形式、API / OpenSearch モードを選択
- **クリーンアップ** — 保持期間を過ぎたアーカイブを削除（書き込み中ファイルの誤削除防止付き）
- **検証** — 全アーカイブの SHA256 を定期的に再検証
- すべての種類で「今すぐ実行」が可能です。

### 検証（SHA256 + オプションの HMAC）

- 全アーカイブに SHA256 を付与し、`glogarch verify`（`--workers N` で並列化）または定期スケジュールで
  再検証します。不一致は **CORRUPTED（損傷）** として表示されます。
- オプションで **鍵付き HMAC-SHA256** を有効にでき、不一致は **TAMPERED（改ざん）** として区別して
  表示・通知されます。範囲と限界は
  [完全性と監査の範囲](#完全性と監査の範囲できることできないこと) を参照してください。

### 操作監査

各 Graylog ノードの nginx リバースプロキシから syslog でアクセスログを受け取り、Graylog 上の操作
（ストリーム、パイプライン、ユーザー、検索、コンテンツパックなど 60 種類以上）を、誰が・いつ・
どこから行ったかを記録します。記録は Graylog とは別の jt-glogarch 側データベースに保存されます。
重要操作の通知や、syslog が途絶えたときのハートビート警告にも対応しています。
jt-glogarch 自身で行った操作（アーカイブ削除、設定変更、検索、スケジュール編集など）も別タブで
確認できます。

### 通知

Telegram・Discord・Slack・Microsoft Teams・Nextcloud Talk・Zulip・Email（SMTP）の 7 チャネルに対応しています。
通知の言語は English / 繁體中文 / 日本語 から選択できます。

### Web UI

ダッシュボード、アーカイブ一覧（タイムライン、絞り込み、一括インポート・削除）、レコード検索、
タスクログ（リアルタイム進捗、キャンセル）、スケジュール、通知設定、システムログ、操作監査、アラート管理、
レポート、設定の各画面を備えています。ライト / ダークテーマ、English / 繁體中文 / 日本語 に対応しています。
ログインには Graylog のアカウントを使います（別途ユーザー管理は不要です）。

### コンテンツパック（v1.18.0 以降）

接続中の各 Graylog のコンテンツパックを表示、編集、インストール、アンインストール、ダウンロード、アップロードできます。Jason Tools ライブラリもあります（下記の公開パックを収録し、サイト独自のパックはローカルにのみ保存されます）。ダッシュボードのレイアウトをプレビューし、インストール前にその Graylog への影響を確認し、編集内容は差分で確認できます。編集は新しいリビジョンとして保存され、インストール済みの内容は変わりません。

**公開パック**：ここには作者が公開したパックのみ掲載します。

- Jason Tools ライブラリに組み込み（v1.18.1 以降）：**Windows Active Directory**、**Linux 登入與 SSH**（Linux の SSH と sudo ログイン）、**Apache HTTP Server**、**QNAP NAS**。コンテンツパック画面から直接インストールでき、ダウンロードには使い方の説明が付きます。
- 個別ダウンロード：[CubeCOS / OpenStack Log Pipeline](https://github.com/jasoncheng7115/it-scripts/blob/master/graylog/cubecos_contentpack_graylog63.json)。CubeCOS、OpenStack、Ceph、Masakari のログ用のパイプライン 1 つとルール 147 個です（パックの表記では Graylog 6.3 以降に対応）。リンク先からダウンロードし、コンテンツパック画面でアップロードしてください。

### アラート管理（v1.17.0 以降）

Graylog のイベント定義と通知を一括で管理します。クイックフィルター、タイトルのタグ（`[ベンダー]`／`製品 - `）、
複数キーワード検索（`checkpoint -notif:Zulip`）、Shift クリックでの範囲選択と「一致するものをすべて選択」のあと、
数百件の定義に通知をまとめて追加・削除・置き換えできます。変更は必ずプレビューしてから適用し、各定義の有効／無効は
そのまま保たれ、プレビュー後に Graylog で変更された定義はスキップされます。タスクログのジョブとして実行され、
「変更履歴」から元に戻せます。ヘルスチェックでは、有効なのに誰にも通知されない定義、削除済み・未使用の通知、
一度も（または長期間）一致していない定義を一覧にします。変更はログインしたユーザー自身の Graylog アカウントで
行われ（その権限が適用されます）、パスワードはログイン時に Graylog セッションに交換され、保存されません。

### オフライン（閉域）環境への導入

インターネット接続のあるマシンで依存パッケージ一式を含むバンドルを作成し、閉域環境に持ち込んで
新規インストールまたはアップグレードできます。導入時に pip がネットワークへ接続することはありません。

### PDF レポート（ベータ）

Graylog のダッシュボードとアーカイブ統計から PDF レポートを生成し、スケジュール実行やメール送付が
できます。オプションのレンダリングエンジン（ヘッドレス Chromium）が必要です。
レポートごとに言語（English / 繁體中文 / 日本語）を選べ、表紙・目次・表の件数表示・期間の説明・
「不完全なレポート」の警告・メール本文・既定の透かし（社外秘）がその言語になります。
ウィジェットのタイトルやフィールド名は Graylog 側の設定がそのまま使われます。

---

## 対応環境・機能サポート表

| 機能 | Graylog 6.x（OpenSearch 自前運用） | Graylog 7.x（OpenSearch 自前運用） | Graylog 7.x + Data Node |
|---|---|---|---|
| Graylog API エクスポート | ✅ 対応 | ✅ 対応 | ✅ 対応 |
| OpenSearch 直接エクスポート | ✅ 対応 | ✅ 対応 | ❌ **非対応** |
| GELF インポート | ✅ 対応 | ✅ 対応 | ✅ 対応 |
| OpenSearch Bulk インポート | ✅ 対応 | ✅ 対応 | ❌ **非対応** |
| アーカイブ内検索 | ✅ 対応 | ✅ 対応 | ✅ 対応 |
| 操作監査（nginx 経由） | ✅ 対応 | ✅ 対応 | ✅ 対応 |

**Data Node で非対応となる理由：** Graylog 7 の Data Node は Graylog が管理する OpenSearch で、
TLS クライアント証明書による認証のみを使い、外部ツール向けのユーザー名・パスワードを公開しません。
また Graylog API 経由のプロキシも、ヘルスやインデックス情報など限られたエンドポイントしか通さず、
`_search` や `_bulk` は利用できません。そのため、OpenSearch へ直接アクセスする 2 つのモードは使えません。

- アーカイブ内検索は jt-glogarch 側のアーカイブファイルを読むため、Graylog の構成に依存しません。
- 本書や英語版に記載している **OpenSearch 直接エクスポート（API モードの約 5 倍）や Bulk インポート
  （GELF の約 5〜10 倍）の速度は、Data Node 環境には当てはまりません。** Data Node 環境では
  Graylog API エクスポートと GELF インポートの速度で容量計画を立ててください。
- jt-glogarch は `GET /api/datanodes` で Data Node を検出し、該当するモードが使えないことを画面上で
  警告します。
- アーカイブとリストアの速度を重視する場合は、Graylog 導入時に Data Node ではなく、独立した
  OpenSearch に接続する構成をおすすめします。

---

## 動作要件

- Python 3.10 以上
- Graylog 6.x または 7.x（Open 版）
- OpenSearch 2.x（任意、OpenSearch 直接モード・Bulk インポートを使う場合）
- Linux（Ubuntu 22.04 / Debian 12 / RHEL 9 で動作確認）

---

## インストール

インターネットに接続できるホストでの手順です。

```bash
# 1. リポジトリを取得
sudo git clone https://github.com/jasoncheng7115/jt-glogarch.git /opt/jt-glogarch
cd /opt/jt-glogarch

# 2. インストールスクリプトを実行（ユーザー、ディレクトリ、SSL 証明書、systemd サービスを作成）
sudo bash deploy/install.sh

# 3. Graylog の接続情報を設定（Web UI の初期設定ウィザードでも可）
sudo vi /opt/jt-glogarch/config.yaml

# 4. サービスを起動
sudo systemctl enable --now jt-glogarch

# 5. Web UI を開く
echo "Open: https://$(hostname):8990"
```

インストールの確認：

```bash
systemctl status jt-glogarch
journalctl -u jt-glogarch -f
curl -sk https://localhost:8990/api/health     # バージョンと状態が返ります
```

- サービスは `jt-glogarch` ユーザーで動作します。アーカイブディレクトリ（既定
  `/data/graylog-archives`）と `config.yaml` の所有者は `jt-glogarch` である必要があります。
- Ubuntu 24.04 / Debian 12 など PEP 668 の環境では、インストールスクリプトが自動的に対応します。

---

## オフライン（閉域）環境へのインストール

インターネットに接続できないホスト向けです。**インターネットに接続できるマシンでバンドルを作成し、
持ち込んでローカルで実行** します。

**手順 1 — インターネット接続のあるマシンで作成**（対象ホストと **同じ Python のマイナーバージョン・
CPU アーキテクチャ** のマシンで行います。例：CPython 3.10 / linux x86_64）

```bash
curl -L -o jt-glogarch-src.tar.gz \
  https://github.com/jasoncheng7115/jt-glogarch/archive/refs/heads/main.tar.gz
tar xzf jt-glogarch-src.tar.gz && cd jt-glogarch-main
bash scripts/build-offline-bundle.sh
# → dist/jt-glogarch-<version>-offline.tar.gz が作成されます（約 370 MB、大半は Chromium）
sha256sum dist/jt-glogarch-*-offline.tar.gz   # 転送後の照合用に控えておきます
```

バンドルには jt-glogarch の wheel、すべての依存 wheel、ソースツリー、インストーラー、PDF レポート用の
Playwright・Chromium・CJK フォントが含まれます。

**手順 2 — `jt-glogarch-<version>-offline.tar.gz` を対象ホストへ持ち込みます**（USB、社内ファイル共有、
scp など、閉域運用のルールに従ってください）。持ち込み後に `sha256sum` で照合してください。

**手順 3 — 対象ホストで実行（root）**

```bash
tar xzf jt-glogarch-<version>-offline.tar.gz
cd jt-glogarch-<version>-offline

# jt-glogarch が未導入のホスト — 新規インストール（v1.14.5 以降）
sudo bash install-offline.sh

# すでに jt-glogarch が動作しているホスト — アップグレード
sudo bash upgrade-offline.sh
```

- `install-offline.sh` はサービスユーザー作成、`/opt/jt-glogarch` への配置、同梱 wheel からのインストール、
  自己署名証明書と systemd ユニットの作成を行います。その後 `systemctl enable --now jt-glogarch` を実行し、
  `https://<host>:8990/` で初期設定ウィザードを開きます。既存のインストールがある場合は実行を拒否します。
- 同梱の wheel（uvloop、httptools、watchfiles、pydantic-core など）はプラットフォーム依存です。
  **Python のマイナーバージョンが異なると導入できません**（`cp310` の wheel は Python 3.12 に入りません）。
  不一致の場合、何も書き込む前に中止します。

> **Chromium の OS 共有ライブラリについて：** tarball に含められないのは、Chromium が必要とする OS 側の
> 共有ライブラリ（`libnss3`、`libatk1.0-0`、`libxkbcommon0`、`libgbm1`、`libasound2` など）です。
> 閉域ホストでは、ディストリビューションのインストールメディアなどから別途導入してください。
> v1.14.5 以降のインストーラーは、`jt-glogarch` ユーザーとして実際に PDF をレンダリングして確認し、
> 不足しているライブラリ名を最後に表示します。この場合でも、アーカイブ・リストア・Web UI には影響しません。
>
> ```bash
> sudo bash -c 'source /opt/jt-glogarch/deploy/report-deps.sh && verify_report_engine'
> ```

---

## アップグレード

どの方法でも、事前にデータベースをバックアップし、`config.yaml` を上書きせず、サービスを再起動します。
データベースのスキーマは起動時に自動移行されます。

### A. オンラインアップグレード（ホストがインターネットに接続できる場合）

```bash
sudo bash /opt/jt-glogarch/deploy/upgrade.sh
```

または、常に最新のアップグレードスクリプトを直接実行する方法（古いバージョンからの大きな更新に推奨）：

```bash
curl -fsSL https://raw.githubusercontent.com/jasoncheng7115/jt-glogarch/main/deploy/upgrade.sh | sudo bash
```

処理内容：DB バックアップ（`/var/backups/jt-glogarch/`）→ git pull → 新しい設定の既定値を適用 →
パッケージの再インストール → 再起動 → `/api/health` でバージョン確認。サービス稼働中でも実行できます。

> `/opt/jt-glogarch` はパーミッション 750 のため、一般ユーザーは `cd` できません。
> `cd /opt/jt-glogarch && sudo bash ...` ではなく、上記のように絶対パスで実行してください。

### B. オフラインアップグレード

[オフライン（閉域）環境へのインストール](#オフライン閉域環境へのインストール) の手順でバンドルを作成・
持ち込み、`sudo bash upgrade-offline.sh` を実行します。DB のバックアップ、`/opt/jt-glogarch` のソース更新、
同梱 wheel のみを使ったインストール、再起動、`GET /api/health` によるバージョン確認まで行います。

### アップグレード時の安全方針

- アップグレードでデータを失わないこと、システムを使えない状態にしないこと、スケジュールされた
  アーカイブを止めないことを原則としています。
- たとえば、クリーンアップスケジュールに表示されていた保持日数が、実際に適用されていた日数より
  短い場合、アップグレード時に **実際に適用されていた（長い）値に合わせます**。これにより、
  アップグレード直後のクリーンアップで、前のバージョンが保持していたアーカイブを削除することは
  ありません。短くしたい場合は Web UI で改めて設定してください。
- アップグレード後は [CHANGELOG](CHANGELOG.md) を確認してください。

---

## アンインストール

```bash
sudo bash /opt/jt-glogarch/deploy/uninstall.sh
```

サービスと systemd ユニットを削除し、パッケージをアンインストールします。アーカイブファイル
（`/data/graylog-archives`）、設定、`/opt/jt-glogarch`（DB・証明書を含む）、サービスユーザーの削除は
それぞれ個別に確認され、既定はすべて「残す」です。

---

## 初期設定

サーバーが 1 台も設定されていない状態で Web UI を開くと、初期設定ウィザードが表示されます。

1. **Graylog サーバー** — URL と認証情報（API トークン、またはユーザー名・パスワード）
2. **OpenSearch**（任意、スキップ可） — OpenSearch 直接エクスポート / Bulk インポートを使う場合
3. **アーカイブの保存先** — 既定 `/data/graylog-archives`
4. **予備の管理者アカウント** — `localadmin` のパスワード
5. **完了**

通常は Graylog のアカウントでログインします。`localadmin` は Graylog に接続できないときでも
ログインできる予備アカウントです。

> **タイムゾーン：** スケジューラーはシステムのタイムゾーンを使います。`cron: "0 3 * * *"` を
> 日本時間の 3 時として動かすには、事前に次を実行してください。
>
> ```bash
> sudo timedatectl set-timezone Asia/Tokyo
> sudo systemctl restart jt-glogarch
> ```

---

## 主要設定

設定ファイルは次の順で検索されます：CLI `--config` → `./config.yaml` → `~/.jt-glogarch/config.yaml` →
`/etc/jt-glogarch/config.yaml`。標準の配置は `/opt/jt-glogarch/config.yaml` で、所有者は
`jt-glogarch` である必要があります（Web UI からの設定保存に必要です）。

接続情報以外の多くの項目（スケジュール、通知、リストア先の既定値、保持期間など）は Web UI から設定でき、
接続設定は再起動なしで反映されます。

```yaml
# === 必須：Graylog 接続 ===
servers:
  - name: log4
    url: "http://YOUR_GRAYLOG_IP:9000"
    auth_token: "YOUR_GRAYLOG_API_TOKEN"

default_server: log4

# === 必須：アーカイブの保存先 ===
export:
  base_path: /data/graylog-archives

# === 任意：OpenSearch 直接モード ===
opensearch:
  hosts:
    - "http://YOUR_OS_IP:9200"
  username: admin
  password: "YOUR_OS_PASSWORD"

# === 任意：DB のパス（通常は既定値のまま）===
database_path: /opt/jt-glogarch/jt-glogarch.db
```

主な項目：

| セクション | 内容 |
|---|---|
| `servers` | Graylog サーバー（複数可）。サーバーごとに `opensearch:` ブロックを持てます |
| `opensearch` | サーバー個別の設定がない場合に使うグローバルな OpenSearch。`hosts` は **1 つのクラスターのフェイルオーバーノード** です（別クラスターを並べるものではありません） |
| `export` | 保存先、バッチサイズ、負荷ガード（JVM ヒープのしきい値など） |
| `retention` | `retention_days`（既定 1095 日）、ディスク残量警告 `disk_alert_months` |
| `integrity` | HMAC による改ざん検知（既定 OFF） |
| `notify` | 通知チャネルと言語 |
| `op_audit` | 操作監査（既定 ON、UDP 8991、保持 180 日） |
| `web` | Web UI（ポート 8990、`localadmin` のパスワードハッシュ） |

設定ファイル、データベース（`jt-glogarch.db`）、アーカイブファイルはそれぞれ独立しています。
すべての項目は [CONFIG.md](CONFIG.md) を参照してください。

---

## 操作監査のセットアップ（nginx）

操作監査は、各 Graylog ノードの nginx が送る JSON 形式のアクセスログ（UDP syslog）を受信して記録します。
機能自体は既定で有効なので、nginx 側の設定だけが必要です。Web UI の「操作監査」画面から、必要な
フィールドをすべて含む nginx 設定例をコピーできます。

**各 Graylog ノードで：**

1. `nginx.conf` の `http { }` ブロック内、`include` 行より **前** に `log_format graylog_audit` を追加します
   （`"http_cookie":"$cookie_authentication"` を含めてください。同じ IP の複数ユーザーを区別するのに必要です）。
2. Graylog のサイト設定に次の行を追加します（`JT_GLOGARCH_IP` は jt-glogarch サーバーの IP）。

   ```nginx
   access_log syslog:server=JT_GLOGARCH_IP:8991,facility=local7,tag=graylog_audit graylog_audit;
   client_body_buffer_size 64k;
   ```

3. `sudo nginx -t && sudo systemctl reload nginx`
4. **Graylog の 9000 番ポートへの直接アクセスを遮断します**（下記の理由を参照）。

   ```bash
   sudo ufw deny 9000
   sudo ufw allow from 127.0.0.1 to any port 9000
   sudo ufw allow from CLUSTER_NODE_IP to any port 9000   # クラスターの各ノードごとに
   ```

**jt-glogarch サーバーで：** `sudo ufw allow 8991/udp`

完全な設定例は英語版 README の
[Setup Operation Audit (nginx)](README.md#setup-operation-audit-nginx) を、記録される操作の一覧は
[AUDIT-OPERATIONS.md](AUDIT-OPERATIONS.md) を参照してください。

---

## 運用ガイド

### スケジュール運用

一般的な構成例：

| 種類 | 頻度の例 | 設定の例 |
|---|---|---|
| エクスポート | 毎日 03:00 | OpenSearch 直接モードで直近 N インデックス、または API モードで直近 N 日 |
| クリーンアップ | 毎月 1 日 04:00 | 保持日数（例：1095 日） |
| 検証 | 毎月第 1 土曜 03:00 | 全アーカイブの SHA256 再検証 |

- **エクスポートの重複排除：** すでにアーカイブ済みの時間範囲は自動でスキップされるため、「直近 N 日」を
  毎日実行しても新しい分だけが処理されます。
- **OpenSearch 直接モードは書き込み中のアクティブインデックスをスキップします。** ローテーション後に
  次回の実行で保存されます。
- **保持期間とディスク容量：** 既定の保持期間 1095 日（3 年）を実際に保持できるディスクは多くありません。
  ダッシュボードの「ハードウェアサイジング」カードに、設定した保持期間に必要な容量と、現在のディスクで
  保持できる月数が表示されます。ディスク容量が足りない場合は、ディスクを拡張するか `retention_days` を
  実態に合わせてください。ディスクカードには、実際の圧縮後サイズとログ期間から算出した「あと何か月分
  保存できるか」の見積もりも表示され、しきい値（既定 1 か月）を下回ると通知します。
- **大量の初回バックログ：** 初回に数年分を保存する場合、エクスポートが数日〜数週間続くことがあります。
  その間、同じスケジュールの次回実行はスキップされますが、実行中のエクスポートが進んでいれば正常です
  （タスクログに残り時間の目安が表示されます）。
- **DB バックアップ：** `glogarch db-backup`（オンラインスナップショット、世代数を指定して自動削除）を
  定期実行することを推奨します。DB を失ってもアーカイブファイルが残っていれば
  `glogarch db-rebuild` で再構築できます。

### アーカイブ失敗時の対応

まず Web UI の次の画面を確認します。

- **タスクログ** — 各ジョブの状態（実行中 / 完了 / 失敗 / キャンセル）、進捗、備考（エラーメッセージ）。
- **システムログ** — アプリケーションのイベント（既定で HTTP アクセスログは除外されています）。
  サーバー上では `journalctl -u jt-glogarch -f` でも確認できます。

よくある状況と対応：

| 状況 | 意味と対応 |
|---|---|
| ジョブに「一時停止 — ソース Graylog の負荷が高い」と表示され、件数が増えない | **意図的な一時停止です。** 負荷ガードが Graylog の JVM ヒープ、ジャーナル、バッファの上昇を検知して待機しています。負荷が下がると自動で再開します。キャンセルや再起動は不要です。頻発する場合は Graylog のヒープ増強（`-Xms` = `-Xmx`）、実行時間帯の変更、OpenSearch 直接モードの利用を検討してください。 |
| API モードの通知に「1 ミリ秒に 10,000 件を超えるメッセージ」があると表示される | Graylog REST API はページング上限（`index.max_result_window`、既定 10,000）を超えて読めないため、その 1 ミリ秒の超過分だけが取得できません。**その時間帯の他のデータはアーカイブ済みで、自動リトライはされません。** 該当時間帯を **OpenSearch 直接モード** でエクスポートしてください（v1.14.8 以降、不足分だけが重複なく補完されます）。毎日発生する環境では、エクスポート自体を OpenSearch 直接モードで運用してください。 |
| スケジュール実行が「ロック中」でスキップされる | 実行中のエクスポートがある場合は、そのジョブが進んでいれば正常です。実行中のエクスポートがないのにスキップが続く場合は、古いロックが残っています（通知されます）。サービスを再起動すると解消します。進んでいないジョブがある場合も通知されますが、負荷ガードによる一時停止中の可能性があるので、まずタスクログの表示を確認してください。 |
| API モードで `500 Result window is too large` | クラスターで `index.max_result_window` が 10,000 未満に下げられています。`PUT <index>/_settings {"index.max_result_window": 10000}` で既定値に戻してください。 |
| 「API token expired」 | Graylog の API トークンが無効です。設定画面でトークンを更新してください（通知も送られます）。 |
| `Permission denied`（`/data/graylog-archives/` への書き込み） | `sudo chown -R jt-glogarch:jt-glogarch /data/graylog-archives` |
| タスクログに「サービス再起動により中断」 | 共有 VM でメモリが不足し、OOM killer に停止された可能性があります。`dmesg -T \| grep -i oom` で確認し、[パフォーマンスとサイジング](#パフォーマンスとサイジング) を参照してください。未完了のチャンクは削除され、次回の実行で再取得されます。 |
| 検証で CORRUPTED | 保存後にファイルが変更されたか、ストレージのビット劣化です。元データが Graylog / OpenSearch に残っていれば、該当アーカイブを削除して同じ時間範囲を再エクスポートしてください。 |
| アーカイブのタイムラインに赤い印（欠落日） | その日のアーカイブが存在しません。該当範囲を手動でエクスポートしてください。 |

> **キャンセルについて：** エクスポートをキャンセルすると、途中までの 1 時間分のファイルは破棄され、
> 完了した時間単位だけが記録されます。次回の実行は破棄した時間から再開します。

### リストア手順とリストア訓練

#### GELF と Bulk の選び方

| | GELF（既定） | OpenSearch Bulk |
|---|---|---|
| 書き込み先 | 対象 Graylog の GELF Input（既定 TCP 32202） → 既定のインデックスセット | 専用のインデックスセット（既定 `jt_restored`） |
| Graylog の処理 | パイプライン、エクストラクター、ストリーム、アラートが適用されます | **すべてスキップ** されます |
| 本番データとの関係 | 本番のインデックスセットに混在します | 分離され、不要になれば削除しやすい |
| 重複 | 同じアーカイブを再インポートすると重複します | `gl2_message_id` を `_id` に使うため重複しません（既定） |
| 照合の精度 | Graylog の indexer failures 件数の差分（最大約 1 万件の循環バッファ） | `_bulk` 応答をドキュメント単位で確認（正確） |
| Data Node | 対応 | 非対応 |

- **GELF は TCP を使ってください。** TCP にはバックプレッシャーがあり、取りこぼしが起きません。
  UDP は受信側が追いつかないとエラーなしにパケットが失われます。
- Bulk でリストアしたデータは、ストリームルールが自動作成されないため、既定ストリームに入ります。
  検索時は「すべてのストリーム」を対象にするか、`_jt_glogarch_imported_at` の存在を条件とする
  ストリームルールを追加してください。

#### 手順

1. **アーカイブ一覧** で時間範囲やストリームで絞り込み、対象を選択して **一括インポート** を押します。
   フィルター結果が複数ページにわたる場合は、「フィルターに一致するすべてを選択」を使ってください
   （現在のページだけを選ぶと、範囲の一部しかリストアされません）。
2. モード（GELF / Bulk）を選び、**リストア先 Graylog の API URL と認証情報（必須）** を入力します。
   よく使うリストア先は、設定画面の「リストア先の既定値」に登録しておくと自動入力されます。
3. **プリフライトチェック** が自動で実行されます。
   - 認証情報の確認、クラスターの状態（RED なら中止）、GELF Input の存在と稼働状態
   - **容量チェック** — ローテーション・保持設定から作成されるインデックス数を計算し、削除型の保持設定で
     リストアしたデータがすぐ消えてしまう場合は警告します（「保持数を N に上げる」ボタンは、保持数を
     上げる方向にのみ変更します）。OpenSearch データディスクの空き容量も表示します。
   - **フィールドマッピングの競合解決** — アーカイブ内で数値と文字列が混在するフィールドや、リストア先で
     数値型になっているフィールドを、事前に文字列（keyword）として固定し、インデックスをローテーションします。
4. 送信中は一時停止・再開・速度調整ができます。リストア先のジャーナル、ヒープ、バッファ、および
   このホストの空きメモリを監視し、負荷が高いと自動で減速・一時停止します。
   「閉じる（実行を継続）」を押しても、インポートはバックグラウンドで継続します。
5. 完了後に **照合** が行われます。indexer failures が 0 件であれば完了、1 件以上なら
   「コンプライアンス違反を伴い完了」と記録されます。「再試行」で失敗したメッセージを再インポートできます
   （Bulk では失敗分だけが追加され、重複しません）。

> **リストア前にインデックスセットを空にする（破壊的操作）：** インポート画面には、選択したインデックス
> セットの既存データをすべて削除してから取り込むオプションがあります。書き込みインデックスを
> ローテーションしたうえで、それ以外のインデックスを削除します。インデックスのプレフィックスを入力して
> 確認する必要があり、元に戻せません。Graylog 内部のイベント用インデックスセットは表示されません。
> jt-glogarch のアーカイブファイルには影響しません。

#### リストア訓練（推奨）

「保存できている」ことと「必要なときに戻せる」ことは別です。定期的（例：四半期ごと）に次の訓練を
行い、結果を記録しておくことを推奨します。

1. **検証** — 検証スケジュールまたは `sudo -u jt-glogarch glogarch verify` を実行し、CORRUPTED /
   TAMPERED がないことを確認します。
2. **アーカイブ内検索で対象を確認** — 訓練対象の時間範囲（例：数か月前の 1 時間〜1 日）を検索し、
   想定したログが含まれていることを確認します。
3. **サンプル期間をリストア** — 本番とは別の検証用 Graylog、または Bulk モードの専用インデックスセットに
   インポートします。
4. **件数を照合** — アーカイブ一覧に表示されるその範囲のレコード数、インポートジョブの処理件数、
   リストア先 Graylog での検索件数を比較します。indexer failures が 0 件であることも確認します。
   - 注意：アーカイブの時刻表示とリストア先の検索時刻は、タイムゾーンの扱いによりずれて見えることが
     あります。照合時は前後に余裕を持った時間範囲で検索してください。
5. **後片付け** — Bulk で作成したストリーム・インデックスセットは `glogarch streams-cleanup` で削除できます。

CLI でのリストア例（サービス稼働中のホストでは、SQLite のロックを避けるため Web UI または
`POST /api/import` の利用を推奨します）：

```bash
sudo -u jt-glogarch glogarch -c /opt/jt-glogarch/config.yaml import \
  --from 2026-04-07 --to 2026-04-09 \
  --mode bulk \
  --target-api-url http://192.168.1.20:9000 \
  --target-api-username admin \
  --target-api-password 'YOUR_PASSWORD' \
  --target full-restore
```

### 通知

- **チャネル：** Telegram（Bot トークン、Chat ID）、Discord / Slack / Microsoft Teams（Webhook URL）、
  Nextcloud Talk（サーバー URL、トークン、ユーザー名、パスワード）、Zulip（サーバー URL、ボットのメールアドレス、API キー、ストリーム、トピック）、Email（SMTP ホスト、ポート、TLS、
  ユーザー、パスワード、送信元、宛先）。
- **言語：** English / 繁體中文 / 日本語。テスト通知を含むすべての通知に適用されます。
- **トリガー：** エクスポート完了、インポート完了、クリーンアップ完了、エラー、検証失敗、重要操作
  （操作監査）、監査アラート（10 分以上 syslog を受信していない）。
- 通知には結果の区分が明示されます：成功 / 超過（アーカイブ済み・リトライ不要・OpenSearch 直接モードで
  補完）/ 実際のチャンク失敗（未保存・次回リトライ）。
- 設定画面の「テスト通知」で、有効なチャネルすべてに送信を確認できます。
- メールの送信元（`from_addr`）はドメインを含む実在のアドレスにしてください。

---

## 完全性と監査の範囲（できること・できないこと）

正式な監査・コンプライアンス手順に組み込む前に、次の範囲を確認してください。

### アーカイブの完全性

| 仕組み | できること | できないこと |
|---|---|---|
| **SHA256**（常時） | 保存後の偶発的な変更（ストレージの劣化、誤操作）を検出します | ファイルと DB の SHA256 値を **両方** 書き換えられると検出できません |
| **HMAC-SHA256**（オプション、既定 OFF） | 秘密鍵がなければ、整合する値を偽造できません。不一致は TAMPERED として区別して通知します | 鍵をホスト上に置いた場合、root やサービスユーザーは鍵を読めるため防げません。すでに改ざんされたファイルを後から封印しても、封印時点以降のことしか証明できません。鍵を失うと SHA256 のみの検証に戻ります |
| **機外マニフェスト**（`integrity-manifest`） | ハッシュ台帳をホスト外に保管すれば、ファイルと DB を書き換える root 権限の攻撃者も、外部コピーとの照合で検出できます | マニフェストをホスト外に移さなければ効果がありません |

```yaml
integrity:
  enabled: true
  hmac_key_file: /opt/jt-glogarch/.hmac_key   # または環境変数 JT_HMAC_KEY
  ledger_enabled: true
```

```bash
sudo -u jt-glogarch glogarch integrity-init      # 鍵を生成（必ずホスト外にバックアップ）
# config.yaml で integrity.enabled: true に設定してから：
sudo -u jt-glogarch glogarch integrity-seal      # 既存アーカイブを封印（封印時点以降を証明）
sudo -u jt-glogarch glogarch verify              # TAMPERED（HMAC 不一致）と CORRUPTED（SHA256）を区別
sudo -u jt-glogarch glogarch integrity-manifest -o /off-box/manifest.json   # 台帳をホスト外へ
```

- 鍵の優先順位：環境変数 `JT_HMAC_KEY`（base64 / hex）> `hmac_key_file`（パーミッション 0600）。
- root に対しても有効にするには、鍵ファイルを置かず、封印・検証時にのみ `JT_HMAC_KEY` を渡し、
  マニフェストをホスト外に保管してください。

> **これは改ざん「検知」であり、改ざん不可能なストレージ（WORM）ではありません。**
> root やサービスユーザーは、アーカイブファイルを削除・上書きできます。jt-glogarch が保証するのは
> 「変更されたことが分かる」ことであり、「変更・削除できない」ことではありません。
> 削除・変更そのものを防ぐ必要がある場合は、WORM ストレージやオブジェクトロック付きのストレージに
> アーカイブを複製し、マニフェストを別の管理者が管理する場所に保管してください。

### 操作監査

| できること | できないこと・前提条件 |
|---|---|
| nginx を経由した Graylog への操作を、ユーザー・送信元 IP・リクエスト本文付きで記録します | **nginx を経由しないリクエストは記録されません。** Graylog の 9000 番ポートに直接アクセスできる状態では、その操作は監査対象外です |
| 記録は Graylog とは別の jt-glogarch 側 DB に保存され、Graylog の管理者権限では削除できません | jt-glogarch ホストの root は DB を変更・削除できます。監査記録は Graylog 管理者からは独立していますが、jt-glogarch ホストの管理者からは独立していません |
| syslog が 10 分以上届かない場合（Graylog は稼働中）にハートビート警告を出します | UDP syslog のため、ネットワーク上で個々のログが失われる可能性はあります |
| 重要操作（ユーザー削除、認証設定の変更など）を即時通知できます | ユーザー名の特定は Authorization ヘッダー、トークン、セッション、Cookie の順に行います。nginx のログに `$cookie_authentication` がないと、同じ IP の複数ユーザーを区別できません |

**推奨事項：**

- Graylog の HTTP を `127.0.0.1` にバインドするか、ファイアウォールで 9000 番ポートを localhost と
  クラスターノード間だけに制限し、**すべての利用者が nginx を経由する** 構成にしてください。
- クラスターのすべての Graylog ノードに nginx の設定を行ってください。
- jt-glogarch ホストの root 権限は、Graylog の管理者とは別の担当者が管理することを推奨します。
- 監査記録の保持期間（`op_audit.retention_days`、既定 180 日）はアーカイブの保持期間とは独立しています。
  1 日 1,000 操作で年間約 360 MB が目安です。

---

## パフォーマンスとサイジング

### ハードウェアサイジング（同一 VM に共存させる場合）

最も一般的な構成は、jt-glogarch をリストア先の Graylog + OpenSearch（+ MongoDB）と **同じ VM** に置く
構成です。制約になるのはメモリです。2 つの JVM と OpenSearch が必要とするページキャッシュで小さな VM は
すぐに埋まり、大きなインポートでスワップ（極端に遅くなる）や OOM killer（ジョブが「サービス再起動により
中断」になる）が発生します。

jt-glogarch は **このホスト自身の値から推奨構成を計算** します。ダッシュボードの
**ハードウェアサイジング** カード（または `GET /api/sizing`）で、`/proc/meminfo`、CPU 数、稼働中の
Graylog / OpenSearch の `-Xmx` とアーカイブ数を基に表示します。目安：

| 構成 | メモリ | コア数 |
|---|---|---|
| アーカイブ専用ノード（Graylog / OpenSearch は別ホスト） | 4 GB | 4 |
| 同一 VM・軽量（アーカイブ 1 万件未満） | 16 GB | 8 |
| 同一 VM・大規模（アーカイブ 1 万件以上 / 大量インポート） | **32 GB** | **16 以上** |

表よりも重要なルール：

- **スワップを使わせないこと。** スワップの継続使用は、インポートが遅くなる最大の兆候です。
- **2 つの JVM ヒープの合計はメモリの 50% 以下に。** OpenSearch はヒープとほぼ同量のページキャッシュを
  必要とします。
- 両方の JVM で **`-Xms` = `-Xmx`** とし、それぞれ 31 GB 以下にしてください。
- MongoDB、カーネル、エージェント用に 2〜3 GB の余裕を残してください。

jt-glogarch 自体の常駐メモリは約 200 MB で、アーカイブはストリーミングで処理します。リストア先の負荷や
ホストの空きメモリが少ないときは、バッチサイズを自動で縮小して処理を続けます。

### インポートモードごとの負荷

- **GELF インポート** は Graylog（ヒープ、ジャーナル、バッファ）に負荷がかかります。まず Graylog の
  `-Xmx` を増やしてください。
- **Bulk インポート** は OpenSearch に直接書き込みます（ヒープとページキャッシュ）。Graylog のヒープは
  ほとんど影響しません。Bulk も OpenSearch のヒープとホストのメモリを監視し、自動で減速・一時停止します。

### エクスポート速度（既定設定での参考値）

| モード | batch_size | delay | 速度 | 1 時間分（約 17.5 万レコード） |
|---|---|---|---|---|
| Graylog API | 1,000 | 5ms | 約 730 レコード/秒 | 約 4 分 |
| OpenSearch 直接 | 10,000 | 2ms | 約 3,300 レコード/秒 | 約 1 分 |

これらは参考値であり、ハードウェア、ストレージ、メッセージサイズ、クラスターの負荷によって大きく
変わります。容量計画の前に、ご利用の環境で数時間分のエクスポートとリストアを実行して実測することを
推奨します。Data Node 環境では OpenSearch 直接モードの値は当てはまりません。

### モードの選び方

**Graylog API モード：** ストリーム単位で保存したい、OpenSearch に直接接続できない（Data Node を含む）、
Graylog の保持期間内のデータにアクセスしたい場合。

**OpenSearch 直接モード：** 大量の過去データを速く保存したい、OpenSearch の認証情報がある、
1 ミリ秒に 10,000 件を超えるバーストがある場合。

大量のバックログを低速なストレージで処理する場合は、OpenSearch 直接モード + 負荷ガード + 夜間などの
閑散時間帯での実行を推奨します。

---

## CLI リファレンス（抜粋）

日常の操作は Web UI が中心で、CLI は自動化・スクリプト向けです。

| コマンド | 説明 |
|---|---|
| `glogarch server` | Web UI + スケジューラーを起動（systemd が実行） |
| `glogarch export` | 手動エクスポート（`--mode api\|opensearch --days 180`） |
| `glogarch import` | アーカイブのインポート（`--mode gelf\|bulk`） |
| `glogarch list` | アーカイブ一覧 |
| `glogarch verify` | 完全性検証（`--workers N` で並列） |
| `glogarch cleanup` | 保持期間を過ぎたアーカイブの削除 |
| `glogarch integrity-init` / `integrity-seal` / `integrity-manifest` | HMAC による改ざん検知 |
| `glogarch db-backup` | SQLite のオンラインスナップショット（`--keep N`） |
| `glogarch db-rebuild` | ディスク上のアーカイブファイルから DB を再構築 |
| `glogarch streams-cleanup` | Bulk インポートで作成したストリーム・インデックスセットの一覧・削除 |
| `glogarch hash-password` | `localadmin` 用パスワードハッシュの生成 |
| `glogarch status` | システム状態 |

全コマンドは `glogarch --help` または英語版の [CLI Reference](README.md#cli-reference) を参照してください。

---

## FAQ

### OS をアップグレード（例：Ubuntu 22.04 → 24.04）した後、サービスが再起動を繰り返す

`journalctl -u jt-glogarch` に `ModuleNotFoundError: No module named 'glogarch'`（または `fastapi`、
`click` など）と表示されます。OS のメジャーアップグレードで `python3` が変わり（22.04 は 3.10、24.04 は
3.12）、古い Python 用に pip でインストールしたものはすべて新しい Python から見えなくなります。アーカイブ、
データベース、設定は変更されておらず、データは失われていませんが、新しい Python 用に再インストールするまで
サービスは起動できません。OS のアップグレード（と再起動）の**後に**、通常のアップグレードを 1 回実行して
ください。

```bash
sudo bash /opt/jt-glogarch/deploy/upgrade.sh
```

Python が変わったことを表示し、まずデータベースをバックアップしてから、jt-glogarch とすべての依存パッケージ
（PDF レポート用のブラウザーを含む）を新しい Python 用に再インストールし、サービスを再起動して、正常に
動作していることとすべてのスケジュールが登録されていることを確認します。その後
`/usr/local/lib/python3.10/` は使われなくなります。**インターネットに接続できない**ホストには、現在の
ホストと同じ Python で作成したオフラインバンドルが必要です（例：3.12 用は `docker run ubuntu:24.04` の中で
作成）。古い Python 用のバンドルは、何も変更しないうちに拒否されます。


### アップグレード後に PDF レポートが失敗する：「Executable doesn't exist at …/chromium_headless_shell-NNNN/…」

影響を受けるのは PDF レポートだけで、アーカイブ、リストア、その他の機能は通常どおり動作します。アップグレード
で新しい Playwright がインストールされ、`/opt/jt-glogarch/.playwright/` にあるものより新しい Chromium が必要に
なっています（例：`chromium-1228` があり、`…-1243` が必要）。v1.16.2 より前のアップグレードは「Chromium が
ある」と判断して処理を飛ばしていましたが、v1.16.2 からは必要なビルドを確認してダウンロードします。インター
ネットに接続できるホストでは、次の手順ですぐに直せます。

```bash
sudo PLAYWRIGHT_BROWSERS_PATH=/opt/jt-glogarch/.playwright python3 -m playwright install chromium
sudo chown -R jt-glogarch:jt-glogarch /opt/jt-glogarch/.playwright
sudo bash -c 'source /opt/jt-glogarch/deploy/report-deps.sh && verify_report_engine'
```

サービスの再起動は不要です。インターネットに接続できないホストは、新しいバージョン用に作成したオフライン
バンドル（対応する Chromium を含む）でアップグレードしてください。


### 工場出荷状態に戻す（再初期化する）には？

次の 3 つは **独立して** 保存されています。どれを消すのかを確認してください。

| 項目 | 場所 | 内容 |
| --- | --- | --- |
| 設定 | `/opt/jt-glogarch/config.yaml` | 接続、スケジュール、通知、`localadmin` パスワード、パス |
| データベース | `/opt/jt-glogarch/jt-glogarch.db` | アーカイブ記録、ジョブ履歴、監査記録 |
| アーカイブファイル | `/data/graylog-archives/` | 実際のログファイル（実データ） |

**設定だけを初期化し、アーカイブは残す（最も一般的）：**

```bash
sudo systemctl stop jt-glogarch
sudo mv /opt/jt-glogarch/config.yaml /opt/jt-glogarch/config.yaml.bak   # バックアップしてから削除
sudo systemctl start jt-glogarch
```

- **サービスの再起動が必要です。** 設定は起動時にメモリに読み込まれるため、ファイルを削除しただけでは
  変わりません。
- 別の検索場所（`~/.jt-glogarch/config.yaml`、`/etc/jt-glogarch/config.yaml`）に設定ファイルがある場合は、
  それも移動してください。
- アーカイブ一覧が空に見える場合は、ウィザードで保存先を元に戻したあと、次のコマンドで DB を再構築します。

  ```bash
  sudo -u jt-glogarch glogarch db-rebuild
  ```

**完全に削除する（アーカイブデータも削除・元に戻せません）：**

```bash
sudo systemctl stop jt-glogarch
sudo rm -f /opt/jt-glogarch/config.yaml
sudo rm -f /opt/jt-glogarch/jt-glogarch.db /opt/jt-glogarch/glogarch.db*   # アーカイブ記録、ジョブ履歴、監査
sudo rm -rf /data/graylog-archives/*                                       # ⚠ アーカイブしたログファイル自体を削除します
sudo systemctl start jt-glogarch
```

### Graylog に接続できないときのログインは？

初期設定ウィザードの最後で設定した `localadmin` アカウントでログインできます。手動でハッシュを生成する
場合は `sudo -u jt-glogarch glogarch hash-password` を実行し、`config.yaml` の
`web.localadmin_password_hash` に設定します。

### クリーンアップが保持日数より早く削除する / ディスクがいっぱいになる

既定の `retention_days` は 1095 日（3 年）ですが、実際にこれを保持できるディスクは多くありません。
ディスクが先に足りなくなれば、実質的な保持期間は短くなります。ダッシュボードの
「ハードウェアサイジング」カードで、必要な容量と実際に保持できる月数を確認し、ディスクを拡張するか
保持日数を実態に合わせてください。スケジュール画面に表示されるクリーンアップの保持日数が、実際に
適用されている値です。

### スケジュールが想定した時刻に実行されない

スケジューラーはシステムのタイムゾーンを使います。`timedatectl` で確認し、
`sudo timedatectl set-timezone Asia/Tokyo` の後に `sudo systemctl restart jt-glogarch` を実行してください。

### OS のメジャーアップグレード後にサービスが起動しない（`ModuleNotFoundError: No module named 'glogarch'`）

OS のアップグレードでシステムの Python が変わると、以前のインストールが使えなくなります。
インストーラーを再実行してください：`sudo bash /opt/jt-glogarch/deploy/install.sh`

### オンラインアップグレードが「Not possible to fast-forward, aborting」で止まる

2026-09-13 に公開履歴が書き換えられたため、それ以前に clone したインストールで発生します。
アップグレードは何も変更せずに停止し、稼働中のサービスには影響しません。v1.14.11 以降は自動で回復します。
それより古い場合は、オフラインバンドルを使うか、次を 1 回実行してください
（`config.yaml`、DB、`certs/`、`reports/` は git の管理外なので影響しません）。

```bash
cd /opt/jt-glogarch
sudo git fetch origin
sudo git reset --hard origin/main
sudo bash deploy/upgrade.sh
```

### Web UI にログインしたのに「Not authenticated」になる

自己署名証明書のため、ブラウザーが Cookie を拒否している可能性があります。証明書の警告画面で続行する、
シークレットウィンドウで開く、または正式な証明書を使ってください。

### 同じ Graylog に対して jt-glogarch を 2 台動かせますか？

可能です。ただしアーカイブの保存先は別にしてください。DB はそれぞれ独立しています。

### 「ストリーム」と「インデックス」の違いは？

- **ストリーム** = Graylog の論理的な分類（例：「すべての認証ログ」）
- **インデックス** = OpenSearch の保存単位（定期的にローテーション）

API モードはストリーム単位、OpenSearch 直接モードはインデックス単位で動作します。

### その他

英語版の [Troubleshooting / FAQ](README.md#troubleshooting--faq) も参照してください。

---

## ライセンス

**ライセンス：** [GNU AGPL v3 or later](LICENSE)

**作者：** Jason Cheng — [Jason Tools](https://github.com/jasoncheng7115)

**リポジトリ：** https://github.com/jasoncheng7115/jt-glogarch

### サードパーティライセンス

- [Iconoir](https://iconoir.com) — MIT License（埋め込み SVG アイコン）
- [FastAPI](https://fastapi.tiangolo.com) — MIT License
- [APScheduler](https://apscheduler.readthedocs.io) — MIT License

詳細は [THIRD-PARTY-LICENSES.md](THIRD-PARTY-LICENSES.md) を参照してください。
