# 📓 Singularity + uv + marimo / Jupyter テンプレート

[marimo](https://marimo.io) と Jupyter Notebook を [uv](https://github.com/astral-sh/uv) で管理する Python プロジェクトのスターター。依存管理・Lint/Format・型チェック・テスト・CI・GPU 対応コンテナまで一通り組み込み済み。

## 📦 構成

| 領域           | ツール                              |
| -------------- | ----------------------------------- |
| 言語           | Python ≥ 3.12                       |
| 依存・仮想環境 | `uv`                                |
| ノートブック   | `marimo`, `Jupyter Notebook`       |
| テスト         | `pytest`                            |
| Lint / Format  | `Ruff` (+ pre-commit)               |
| 型チェック     | `ty` (Astral)                       |
| CI             | GitHub Actions                      |
| GPU コンテナ   | SingularityCE (Ubuntu + NVIDIA GPU) |

## 🚀 クイックスタート

```bash
gh repo clone ReoHakase/singularity-uv-marimo
cd marimo-uv-starter-template
uv sync
uv run marimo edit notebooks/
uv run jupyter notebook notebooks/
```

---

## 1. uv と仮想環境

`uv` は Python バージョン管理・仮想環境・依存解決を統合した高速ツール。本テンプレートでは `.venv` を自動管理するため `python -m venv` を直接叩く必要はない。

### 1.1 Python のインストール

`pyproject.toml` の `requires-python` に合致する Python がホストに存在しない場合は次で導入する。

```bash
uv python install 3.12
uv python list
```

### 1.2 仮想環境の同期

```bash
uv sync                   # 通常
uv sync --group dev       # 特定グループのみ
uv sync --no-dev          # dev を除外
```

実行すると `.venv/` が生成され、`pyproject.toml` と `uv.lock` に従ってパッケージが配置される。

### 1.3 コマンド実行

`uv run` を用いれば `activate` を省略できる。

```bash
uv run python script.py
uv run pytest
uv run marimo edit notebooks/
uv run jupyter notebook notebooks/
```

従来どおりの activate も可能:

```bash
source .venv/bin/activate   # 有効化
deactivate                  # 無効化
```

### 1.4 依存の追加・削除・更新

```bash
uv add polars                     # 本体依存
uv add --dev pytest-cov           # 開発依存
uv remove polars
uv lock --upgrade                 # 全依存を更新
uv lock --upgrade-package marimo  # 個別更新
```

追加・削除に応じて `pyproject.toml` と `uv.lock` が自動更新される。

### 1.5 環境のリセット

```bash
rm -rf .venv
uv sync
```

---

## 2. 開発ワークフロー

### 2.1 marimo ノートブック ✏️

```bash
uv run marimo edit notebooks/
uv run marimo edit notebooks/notebook.py
```

### 2.2 Jupyter Notebook 📔

`.ipynb` を使いたい場合は、そのまま `uv` 管理下で起動できる。

```bash
uv run jupyter notebook notebooks/
uv run jupyter notebook --no-browser --port 8888 notebooks/
```

VS Code や外部の Jupyter クライアントからこの仮想環境を明示的に選びたい場合は、カーネル登録も可能。

```bash
uv run python -m ipykernel install --user --name marimo-template --display-name "Python (marimo-template)"
```

ノートブックの差分やマージを見やすくしたい場合は `nbdime` も同梱している。

```bash
uv run nbdiff notebooks/example.ipynb
uv run nbdime config-git --enable --global
```

### 2.3 テスト 🧪

通常の Python コードと marimo ノートブックのセル (`test_` 接頭辞) の双方に対応。

```bash
uv run pytest tests        # tests/ 配下
uv run pytest notebooks    # ノートブック内のテストセル
uv run pytest              # すべて
```

### 2.4 Lint / Format 🧹

```bash
uv run ruff check .         # Lint
uv run ruff check . --fix   # 自動修正
uv run ruff format .        # Format
```

### 2.5 型チェック 🔍

[`ty`](https://github.com/astral-sh/ty) は Astral 製の高速な Python 型チェッカー。

```bash
uv run ty check                         # 全体
uv run ty check src                     # 特定ディレクトリ
uv run ty check --output-format concise # 簡潔出力
```

対象および first-party のルートは `pyproject.toml` の `[tool.ty.*]` で定義している。本テンプレートでは `src/`・`tests/`・`notebooks/` を対象とし、`./src` を first-party ルートとして解決する。

### 2.6 pre-commit (任意) 🪝

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

---

## 3. SingularityCE によるコンテナ実行 🐳

Ubuntu + NVIDIA GPU (例: RTX 5060 Ti / Blackwell, `sm_120`) における再現可能な実行環境として [SingularityCE](https://github.com/sylabs/singularity) を採用する。定義ファイルは [`container.def`](container.def)、CI は [`.github/workflows/singularity.yml`](.github/workflows/singularity.yml)。

### 3.1 CUDA の分離方針

> [!IMPORTANT]
> ホスト OS に CUDA toolkit をインストールしない。CUDA ランタイムは利用環境ごとに閉じ込める。

| 環境        | CUDA の入れ方                                                                                                  |
| ----------- | -------------------------------------------------------------------------------------------------------------- |
| venv (pip)  | `pip install cuda-toolkit`                                                                                     |
| conda       | `conda install nvidia/label/cuda-12.8.1::cuda-toolkit`                                                         |
| Singularity | `.def` の `From:` に CUDA 入りのベースイメージ (本テンプレートは `nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04`) |

ホストに必要なのは **NVIDIA ドライバのみ**。Blackwell 世代 GPU では `570` 系以上が要求される。

### 3.2 ホスト要件

- Ubuntu 22.04 / 24.04
- NVIDIA driver ≥ 570 (`nvidia-smi` で確認)
- SingularityCE 4.x

### 3.3 SingularityCE のインストール

```bash
sudo apt-get update
sudo apt-get install -y wget

VER=4.1.5
wget https://github.com/sylabs/singularity/releases/download/v${VER}/singularity-ce_${VER}-$(. /etc/os-release; echo ${UBUNTU_CODENAME})_amd64.deb
sudo apt-get install -y ./singularity-ce_${VER}-*_amd64.deb

singularity --version
```

### 3.4 `.sif` のビルド

```bash
sudo singularity build container.sif container.def
```

> [!NOTE]
> ビルドには数分〜十数分を要する。生成される `container.sif` は `.gitignore` で除外済み。

### 3.5 GPU 検出確認

> [!WARNING]
> 実行時は必ず `--nv` を付与する。これによりホスト側 NVIDIA ドライバがコンテナにバインドされる。省略すると GPU が認識されない。

```bash
singularity exec --nv container.sif nvidia-smi
```

### 3.6 開発コマンド

プロジェクトを `/workspace` にバインドし、コンテナ内で `uv` を実行する。

```bash
# 依存同期 (初回)
singularity exec --nv --bind "$(pwd):/workspace" container.sif \
    bash -c "cd /workspace && uv sync"

# テスト
singularity exec --nv --bind "$(pwd):/workspace" container.sif \
    bash -c "cd /workspace && uv run pytest"

# 型チェック
singularity exec --nv --bind "$(pwd):/workspace" container.sif \
    bash -c "cd /workspace && uv run ty check"

# 対話シェル
singularity shell --nv --bind "$(pwd):/workspace" container.sif
```

### 3.7 marimo 🌐

コンテナ内の marimo をホストのブラウザで開くには `0.0.0.0` で listen させる。

```bash
singularity exec --nv --bind "$(pwd):/workspace" container.sif \
    bash -c "cd /workspace && uv run marimo edit --host 0.0.0.0 --port 2718 notebooks/"
```

ブラウザで <http://localhost:2718> を開く。

### 3.8 Jupyter Notebook 🌐

Jupyter をホストのブラウザで開く場合も同様に `0.0.0.0` で listen させる。

```bash
singularity exec --nv --bind "$(pwd):/workspace" container.sif \
    bash -c "cd /workspace && uv run jupyter notebook --ip 0.0.0.0 --port 8888 --no-browser notebooks/"
```

ブラウザで <http://localhost:8888> を開く。

### 3.9 `.venv` と `.venv-sif` の分離

ホスト側 Python とコンテナ内 Python は ABI が異なるため、仮想環境を物理的に分離する。

| 実行環境 | venv パス    | 生成契機                                      |
| -------- | ------------ | --------------------------------------------- |
| ホスト   | `.venv/`     | ホスト Python で `uv sync`                    |
| コンテナ | `.venv-sif/` | コンテナ内 `/usr/bin/python3.12` で `uv sync` |

分離は `container.def` 内の `UV_PROJECT_ENVIRONMENT=/workspace/.venv-sif` によって実現される。両ディレクトリとも `.gitignore` に登録済み。

### 3.10 `PYTHONNOUSERSITE=1` について

> [!CAUTION]
> Singularity は `$HOME` を自動バインドマウントする。未設定の場合ホストの `~/.local/lib/python*/site-packages` がコンテナの Python から参照され、環境が混ざる。

コンテナ内では `PYTHONNOUSERSITE=1` を既定値として有効化することでこの混入を阻止している。

### 3.11 CI

[`.github/workflows/singularity.yml`](.github/workflows/singularity.yml) は `.sif` をビルドし、`singularity exec` 経由で `ruff` / `ty` / `pytest` を実行する。

> [!NOTE]
> GitHub hosted runner に GPU は付属しない。したがって CI では `--nv` を付けない。Lint・型チェック・ユニットテストはいずれも GPU 不要であるためこれで十分。GPU を要するテストを追加する場合は self-hosted runner を用意すること。

### 3.12 参考: PyTorch の導入

> [!TIP]
> RTX 5060 Ti (Blackwell, `sm_120`) は CUDA 12.8+ を要求し、対応 PyTorch は `cu128` ビルドである。

```bash
singularity exec --nv --bind "$(pwd):/workspace" container.sif \
    bash -c "cd /workspace && uv add torch torchvision --index https://download.pytorch.org/whl/cu128"
```

より確実な選択肢として、ベースイメージを [`pytorch/pytorch:2.7.1-cuda12.8-cudnn9-devel`](https://hub.docker.com/r/pytorch/pytorch) または [NGC PyTorch](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/pytorch) に差し替えれば、CUDA と PyTorch の互換性がイメージ提供元で保証される。その場合 `container.def` の `From:` を変更し、`uv venv --system-site-packages` でベースの PyTorch を継承する運用へ切り替える。
