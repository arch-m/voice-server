{
  description = "Qwen3 Voice Server";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python312
            python312Packages.pip
            python312Packages.virtualenv
            uv
            python312Packages.fastapi
            python312Packages.uvicorn
            python312Packages.python-multipart
            python312Packages.soundfile
            python312Packages.numpy
            python312Packages.pydantic

            python312Packages.python-lsp-server
            python312Packages.pylsp-mypy
            python312Packages.python-lsp-ruff

            python312Packages.black
            python312Packages.isort
            python312Packages.pylint
            python312Packages.pytest

            curl
            jq
          ];

          shellHook = ''
            echo "╔═══════════════════════════════════════════════════╗"
            echo "║   Qwen3 Voice Server - Development Environment   ║"
            echo "╚═══════════════════════════════════════════════════╝"
            echo ""
            echo ""
          '';
        };
      }
    );
}
