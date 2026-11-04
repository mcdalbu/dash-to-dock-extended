# Validação da versão 28

GNOME Shell 51.1, sessões D-Bus/Wayland isoladas, 4 de novembro de 2026.

- make check: PASS, incluindo ESLint 9, layout do GtkBuilder e testes de
  bordas/cantos 1x/2x, autohide e recuperação de redraw após suspensão.
- Dock sozinho, sem GNOME Extended: PASS. Perfil do menu ativa/desativa,
  hover é preservado, renderer não contém blur e chaves de blur/sombra de ícones/contorno manual são ausentes.
- Sombra externa: switch, intensidade/tamanho, dependência do perfil Shell,
  renderização ativada/desativada e preservação de bordas: PASS.
- Integração com GNOME Extended 11: PASS. Efeito externo, três frequências,
  sombra independente da grade, quatro posições, toggle e desmontagem.
- Preferências: controles de blur/sombra de ícones/contorno manual ausentes; visual do Shell
  e botão para abrir o GNOME Extended presentes: PASS.
- ZIP: sem módulos de backend/guarda de blur; schemas estritos e hash: PASS.

Testes gráficos: python3 tests/shell-menu-headless.py (sozinho) e
SOFT_TEST_WITH_SHELL_SOFT=1 python3 tests/shell-menu-headless.py (integração;
requer checkout do GNOME Extended ao lado). Não houve novo benchmark ou
certificação de todas as GPUs/versões de GNOME.
