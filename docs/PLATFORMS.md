# Platform Support

ADR Ledger é desenvolvido e operado primariamente em NixOS. As outras plataformas funcionam,
mas exigem setup manual do que o Nix entrega automaticamente.

---

## NixOS / Nix (Linux, macOS)

Setup completo em um comando:

```bash
git clone https://github.com/marcosfpina/adr-ledger.git
cd adr-ledger
nix develop
```

O `devShell` provisiona Python 3.13, dependências, e instala os git hooks automaticamente.
Ambiente reproduzível — funciona igual em qualquer máquina com Nix.

Para validar:

```bash
nix flake check
```

**Nix no macOS**: instale via [determinate.systems/nix](https://determinate.systems/nix) ou
o installer oficial. O flake funciona em `aarch64-darwin` (Apple Silicon) e `x86_64-darwin`.

---

## Linux (sem Nix)

Instale as dependências manualmente:

```bash
# Debian/Ubuntu
sudo apt install python3 python3-yaml yamllint jq git

# Fedora/RHEL
sudo dnf install python3 python3-pyyaml yamllint jq git

# Arch
sudo pacman -S python python-yaml yamllint jq git
```

Clone e configure:

```bash
git clone https://github.com/marcosfpina/adr-ledger.git
cd adr-ledger
chmod +x scripts/adr
export PATH="$PWD/scripts:$PATH"
bash .hooks/install.sh   # instala git hooks manualmente
```

Adicione ao seu shell profile para persistir o PATH:

```bash
echo 'export PATH="/path/to/adr-ledger/scripts:$PATH"' >> ~/.bashrc
```

---

## macOS

Requer [Homebrew](https://brew.sh):

```bash
brew install python3 yamllint jq
pip3 install pyyaml
```

Clone e configure:

```bash
git clone https://github.com/marcosfpina/adr-ledger.git
cd adr-ledger
chmod +x scripts/adr
export PATH="$PWD/scripts:$PATH"
bash .hooks/install.sh
```

Para uma experiência mais próxima do ambiente de desenvolvimento original, considere instalar
Nix — o flake funciona em Apple Silicon e Intel sem modificações.

---

## Windows

O caminho recomendado é WSL2 com Ubuntu. Após instalar o WSL2:

```bash
# No terminal WSL2
sudo apt install python3 python3-yaml yamllint jq git

git clone https://github.com/marcosfpina/adr-ledger.git
cd adr-ledger
chmod +x scripts/adr
export PATH="$PWD/scripts:$PATH"
bash .hooks/install.sh
```

O CLI (`scripts/adr`) é um script Bash — requer WSL2 ou Git Bash. PowerShell não é suportado.

Alternativamente, Nix funciona dentro do WSL2:

```bash
# No WSL2, após instalar Nix
cd adr-ledger
nix develop
```

---

## Matriz de suporte

| Plataforma | Setup | Git hooks | `nix flake check` | Suporte |
|------------|-------|-----------|-------------------|---------|
| NixOS | `nix develop` | automático | nativo | primário |
| Linux + Nix | `nix develop` | automático | nativo | primário |
| macOS + Nix | `nix develop` | automático | nativo | primário |
| Linux (sem Nix) | manual | manual | não disponível | community |
| macOS (sem Nix) | manual | manual | não disponível | community |
| Windows (WSL2 + Nix) | `nix develop` | automático | nativo | community |
| Windows (WSL2, sem Nix) | manual | manual | não disponível | community |

**Primário**: testado continuamente, CI roda aqui.
**Community**: funciona, mas não é o ambiente de desenvolvimento padrão.

---

## Dependências

| Dependência | Versão mínima | Uso |
|-------------|---------------|-----|
| Python | 3.8+ | Parser, CLI, chain modules |
| PyYAML | qualquer | Parsing de frontmatter |
| yamllint | qualquer | Validação de YAML |
| jq | qualquer | Queries no knowledge base |
| git | 2.x | Controle de versão, hooks |
| PyNaCl | qualquer | Assinaturas criptográficas (chain) |

Com Nix, todas as versões são fixadas no `flake.lock`.
