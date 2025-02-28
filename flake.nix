{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    systems.url = "github:nix-systems/default";
    devenv.url = "github:cachix/devenv";
    devenv.inputs.nixpkgs.follows = "nixpkgs";
  };

  nixConfig = {
    extra-trusted-public-keys = "devenv.cachix.org-1:w1cLUi8dv3hnoSPGAuibQv+f9TZLr6cv/Hm9XgU50cw=";
    extra-substituters = "https://devenv.cachix.org";
  };

  outputs =
    {
      self,
      nixpkgs,
      devenv,
      systems,
      ...
    }@inputs:
    let
      forEachSystem = nixpkgs.lib.genAttrs (import systems);
    in
    {
      packages = forEachSystem (system: {
        devenv-up = self.devShells.${system}.default.config.procfileScript;
        devenv-test = self.devShells.${system}.default.config.test;
      });

      devShells = forEachSystem (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = devenv.lib.mkShell {
            inherit inputs pkgs;
            modules = [
              {
                env.LD_LIBRARY_PATH = "${pkgs.gcc-unwrapped.lib}/lib64:${pkgs.cairo}/lib";

                # https://devenv.sh/packages/
                packages = with pkgs; [
                  git
                  gcc-unwrapped
                  cairo
                ];

                # https://devenv.sh/languages/
                languages.python = {
                  enable = true;
                  uv.enable = true;
                };

                git-hooks.hooks = {
                  ruff.enable = true;
                  ruff-format.enable = true;

                  check-toml.enable = true;
                  taplo.enable = true;
                  yamlfmt.enable = true;

                  nixfmt-rfc-style.enable = true;
                  deadnix.enable = true;
                  nil.enable = true;
                  statix.enable = true;

                  actionlint.enable = true;
                  check-added-large-files.enable = true;
                  check-executables-have-shebangs.enable = true;
                  check-shebang-scripts-are-executable.enable = true;
                  check-symlinks.enable = true;
                  end-of-file-fixer.enable = true;
                  mixed-line-endings.enable = true;
                  prettier.enable = true;
                  trim-trailing-whitespace.enable = true;
                };
              }
            ];
          };
        }
      );
    };
}
