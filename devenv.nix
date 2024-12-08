{pkgs, ...}: {
  # https://devenv.sh/basics/
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

  # https://devenv.sh/processes/
  # processes.cargo-watch.exec = "cargo-watch";

  # https://devenv.sh/services/
  # services.postgres.enable = true;

  # https://devenv.sh/scripts/
  scripts.hello.exec = ''
    echo hello from $GREET
  '';

  enterShell = ''
    hello
    git --version
  '';

  # https://devenv.sh/tests/
  enterTest = ''
    echo "Running tests"
    git --version | grep --color=auto "${pkgs.git.version}"
  '';

  # https://devenv.sh/pre-commit-hooks/
  # pre-commit.hooks.shellcheck.enable = true;
  git-hooks.hooks = {
    ruff.enable = true;
    ruff-format.enable = true;

    check-toml.enable = true;
    taplo.enable = true;
    yamlfmt.enable = true;

    alejandra.enable = true;
    deadnix.enable = true;
    nil.enable = true;
    statix.enable = true;
  };

  # See full reference at https://devenv.sh/reference/options/
}
