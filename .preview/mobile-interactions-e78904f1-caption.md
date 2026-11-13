# Mobile interactions private preview

Status: approved exact product active on a distinct Tailnet-only preview. Captain selection is still pending.

Surface: standalone Kanban WebUI with a synthetic isolated board. This is not Electron Desktop and not the chat sidebar.

- Open Live: https://0.taila30dc.ts.net:8453/kanban?rev=e78904f1
- Compare: https://0.taila30dc.ts.net:8450/kanban?rev=dcb6804e9
- Evidence: `mobile-interactions-e78904f1-evidence.json`

Exact product: `e78904f1ffb2af707d896c0de9fcb298c4d747fb`

Evidence: `ba17e764467557a4e1dcbaaf48cd04de9e121f9c`

Verified: startup 4/4, hold and gesture matrices at 320/360/390/430/1280, exact served JS/CSS hashes, synthetic DB isolation, single origin listener, no horizontal overflow, 67.9375px controls, zero-byte stderr, and baseline :8450 unchanged.

Compact Snooze is not represented by this exact standalone product. There is no Kanban Snooze literal or surface at `e78904f1`, so this artifact makes no Snooze claim.

Rollback:

```text
tailscale serve --https=8453 off
systemctl --user disable --now hermes-mobile-interactions-e78904f1-proxy.service hermes-mobile-interactions-e78904f1.service
```

No push, public PR mutation, or :8450 replacement was performed.
