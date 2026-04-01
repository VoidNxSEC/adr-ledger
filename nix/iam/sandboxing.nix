# /etc/nixos/iam/sandboxing.nix
{ config, lib, pkgs, ... }:

{
  # Serviço isolado por agente
  systemd.services."adr-agent@" = {
    description = "ADR Ledger Agent - %i";
    serviceConfig = {
      # Isolamento de identidade
      User = "agent-%i";
      Group = "adr-agents";
      DynamicUser = false;

      # === SANDBOXING FORTE ===
      # Filesystem
      ProtectSystem = "strict";
      ProtectHome = true;
      ReadWritePaths = [
        "/var/lib/adr-ledger/agents/%i"
        "/var/lib/adr-ledger/proposals"  # só se for proposer
      ];
      ReadOnlyPaths = [
        "/var/lib/adr-ledger/records"
        "/var/lib/adr-ledger/policies"
      ];
      TemporaryFileSystem = "/tmp:size=50M";

      # Rede
      RestrictAddressFamilies = [ "AF_INET" "AF_INET6" "AF_UNIX" ];
      IPAddressAllow = [ "127.0.0.1/8" "10.0.0.0/8" ];
      IPAddressDeny = "any";

      # Capabilities — princípio do menor privilégio
      CapabilityBoundingSet = "";
      AmbientCapabilities = "";
      NoNewPrivileges = true;

      # Segurança adicional
      PrivateTmp = true;
      PrivateDevices = true;
      ProtectKernelTunables = true;
      ProtectKernelModules = true;
      ProtectKernelLogs = true;
      ProtectControlGroups = true;
      RestrictRealtime = true;
      RestrictSUIDSGID = true;
      SystemCallFilter = [ "@system-service" "~@privileged" "~@resources" ];
      SystemCallArchitectures = "native";
      MemoryDenyWriteExecute = true;
      LockPersonality = true;

      # Limites de recursos
      MemoryMax = "512M";
      CPUQuota = "50%";
      TasksMax = 32;
    };
  };
}
