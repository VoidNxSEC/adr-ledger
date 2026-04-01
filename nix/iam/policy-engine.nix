# /etc/nixos/iam/policy-engine.nix
{ config, lib, pkgs, ... }:

{
  environment.systemPackages = with pkgs; [
    open-policy-agent
    conftest  # para validação de policies em CI
  ];

  # OPA como serviço de decisão
  systemd.services.opa-adr-ledger = {
    description = "OPA Policy Engine for ADR Ledger";
    wantedBy = [ "multi-user.target" ];
    after = [ "network.target" ];

    serviceConfig = {
      ExecStart = ''
        ${pkgs.open-policy-agent}/bin/opa run \
          --server \
          --addr localhost:8181 \
          --log-level info \
          --log-format json \
          --bundle /var/lib/adr-ledger/policies/bundle \
          --watch
      '';
      User = "agent-governance";
      Group = "adr-admin";

      # Hardening do próprio OPA
      ProtectSystem = "strict";
      ReadOnlyPaths = [ "/var/lib/adr-ledger/policies" ];
      ReadWritePaths = [ "/var/lib/opa" ];
      PrivateTmp = true;
      NoNewPrivileges = true;
    };
  };
}
