{
  description = "ADR Ledger - Architecture Decision Records as Knowledge Law";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Versão
        version = "1.0.0";

        # Python e dependências
        python = pkgs.python313;
        pythonPackages = python.pkgs;

      in {
        # =================================================================
        # PACKAGES
        # =================================================================
        packages = rec {
          # Parser Python empacotado
          adr-parser = pythonPackages.buildPythonApplication {
            pname = "adr-parser";
            version = version;

            src = ./.;

            # Apenas PyYAML como dependência externa
            propagatedBuildInputs = with pythonPackages; [
              pyyaml
            ];

            # Script de entrada
            format = "other";

            installPhase = ''
              mkdir -p $out/bin
              mkdir -p $out/lib

              # Instalar o parser
              cp .parsers/adr_parser.py $out/lib/

              # Criar wrapper executável
              cat > $out/bin/adr-parser <<EOF
              #!${python}/bin/python313
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
              license = pkgs.lib.licenses.mit;
            };
          };

          # CLI wrapper
          adr-cli = pkgs.writeShellScriptBin "adr" ''
            set -euo pipefail

            LEDGER_ROOT="''${ADR_LEDGER_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
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
                echo "🔍 Validating ADRs..."

                # Validate schema
                if [ ! -f "$SCHEMA" ]; then
                  echo "❌ Schema not found: $SCHEMA"
                  exit 1
                fi

                # Check if any ADRs exist
                if ! ls "$LEDGER_ROOT/adr"/*/*.md 1> /dev/null 2>&1; then
                  echo "⚠️  No ADRs found"
                  exit 0
                fi

                # Validate each ADR
                for adr in "$LEDGER_ROOT/adr"/*/*.md; do
                  [ -f "$adr" ] || continue

                  echo "  Validating $(basename $adr)..."

                  # Extract YAML frontmatter and validate
                  ${python.withPackages (ps: [ ps.pyyaml ])}/bin/python3 -c "
            import re, sys, yaml, json

            with open('$adr') as f:
                content = f.read()

            match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not match:
                print('❌ No YAML frontmatter found', file=sys.stderr)
                sys.exit(1)

            try:
                data = yaml.safe_load(match.group(1))
                # Basic validation
                required_fields = ['id', 'title', 'status', 'date']
                for field in required_fields:
                    if field not in data:
                        print(f'❌ Missing required field: {field}', file=sys.stderr)
                        sys.exit(1)
            except Exception as e:
                print(f'❌ Invalid YAML: {e}', file=sys.stderr)
                sys.exit(1)
                  " || exit 1
                done

                echo "✅ All ADRs valid"
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
                cat <<HELP
            ADR Ledger CLI (Nix)

            Usage: adr <command> [options]

            Commands:
              sync         Generate knowledge artifacts (JSON outputs)
              validate     Validate ADRs against schema
              parser       Direct access to Python parser
              export       Export ADRs as JSON/JSONL with filtering
              bash-cli     Use original bash CLI

            Examples:
              adr sync
              adr validate
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
                ;;
            esac
          '';

          # Git hooks installer
          adr-hooks = pkgs.writeShellScriptBin "adr-install-hooks" ''
            set -euo pipefail

            REPO_ROOT=$(git rev-parse --show-toplevel)
            HOOKS_DIR="$REPO_ROOT/.git/hooks"

            echo "Installing ADR git hooks..."

            # Pre-commit: validação de schema
            cat > "$HOOKS_DIR/pre-commit" <<'EOF'
            #!/usr/bin/env bash
            set -euo pipefail

            echo "🔍 Validating ADRs..."

            # Pegar ADRs modificados
            MODIFIED_ADRS=$(git diff --cached --name-only --diff-filter=ACM | grep -E 'adr/.*\.md$' || true)

            if [ -z "$MODIFIED_ADRS" ]; then
              echo "✅ No ADRs to validate"
              exit 0
            fi

            # Validar cada ADR
            for adr in $MODIFIED_ADRS; do
              echo "  Validating $adr..."

              # Extrair YAML frontmatter
              ${python.withPackages (ps: [ ps.pyyaml ])}/bin/python3 -c "
            import re, sys, yaml, json

            with open('$adr') as f:
                content = f.read()

            match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if not match:
                print('❌ No YAML frontmatter found', file=sys.stderr)
                sys.exit(1)

            try:
                data = yaml.safe_load(match.group(1))
                required = ['id', 'title', 'status', 'date']
                for field in required:
                    if field not in data:
                        print(f'❌ Missing field: {field}', file=sys.stderr)
                        sys.exit(1)
            except Exception as e:
                print(f'❌ Invalid YAML: {e}', file=sys.stderr)
                sys.exit(1)
              " || exit 1
            done

            echo "✅ All ADRs valid"
            EOF

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
            echo "  - pre-commit: Validate ADR schema"
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

          buildInputs = with pkgs; [
            # Python e dependências
            python3
            python3Packages.pyyaml
            python3Packages.jsonschema

            # Ferramentas de validação
            check-jsonschema
            yamllint
            jq

            # Ferramentas de visualização
            graphviz

            # Git
            git

            # Packages deste flake
            self.packages.${system}.adr-parser
            self.packages.${system}.adr-cli
            self.packages.${system}.adr-hooks

            # Bash CLI original
            (pkgs.writeShellScriptBin "adr-bash" ''
              ${pkgs.bash}/bin/bash ${./scripts/adr} "$@"
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
            echo "  yamllint         - Validate YAML files"
            echo "  check-jsonschema - Validate JSON against schema"
            echo "  jq               - JSON processor"
            echo ""

            # Auto-instalar hooks se ainda não existir
            if [ -d .git ] && [ ! -f .git/hooks/pre-commit ]; then
              echo "Installing git hooks automatically..."
              adr-install-hooks
            fi

            export ADR_LEDGER_ROOT="$PWD"
          '';
        };

        # =================================================================
        # CHECKS
        # =================================================================
        checks = {
          # Validar schema JSON
          schema-valid = pkgs.runCommand "validate-schema" {
            buildInputs = [ pkgs.check-jsonschema ];
          } ''
            ${pkgs.check-jsonschema}/bin/check-jsonschema \
              --check-metaschema ${./.schema/adr.schema.json}

            touch $out
          '';

          # Validar governance.yaml
          governance-valid = pkgs.runCommand "validate-governance" {
            buildInputs = [ pkgs.yamllint ];
          } ''
            ${pkgs.yamllint}/bin/yamllint ${./.governance/governance.yaml}

            touch $out
          '';

          # Testar parser
          parser-tests = pkgs.runCommand "parser-tests" {
            buildInputs = [
              self.packages.${system}.adr-parser
              pkgs.python3Packages.pyyaml
            ];
          } ''
            # Tentar parsear os ADRs aceitos
            ${self.packages.${system}.adr-parser}/bin/adr-parser \
              ${./adr/accepted} \
              --format json > /dev/null

            echo "Parser tests passed"
            touch $out
          '';
        };
      }
    ) // {
      # ===================================================================
      # OUTPUTS CROSS-SYSTEM (lib, NixOS modules)
      # ===================================================================

      lib = {
        # Carregar knowledge base em Nix
        loadKnowledgeBase = path:
          builtins.fromJSON (builtins.readFile path);

        # Filtrar ADRs por projeto
        filterByProject = kb: project:
          builtins.filter
            (adr: builtins.elem project adr.scope.projects)
            kb.decisions;

        # Extrair ADRs de compliance
        getComplianceADRs = kb:
          builtins.filter
            (adr: adr.governance.compliance_tags != [])
            kb.decisions;

        # Extrair ADRs por status
        filterByStatus = kb: status:
          builtins.filter
            (adr: adr.status == status)
            kb.decisions;
      };

      # NixOS Module (para integração futura)
      nixosModules.adr-ledger = { config, lib, pkgs, ... }:
        with lib;

        let
          cfg = config.services.adr-ledger;

        in {
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
            # Systemd service para auto-sync
            systemd.services.adr-sync = mkIf cfg.autoSync {
              description = "ADR Knowledge Sync";
              after = [ "network.target" ];

              serviceConfig = {
                Type = "oneshot";
                ExecStart = "${self.packages.${pkgs.system}.adr-cli}/bin/adr sync";
                WorkingDirectory = cfg.ledgerPath;
              };
            };

            # Timer para sync periódico (opcional)
            systemd.timers.adr-sync = mkIf cfg.autoSync {
              description = "ADR Knowledge Sync Timer";
              wantedBy = [ "timers.target" ];

              timerConfig = {
                OnCalendar = "daily";
                Persistent = true;
              };
            };

            # Disponibilizar knowledge base como arquivo do sistema
            environment.etc."adr/knowledge_base.json" = mkIf cfg.autoSync {
              source = cfg.knowledgeBasePath;
            };
          };
        };
    };
}
