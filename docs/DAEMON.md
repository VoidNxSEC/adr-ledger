# Agent Daemon Integration

`adr-ledger` does not ship its own MCP server binary.

The supported model is:

- `adr-ledger` owns the ledger, governance rules, chain state, and NixOS modules.
- `securellm-mcp` provides the MCP transport/runtime.
- ADR agents run as isolated system users with granular filesystem access, but all of them execute the `securellm-mcp` package as backend.

## NixOS module layout

The flake now exports three modules:

- `nixosModules.adr-ledger`
- `nixosModules.adr-ledger-sync`
- `nixosModules.adr-ledger-agents`

For host usage, the normal entrypoint is `nixosModules.adr-ledger`, which imports sync plus agent daemon management.

## Minimal host example

```nix
{
  imports = [
    inputs.adr-ledger.nixosModules.adr-ledger
  ];

  services.adr-ledger = {
    enable = true;
    ledgerPath = /var/lib/adr-ledger;
    autoSync = true;
  };

  services.adr-ledger-agents = {
    enable = true;
    ledgerRoot = "/var/lib/adr-ledger";

    agents = {
      cerebro = {
        role = "agent";
      };

      spectre = {
        role = "engineer";
        repoAccess = "propose";
      };

      architect = {
        role = "architect";
        repoAccess = "maintain";
      };
    };
  };
}
```

## Security model

Each configured agent gets:

- a dedicated system user and primary group
- a private home, cache, log, and workspace directory
- role-derived `ADR_ALLOWED_ACTIONS`
- role-derived repository write scope
- hardened `systemd` settings such as `ProtectSystem=strict`, `PrivateTmp=true`, `NoNewPrivileges=true`, and bounded writable paths

The service exposes:

- `ADR_AGENT_NAME`
- `ADR_AGENT_ROLE`
- `ADR_ALLOWED_ACTIONS`
- `ADR_REPO_PATH`
- `MCP_WORKDIR`
- `NODE_ENV`
- `MCP_ENV`

## Repository access levels

Current repository access presets are:

- `read-only`: no write access to the ledger tree
- `propose`: write access only to `adr/proposed`
- `maintain`: write access to `adr`, `.chain`, `knowledge`, and `reports`

These defaults can be tightened further with:

- `extraReadOnlyPaths`
- `extraReadWritePaths`
- `extraGroups`
- `environment`

## Runtime package

The module expects `securellm-mcp` from the flake input and uses its package output as the daemon backend.

By default:

- `services.adr-ledger-agents.package = inputs.securellm-mcp.packages.${pkgs.system}.default`

You can override that package explicitly if needed.

## What is intentionally not supported here

The following model is intentionally deprecated for this repository:

- a local `adr-mcp-server` binary shipped by `adr-ledger`
- a standalone `scripts/adr-ledger-mcp.service` as the primary deployment method
- docs that imply ADR MCP transport is implemented independently from `securellm-mcp`

If you need a manual daemon outside NixOS, document it in terms of `securellm-mcp` invoking the ADR tools, not a separate MCP server living in this repo.
