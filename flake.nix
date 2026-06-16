{
  description = "Repository runtime dependencies for uv-singularity-template";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs =
    { nixpkgs, ... }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
      perSystem =
        system:
        let
          pkgs = import nixpkgs { inherit system; };
          repoDeps = with pkgs; [
            uv
            ffmpeg
            p7zip
            unzip
            zstd
            cacert
            nix-direnv
          ];
        in
        {
          inherit pkgs repoDeps;
        };
    in
    {
      packages = forAllSystems (
        system:
        let
          inherit (perSystem system) pkgs repoDeps;
          repoDepsPackage = pkgs.buildEnv {
            name = "uv-singularity-template-deps";
            paths = repoDeps;
          };
        in
        {
          default = repoDepsPackage;
        }
      );

      devShells = forAllSystems (
        system:
        let
          inherit (perSystem system) pkgs repoDeps;
        in
        {
          default = pkgs.mkShell {
            packages = repoDeps;
            shellHook = ''
              : "''${UV_PROJECT_ENVIRONMENT:=$PWD/.venv}"
              : "''${UV_CACHE_DIR:=$PWD/.uv-cache}"
              export UV_PROJECT_ENVIRONMENT UV_CACHE_DIR
            '';
          };
        }
      );

      formatter = forAllSystems (system: (import nixpkgs { inherit system; }).nixfmt-rfc-style);
    };
}
