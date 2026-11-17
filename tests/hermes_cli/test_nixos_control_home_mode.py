"""Keep NixOS gateway-home provisioning consistent with CLI discovery.

This is a source-level guard; the Nix flake check evaluates the real module.
"""

import re
from pathlib import Path


def test_nixos_control_home_mode_is_safe_in_both_provisioners():
    """The shared-group control dir must never be created group-writable."""
    module = (
        Path(__file__).resolve().parents[2] / "nix" / "nixosModules.nix"
    ).read_text(encoding="utf-8")

    # systemd-tmpfiles runs on boot and may reset an activation-script chmod.
    tmpfiles_modes = re.findall(
        r'^\s*"d\s+\$\{hermesHome\}\s+([0-7]{4})\s+\$\{cfg\.user\}\s+\$\{cfg\.group\}\s+-\s+-"',
        module,
        flags=re.MULTILINE,
    )

    # nixos-rebuild runs the activation script independently of tmpfiles.
    chmods = re.findall(
        r"^\s*chmod\s+([0-7]{4})\s+([^\n#]+)$",
        module,
        flags=re.MULTILINE,
    )
    activation_modes = [
        mode for mode, targets in chmods if "${hermesHome}" in targets.split()
    ]

    assert tmpfiles_modes == ["2750"], "tmpfiles must provision hermesHome as 2750"
    assert activation_modes == ["2750"], "activation must chmod only hermesHome to 2750"
