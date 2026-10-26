# Componentes de terceiros

A licença MIT cobre somente o código próprio deste aplicativo. Cada componente
abaixo mantém seus avisos de autoria e condições de licença.

| Componente | Origem | Versão fixada | Licença |
|---|---|---|---|
| Win11 icon theme | [yeyushengfan258/Win11-icon-theme](https://github.com/yeyushengfan258/Win11-icon-theme) | `a5b460a407da143b32f19a503d7fcebb3edf2371` | GPL-3.0 |
| Win11OS Plasma Theme | [yeyushengfan258/Win11OS-kde](https://github.com/yeyushengfan258/Win11OS-kde) | `9f021c3e71da7baf59a0614ab858d53b1e455fd5` | GPL-3.0 |
| Fluent icon theme | [vinceliuice/Fluent-icon-theme](https://github.com/vinceliuice/Fluent-icon-theme) | `c8a244f571ef8fb47812bdc9dbce76546cedce69` | GPL-3.0 |
| DoorOS-Dolphin | [Rk7gamerYT/DoorOS-Dolphin](https://github.com/Rk7gamerYT/DoorOS-Dolphin) | `a5b4f9186ed146f1e7804fada86cde8277a0df97` | Alterações GPL-2.0-or-later; upstream por arquivo |
| PySide6 Essentials / Shiboken6 | [Qt for Python](https://www.qt.io/qt-for-python) | 6.12.0 | LGPL-3.0 / GPL e avisos de componentes incluídos nos wheels |
| Breeze, quando selecionado | KDE, já instalado no sistema | versão do sistema | Avisos do tema Breeze (LGPL) |

Os arquivos-fonte de temas, ícones e DoorOS-Dolphin são redistribuídos nos arquivos
`vendor/*.tar.gz`, sem remover seus COPYING, LICENSES, AUTHORS ou demais avisos.
O código-fonte exato do DoorOS-Dolphin usado para compilar o binário está incluso.
O binário é criado com a receita `dooros.py`; as dependências nativas vêm do Ubuntu.
O repo original do DoorOS-Dolphin pode exigir acesso do proprietário; os fontes
autorizados também estão disponíveis neste pacote público.

Os wheels PySide6/Shiboken6 inclusos na Release mantêm diretórios `.dist-info`,
licenças, metadados, bibliotecas compartilhadas e avisos de terceiros originais.
A interface importa essas bibliotecas dinamicamente; o código próprio da interface
permanece disponível neste repositório e as bibliotecas podem ser substituídas.
Fontes correspondentes do Qt for Python: [releases oficiais](https://download.qt.io/official_releases/QtForPython/pyside6/).

Checksums de temas e ícones: `community_assets.py` e `profile.py`.
Checksum dos fontes DoorOS: `dooros.py`.
Checksums dos wheels: `vendor/wheels/SHA256SUMS.json`.
Checksum do pacote completo: arquivo `.sha256` junto da Release.
