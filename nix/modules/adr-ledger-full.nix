{
  self,
  securellmMcp ? null,
}:
{
  imports = [
    (import ./adr-ledger-sync.nix { inherit self; })
    (import ./adr-ledger-iam.nix {
      inherit self securellmMcp;
    })
  ];
}
