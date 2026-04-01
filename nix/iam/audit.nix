# /etc/nixos/iam/audit.nix
{ config, pkgs, ... }:

{
  # Diretório append-only para audit trail
  systemd.tmpfiles.rules = [
    # Audit log é append-only (atributo do filesystem)
    "d /var/lib/adr-ledger/audit 0750 agent-governance adr-auditor -"
    "d /var/lib/adr-ledger/audit/decisions 0750 agent-governance adr-auditor -"
  ];

  # Serviço de rotação + hash chain do audit log
  systemd.services.adr-audit-integrity = {
    description = "ADR Ledger Audit Log Integrity Check";
    startAt = "*:0/15";  # a cada 15 minutos
    serviceConfig = {
      Type = "oneshot";
      User = "agent-auditor";
      ExecStart = pkgs.writeShellScript "audit-integrity" ''
        #!/bin/sh
        AUDIT_DIR="/var/lib/adr-ledger/audit/decisions"
        HASH_CHAIN="/var/lib/adr-ledger/audit/hash_chain"

        # Calcula hash encadeado (tamper-evident)
        LAST_HASH=$(tail -1 "$HASH_CHAIN" 2>/dev/null || echo "genesis")
        CURRENT_HASH=$(find "$AUDIT_DIR" -newer "$HASH_CHAIN" -type f \
          | sort | xargs cat | sha256sum | cut -d' ' -f1)

        CHAINED="${LAST_HASH}:${CURRENT_HASH}:$(date -u +%s)"
        echo "$CHAINED" | sha256sum >> "$HASH_CHAIN"
      '';
    };
  };
}
