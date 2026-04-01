# /etc/nixos/modules/adr-ledger-full.nix
{ config, lib, pkgs, ... }:

{
  imports = [
    ./adr-ledger-iam.nix
    ../iam/radicle.nix
    ../iam/policy-engine.nix
    ../iam/algorand.nix
  ];

  services.adr-ledger.iam = {
    enable = true;
    failClosed = true;

    agents = {
      drafter = {
        role = "proposer";
        type = "automated";
        rateLimit = 15;
      };
      reviewer = {
        role = "approver";
        type = "hybrid";
        rateLimit = 30;
      };
      auditor = {
        role = "auditor";
        type = "automated";
        rateLimit = 100;
      };
    };
  };

  # === ALGORAND NODE (opcional — pode usar API pública) ===
  # Se quiser rodar um participation node:
  systemd.services.algorand-node = {
    description = "Algorand Participation Node";
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      ExecStart = "${pkgs.algorand}/bin/goal node start -d /var/lib/algorand";
      User = "algorand";
      ProtectSystem = "strict";
      ReadWritePaths = [ "/var/lib/algorand" ];
    };
  };

  # === WATCHER: Radicle → OPA → Algorand ===
  systemd.services.adr-policy-watcher = {
    description = "Watch Radicle for policy changes, sync to OPA, record on Algorand";
    wantedBy = [ "multi-user.target" ];
    after = [ "radicle-node.service" "opa-adr-ledger.service" ];

    serviceConfig = {
      ExecStart = pkgs.writeShellScript "policy-watcher" ''
        #!/bin/sh
        REPO="/var/lib/adr-ledger/radicle/policy-repo"
        BUNDLE="/var/lib/adr-ledger/policies/bundle"
        LAST_REV=""

        while true; do
          # Fetch latest from Radicle network
          cd "$REPO" && ${pkgs.radicle}/bin/rad sync --fetch 2>/dev/null

          CURRENT_REV=$(git -C "$REPO" rev-parse HEAD)

          if [ "$CURRENT_REV" != "$LAST_REV" ]; then
            echo "Policy update detected: $CURRENT_REV"

            # Sync to OPA bundle
            ${pkgs.python3}/bin/python -c "
            from adr_ledger.policies.radicle_sync import RadiclePolicySync, RadicleConfig
            sync = RadiclePolicySync(RadicleConfig())
            sync._sync_to_opa_bundle(Path('$REPO'))
            "

            # Notify OPA to reload
            ${pkgs.curl}/bin/curl -X POST http://localhost:8181/v1/policies

            LAST_REV="$CURRENT_REV"
          fi

          sleep 30
        done
      '';

      User = "agent-governance";
      Restart = "always";
      RestartSec = 10;
    };
  };

  # === SECRETS ===
  sops.secrets = {
    "algorand/governance_mnemonic" = {
      owner = "agent-governance";
      mode = "0400";
    };
    "radicle/signing_key" = {
      owner = "agent-governance";
      mode = "0400";
    };
  };
}
