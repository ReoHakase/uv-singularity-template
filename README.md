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

## HPC でリポジトリ固有の開発環境を作る

共用 GPU マシンでは、ホストに Nix を入れられないことが多い。このテンプレートは SingularityCE だけを入口にして、PyTorch 公式 CUDA イメージから 1 つの SIF を作る。Nix は SIF の中に `nix-portable` として入れ、変更される状態ファイルは `.container/` に閉じ込める。

```bash
git clone https://github.com/ReoHakase/uv-singularity-template.git
cd uv-singularity-template

singularity build --fakeroot \
  container.sif container.def

singularity run --cleanenv --no-home --nv \
  --bind "$PWD:/workspace,$HOME/.ssh/authorized_keys:/authorized_keys:ro" \
  --pwd /workspace \
  container.sif init

singularity run --cleanenv --no-home --nv \
  --bind "$PWD:/workspace,$HOME/.ssh/authorized_keys:/authorized_keys:ro" \
  --pwd /workspace \
  container.sif direnv allow

singularity run --cleanenv --no-home --nv \
  --bind "$PWD:/workspace,$HOME/.ssh/authorized_keys:/authorized_keys:ro" \
  --pwd /workspace \
  container.sif direnv exec . bash -lc 'echo "$VIRTUAL_ENV"; uv --version'

singularity exec --cleanenv --no-home --nv \
  --bind "$PWD:/workspace,$HOME/.ssh/authorized_keys:/authorized_keys:ro" \
  --pwd /workspace \
  container.sif nvidia-smi
```

`init` が `.container/` を作る。SIF は `container.sif` に置かれ、`nix-portable`、Codex の状態、Cursor server、必要に応じた Home Manager profile や `gh` の認証状態もリポジトリ配下に閉じる。

`authorized_keys` はリポジトリ内へコピーしない。ホストの `$HOME/.ssh/authorized_keys` だけを `/authorized_keys` へ read-only bind し、コンテナ初期化時に `/workspace/.container/home/.ssh/authorized_keys` から symlink する。

実行例では `--cleanenv --no-home` を付ける。SingularityCE は既定でホストの環境変数と home を持ち込みやすく、ホスト側の `NIX_PROFILE` や `PYTHONPATH` が混ざると Home Manager や Python がリポジトリ外を参照することがあるためだ。必要な値は `--env NAME=value` で明示的に渡す。

`flake.nix#default` の依存は SIF build 時に常に事前取得する。同じ `flake.lock` のままなら、初回の `direnv exec` や `nix-develop` で追加取得が出にくい。

コンテナ内 sshd の既定 port は `2222`。別の port を焼き込みたい場合は、SIF build 時に `--build-arg sshd_port=2223` のように指定する。ローカルの SSH config の `Port` も同じ値にする。

依存は次の 3 層に分ける。

| 層                       | 扱うもの                                           | 例                                                |
| ------------------------ | -------------------------------------------------- | ------------------------------------------------- |
| `%post` の `apt-get`     | コンテナ内で最低限の開発ホストとして必要な CLI    | `zsh`, `curl`, `tmux`, `openssh`, `git`, `git-lfs`, `direnv` |
| `flake.nix#default`      | リポジトリ固有の実行依存、Python から呼ぶ外部依存 | `uv`, `ffmpeg`, `p7zip`, `unzip`, `zstd`, `cacert`, `nix-direnv` |
| dotfiles                 | 個人のシェル、エディタ、Git、好みの開発道具       | `nvim`, `starship`, `mise`, `gh`, 個人設定         |

### なぜ SIF と `flake.nix` を分けるのか

SIF は、root 権限のない共用 GPU ホストで動く実行基盤として扱う。Ubuntu/FHS、PyTorch CUDA runtime、コンテナ内 sshd、`git`、`tmux`、`nix-portable` など、ホストに Nix がなくても開発を始めるための土台をここに入れる。

一方、`flake.nix` はリポジトリ固有の依存を再現する契約として扱う。`uv`、`ffmpeg`、`p7zip`、`nix-direnv` のように、Python コードの実行や前処理で必要になる外部コマンドを置く。`flake.lock` は nixpkgs などの入力を固定するため、同じ lock file から個人 PC、コンテナ内、CI で同じ依存集合を使い回せる。

個人 PC に Nix が入っている場合は、SingularityCE を使わずに `nix develop` だけで同じ `uv` や外部コマンドへ入れる。GitHub CI も `nix develop --command ...` へ寄せられる設計で、現状の Singularity CI では SIF 内に bake した `flake.nix#default` を検証している。

dotfiles はさらに別の層にする。個人の Nix/Home Manager 設定はテンプレートへ固定せず、必要なときだけ root なしコンテナ内の `.container/home` に閉じて展開する。

Codex CLI と Claude Code は、必要な場合だけ SIF に含められる。どちらも build 時点の `latest` を使うため、完全に同じ SIF を再生成したい用途ではなく、共用 HPC へ新しい CLI 本体を持ち込むためのオプションとして扱う。ログインはコンテナ起動後に手動で行い、状態は `.container/state/codex` と `.container/state/claude` に置く。

dotfiles を SIF に含める場合は、特定ユーザーの設定をテンプレートに固定せず、build arg で注入する。

```bash
singularity build --fakeroot \
  --build-arg bake_dotfiles=1 \
  --build-arg DOTFILES_REPOSITORY=https://github.com/you/dotfiles.git \
  container.sif container.def
```

コンテナ内 sshd は SingularityCE instance として起動する。

```bash
singularity instance start --cleanenv --no-home --nv \
  --bind "$PWD:/workspace,$HOME/.ssh/authorized_keys:/authorized_keys:ro" \
  --pwd /workspace \
  container.sif dev-container
```

ローカル側の `~/.ssh/config` には次のように追記する。スクリプトで編集する手順は用意しない。

```sshconfig
Host kcvl-container-uv-singularity-template
  HostName 127.0.0.1
  Port 2222
  User reohakuta
  ProxyCommand ssh -W %h:%p kcvl
  ForwardAgent yes
  HostKeyAlias kcvl-container-uv-singularity-template
  UserKnownHostsFile ~/.ssh/known_hosts_kcvl_container_uv_singularity_template
  StrictHostKeyChecking accept-new
  ServerAliveInterval 30
  ServerAliveCountMax 3
```

`User` と `ProxyCommand` の `kcvl` は接続先の HPC に合わせて変える。Cursor Remote-SSH でもこの Host 名を選べば、Cursor server は `.container/state/cursor-server` 配下に作られる。`~/.ssh/config` はリポジトリ外のファイルなので、cleanup では削除しない。

消すときは次を実行する。

```bash
singularity instance stop dev-container || true
chmod -R u+rwX .container 2>/dev/null || true
rm -rf container.sif .container
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

このテンプレートの `container.def` は `pytorch/pytorch:2.11.0-cuda12.8-cudnn9-runtime` をベースイメージにする。Ubuntu/FHS 系のイメージなので、`singularity exec --nv` でホスト側の NVIDIA ドライバと `nvidia-smi` を使いやすい。

ホストに Nix は不要。SIF build の `%post` で `nix-portable` を `/opt/hpcdev/bin/` に入れ、実行時の store と profile は `.container/state/nix-portable/` に置く。

### 3.1 ホスト要件

- SingularityCE 4.x
- fakeroot build が使えること
- リポジトリを clone できる Git
- GPU を使う場合はホスト側 NVIDIA ドライバ

### 3.2 `.container/` の扱い

`.container/` は Git 管理しない。事前に作る必要はなく、最初の `singularity run ... init` が作成する。SIF、Nix の状態、uv venv、Codex/Cursor/VS Code server、SSH host key、ログをここへ集める。

`authorized_keys` は `.container/` にコピーしない。ホストの `$HOME/.ssh/authorized_keys` を `/authorized_keys` に read-only bind し、コンテナ側で symlink を作る。

### 3.3 `.sif` のビルド

PyTorch CUDA runtime、`nix-portable`、apt で入れる最小 CLI、`flake.nix#default` の依存が SIF に入る。

```bash
singularity build --fakeroot \
  container.sif container.def
```

SIF build 中に `nix build .#default` と `nix develop --command true` を実行し、その結果を `nix-portable` の seed として保存する。

コンテナ内 sshd の待ち受け port は build arg で変えられる。省略時は `2222`。

```bash
singularity build --fakeroot \
  --build-arg sshd_port=2223 \
  container.sif container.def
```

dotfiles も SIF に含める場合は、リポジトリ URL を build arg で渡す。秘密鍵、token、認証状態は含めない。

```bash
singularity build --fakeroot \
  --build-arg bake_dotfiles=1 \
  --build-arg DOTFILES_REPOSITORY=https://github.com/you/dotfiles.git \
  container.sif container.def
```

Codex CLI と Claude Code も、必要なら SIF に含められる。どちらも build 時点の `latest` を取得する。CLI 本体だけを bake し、認証情報や token は含めない。

```bash
singularity build --fakeroot \
  --build-arg bake_codex=1 \
  container.sif container.def

singularity build --fakeroot \
  --build-arg bake_claude=1 \
  container.sif container.def

singularity build --fakeroot \
  --build-arg bake_codex=1 \
  --build-arg bake_claude=1 \
  container.sif container.def
```

起動後に `codex login` や `claude` のログインを行う。Codex の状態は `.container/state/codex`、Claude Code の状態は `.container/state/claude` に置かれる。

ベースイメージを差し替える場合は `base_image` を指定する。CUDA extension をコンテナ内でビルドするなら `*-devel` tag を使う。

```bash
singularity build --fakeroot \
  --build-arg base_image=nvcr.io/nvidia/pytorch:25.09-py3 \
  container.sif container.def
```

### 3.4 実行と direnv

SIF 内の dispatcher は `singularity run` で呼び出す。

```bash
singularity run --cleanenv --no-home --nv \
  --bind "$PWD:/workspace,$HOME/.ssh/authorized_keys:/authorized_keys:ro" \
  --pwd /workspace \
  container.sif init
```

`flake.nix` はコンテナ内の `nix-portable` から読む。実行時に `flake.nix` と `flake.lock` だけを `.container/state/flake/` へコピーし、Nix が `.container/state/nix-portable/` まで flake input として読まないようにしている。

```bash
singularity run --cleanenv --no-home --nv \
  --bind "$PWD:/workspace,$HOME/.ssh/authorized_keys:/authorized_keys:ro" \
  --pwd /workspace \
  container.sif direnv allow
```

`.envrc` は、通常のローカル環境では `use flake` を使う。コンテナ内では `HPCDEV_STATE_DIR/flake` にコピーした `flake.nix` と `flake.lock` を読むため、`.container/state/nix-portable/` を flake input として巻き込まない。`init` 時には `.container/home/.config/direnv/direnvrc` も生成し、`flake.nix#default` に入っている `nix-direnv` を読み込む。

`nix-direnv` が出す PATH は `/nix/store/...` を指すため、SIF 内には `/nix -> /workspace/.container/state/nix-portable/.nix-portable/nix` の symlink を置いている。実体は `.container/state/` 配下にあり、cleanup で消せる。

`direnv allow` は flake 依存を読み、venv がなければ作成し、以後の `direnv exec` で自動 activate できる状態にする。コンテナ内の既定 venv は `.venv-sif` で、ベースイメージの PyTorch を使えるように `uv venv --system-site-packages` で作る。通常のローカル環境では `.venv` を使う。

これで、ホストに Nix や direnv がなくても、コンテナ内では `direnv allow` と `direnv exec` が使える。

個人 PC に Nix がある場合は、コンテナを使わずに同じ flake へ入れる。

```bash
nix develop --command uv --version
nix develop --command uv sync
```

```bash
singularity run --cleanenv --no-home --nv \
  --bind "$PWD:/workspace,$HOME/.ssh/authorized_keys:/authorized_keys:ro" \
  --pwd /workspace \
  container.sif direnv exec . bash -lc 'echo "$VIRTUAL_ENV"; uv --version'
```

dotfiles 側で `eval "$(direnv hook zsh)"` や `eval "$(direnv hook bash)"` を設定していれば、コンテナ SSH 後に `/workspace` へ入るだけで同じ環境が有効になる。dotfiles を使わない場合は、明示的に `direnv exec . <command>` を使う。

コンテナ内で direnv を使わず、`nix develop` を直接呼びたい場合の退避導線も残している。

```bash
singularity run --cleanenv --no-home --nv \
  --bind "$PWD:/workspace,$HOME/.ssh/authorized_keys:/authorized_keys:ro" \
  --pwd /workspace \
  container.sif nix-develop uv --version
```

依存同期は自動実行しない。必要なタイミングで `uv-sync` を実行する。Python はベースイメージから自動検出する。明示したい場合だけ `--env HPCDEV_PYTHON=/path/to/python` で渡す。

```bash
singularity run --cleanenv --no-home --nv \
  --bind "$PWD:/workspace,$HOME/.ssh/authorized_keys:/authorized_keys:ro" \
  --pwd /workspace \
  container.sif uv-sync
```

`pyproject.toml` で `torch` を pin した場合は、uv が `.venv-sif` 側に入れた wheel がベースイメージの PyTorch より優先される。

### 3.5 GPU 確認

```bash
singularity exec --cleanenv --no-home --nv \
  --bind "$PWD:/workspace,$HOME/.ssh/authorized_keys:/authorized_keys:ro" \
  --pwd /workspace \
  container.sif nvidia-smi

singularity exec --cleanenv --no-home --nv \
  --bind "$PWD:/workspace,$HOME/.ssh/authorized_keys:/authorized_keys:ro" \
  --pwd /workspace \
  container.sif python -c 'import torch; print(torch.__version__, torch.version.cuda); print(torch.cuda.is_available())'
```

CPU ノードで起動確認だけする場合は `--nv` を外す。

### 3.6 dotfiles の適用

build 時に dotfiles を含めていない場合は、実行時に URL を渡す。
実行時に読む設定名は `DOTFILES_REPOSITORY`、`DOTFILES_TARGET_PATH`、`DOTFILES_INSTALL_COMMAND` だけにしている。これは Dev Containers の dotfiles 設定に対応する shell 向けの名前だ。

```bash
singularity run --cleanenv --no-home --nv \
  --env DOTFILES_REPOSITORY=https://github.com/you/dotfiles.git \
  --env DOTFILES_TARGET_PATH=dotfiles \
  --env DOTFILES_INSTALL_COMMAND=./install.sh \
  --bind "$PWD:/workspace,$HOME/.ssh/authorized_keys:/authorized_keys:ro" \
  --pwd /workspace \
  container.sif install-dotfiles
```

`ReoHakase/dotfiles-nix` のコンテナ用 Home Manager 出力を使う場合は、出力名だけを `DOTFILES_HM_OUTPUT` で渡す。`vscode@devcontainer` は互換用の出力名で、実際の `home.username` と `home.homeDirectory` は dotfiles 側の `install.sh` がコンテナ内の `id -un` と `$HOME` から補完する。そのため、`$PWD/.container/home:/home/vscode` のような追加 bind は不要。

```bash
singularity run --cleanenv --no-home --nv \
  --env DOTFILES_REPOSITORY=https://github.com/ReoHakase/dotfiles-nix.git \
  --env DOTFILES_TARGET_PATH=dotfiles-nix \
  --env DOTFILES_HM_OUTPUT=vscode@devcontainer \
  --bind "$PWD:/workspace,$HOME/.ssh/authorized_keys:/authorized_keys:ro" \
  --pwd /workspace \
  container.sif install-dotfiles
```

`DOTFILES_TARGET_PATH` を省略した場合、clone 先は `.container/home/dotfiles` になる。`DOTFILES_INSTALL_COMMAND` を省略した場合は Dev Containers の既定順に合わせて、`install.sh`、`install`、`bootstrap.sh`、`bootstrap`、`setup.sh`、`setup` を探す。見つからない場合は、dotfiles リポジトリ直下の top-level dotfile を `$HOME` へ symlink する。

dotfiles を bake した場合は、`DOTFILES_REPOSITORY` なしで同じコマンドを実行できる。

### 3.7 コンテナ SSH

Cursor Remote-SSH や Codex App から入る場合は、SingularityCE instance として user-level sshd を起動する。

```bash
singularity instance start --cleanenv --no-home --nv \
  --bind "$PWD:/workspace,$HOME/.ssh/authorized_keys:/authorized_keys:ro" \
  --pwd /workspace \
  container.sif dev-container
```

ローカル側の `~/.ssh/config` には次を追記する。

```sshconfig
Host kcvl-container-uv-singularity-template
  HostName 127.0.0.1
  Port 2222
  User reohakuta
  ProxyCommand ssh -W %h:%p kcvl
  ForwardAgent yes
  HostKeyAlias kcvl-container-uv-singularity-template
  UserKnownHostsFile ~/.ssh/known_hosts_kcvl_container_uv_singularity_template
  StrictHostKeyChecking accept-new
  ServerAliveInterval 30
  ServerAliveCountMax 3
```

`User reohakuta` と `kcvl` は実際の HPC アカウントとホスト名に置き換える。`~/.ssh/config` はリポジトリ外のファイルなので、cleanup では削除しない。
`sshd_port` を変更して SIF を build した場合は、`Port 2222` も同じ値へ変更する。

コンテナ内 sshd は `PermitUserEnvironment no` にしている。ホスト側の `~/.ssh/environment` に古いコンテナ用の環境変数が残っていても読まず、必要な値はコンテナが生成する `sshd_config` の `SetEnv` で固定する。

```bash
ssh kcvl-container-uv-singularity-template
```

### 3.8 cleanup

```bash
singularity instance stop dev-container || true
chmod -R u+rwX .container 2>/dev/null || true
rm -rf container.sif .container
```

`chmod` は、Nix store 配下の read-only ファイルを消すために入れている。
