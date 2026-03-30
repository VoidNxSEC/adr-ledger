# Platform Support

ADR Ledger is primarily developed and operated on NixOS. Other platforms work,
but require manual setup for what Nix provides automatically.

---

## NixOS / Nix (Linux, macOS)

Full setup in one command:

```bash
git clone https://github.com/marcosfpina/adr-ledger.git
cd adr-ledger
nix develop
```

The `devShell` provisions Python 3.13, dependencies, and installs git hooks automatically.
Reproducible environment — works the exact same way on any machine with Nix.

To validate:

```bash
nix flake check
```

**Nix on macOS**: install via [determinate.systems/nix](https://determinate.systems/nix) or
the official installer. The flake works on `aarch64-darwin` (Apple Silicon) and `x86_64-darwin`.

---

## Linux (without Nix)

Install dependencies manually:

```bash
# Debian/Ubuntu
sudo apt install python3 python3-yaml yamllint jq git

# Fedora/RHEL
sudo dnf install python3 python3-pyyaml yamllint jq git

# Arch
sudo pacman -S python python-yaml yamllint jq git
```

Clone and configure:

```bash
git clone https://github.com/marcosfpina/adr-ledger.git
cd adr-ledger
chmod +x scripts/adr
export PATH="$PWD/scripts:$PATH"
bash .hooks/install.sh   # manually install git hooks
```

Add to your shell profile to persist the PATH:

```bash
echo 'export PATH="/path/to/adr-ledger/scripts:$PATH"' >> ~/.bashrc
```

---

## macOS

Requires [Homebrew](https://brew.sh):

```bash
brew install python3 yamllint jq
pip3 install pyyaml
```

Clone and configure:

```bash
git clone https://github.com/marcosfpina/adr-ledger.git
cd adr-ledger
chmod +x scripts/adr
export PATH="$PWD/scripts:$PATH"
bash .hooks/install.sh
```

For an experience closer to the original development environment, consider installing
Nix — the flake works on Apple Silicon and Intel without modifications.

---

## Windows

The recommended path is WSL2 with Ubuntu. After installing WSL2:

```bash
# In WSL2 terminal
sudo apt install python3 python3-yaml yamllint jq git

git clone https://github.com/marcosfpina/adr-ledger.git
cd adr-ledger
chmod +x scripts/adr
export PATH="$PWD/scripts:$PATH"
bash .hooks/install.sh
```

The CLI (`scripts/adr`) is a Bash script — it requires WSL2 or Git Bash. PowerShell is not supported.

Alternatively, Nix works inside WSL2:

```bash
# In WSL2, after installing Nix
cd adr-ledger
nix develop
```

---

## Support Matrix

| Platform | Setup | Git hooks | `nix flake check` | Support |
|------------|-------|-----------|-------------------|---------|
| NixOS | `nix develop` | automatic | native | primary |
| Linux + Nix | `nix develop` | automatic | native | primary |
| macOS + Nix | `nix develop` | automatic | native | primary |
| Linux (without Nix) | manual | manual | not available | community |
| macOS (without Nix) | manual | manual | not available | community |
| Windows (WSL2 + Nix) | `nix develop` | automatic | native | community |
| Windows (WSL2, without Nix) | manual | manual | not available | community |

**Primary**: continuously tested, CI runs here.
**Community**: works, but is not the default development environment.

---

## Dependencies

| Dependency | Minimum Version | Usage |
|-------------|---------------|-----|
| Python | 3.8+ | Parser, CLI, chain modules |
| PyYAML | any | Frontmatter parsing |
| yamllint | any | YAML validation |
| jq | any | Knowledge base queries |
| git | 2.x | Version control, hooks |
| PyNaCl | any | Cryptographic signatures (chain) |

With Nix, all versions are pinned in `flake.lock`.
