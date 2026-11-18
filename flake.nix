{
  description = "Chamber heater controller: design tooling (TLA+, docs diagrams)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3.withPackages (ps: [ ps.schemdraw ]);
      in
      {
        # NoCC: no host C compiler needed yet. The firmware toolchain is added
        # once the framework is chosen (ADR-012).
        devShells.default = pkgs.mkShellNoCC {
          packages = with pkgs; [
            tlaplus # tlc / tla2sany: model-check spec/*.tla (`make -C spec check`)
            gnumake
            python # docs/diagrams/gen_diagrams.py
          ];
          # KiCad is not included: the nixpkgs build is marked broken here.
          # Use the KiCad 10 app; `kicad-cli` lives inside it.
        };
      });
}
