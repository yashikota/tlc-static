# TLC: GraalVM + musl 完全静的バイナリ

Linux x86_64 向けの TLC (`tlc2.TLC`) です。Java のインストールも JAR の配置も不要です。標準 TLA+ モジュールは実行ファイルに埋め込まれています。

```sh
chmod +x tlc
./tlc -Xmx2g -workers 2 -config Model.cfg Model.tla
```

`-Xmx` と `-Dname=value` は GraalVM Native Image の実行時オプションです。書き込み可能な `/tmp` とモデル検査の作業ディレクトリを用意してください。

## ダウンロード

[Linux x86_64 配布アーカイブ](artifacts/tlc-static-linux-x86_64.tar.gz) · [ビルド用キット](artifacts/tlc-static-build-kit.tar.gz) · [SHA-256](artifacts/ARCHIVE-SHA256SUMS)

## ビルド

Docker、Git、curl、Python 3、binutils、file、約 8 GiB の空きメモリが必要です。

```sh
./build.sh
```

- TLC ソース: `tlaplus/tlaplus` commit `606dfa48298a1b36c4ee4625c705041c35bd7393`
- GraalVM CE 25.0.2 (Java 25)
- musl 対応公式イメージを digest で固定
- Apache Ant 1.10.15 を SHA-256 で検証
- `--static --libc=musl --no-fallback --enable-monitoring=jfr -march=compatibility`
- 生成先: `dist/tlc`

上流ソースへのパッチはありません。標準 Java モジュールと FPSet 実装を `configure.py` で列挙し、リフレクションに登録します。標準モジュール等の JAR 内リソースと、override の診断に使う標準 Java モジュールのクラスリソースを埋め込みます。Tracing Agent の単一モデルへの依存を避けています。ソースとツールチェーンを固定していますが、上流がビルド時刻を埋め込むため、ビット単位で同一になるビルドではありません。

## 検証

```sh
./verify.py
file dist/tlc
readelf -l dist/tlc  # INTERP がないこと
readelf -d dist/tlc  # NEEDED がないこと
ldd dist/tlc         # not a dynamic executable
```

`verification/` にログを残します。標準演算子、安全性、WF を含む活性、違反の反例と終了コード、シミュレーション、単一ワーカーの DFID、上流 Bakery モデルの相互排他性を確認します。Bakery は安全性用の設定で検査します。同じケースを同じ JAR の JVM 版でも実行して比較しています。小さなモデルによる検証であり、TLC 全機能の互換性保証ではありません。

```sh
docker build -f Dockerfile.scratch -t tlc-static .
docker run --rm --tmpfs /tmp:rw,mode=1777 \
  -v "$PWD/tests:/models" tlc-static \
  -Xmx512m -workers 2 -fpmem 0.1 -noGenerateSpecTE Counter.tla
```

## 制限

この配布物の入口は TLC のみです。SANY CLI、PlusCal コンパイラ、Toolbox の実行ファイルは含みません。TLC が必要とするパーサーは含みます。

Native Image はビルド時に Java クラスを確定します。実行後に任意の Java override や CommunityModules の JAR を追加する使い方には対応しません。追加する場合はクラスパスとリフレクション登録に含めて再ビルドが必要です。通常の `.tla` モジュールと `.cfg` は実行時に読み込めます。

分散 TLC、メール送信、REPL、チェックポイント回復、大規模モデルの性能は未検証です。Serial GC のため JVM の Parallel GC と性能特性が異なります。

再配布時は `licenses/` を実行ファイルに添付してください。
