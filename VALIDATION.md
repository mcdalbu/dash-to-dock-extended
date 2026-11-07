# Validação da versão 30 — 7 de novembro de 2026

`make check`: PASS. Sessão isolada do GNOME Shell com
`SOFT_TEST_LABEL=default-highlight /usr/bin/python3 tests/shell-menu-headless.py`: PASS.
Destaque do aplicativo em foco igual ao padrão do tema em 0%, 35% e 100%
de opacidade do dock, nos temas claro e escuro. Hover, preferências e
ativação/desativação das cores do Shell preservados.
Resultado: `validation/shell-menu-default-highlight-results.json`.

# Validação da versão 29

Destaques da versão 29 (4 de novembro de 2026): `make check` e
`SOFT_TEST_LABEL=highlight-opacity python3 tests/shell-menu-headless.py`: PASS.
Na sessão isolada do GNOME Shell, as cores computadas do hover correspondem
ao menu nos temas claro/escuro, incluindo ícones ativos e Mostrar aplicativos.
O fundo persistente do aplicativo em foco usa a mesma cor com seu alfa
multiplicado pela opacidade configurada (0%, 35% e 100% verificados).
Com as cores do Shell desabilitadas, a cor original do destaque continua
acompanhando a opacidade. Preferências e ativação/desativação do perfil: PASS.
Resultado: `validation/shell-menu-highlight-opacity-results.json`.

Validação de base da versão 28 (mantida como histórico):
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
