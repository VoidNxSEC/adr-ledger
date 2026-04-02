{
  self,
  securellmMcp ? null,
}:
{
  config,
  lib,
  pkgs,
  ...
}:

with lib;

let
  cfg = config.services.adr-ledger-agents;

  packageDefault =
    if securellmMcp != null
      && builtins.hasAttr "packages" securellmMcp
      && builtins.hasAttr pkgs.system securellmMcp.packages
      && builtins.hasAttr "default" securellmMcp.packages.${pkgs.system}
    then
      securellmMcp.packages.${pkgs.system}.default
    else
      null;

  roleDefaults = rec {
    agent = {
      repoAccess = "read-only";
      allowedActions = [
        "adr_list"
        "adr_show"
        "adr_search"
        "adr_relations"
        "adr_validate"
        "governance_rules"
        "chain_status"
        "chain_verify"
        "provenance_trace"
        "snapshot_latest"
        "sbom_status"
      ];
    };

    engineer = {
      repoAccess = "propose";
      allowedActions = roleDefaults.agent.allowedActions ++ [
        "adr_new"
        "adr_new_from_research"
      ];
    };

    architect = {
      repoAccess = "maintain";
      allowedActions = roleDefaults.engineer.allowedActions ++ [
        "adr_accept"
        "adr_supersede"
        "adr_pre_sign"
        "chain_sign"
        "snapshot_create"
        "sbom_generate"
      ];
    };

    security_lead = {
      repoAccess = "maintain";
      allowedActions = roleDefaults.architect.allowedActions;
    };
  };

  activeAgents = filterAttrs (_: agent: agent.enable) cfg.agents;

  roleGroupName = role: "adr-${replaceStrings [ "_" ] [ "-" ] role}";
  serviceName = name: "adr-ledger-agent-${name}";

  repoWritePathsFor =
    access:
    if access == "read-only" then
      [ ]
    else if access == "propose" then
      [ "${cfg.ledgerRoot}/adr/proposed" ]
    else
      [
        "${cfg.ledgerRoot}/adr"
        "${cfg.ledgerRoot}/.chain"
        "${cfg.ledgerRoot}/knowledge"
        "${cfg.ledgerRoot}/reports"
      ];

  effectiveAllowedActions =
    agent: if agent.allowedActions != [ ] then agent.allowedActions else roleDefaults.${agent.role}.allowedActions;

  policyDocument = name: agent: {
    inherit name;
    user = agent.user;
    group = agent.group;
    role = agent.role;
    repo_access = agent.repoAccess;
    allowed_actions = effectiveAllowedActions agent;
    workspace = agent.workspaceDir;
    home = agent.homeDir;
    log_dir = agent.logDir;
  };

  commonServicePath = [
    cfg.package
    self.packages.${pkgs.system}.adr-cli
    pkgs.bash
    pkgs.coreutils
    pkgs.git
    pkgs.jq
    pkgs.open-policy-agent
    pkgs.openssl
  ];
in
{
  options.services.adr-ledger-agents = {
    enable = mkEnableOption "ADR Ledger agent daemons backed by securellm-mcp";

    package = mkOption {
      type = types.nullOr types.package;
      default = packageDefault;
      defaultText = literalExpression "inputs.securellm-mcp.packages.\${pkgs.system}.default";
      description = "SecureLLM MCP package used as the backend daemon for ADR agents.";
    };

    installPackage = mkOption {
      type = types.bool;
      default = true;
      description = "Install the SecureLLM MCP package in environment.systemPackages.";
    };

    environment = mkOption {
      type = types.enum [
        "development"
        "staging"
        "production"
      ];
      default = "production";
      description = "NODE_ENV and MCP_ENV value shared by all agent daemons.";
    };

    ledgerRoot = mkOption {
      type = types.str;
      default = "/var/lib/adr-ledger";
      description = "Canonical ADR ledger repository path exposed via ADR_REPO_PATH.";
    };

    baseDir = mkOption {
      type = types.str;
      default = "/var/lib/adr-ledger-agents";
      description = "Base directory for isolated agent homes, caches, logs, and workspaces.";
    };

    sharedGroup = mkOption {
      type = types.str;
      default = "adr-ledger-agents";
      description = "Shared supplementary group for all ADR agents.";
    };

    agents = mkOption {
      type = types.attrsOf (
        types.submodule (
          { config, name, ... }:
          {
            options = {
              enable = mkOption {
                type = types.bool;
                default = true;
                description = "Enable the ${name} agent daemon.";
              };

              role = mkOption {
                type = types.enum [
                  "agent"
                  "architect"
                  "engineer"
                  "security_lead"
                ];
                default = "agent";
                description = "Governance role exported to the daemon via ADR_AGENT_ROLE.";
              };

              user = mkOption {
                type = types.str;
                default = "adr-agent-${name}";
                description = "System user assigned to this agent.";
              };

              group = mkOption {
                type = types.str;
                default = "adr-agent-${name}";
                description = "Primary group assigned to this agent.";
              };

              repoAccess = mkOption {
                type = types.enum [
                  "read-only"
                  "propose"
                  "maintain"
                ];
                default = roleDefaults.${config.role}.repoAccess;
                description = "Filesystem write scope granted over the ledger repository.";
              };

              allowedActions = mkOption {
                type = types.listOf types.str;
                default = roleDefaults.${config.role}.allowedActions;
                description = "Action list exported as ADR_ALLOWED_ACTIONS for policy-aware tooling.";
              };

              homeDir = mkOption {
                type = types.str;
                default = "${cfg.baseDir}/home/${name}";
                description = "Home directory for the agent user.";
              };

              cacheDir = mkOption {
                type = types.str;
                default = "${cfg.baseDir}/cache/${name}";
                description = "Writable cache directory for the agent runtime.";
              };

              logDir = mkOption {
                type = types.str;
                default = "${cfg.baseDir}/logs/${name}";
                description = "Writable log directory for the daemon.";
              };

              workspaceDir = mkOption {
                type = types.str;
                default = "${cfg.baseDir}/workspaces/${name}";
                description = "Working directory for the agent process.";
              };

              extraGroups = mkOption {
                type = types.listOf types.str;
                default = [ ];
                description = "Extra system groups granted to the agent user and service.";
              };

              extraReadWritePaths = mkOption {
                type = types.listOf types.str;
                default = [ ];
                description = "Additional writable paths exposed to the daemon sandbox.";
              };

              extraReadOnlyPaths = mkOption {
                type = types.listOf types.str;
                default = [ ];
                description = "Additional read-only paths exposed to the daemon sandbox.";
              };

              environment = mkOption {
                type = types.attrsOf types.str;
                default = { };
                description = "Extra environment variables merged into the daemon environment.";
              };

              restartOnFailure = mkOption {
                type = types.bool;
                default = true;
                description = "Restart the agent daemon on failure.";
              };

              cpuQuota = mkOption {
                type = types.str;
                default = "50%";
                description = "systemd CPUQuota for the daemon.";
              };

              memoryMax = mkOption {
                type = types.str;
                default = "1G";
                description = "systemd MemoryMax for the daemon.";
              };
            };
          }
        )
      );
      default = { };
      description = "Agent instances that should run isolated SecureLLM MCP daemons.";
    };
  };

  config = mkIf cfg.enable {
    assertions =
      [
        {
          assertion = cfg.package != null;
          message = "services.adr-ledger-agents.package must be set or the securellm-mcp flake input must be available.";
        }
        {
          assertion = hasPrefix "/" cfg.ledgerRoot;
          message = "services.adr-ledger-agents.ledgerRoot must be an absolute path.";
        }
      ]
      ++ mapAttrsToList (
        name: agent: {
          assertion =
            hasPrefix "/" agent.homeDir
            && hasPrefix "/" agent.cacheDir
            && hasPrefix "/" agent.logDir
            && hasPrefix "/" agent.workspaceDir;
          message = "Agent ${name}: homeDir/cacheDir/logDir/workspaceDir must be absolute paths.";
        }
      ) activeAgents;

    environment.systemPackages = optionals cfg.installPackage [ cfg.package ];

    environment.etc = mapAttrs' (
      name: agent:
      nameValuePair "adr-ledger/agents/${name}.json" {
        mode = "0440";
        text = builtins.toJSON (policyDocument name agent);
      }
    ) activeAgents;

    users.groups =
      {
        ${cfg.sharedGroup} = { };
        ${roleGroupName "agent"} = { };
        ${roleGroupName "architect"} = { };
        ${roleGroupName "engineer"} = { };
        ${roleGroupName "security_lead"} = { };
      }
      // listToAttrs (mapAttrsToList (_: agent: nameValuePair agent.group { }) activeAgents);

    users.users = mapAttrs' (
      name: agent:
      nameValuePair agent.user {
        isSystemUser = true;
        inherit (agent) group;
        home = agent.homeDir;
        createHome = false;
        description = "ADR Ledger agent ${name} (${agent.role})";
        extraGroups = [
          cfg.sharedGroup
          (roleGroupName agent.role)
        ] ++ agent.extraGroups;
      }
    ) activeAgents;

    systemd.tmpfiles.rules = flatten (
      mapAttrsToList (
        _: agent:
        [
          "d ${agent.homeDir} 0750 ${agent.user} ${agent.group} -"
          "d ${agent.cacheDir} 0750 ${agent.user} ${agent.group} -"
          "d ${agent.logDir} 0750 ${agent.user} ${agent.group} -"
          "d ${agent.workspaceDir} 0750 ${agent.user} ${agent.group} -"
        ]
      ) activeAgents
    );

    systemd.services = mapAttrs' (
      name: agent:
      nameValuePair (serviceName name) {
        description = "ADR Ledger agent daemon (${name})";
        wantedBy = [ "multi-user.target" ];
        after = [ "network.target" ];
        path = commonServicePath;

        environment =
          {
            ADR_AGENT_NAME = name;
            ADR_AGENT_ROLE = agent.role;
            ADR_ALLOWED_ACTIONS = concatStringsSep "," (effectiveAllowedActions agent);
            ADR_REPO_PATH = cfg.ledgerRoot;
            HOME = agent.homeDir;
            LOG_DIR = agent.logDir;
            MCP_ENV = cfg.environment;
            MCP_WORKDIR = agent.workspaceDir;
            NODE_ENV = cfg.environment;
            PROJECT_ROOT = agent.workspaceDir;
            XDG_CACHE_HOME = agent.cacheDir;
            XDG_STATE_HOME = agent.logDir;
          }
          // agent.environment;

        serviceConfig = {
          Type = "simple";
          ExecStart = "${cfg.package}/bin/securellm-mcp";
          WorkingDirectory = agent.workspaceDir;
          User = agent.user;
          Group = agent.group;
          SupplementaryGroups = [
            cfg.sharedGroup
            (roleGroupName agent.role)
          ] ++ agent.extraGroups;

          Restart = if agent.restartOnFailure then "on-failure" else "no";
          RestartSec = "5s";

          UMask = "0027";
          NoNewPrivileges = true;
          PrivateTmp = true;
          PrivateDevices = true;
          ProtectSystem = "strict";
          ProtectHome = true;
          ProtectKernelTunables = true;
          ProtectKernelModules = true;
          ProtectKernelLogs = true;
          ProtectControlGroups = true;
          RestrictNamespaces = true;
          RestrictRealtime = true;
          RestrictSUIDSGID = true;
          LockPersonality = true;
          MemoryDenyWriteExecute = true;
          SystemCallArchitectures = "native";
          RestrictAddressFamilies = [
            "AF_UNIX"
            "AF_INET"
            "AF_INET6"
          ];

          ReadOnlyPaths = agent.extraReadOnlyPaths;
          ReadWritePaths =
            [
              agent.homeDir
              agent.cacheDir
              agent.logDir
              agent.workspaceDir
            ]
            ++ (repoWritePathsFor agent.repoAccess)
            ++ agent.extraReadWritePaths;

          CPUQuota = agent.cpuQuota;
          MemoryMax = agent.memoryMax;
          TasksMax = 64;
          StandardOutput = "journal";
          StandardError = "journal";
          SyslogIdentifier = serviceName name;
        };
      }
    ) activeAgents;
  };
}
