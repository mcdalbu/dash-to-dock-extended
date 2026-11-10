# Dash to Dock Extended 31 — 10 de novembro de 2026

- O Intellihide mantém um observador por janela, libera as conexões ao desativar e agrupa verificações de sobreposição durante uma sequência de eventos.
- A transparência dinâmica verifica a proximidade uma vez por quadro e reaplica o estilo quando o estado muda.
- Alterações consecutivas na opacidade e na sombra usam a mesma atualização de tema. O separador fica no lugar quando a lista de ícones permanece igual.
- O GNOME Extended continua aplicando o blur e as sombras de ícones do dock quando essas opções estão ativadas.

Instale `dash-to-dock-extended@local_v31.zip` com `gnome-extensions install --force`. Saia da sessão e entre novamente para carregar o código.

Validação em sessões isoladas do GNOME Shell 51.1, com o dock sozinho e integrado ao GNOME Extended.

# Dash to Dock Extended 30 — 7 de novembro de 2026

- Restaurado o destaque padrão do tema para o aplicativo em foco.
- A barra de opacidade volta a controlar somente o fundo do dock; o destaque
  dos ícones permanece independente. O hover com as cores do Shell é mantido.

# Dash to Dock Extended 29 — 4 de novembro de 2026

- O destaque persistente do aplicativo ativo usa a cor do menu do tema quando
  as cores do GNOME Shell estão habilitadas.
- A transparência desse destaque acompanha a barra de opacidade, inclusive
  com as cores do Shell desabilitadas. O alfa original é multiplicado pela
  opacidade configurada; em 0%, o fundo persistente fica transparente.
- O hover mantém a intensidade original do tema, inclusive sobre o aplicativo
  ativo e o botão Mostrar aplicativos.
- Testes no GNOME Shell 51.1: temas claro e escuro, opacidades 0%, 35% e 100%,
  preferências e ativação/desativação do perfil. `make check`: PASS.

# Dash to Dock Extended 28 — 4 de novembro de 2026

Versão estável publicada na branch principal fork/soft-icons.

- Mantidos bordas, cantos, cores, separadores e hover dos menus do Shell,
  opção de conservar o raio original do dock e ajuste de posição vertical.
- Sombra externa opcional no campo Visual dos menus do Shell, com ativação,
  intensidade e tamanho. Os percentuais antigos são preservados.
- Removidos blur próprio, sombra de ícones e contorno manual do
  renderer, dos controles, do schema e do ZIP.
- Blur e sombras opcionais podem ser aplicados externamente pelo GNOME
  Extended. Um botão nas preferências abre suas configurações centrais.
- Mantidos UUID, caminho das preferências e funcionalidades originais do dock.
  Valores antigos das chaves removidas no dconf não são lidos nem apagados.

Sem o GNOME Extended, o dock continua funcionando normalmente sem esses efeitos.
