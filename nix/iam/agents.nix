# /etc/nixos/iam/agents.nix
{ config, lib, pkgs, ... }:

let
  # Taxonomia de roles para agentes
  agentRoles = {
    reader = { gid = 5001; permissions = "ro"; };
    proposer = { gid = 5002; permissions = "rw-propose"; };
    approver = { gid = 5003; permissions = "rw-approve"; };
    admin = { gid = 5004; permissions = "full"; };
    auditor = { gid = 5005; permissions = "ro-audit"; };
  };

  # Factory de usuários-agente
  mkAgentUser = name: role: {
    isSystemUser = true;
    group = "adr-agents";
    extraGroups = [ "adr-${role}" ];
    home = "/var/lib/adr-ledger/agents/${name}";
    createHome = true;
    shell = pkgs.bashInteractive;
    description = "ADR Ledger Agent - ${name} (${role})";
  };

in {
  # === GRUPOS ===
  users.groups = {
    adr-agents = { gid = 5000; };
    adr-reader = { gid = agentRoles.reader.gid; };
    adr-proposer = { gid = agentRoles.proposer.gid; };
    adr-approver = { gid = agentRoles.approver.gid; };
    adr-admin = { gid = agentRoles.admin.gid; };
    adr-auditor = { gid = agentRoles.auditor.gid; };
  };

  # === USUÁRIOS-AGENTE ===
  users.users = {
    agent-drafter    = mkAgentUser "drafter" "proposer";
    agent-reviewer   = mkAgentUser "reviewer" "approver";
    agent-executor   = mkAgentUser "executor" "reader";
    agent-auditor    = mkAgentUser "auditor" "auditor";
    agent-governance = mkAgentUser "governance" "admin";
  };
}
