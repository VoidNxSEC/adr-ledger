# Roadmap de Publicacao de Release

**Status:** draft operacional
**Data-base:** 2026-04-01
**Objetivo:** publicar a proxima release publica do `adr-ledger` com validacao reprodutivel, documentacao coerente e integracao MCP alinhada ao `securellm-mcp`.

## Baseline atual

- `flake.nix` ainda declara a versao `0.1.0`.
- O README anuncia `v0.1.0` como beta atual.
- `nix flake check --no-build` passa no estado atual do repositório.
- A integracao MCP ativa vive em `~/master/securellm-mcp`, nao em um servidor MCP nativo dentro deste repo.
- O flake agora importa o `securellm-mcp` como input e exporta modulos NixOS separados para sync e agentes.
- O input transitive de `spider-nix` precisa permanecer remoto para nao reintroduzir `file:/home/...` no `flake.lock`.
- O workflow de GitHub ainda referencia `.parsers/adr_parser.py adr/ --validate`, mas esse argumento nao existe mais no parser atual.
- `adr validate ADR-0001` funciona, mas o ledger ainda expõe warnings conhecidos:
  - `ADR-0001` com warnings de schema/governance.
  - `ADR-0054` com drift de chain/signature.
  - receipts Bitcoin ausentes no repositório local.

## Regra de versao

- Use `v0.1.1` se a release for apenas de estabilizacao, docs e CI.
- Use `v0.2.0` se a release incluir novas interfaces publicas, modulos Nix suportados oficialmente ou mudancas de fluxo para consumidores externos.
- Se `nixosModules.adr-ledger-agents` entrar na narrativa oficial da release como superficie suportada, trate isso como `v0.2.0`.

## Fase 0 - Congelar escopo

- [ ] Escolher a versao alvo (`v0.1.1` ou `v0.2.0`).
- [ ] Definir o que entra e o que fica explicitamente fora da release.
- [ ] Gerar rascunho de changelog a partir dos commits desde a ultima tag.
- [ ] Decidir se os arquivos locais em andamento entram na release:
  - `docs/DAEMON.md` -> manter apenas se refletir a arquitetura `adr-ledger modules + securellm-mcp backend`
  - `nix/modules/agents.nix` -> nao entra se continuar como modulo duplicado/legado
  - `scripts/adr-ledger-mcp.service` -> nao entra se continuar assumindo `adr-mcp-server` local
  - `config.toml` -> nao entra se continuar sendo configuracao de ambiente local
- [ ] Limpar lixo acidental antes do corte, como a alteracao em `inspirations/002.md`.

**Saida esperada:** escopo travado, versao definida e backlog de release separado do backlog de produto.

## Fase 1 - Fechar blockers de release

- [ ] Corrigir o workflow `.github/workflows/adr-validation.yml` para usar entrypoints suportados de validacao.
- [ ] Decidir politica para warnings atuais do ledger:
  - corrigir antes da release; ou
  - documentar como known issues com criterio explicito.
- [ ] Resolver ou documentar o drift criptografico de `ADR-0054`.
- [ ] Confirmar se receipts Bitcoin sao obrigatorios para a release ou apenas `warn`.
- [ ] Revisar docs e remover ambiguidade sobre MCP local vs integracao via `securellm-mcp`.
- [ ] Garantir que `flake.lock` nao carregue dependencias locais transitivas (`file:/home/...`) para a release publica.

**Saida esperada:** CI coerente com o estado atual do codigo e sem blockers desconhecidos no fluxo de release.

## Fase 2 - Consolidar documentacao e mensagem da release

- [ ] Atualizar README, comandos e exemplos para refletir apenas fluxos suportados.
- [ ] Criar release notes da versao alvo:
  - resumo executivo
  - mudancas principais
  - breaking changes
  - known issues
  - comandos de validacao
- [ ] Garantir que o posicionamento da release esteja claro:
  - beta estabilizado; ou
  - minor release com novo escopo oficial.
- [ ] Documentar a fronteira de integracao com `securellm-mcp` como dependencia externa, nao como pacote deste repo.

**Saida esperada:** narrativa de release pronta para GitHub Release, README e anuncio.

## Fase 3 - Gate de validacao

Executar e registrar o resultado dos checks que definem o go/no-go:

```bash
nix flake check
nix develop . --command bash -lc 'cd "$PWD" && bash scripts/validate.sh'
nix develop . --command bash -lc 'cd "$PWD" && bash scripts/adr list -f json >/tmp/adr-list.json'
nix develop . --command bash -lc 'cd "$PWD" && bash scripts/adr validate ADR-0001'
```

Checks complementares recomendados:

- [ ] Smoke test do fluxo `securellm-mcp -> adr-ledger` para `adr_list`, `adr_show` e `adr_validate`.
- [ ] Verificar que `knowledge/*.json` esta sincronizado com o estado atual antes da tag.
- [ ] Confirmar que os warnings aceitos estao documentados nas release notes.

**Saida esperada:** pacote de evidencias de validacao anexavel ao release.

## Fase 4 - Publicacao

- [ ] Atualizar versao em `flake.nix` e badges/docs correlatas, se necessario.
- [ ] Criar tag anotada `vX.Y.Z`.
- [ ] Publicar GitHub Release com notas, comandos de verificacao e known issues.
- [ ] Anexar artefatos, se houver:
  - source tarball
  - hashes
  - relatorio resumido de validacao
- [ ] Fazer smoke check pos-publicacao em clone limpo.

**Saida esperada:** release publicada e verificavel em ambiente limpo.

## Definicao de pronto

A release so pode ser considerada pronta quando todos os itens abaixo forem verdadeiros:

- O fluxo de CI usa comandos que existem hoje no repositório.
- A versao publicada bate com `flake.nix`, README e tag.
- O README nao promete um servidor MCP local que este repo nao entrega.
- Warnings remanescentes estao resolvidos ou explicitamente aceitos nas release notes.
- Existe evidencia reproduzivel de validacao antes da tag.

## Fora do escopo desta release

Itens validos para roadmap de produto, mas nao obrigatorios para publicar a proxima release:

- MCP server nativo dentro do `adr-ledger`.
- Empacotamento `.deb`/`.rpm`.
- Submissao a `nixpkgs`.
- Automacao de ADR por detecao de commits.
- Expansao dos modulos Nix de agentes alem do baseline atual de sync + usuarios + sandbox.

## Decisoes atuais de curadoria

Itens que fazem sentido manter no commit atual:

- modularizacao Nix em `nix/modules/adr-ledger-sync.nix`, `nix/modules/adr-ledger-iam.nix` e `nix/modules/adr-ledger-full.nix`
- integracao por flake input com `securellm-mcp`
- override remoto de `spider-nix` para manter o `flake.lock` publico e portavel
- correcao do CLI para `adr validate ADR-xxxx`
- `docs/DAEMON.md`, porque agora documenta o backend `securellm-mcp` e nao um servidor MCP local
- `docs/RELEASE_ROADMAP.md`
- link de documentacao no `README.md` para o modelo de daemon suportado

Itens que nao devem entrar enquanto permanecerem no formato atual:

- `config.toml`
- `nix/modules/agents.nix` porque e um duplicado nao referenciado pelo flake
- `scripts/adr-ledger-mcp.service` porque continua assumindo `adr-mcp-server` local
- alteracoes acidentais em arquivos de inspiracao
