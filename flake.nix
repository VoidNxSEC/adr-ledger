{
  description = "ADR Ledger - Agents Governance Ecosystem for granular decisions based on cryptographic ADRs";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    spider-nix = {
      url = "git+ssh://git@github.com/VoidNxSEC/spider-nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };
    securellm-mcp = {
      url = "git+ssh://git@github.com/VoidNxSEC/securellm-mcp";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
      inputs.spider-nix.follows = "spider-nix";
    };

    phantom = {
      url = "git+ssh://git@github.com/VoidNxSEC/phantom";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    cerebro = {
      url = "git+ssh://git@github.com/VoidNxSEC/cerebro";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };

    ml-ops-api = {
      url = "git+ssh://git@github.com/VoidNxSEC/ml-ops-api";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };

    neotron = {
      url = "git+ssh://git@github.com/VoidNxSEC/neotron";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };

    ai-agent-os = {
      url = "git+ssh://git@github.com/VoidNxSEC/ai-agent-os";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };

    spectre = {
      url = "git+ssh://git@github.com/VoidNxSEC/spectre";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };

    # This is the SIEM tool for collect and monitoring all logs from the framework.
    owasaka = {
      url = "git+ssh://git@github.com/VoidNxSEC/O.W.A.S.A.K.A.";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };

    sentinel = {
      url = "git+ssh://git@github.com/VoidNxSEC/sentinel";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-utils.follows = "flake-utils";
    };

  };

  outputs =
    inputs@{
      self,
      nixpkgs,
      flake-utils,
      ...
    }:
    let
      securellmMcp = inputs.securellm-mcp;
    in
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Versão
        version = "0.1.0";

        # Python e dependências
        python = pkgs.python313;
        pythonPackages = python.pkgs;

      in
      {
        # =================================================================
        # PACKAGES
        # =================================================================
        packages = rec {
          # Parser Python empacotado
          adr-parser = pythonPackages.buildPythonApplication {
            pname = "adr-parser";
            version = version;

            src = ./.;

            # Dependências Python
            propagatedBuildInputs = with pythonPackages; [
              pyyaml
              pynacl
              pytest
              pytest-asyncio
              httpx
              pyyaml-include
              # Ed25519 signatures for decision chain
            ];

            # Script de entrada
            format = "other";

            installPhase = ''
              mkdir -p $out/bin
              mkdir -p $out/lib

              # Instalar o parser
              cp .parsers/adr_parser.py $out/lib/

              # Instalar chain modules (private blockchain)
              if [ -d .chain ]; then
                cp .chain/*.py $out/lib/ 2>/dev/null || true
              fi

              # Criar wrapper executável
              cat > $out/bin/adr-parser <<EOF
              #!${python}/bin/python3.13
              import sys
              sys.path.insert(0, "$out/lib")
              from adr_parser import main
              if __name__ == "__main__":
                  sys.exit(main())
              EOF

              chmod +x $out/bin/adr-parser
            '';

            # Metadata
            meta = {
              description = "ADR Parser - Transforms Architecture Decision Records into Knowledge Law";
              license = pkgs.lib.licenses.asl20;
            };
          };

          # CLI wrapper
          adr-cli = pkgs.writeShellScriptBin "adr" ''
            set -euo pipefail

            if [ -f "$PWD/flake.nix" ] && [ -f "$PWD/scripts/adr" ] && [ -d "$PWD/adr" ]; then
              LEDGER_ROOT="$PWD"
            elif [ -n "''${ADR_LEDGER_ROOT:-}" ] && [ -f "''${ADR_LEDGER_ROOT}/scripts/adr" ]; then
              LEDGER_ROOT="$ADR_LEDGER_ROOT"
            else
              LEDGER_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
            fi
            SCHEMA="$LEDGER_ROOT/.schema/adr.schema.json"
            GOVERNANCE="$LEDGER_ROOT/.governance/governance.yaml"
            KNOWLEDGE_DIR="$LEDGER_ROOT/knowledge"
            PARSER="${adr-parser}/bin/adr-parser"

            cmd="''${1:-help}"
            shift || true

            case "$cmd" in
              sync)
                echo "🔄 Synchronizing Knowledge Base..."

                # Generate all knowledge artifacts
                $PARSER "$LEDGER_ROOT/adr/accepted" --format knowledge --pretty -o "$KNOWLEDGE_DIR/knowledge_base.json"
                $PARSER "$LEDGER_ROOT/adr/accepted" --format graph --pretty -o "$KNOWLEDGE_DIR/graph.json"
                $PARSER "$LEDGER_ROOT/adr/accepted" --format spectre --pretty -o "$KNOWLEDGE_DIR/spectre_corpus.json"
                $PARSER "$LEDGER_ROOT/adr/accepted" --format phantom --pretty -o "$KNOWLEDGE_DIR/phantom_training.json"

                # Generate index
                cat > "$KNOWLEDGE_DIR/index.json" <<EOF
            {
              "version": "1.0",
              "generated_at": "$(date -Iseconds)",
              "files": {
                "knowledge_base": "knowledge_base.json",
                "graph": "graph.json",
                "spectre_corpus": "spectre_corpus.json",
                "phantom_training": "phantom_training.json"
              },
              "agents": {
                "CEREBRO": {
                  "primary": "knowledge_base.json",
                  "secondary": ["graph.json"]
                },
                "SPECTRE": {
                  "primary": "spectre_corpus.json"
                },
                "PHANTOM": {
                  "primary": "phantom_training.json"
                },
                "NEUTRON": {
                  "primary": "knowledge_base.json",
                  "enforce_compliance": true
                }
              }
            }
            EOF

                echo "✅ Knowledge synchronized"
                ;;

              validate)
                export ADR_LEDGER_ROOT="$LEDGER_ROOT"
                ${pkgs.bash}/bin/bash $LEDGER_ROOT/scripts/validate.sh "$LEDGER_ROOT/adr"
                ;;

              policy-check)
                export ADR_LEDGER_ROOT="$LEDGER_ROOT"
                ${pkgs.bash}/bin/bash $LEDGER_ROOT/scripts/opa-validate.sh "$LEDGER_ROOT/adr"
                ;;

              bitcoin)
                export ADR_LEDGER_ROOT="$LEDGER_ROOT"
                ${python}/bin/python3.13 $LEDGER_ROOT/.chain/bitcoin_attestation.py "$@"
                ;;

              parser)
                # Direct access to parser
                $PARSER "$@"
                ;;

              export)
                # Export ADRs in JSON/JSONL format with filtering
                $PARSER export "$@"
                ;;

              bash-cli)
                # Use the original bash CLI
                ${pkgs.bash}/bin/bash ${./scripts/adr} "$@"
                ;;

              *)
                if [ "$cmd" = "help" ] || [ "$cmd" = "--help" ] || [ "$cmd" = "-h" ]; then
                  cat <<HELP
            ADR Ledger CLI (Nix)

            Usage: adr <command> [options]

            Commands:
              sync         Generate knowledge artifacts (JSON outputs)
              validate     Run schema + OPA + cryptographic health validation
              policy-check Evaluate OPA/Rego policy only
              bitcoin      Bitcoin-compatible secp256k1 attestation helper
              parser       Direct access to Python parser
              export       Export ADRs as JSON/JSONL with filtering
              bash-cli     Use original bash CLI explicitly
              <other>      Delegated to scripts/adr automatically

            Examples:
              adr sync
              adr validate
              adr policy-check
              adr bitcoin list
              adr list
              adr parser adr/accepted --format json --pretty

              # Export examples
              adr export adr/accepted --format jsonl --compact
              adr export adr --format json --filter-status accepted --filter-project CEREBRO
              adr export adr/accepted --format jsonl --since 2026-01-01

              adr bash-cli new -t "New Decision" -p CEREBRO -c major

            Export filtering options:
              --format json|jsonl              Output format (default: json)
              --compact                        Minified JSON (no whitespace)
              --filter-status STATUS           Filter by status (proposed, accepted, rejected, deprecated, superseded)
              --filter-project PROJECT         Filter by project (CEREBRO, PHANTOM, SPECTRE, NEUTRON, GLOBAL)
              --filter-classification CLASS    Filter by classification (critical, major, minor, patch)
              --since YYYY-MM-DD              Filter ADRs from this date (inclusive)
              --until YYYY-MM-DD              Filter ADRs until this date (inclusive)

            For full bash CLI help:
              adr bash-cli help
            HELP
                else
                  exec ${pkgs.bash}/bin/bash ${./scripts/adr} "$cmd" "$@"
                fi
                ;;
            esac
          '';

          # Git hooks installer
          adr-hooks = pkgs.writeShellScriptBin "adr-install-hooks" ''
            set -euo pipefail

            REPO_ROOT=$(git rev-parse --show-toplevel)
            HOOKS_DIR="$REPO_ROOT/.git/hooks"

            echo "Installing ADR git hooks..."

            # Pre-commit: schema validation + chain integrity + SBOM drift
            cat > "$HOOKS_DIR/pre-commit" <<'HOOK'
            #!/usr/bin/env bash
            set -euo pipefail

            REPO_ROOT=$(git rev-parse --show-toplevel)
            CHAIN_DIR="$REPO_ROOT/.chain"
            PYTHON="${
              python.withPackages (ps: [
                ps.pyyaml
                ps.pynacl
              ])
            }/bin/python3"
            ERRORS=0

            # --- 1. ADR Schema Validation ---
            MODIFIED_ADRS=$(git diff --cached --name-only --diff-filter=ACM | grep -E 'adr/.*\.md$' || true)

            if [ -n "$MODIFIED_ADRS" ]; then
              echo "🔍 Validating ADR schemas..."
              for adr in $MODIFIED_ADRS; do
                $PYTHON -c "
            import re, sys, yaml
            with open('$adr') as f:
                content = f.read()
            match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not match:
                print('❌ No YAML frontmatter: $adr', file=sys.stderr)
                sys.exit(1)
            try:
                data = yaml.safe_load(match.group(1))
                for field in ['id', 'title', 'status', 'date']:
                    if field not in data:
                        print(f'❌ Missing field: {field} in $adr', file=sys.stderr)
                        sys.exit(1)
            except Exception as e:
                print(f'❌ Invalid YAML in $adr: {e}', file=sys.stderr)
                sys.exit(1)
                " || ERRORS=$((ERRORS + 1))
              done
              [ $ERRORS -eq 0 ] && echo "  ✅ ADR schemas valid"
            fi

            # --- 2. Chain Integrity ---
            CHAIN_MODIFIED=$(git diff --cached --name-only | grep -E '\.chain/' || true)

            if [ -n "$CHAIN_MODIFIED" ] && [ -f "$CHAIN_DIR/chain.json" ]; then
              echo "🔗 Verifying chain integrity..."
              cd "$REPO_ROOT"
              if ! $PYTHON .chain/chain_manager.py verify > /dev/null 2>&1; then
                echo "  ❌ Chain integrity check FAILED" >&2
                ERRORS=$((ERRORS + 1))
              else
                echo "  ✅ Chain integrity OK"
              fi
            fi

            # --- 3. SBOM Drift Detection ---
            DEPS_MODIFIED=$(git diff --cached --name-only | grep -E '(flake\.nix|flake\.lock)' || true)

            if [ -n "$DEPS_MODIFIED" ] && [ -f "$CHAIN_DIR/sbom/sbom_current.json" ]; then
              echo "📦 Checking SBOM drift..."
              cd "$REPO_ROOT"
              DRIFT=$($PYTHON .chain/sbom_manager.py verify 2>&1) || true
              if echo "$DRIFT" | grep -q "DRIFT DETECTED"; then
                echo "  ⚠️  SBOM drift detected — run 'adr sbom generate' to update" >&2
                echo "  $DRIFT" >&2
                # Warning only, don't block commit
              else
                echo "  ✅ SBOM in sync"
              fi
            fi

            if [ $ERRORS -gt 0 ]; then
              echo ""
              echo "❌ Pre-commit failed with $ERRORS error(s)" >&2
              exit 1
            fi
            HOOK

            chmod +x "$HOOKS_DIR/pre-commit"

            # Post-merge: regenerar JSONs
            cat > "$HOOKS_DIR/post-merge" <<'EOF'
            #!/usr/bin/env bash
            set -euo pipefail

            echo "🔄 Regenerating knowledge artifacts..."

            ${adr-cli}/bin/adr sync

            echo "✅ Knowledge synchronized after merge"
            EOF

            chmod +x "$HOOKS_DIR/post-merge"

            # Post-commit: também regenerar após commits locais
            cat > "$HOOKS_DIR/post-commit" <<'EOF'
            #!/usr/bin/env bash
            set -euo pipefail

            echo "🔄 Regenerating knowledge artifacts..."

            ${adr-cli}/bin/adr sync

            echo "✅ Knowledge synchronized after commit"
            EOF

            chmod +x "$HOOKS_DIR/post-commit"

            echo "✅ Git hooks installed successfully"
            echo ""
            echo "Hooks installed:"
            echo "  - pre-commit: ADR schema + chain integrity + SBOM drift"
            echo "  - post-merge: Auto-generate knowledge JSONs"
            echo "  - post-commit: Auto-generate knowledge JSONs"
          '';

          # Default package
          default = adr-cli;
        };

        # =================================================================
        # APPS
        # =================================================================
        apps = {
          adr = {
            type = "app";
            program = "${self.packages.${system}.adr-cli}/bin/adr";
          };

          adr-parser = {
            type = "app";
            program = "${self.packages.${system}.adr-parser}/bin/adr-parser";
          };

          adr-sync = {
            type = "app";
            program = "${pkgs.writeShellScript "adr-sync" ''
              ${self.packages.${system}.adr-cli}/bin/adr sync
            ''}";
          };

          adr-validate = {
            type = "app";
            program = "${pkgs.writeShellScript "adr-validate" ''
              ${self.packages.${system}.adr-cli}/bin/adr validate
            ''}";
          };

          default = self.apps.${system}.adr;
        };

        # =================================================================
        # DEV SHELL
        # =================================================================
        devShells.default = pkgs.mkShell {
          name = "adr-ledger-dev";

          buildInputs = [
            # Python 3.13 e dependências
            python
            pythonPackages.pyyaml
            pythonPackages.pynacl # Ed25519 for decision chain
            pythonPackages.jsonschema

            # Ferramentas de validação
            pkgs.check-jsonschema
            pkgs.yamllint
            pkgs.jq
            pkgs.open-policy-agent
            pkgs.conftest
            pkgs.openssl

            # Ferramentas de visualização
            pkgs.graphviz

            # Git
            pkgs.git
            pkgs.nix

            # OpenTimestamps CLI for temporal anchoring
            pkgs.opentimestamps-client

            # Packages deste flake
            self.packages.${system}.adr-parser
            self.packages.${system}.adr-cli
            self.packages.${system}.adr-hooks

            # Bash CLI original
            (pkgs.writeShellScriptBin "adr-bash" ''
              ${pkgs.bash}/bin/bash ${./scripts/adr} "$@"
            '')
            (pkgs.writeShellScriptBin "adr-phantom-scan" ''
              ${pkgs.bash}/bin/bash ${./scripts/phantom-scan-check.sh} "$@"
            '')
            (pkgs.writeShellScriptBin "adr-opa-validate" ''
              ${pkgs.bash}/bin/bash ${./scripts/opa-validate.sh} "$@"
            '')
            (pkgs.writeShellScriptBin "adr-bitcoin" ''
              ${python}/bin/python3.13 ${./.chain/bitcoin_attestation.py} "$@"
            '')
          ];

          shellHook = ''
            echo "🧠 ADR Ledger Development Environment"
            echo ""
            echo "Available commands:"
            echo "  adr              - ADR CLI (Nix wrapper)"
            echo "  adr-bash         - Original Bash CLI"
            echo "  adr-parser       - Parse ADRs directly"
            echo "  adr-install-hooks - Install git hooks"
            echo "  adr-phantom-scan - Phantom-backed leak scan"
            echo "  adr-opa-validate - OPA/Rego policy validation"
            echo "  adr-bitcoin      - Bitcoin-compatible attestation helper"
            echo "  yamllint         - Validate YAML files"
            echo "  check-jsonschema - Validate JSON against schema"
            echo "  jq               - JSON processor"
            echo ""

            # Auto-instalar hooks se ainda não existir
            if [ -d .git ] && [ ! -f .git/hooks/pre-commit ]; then
              echo "Installing git hooks automatically..."
              adr-install-hooks
            fi

            if [ -f "$PWD/scripts/adr" ] && [ -d "$PWD/adr" ]; then
              export ADR_LEDGER_ROOT="$PWD"
            fi
          '';
        };

        # =================================================================
        # CHECKS
        # =================================================================
        checks = {
          # Validar schema JSON
          schema-valid =
            pkgs.runCommand "validate-schema"
              {
                buildInputs = [ pkgs.check-jsonschema ];
              }
              ''
                ${pkgs.check-jsonschema}/bin/check-jsonschema \
                  --check-metaschema ${./.schema/adr.schema.json}

                touch $out
              '';

          # Validar governance.yaml
          governance-valid =
            pkgs.runCommand "validate-governance"
              {
                buildInputs = [ pkgs.yamllint ];
              }
              ''
                ${pkgs.yamllint}/bin/yamllint \
                  -d "{extends: default, rules: {line-length: {max: 120}}}" \
                  ${./.governance/governance.yaml}

                touch $out
              '';

          # Testar parser
          parser-tests =
            pkgs.runCommand "parser-tests"
              {
                buildInputs = [
                  self.packages.${system}.adr-parser
                  pythonPackages.pyyaml
                ];
              }
              ''
                # Tentar parsear os ADRs aceitos
                ${self.packages.${system}.adr-parser}/bin/adr-parser \
                  ${./adr/accepted} \
                  --format json > /dev/null

                echo "Parser tests passed"
                touch $out
              '';

          # Validar ADRs contra policy OPA
          opa-policy-valid =
            pkgs.runCommand "validate-opa-policy"
              {
                buildInputs = [
                  python
                  pythonPackages.pyyaml
                  pythonPackages.jsonschema
                  pkgs.open-policy-agent
                ];
              }
              ''
                cd ${./.}
                export PATH=${pkgs.open-policy-agent}/bin:$PATH
                ${python}/bin/python3.13 scripts/validate_adr.py \
                  adr \
                  --skip-schema \
                  --opa-policy policies/adr/validation.rego
                touch $out
              '';

          # Pipeline de validação principal
          validation-pipeline =
            pkgs.runCommand "validate-adr-ledger"
              {
                buildInputs = [
                  python
                  pythonPackages.pyyaml
                  pythonPackages.pynacl
                  pythonPackages.jsonschema
                  pkgs.open-policy-agent
                  pkgs.openssl
                ];
              }
              ''
                cd ${./.}
                export PATH=${pkgs.open-policy-agent}/bin:${pkgs.openssl}/bin:$PATH
                ${pkgs.bash}/bin/bash scripts/validate.sh
                touch $out
              '';

          # Verificar SBOM integrity (se existir)
          sbom-valid =
            pkgs.runCommand "validate-sbom"
              {
                buildInputs = [
                  python
                  pythonPackages.pyyaml
                  pythonPackages.pynacl
                ];
              }
              ''
                if [ -f ${./.chain/sbom/sbom_current.json} ]; then
                  cd ${./.}
                  ${python}/bin/python3.13 .chain/sbom_manager.py verify
                  echo "SBOM verification passed"
                else
                  echo "No SBOM found (skipping verification)"
                fi
                touch $out
              '';

          # Verificar integridade da chain (se existir)
          chain-valid =
            pkgs.runCommand "validate-chain"
              {
                buildInputs = [
                  python
                  pythonPackages.pyyaml
                  pythonPackages.pynacl
                ];
              }
              ''
                if [ -f ${./.chain/chain.json} ]; then
                  cd ${./.}
                  ${python}/bin/python3.13 .chain/chain_manager.py verify
                  echo "Chain verification passed"
                else
                  echo "No chain found (skipping verification)"
                fi
                touch $out
              '';

          # Validar governance contracts em todos os ADRs aceitos
          governance-contracts =
            pkgs.runCommand "validate-governance-contracts"
              {
                buildInputs = [
                  python
                  pythonPackages.pyyaml
                  pythonPackages.pynacl
                ];
              }
              ''
                cd ${./.}
                ${python}/bin/python3.13 .chain/governance_engine.py validate-all \
                  --adr-dir adr/accepted \
                  --mode warn
                echo "Governance contracts validation passed"
                touch $out
              '';

          # Verificar consistência da Merkle tree com a chain
          merkle-valid =
            pkgs.runCommand "validate-merkle"
              {
                buildInputs = [
                  python
                  pythonPackages.pyyaml
                  pythonPackages.pynacl
                ];
              }
              ''
                            cd ${./.}
                            ${python}/bin/python3.13 << 'PYEOF'
                import sys, json, hashlib
                sys.path.insert(0, ".chain")
                from merkle_tree import MerkleTree

                # Rebuild from chain in memory
                tree = MerkleTree()
                root = tree.build_from_chain()

                # Load stored state
                state = json.loads(open(".chain/merkle/merkle_state.json").read())
                stored_root = state.get("root_hash", "")

                if root != stored_root:
                    print(f"Merkle root mismatch: computed={root[:32]}... stored={stored_root[:32]}...", file=sys.stderr)
                    sys.exit(1)

                print(f"Merkle tree consistent: {state['leaf_count']} leaves, {state['height']} levels")
                print(f"Root: {root[:32]}...")
                PYEOF
                            echo "Merkle tree validation passed"
                            touch $out
              '';

          # Detectar IDs duplicados entre proposed/, accepted/, superseded/
          id-conflicts =
            pkgs.runCommand "check-id-conflicts"
              {
                buildInputs = [
                  python
                  pythonPackages.pyyaml
                ];
              }
              ''
                            ${python}/bin/python3.13 -c "
                import os, re, sys
                ids = {}
                for root, _, files in os.walk('${./adr}'):
                    for f in files:
                        if f.endswith('.md'):
                            path = os.path.join(root, f)
                            with open(path) as fh:
                                for line in fh:
                                    m = re.match(r'^id:\s*\"?(ADR-\d+)\"?', line)
                                    if m:
                                        aid = m.group(1)
                                        if aid in ids:
                                            print(f'CONFLICT: {aid} in {ids[aid]} AND {path}', file=sys.stderr)
                                            sys.exit(1)
                                        ids[aid] = path
                                        break
                print(f'No ID conflicts ({len(ids)} unique ADRs)')
                            "
                            touch $out
              '';

          # Verificar assinaturas criptográficas na chain
          signatures-valid =
            pkgs.runCommand "validate-signatures"
              {
                buildInputs = [
                  python
                  pythonPackages.pyyaml
                  pythonPackages.pynacl
                ];
              }
              ''
                            cd ${./.}
                            ${python}/bin/python3.13 -c "
                import sys
                sys.path.insert(0, '.chain')
                from chain_manager import ChainManager
                from crypto import verify_signature, Signature

                cm = ChainManager()
                cm.load()
                checked = 0
                for block in cm.state.chain:
                    for sig in block.signatures:
                        s = Signature(**sig) if isinstance(sig, dict) else sig
                        if not verify_signature(block.block_hash, s):
                            print(f'WARN: {block.adr_id} sig by {s.signer_id} — key may not be registered', file=sys.stderr)
                        else:
                            checked += 1
                            print(f'  OK: {block.adr_id} sig by {s.signer_id}')
                print(f'Verified {checked} signature(s)')
                            "
                            touch $out
              '';
        };
      }
    )
    // (
      let
        # ===================================================================
        # OUTPUTS CROSS-SYSTEM (lib, NixOS modules)
        # ===================================================================
        syncModule = import ./nix/modules/adr-ledger-sync.nix { inherit self; };
        agentsModule = import ./nix/modules/adr-ledger-iam.nix {
          inherit self securellmMcp;
          phantom = inputs.phantom;
          cerebro = inputs.cerebro;
          spectre = inputs.spectre;
          owasaka = inputs.owasaka;
          mlOpsApi = inputs.ml-ops-api;
        };
        fullModule = import ./nix/modules/adr-ledger-full.nix {
          inherit self securellmMcp;
          phantom = inputs.phantom;
          cerebro = inputs.cerebro;
          spectre = inputs.spectre;
          owasaka = inputs.owasaka;
          mlOpsApi = inputs.ml-ops-api;
        };
      in
      {

        lib = {
          # Carregar knowledge base em Nix
          loadKnowledgeBase = path: builtins.fromJSON (builtins.readFile path);

          # Filtrar ADRs por projeto
          filterByProject =
            kb: project: builtins.filter (adr: builtins.elem project adr.scope.projects) kb.decisions;

          # Extrair ADRs de compliance
          getComplianceADRs = kb: builtins.filter (adr: adr.governance.compliance_tags != [ ]) kb.decisions;

          # Extrair ADRs por status
          filterByStatus = kb: status: builtins.filter (adr: adr.status == status) kb.decisions;
        };

        nixosModules = {
          adr-ledger = fullModule;
          adr-ledger-sync = syncModule;
          adr-ledger-agents = agentsModule;
        };
      }
    );
}
