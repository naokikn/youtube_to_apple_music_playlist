# youtube-apple-music-playlist

YouTubeプレイリストの各動画説明欄を `yt-dlp` で取得し、1つの動画に複数曲が記載されている場合も含めて、LLMで曲名・アーティスト名を手動抽出した結果を MusicBrainz と iTunes Search API で確認して、MacショートカットからApple Musicプレイリスト作成に使える入力ファイルを生成するツールです。

Apple Musicへの実登録はMacのショートカットアプリとMusicアプリで行います。このプロジェクトではApple Music API、Developer Token、有料Apple Developer Programには依存しません。

## 1. このツールの目的

YouTubeプレイリスト内の動画説明欄には、BGM、使用曲、Tracklist、タイムスタンプ付き曲リストとして、1つの動画に複数曲が書かれていることがあります。このツールは、その説明欄をまとめて取得し、LLMで曲名・アーティスト名を抽出し、実在確認とApple系カタログ候補確認をしたうえで、Macショートカットに渡せる `workflow/04_validated/shortcuts_tracks.txt` を作ります。

Python側ではYouTube説明欄から曲名を自動推測しません。曲名・アーティスト名の抽出は、`workflow/02_descriptions/descriptions.json` をLLMへ手動投入して行います。

## 2. 全体ワークフロー

```text
YouTube Playlist URL
  workflow/00_input/playlist_url.txt
  ↓
yt-dlp playlist_items.jsonl
  workflow/01_ytdlp/playlist_items.jsonl
  ↓
Python descriptions.json
  workflow/02_descriptions/descriptions.json
  ↓
LLM手動抽出 llm_tracks.json
  workflow/03_llm/llm_tracks.json
  ↓
MusicBrainz / iTunes確認 cleaned_tracks.json / shortcuts_tracks.txt / shortcuts_tracks.csv
  workflow/04_validated/
  ↓
Macショートカット Apple Musicプレイリスト作成・曲追加
```

## 3. 無料APIだけでできる範囲

- `yt-dlp` でYouTubeプレイリストのメタデータと説明欄を取得する
- MusicBrainzで曲・録音物としての実在確認をする
- iTunes Search APIでApple系カタログ上の候補を確認する
- MacショートカットでMusicアプリを操作し、プレイリスト作成と曲追加を行う

Apple Music APIによる直接操作は、このプロジェクトでは使いません。

## 4. YouTube取得に yt-dlp を使う理由

- YouTube Data APIキーが不要
- プレイリストURLだけで取得できる
- 動画説明欄をまとめてJSON Lines化できる
- ローカル処理として扱いやすい

## 5. Apple Music APIを使わず、Macショートカットで登録する理由

- Apple Music APIでユーザーのライブラリやプレイリストを直接操作するには認可が必要
- Developer Tokenなどの準備が重い
- 無料API中心の構成では、Apple Music登録部分をMacショートカットに任せる方が現実的
- 最初は候補確認ありで運用する方が誤追加を避けやすい

## 6. 事前準備

- Python 3.11+
- `yt-dlp`
- MusicBrainz User-Agent
- Macのショートカットアプリ
- Apple Musicアプリ

## 7. セットアップ手順

```bash
git clone <this-repo>
cd youtube-apple-music-playlist

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

yt-dlpのインストール:

```bash
brew install yt-dlp
```

代替:

```bash
python -m pip install yt-dlp
```

MusicBrainz User-Agent設定:

```bash
export MUSICBRAINZ_USER_AGENT="youtube-apple-music-playlist/0.1 (your-email@example.com)"
```

`.env.example` は例示用です。このツールは `.env` の読み込みを必須にしていないため、基本は環境変数で設定してください。

## 8. 実行手順

```bash
# 1. playlist URLを入力
mkdir -p workflow/00_input
echo "https://www.youtube.com/playlist?list=PLxxxx" > workflow/00_input/playlist_url.txt

# 2. yt-dlpでプレイリスト内動画情報をJSONL化
bash scripts/01_fetch_playlist_items_with_yt_dlp.sh

# 3. JSONLをLLM投入用descriptions.jsonへ変換
python scripts/02_convert_playlist_items_to_descriptions.py

# 4. workflow/02_descriptions/descriptions.json をLLMへ渡す
#    prompts/llm_extract_tracks_prompt.md を使って曲名・アーティスト名を抽出する

# 5. LLM出力を workflow/03_llm/llm_tracks.json として保存

# 6. MusicBrainz + iTunes Search APIで検証
python scripts/03_validate_with_musicbrainz_itunes.py

# 7. workflow/04_validated/shortcuts_tracks.txt をMacショートカットへ渡す
```

## 9. LLM抽出プロンプトの使い方

1. `prompts/llm_extract_tracks_prompt.md` を開きます。
2. プロンプト本文の末尾に `workflow/02_descriptions/descriptions.json` の内容を貼り付けます。
3. LLMに送信し、JSONのみで返させます。
4. 返ってきたJSONを `workflow/03_llm/llm_tracks.json` として保存します。
5. `python scripts/03_validate_with_musicbrainz_itunes.py` を実行します。

LLMの出力に説明文やMarkdownコードフェンスが混ざっている場合は、JSON本体だけを保存してください。

## 10. MusicBrainz / iTunes確認の説明

MusicBrainzは、曲・録音物としての実在確認に使います。`recording:"曲名" AND artist:"アーティスト名"` 形式でRecording Search APIを呼び、最上位候補のスコア、録音ID、タイトル、アーティスト、ISRCを保存します。

iTunes Search APIは、Apple系カタログ上に候補があるかを確認するために使います。`country=JP`, `media=music`, `entity=song`, `limit=5` で検索し、最上位候補を保存します。

iTunes Search APIで見つかっても、Apple Musicで必ず追加できるとは限りません。同名曲、ライブ版、リマスター版、カバー版、別アーティスト版などの誤マッチに注意してください。

## 11. Macショートカットの作り方

ショートカットアプリで、概念的に次の流れを作ります。最初は完全自動追加ではなく、候補確認ありを推奨します。

```text
1. ファイルを選択
   → workflow/04_validated/shortcuts_tracks.txt
2. テキストを取得
3. テキストを改行で分割
4. プレイリスト名を尋ねる
5. Musicで新規プレイリスト作成
6. 各行について繰り返し
   - iTunes Storeを検索
   - 種類: music / song
   - 検索語: Repeat Item
   - 件数: 1 または 5
7. 候補が1件なら追加
   候補が複数なら選択
   見つからなければスキップまたはログに残す
8. Musicプレイリストに追加
```

実運用では、`workflow/04_validated/shortcuts_tracks.csv` を先に確認し、`CHECK_MANUALLY` の曲を見直してからショートカットへ渡すと誤追加を減らせます。

## 12. 出力ファイルの説明

- `workflow/00_input/playlist_url.txt`: ユーザーがYouTubeプレイリストURLを1行で入れるファイルです。
- `workflow/01_ytdlp/playlist_items.jsonl`: `yt-dlp` が作るJSON Lines。1行につき1動画分のメタデータが入ります。
- `workflow/02_descriptions/descriptions.json`: LLMへ渡す説明欄データ。説明欄は加工せず全文を保存します。
- `workflow/03_llm/llm_tracks.json`: ユーザーがLLMから得た曲名・アーティスト名抽出結果を保存するファイルです。
- `workflow/04_validated/cleaned_tracks.json`: MusicBrainzとiTunes Search APIの確認結果、ステータス、ショートカット用検索語を含む詳細JSONです。
- `workflow/04_validated/shortcuts_tracks.txt`: Macショートカットへ渡すための `Artist - Song Title` 形式のテキストです。初期設定では `OK_APPLE_FOUND` と `CHECK_MANUALLY` のみ出力します。
- `workflow/04_validated/shortcuts_tracks.csv`: Excelで確認しやすいUTF-8 BOM付きCSVです。

## 13. ステータスの意味

- `OK_APPLE_FOUND`: iTunes Search APIで候補があり、MusicBrainzでも候補があり、MusicBrainz score が80以上。
- `CHECK_MANUALLY`: iTunes Search APIでは候補があるが、MusicBrainz未検出またはscoreが80未満。
- `NOT_FOUND_APPLE`: MusicBrainzでは候補があるが、iTunes Search APIでは候補がない。
- `NOT_FOUND_MUSICBRAINZ`: MusicBrainzにもiTunes Search APIにも候補がない。
- `DUPLICATE`: `raw_artist + raw_title` の小文字化キーが既出。`cleaned_tracks.json` には残しますが、`shortcuts_tracks.txt` には出しません。
- `SKIP`: artist または title が空、null、または明らかに不正。

## 14. よくある問題

- `yt-dlp: command not found`: `brew install yt-dlp` または `python -m pip install yt-dlp` を実行してください。
- プレイリストが非公開で取得できない: 公開プレイリストURLか確認してください。
- 年齢制限・地域制限・ログイン必須動画が取得できない: `yt-dlp` 側で取得できない動画はスキップされることがあります。
- 説明欄が空: `description` は空文字として保存されます。LLM抽出では曲なしとして扱ってください。
- `playlist_items.jsonl` の一部行がJSON parse errorになる: 変換スクリプトは警告を出して該当行だけスキップします。
- `workflow/03_llm/llm_tracks.json` がJSON parse errorになる: LLM出力にMarkdownコードフェンス、説明文、スマートクォート `“ ”`、末尾カンマが混ざっていないか確認してください。JSONのキーと文字列は半角ダブルクォート `"` で囲む必要があります。
- MusicBrainzで見つからない: 表記揺れ、未登録曲、カバー、リミックス、YouTube独自表記の可能性があります。
- iTunesでは見つかるがMusicBrainzでは見つからない: `CHECK_MANUALLY` として手動確認してください。
- 同名曲・ライブ版・リマスター版の誤マッチ: `workflow/04_validated/shortcuts_tracks.csv` の候補名とURLを確認してください。
- ショートカットで曲が追加できない: iTunes Search API上の候補とApple Musicアプリ上で追加可能な曲が一致しないことがあります。候補選択ありで運用してください。

## 15. 注意事項

- YouTube説明欄の記載が不正確な場合があります。
- MusicBrainzは無料ですが、レート制限を守ってください。
- このツールはMusicBrainz APIへのアクセスを1.1秒以上空けます。
- iTunes Search APIはApple Musicの自分のライブラリ操作APIではありません。
- Apple Music APIはこのプロジェクトでは使いません。
- 最初は完全自動追加ではなく候補確認ありで運用するのが安全です。

## プロジェクト構成

```text
youtube-apple-music-playlist/
  README.md
  requirements.txt
  .env.example
  .gitignore
  prompts/
    llm_extract_tracks_prompt.md
  examples/
    playlist_items.example.jsonl
    llm_tracks.example.json
  workflow/
    00_input/
      playlist_url.txt
    01_ytdlp/
      playlist_items.jsonl
    02_descriptions/
      descriptions.json
    03_llm/
      llm_tracks.json
    04_validated/
      cleaned_tracks.json
      shortcuts_tracks.txt
      shortcuts_tracks.csv
  src/
    __init__.py
    config.py
    convert_yt_dlp_jsonl.py
    validate_tracks.py
    models.py
    utils.py
  scripts/
    01_fetch_playlist_items_with_yt_dlp.sh
    02_convert_playlist_items_to_descriptions.py
    03_validate_with_musicbrainz_itunes.py
```

## 開発者向けメモ

- JSONは `ensure_ascii=False, indent=2` で出力します。
- CSVはExcelで開きやすいように `utf-8-sig` で出力します。
- `src/config.py` でプロジェクトルートを `Path(__file__).resolve()` から解決します。
- `workflow/04_validated/shortcuts_tracks.txt` に出すステータスは `src/config.py` の `SHORTCUTS_INCLUDED_STATUSES` で変更できます。
- MusicBrainzやiTunes Search APIの通信エラーは、可能な範囲で各曲の結果に `error` として残して処理を継続します。
