# /etc/nixos/modules/adr-ledger-iam.nix
{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.adr-ledger.iam;
in {
  options.services.adr-ledger.iam = {
    enable = mkEnableOption "ADR Ledger IAM governance";

    agents = mkOption {
      type = types.attrsOf (types.submodule {
        options = {
          role = mkOption {
            type = types.enum [ "reader" "proposer" "approver" "admin" "auditor" ];
          };
          type = mkOption {
            type = types.enum [ "human" "automated" "hybrid" ];
            default = "automated";
          };
          rateLimit = mkOption {
            type = types.int;
            default = 20;
            description = "Máx ações por hora";
          };
          allowedActions = mkOption {
            type = types.listOf types.str;
            default = [];
            description = "Override de ações permitidas (vazio = herda do role)";
          };
        };
      });
      default = {};
    };

    policyDir = mkOption {
      type = types.path;
      default = /var/lib/adr-ledger/policies;
    };

    failClosed = mkOption {
      type = types.bool;
      default = true;
      description = "Negar por padrão se policy engine estiver indisponível";
    };
  };

  config = mkIf cfg.enable {
    imports = [
      ./iam/agents.nix
      ./iam/sandboxing.nix
      ./iam/policy-engine.nix
      ./iam/secrets.nix
      ./iam/audit.nix
    ];

    # Validação em build-time: garante que todo agente tem role válido
    assertions = mapAttrsToList (name: agent: {
      assertion = agent.rateLimit > 0 && agent.rateLimit <= 100;
      message = "Agent ${name}: rateLimit deve estar entre 1 e 100";
    }) cfg.agents;
  };
}
