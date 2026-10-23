# tlc-static

TLA+ TLC を JVM 不要の実行ファイルとして配布します。

**[GitHub Releases からダウンロード](https://github.com/yashikota/tlc-static/releases/latest)**

| OS | amd64 / x86_64 | arm64 / AArch64 |
| --- | --- | --- |
| Linux | 完全静的 musl | 完全静的 musl（GraalVM ベースの Liberica NIK） |
| macOS | Intel ネイティブ | Apple Silicon ネイティブ |
| Windows | x64 ネイティブ | x64 エミュレーション版（Windows 11 ARM64 で検証） |

Linux 版は JVM・共有ライブラリ・動的ローダー不要で、scratch コンテナでも実行できます。macOS／Windows 版は OS のライブラリに依存するネイティブ実行ファイルで、完全静的ではありません。Windows ARM64 版の中身は x64 実行ファイルです。GraalVM CE の Windows ARM64 用 Native Image 配布がないため、ARM64 ネイティブを意味しない `emulated` という名前で配布します。

標準 TLA+ モジュールは埋め込み済みです。任意の `.tla` と `.cfg` を実行時に読み込めます。Java override や CommunityModules の JAR を後から追加する場合は再ビルドが必要です。

## 使い方

Releases の対象アーカイブを展開します。Linux／macOS:

```sh
./tlc -Xmx2g -workers 2 -config Model.cfg Model.tla
# 同梱モデルで確認
./tlc -Xmx512m -workers 2 -fpmem 0.1 -noGenerateSpecTE examples/Counter.tla
```

Windows PowerShell:

```powershell
.\tlc.exe -Xmx2g -workers 2 -config Model.cfg Model.tla
```

作業ディレクトリと一時ディレクトリに書き込み権限が必要です。macOS 版は未署名・未公証です。

各アーカイブには実行ファイル、モデル例、ライセンス、ビルド情報 `BUILD.json`、検証ログを含みます。Releases の `SHA256SUMS` はアーカイブのハッシュ、アーカイブ内の `SHA256SUMS` は実行ファイルのハッシュです。

## GitHub Actions でのリリース

[release.yml](.github/workflows/release.yml) は `v*` タグの push で起動します。

```sh
git tag v0.1.0
git push origin v0.1.0
```

OS／CPU ごとのネイティブランナーで5種類をビルドし、Windows ARM64 ランナーで x64 版を追加検証します。すべて成功した場合だけ6種類と `SHA256SUMS` を GitHub Releases に公開します。手動の workflow_dispatch は検証用で、タグ ref 以外からはリリースを公開しません。各ターゲットのログも Actions artifacts に保存します。

固定しているビルド入力:

- TLA+ commit: `606dfa48298a1b36c4ee4625c705041c35bd7393`
- Linux amd64: GraalVM CE 25.0.2 + musl、コンテナ digest 固定
- Linux arm64: Liberica NIK 25.0.4.1 + musl、コンテナ digest 固定
- macOS／Windows: GraalVM CE 24.0.2（macOS Intel の配布を含むバージョン）
- Ant 1.10.15: SHA-256 検証
- GitHub Actions: commit SHA 固定

上流ソースにパッチは当てません。`configure.py` で標準 Java モジュールと FPSet 実装のリフレクションを登録し、必要なリソースを埋め込みます。上流がビルド時刻を埋め込むため、ビット単位の同一性は保証しません。

## ローカルビルド

Linux は Docker、Git、Python 3、binutils が必要です。macOS／Windows は GraalVM CE 24.0.2、C ツールチェーン、Git、Python 3 を用意します。Windows は MSVC Developer Shell から実行してください。

```sh
python ci/build.py --target linux-amd64
# その他: linux-arm64 / macos-amd64 / macos-arm64 / windows-amd64
```

ホストの OS／CPU と同じターゲットを指定します。Linux 用の musl ビルドは Docker 内で実行します。約8 GiBの空きメモリを推奨します。出力は `release/`、ログは `ci-logs/` です。従来の Linux amd64 用 `build.sh` も利用できます。

## 検証と制限

同じ JAR の JVM 実行と比較し、安全性、WF を含む活性、不変条件違反と活性違反の反例・終了コード、シミュレーション、DFID、上流 Bakery モデルを検証します。Linux は ELF の INTERP／NEEDED がないことと、scratch コンテナ実行を検証します。[検証内容](VERIFICATION.md)も参照してください。

配布の入口は `tlc2.TLC` のみです。Toolbox、SANY CLI、PlusCal CLI は含みません。分散 TLC、REPL、メール送信、チェックポイント回復、大規模モデルの性能は未検証です。Native Image の Serial GC は JVM の Parallel GC と性能特性が異なります。Windows 版は JFR 記録を有効にしていません。

## ライセンス

ビルド用コードは [MIT License](LICENSE)。TLA+ 本体は [TLAplus-LICENSE.txt](TLAplus-LICENSE.txt)、配布バイナリの依存ライセンスはアーカイブ内の `licenses/` を参照してください。

対応範囲の根拠: [GraalVM CE 配布](https://github.com/graalvm/graalvm-ce-builds/releases/tag/jdk-24.0.2)、[Liberica NIK 対応環境](https://bell-sw.com/pages/nik-supported-configurations/)、[GitHub hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)。
