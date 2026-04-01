{ self }:
{
  config,
  lib,
  pkgs,
  ...
}:

with lib;

let
  cfg = config.services.adr-ledger;
in
{
  options.services.adr-ledger = {
    enable = mkEnableOption "ADR Ledger auto-sync";

    ledgerPath = mkOption {
      type = types.path;
      description = "Path to ADR ledger repository";
    };

    autoSync = mkOption {
      type = types.bool;
      default = true;
      description = "Auto-sync knowledge on system rebuild";
    };

    knowledgeBasePath = mkOption {
      type = types.path;
      default = "${cfg.ledgerPath}/knowledge/knowledge_base.json";
      description = "Path to generated knowledge base";
    };
  };

  config = mkIf cfg.enable {
    systemd.services.adr-sync = mkIf cfg.autoSync {
      description = "ADR Knowledge Sync";
      after = [ "network.target" ];

      serviceConfig = {
        Type = "oneshot";
        ExecStart = "${self.packages.${pkgs.system}.adr-cli}/bin/adr sync";
        WorkingDirectory = cfg.ledgerPath;
      };
    };

    systemd.timers.adr-sync = mkIf cfg.autoSync {
      description = "ADR Knowledge Sync Timer";
      wantedBy = [ "timers.target" ];

      timerConfig = {
        OnCalendar = "daily";
        Persistent = true;
      };
    };

    environment.etc."adr/knowledge_base.json" = mkIf cfg.autoSync {
      source = cfg.knowledgeBasePath;
    };
  };
}
