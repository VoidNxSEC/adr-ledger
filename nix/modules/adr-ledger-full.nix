{
  self,
  securellmMcp ? null,
  phantom ? null,
  cerebro ? null,
  spectre ? null,
  owasaka ? null,
  mlOpsApi ? null,
}:
{
  imports = [
    (import ./adr-ledger-sync.nix { inherit self; })
    (import ./adr-ledger-iam.nix {
      inherit self securellmMcp phantom cerebro spectre owasaka mlOpsApi;
    })
  ];
}
