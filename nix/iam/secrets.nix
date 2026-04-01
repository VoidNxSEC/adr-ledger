# /etc/nixos/iam/secrets.nix
{ config, pkgs, ... }:

{
  imports = [ <sops-nix/modules/sops> ];

  sops = {
    defaultSopsFile = ./secrets/adr-ledger.yaml;
    age.keyFile = "/var/lib/sops-nix/key.txt";

    secrets = {
      # Token de cada agente — nunca em plaintext no repo
      "agents/drafter/token" = {
        owner = "agent-drafter";
        group = "adr-agents";
        mode = "0400";
      };
      "agents/reviewer/token" = {
        owner = "agent-reviewer";
        group = "adr-agents";
        mode = "0400";
      };
      "agents/governance/token" = {
        owner = "agent-governance";
        group = "adr-admin";
        mode = "0400";
      };

      # Chave de assinatura do audit log
      "audit/signing_key" = {
        owner = "agent-governance";
        mode = "0400";
      };

      # OPA bearer token
      "opa/auth_token" = {
        owner = "agent-governance";
        mode = "0400";
      };
    };
  };
}
