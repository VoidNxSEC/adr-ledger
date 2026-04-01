# /etc/nixos/iam/radicle.nix
{ config, lib, pkgs, ... }:

let
  # Radicle ainda não está no nixpkgs stable, então buildamos
  radicle = pkgs.rustPlatform.buildRustPackage rec {
    pname = "radicle-node";
    version = "1.1.0";
    src = pkgs.fetchFromGitHub {
      owner = "radicle-dev";
      repo = "heartwood";
      rev = "v${version}";
      sha256 = lib.fakeSha256; # substituir pelo real
    };
    cargoLock.lockFile = "${src}/Cargo.lock";
    nativeBuildInputs = with pkgs; [ pkg-config ];
    buildInputs = with pkgs; [ openssl ];
  };

in {
  environment.systemPackages = [ radicle ];

  # === RADICLE NODE SERVICE ===
  systemd.services.radicle-node = {
    description = "Radicle Node - ADR Ledger Policy Sync";
    wantedBy = [ "multi-user.target" ];
    after = [ "network-online.target" ];

    serviceConfig = {
      ExecStart = "${radicle}/bin/radicle-node --listen 0.0.0.0:8776";
      User = "agent-governance";
      Group = "adr-admin";

      # Radicle home com as policies
      Environment = [
        "RAD_HOME=/var/lib/adr-ledger/radicle"
        "RAD_PASSPHRASE="  # key sem passphrase (protegida por filesystem perms)
      ];

      # Sandboxing
      ProtectSystem = "strict";
      ReadWritePaths = [
        "/var/lib/adr-ledger/radicle"
        "/var/lib/adr-ledger/policies"
      ];
      PrivateTmp = true;
      NoNewPrivileges = true;
      ProtectHome = true;

      # Rede — só p2p do Radicle
      RestrictAddressFamilies = [ "AF_INET" "AF_INET6" "AF_UNIX" ];
    };
  };

  # === DIRETÓRIOS ===
  systemd.tmpfiles.rules = [
    "d /var/lib/adr-ledger/radicle 0750 agent-governance adr-admin -"
  ];

  # === FIREWALL ===
  networking.firewall.allowedTCPPorts = [ 8776 ];  # Radicle P2P
}
