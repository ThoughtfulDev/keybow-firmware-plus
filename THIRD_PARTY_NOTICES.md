# Third-party notices

Keybow Firmware Plus includes or redistributes the components below. The repository's [license overview](LICENSE) identifies which parts are covered by each license. This notice is copied into the desktop app packages and SD card ZIP.

## Firmware and SD card image

- **Raspberry Pi boot firmware**: supplied under the terms in [`sdcard/LICENCE.broadcom`](sdcard/LICENCE.broadcom); its use is limited by that notice.
- **Linux kernel**: `sdcard/kernel.img` is a Linux ARM kernel image. Its embedded banner reports Linux 4.14.78+, built on 20 February 2019 by `phil@philbuntu` using a Linaro GCC 4.8.3 toolchain. Linux kernel code is GPL-2.0. The image does not identify the exact source commit or complete build configuration. The previously cited generic Raspberry Pi Linux repository is not enough to establish that it is the corresponding source for this exact binary. This repository therefore does not claim that the exact corresponding kernel source has been located; resolve that source offer before redistributing the SD card image as a compliant GPL binary distribution.
- **Initrd**: `sdcard/initrd` is an XZ-compressed cpio archive containing a Raspbian/Debian userspace. The archive retains the installed package copyright notices at `/usr/share/doc/*/copyright`. The initrd is a historical prebuilt artifact; package versions and a complete source manifest were not available in this checkout. Consult each retained package notice for its terms.
- **bcm2835 1.68**: GPL-3.0-only; see [`bcm2835-1.68/COPYING`](bcm2835-1.68/COPYING).
- **libusbgx**: library under LGPL-2.1-or-later and example code under GPL-2.0-or-later; see [`libusbgx/COPYING.LGPL`](libusbgx/COPYING.LGPL), [`libusbgx/COPYING`](libusbgx/COPYING), and upstream [libusbgx](https://github.com/linux-usb-gadgets/libusbgx).
- **Lua 5.4.0**: MIT; copyright and license are reproduced in [`lua-5.4.0/doc/readme.html`](lua-5.4.0/doc/readme.html).

The firmware build statically links libraries. In particular, bcm2835 1.68 is GPL-3.0-only, so the combined `keybow` executable has copyleft obligations. The relevant library sources and their license texts are included in this repository. Review the license terms before distributing modified or binary versions.

## Desktop application

The local desktop build bundles Python and Python packages. The pinned direct dependencies are listed in [`editor/requirements-desktop.txt`](editor/requirements-desktop.txt).

- **Python 3.12 runtime**: Python Software Foundation License Version 2. The package includes the target build's full Python license text as `PythonLicense.txt` (in the app's Resources folder on macOS and the documentation folder on Ubuntu). No Python source is modified by this project.
- **pySerial 3.5**: BSD-3-Clause, Copyright (c) 2001–2020 Chris Liechti. Its license requires the notice, conditions, and disclaimer to accompany binary distributions; the full text is included below.
- **pywebview 6.2.1**: BSD-3-Clause, Copyright (c) 2014–2017 Roman Sirokov. The full text is included below.
- **PyInstaller 6.22.3**: GPL-2.0-or-later with a bootloader exception; the exception permits distributing generated executables under another license, subject to the licenses of included software. Some PyInstaller runtime-hook files are Apache-2.0. See [PyInstaller's license documentation](https://pyinstaller.org/en/stable/license.html).
- **Platform webview libraries**: macOS WebKit, Windows WebView2, and Ubuntu GTK/WebKit are system components supplied by the target platform, not copied into the package by this project. Their respective platform licenses apply.
- Any additional transitive Python package included by PyInstaller retains its own license. The package lock is currently represented by pinned direct requirements rather than a complete transitive lock; inspect the built environment's installed package metadata when making a release.

### BSD-3-Clause text: pySerial 3.5

Copyright (c) 2001-2020 Chris Liechti <cliechti@gmx.net>
All Rights Reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

### BSD-3-Clause text: pywebview 6.2.1

Copyright (c) 2014-2017, Roman Sirokov
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
