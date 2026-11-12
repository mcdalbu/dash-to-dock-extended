> Versão estável [34](RELEASE_NOTES.md), com visual dos menus do Shell. A sombra externa é opcional no visual dos menus do Shell. Blur e sombra dos ícones são fornecidos pelo GNOME Extended.

# Dash to Dock Extended

Fork independente baseado no [Dash to Dock](https://github.com/micheleg/dash-to-dock)
v110. O dock usa o mesmo contorno, os mesmos cantos e a mesma sombra externa dos
menus de notificações/calendário e Quick Settings do GNOME Shell.

- **Nome:** Dash to Dock Extended
- **UUID:** `dash-to-dock-extended@local`
- **Schema:** `org.gnome.shell.extensions.dash-to-dock-extended`
- **Versão deste fork:** 34
- **Repositório:** [mcdalbu/dash-to-dock-extended](https://github.com/mcdalbu/dash-to-dock-extended)

Esta versão adota o nome Dash to Dock Extended e um novo UUID e schema.
O caminho dconf foi preservado: os valores já salvos continuam disponíveis.
Mantenha apenas uma extensão de dock ativada por vez.
A extensão **Gnome Extended** pode continuar ativa para os menus.

## Visual dos menus do Shell

Em **Preferências → Temas**, a opção de bordas e cantos dos menus do Shell
vem ativada. Lê diretamente o estilo do Quick Settings do tema ativo (com o menu
do relógio como alternativa), incluindo:

- cor e espessura de cada lado do contorno;
- raio de cada canto;
- cor, opacidade, deslocamento, desfoque e expansão da sombra externa.

A cor do fundo tem um controle independente, descrito abaixo.

Acompanha mudanças entre tema claro e escuro e estilos aplicados ao menu por
**Gnome Extended**. Não aplica transparência aos ícones nem os desfoca.
A versão 20 restaura as margens originais do Dash to Dock, também com o visual
dos menus ativado. A margem fixa de 12 pixels usada para a sombra foi removida.
Sombras que ultrapassam a borda do monitor são recortadas pela tela.
Na versão 17, a sombra externa acompanha o dock durante toda a animação de
entrada e saída, em vez de aparecer somente ao atingir a posição final.
O recorte de pintura acompanha a borda do monitor, preservando a sombra fora
da superfície sem ampliar a área de entrada do dock. No estado totalmente
oculto, o recorte elimina também a sombra, inclusive em temas com sombras grandes.
O modo estendido mantém seu posicionamento junto à borda da tela.

Os controles manuais de contorno e raio ficam desabilitados enquanto o estilo
dos menus é seguido. Desligue essa opção para voltar a ajustá-los separadamente.
Os valores manuais permanecem salvos.

A opção **Manter o raio padrão dos cantos do Dash to Dock** permite conservar
os cantos do dock e usar somente o contorno e a sombra dos menus. O raio continua
acompanhando os modos compacto e estendido, e o recorte do blur usa o mesmo raio
do fundo. Essa opção vem desativada, preservando o visual dos menus por padrão.

O controle **Intensidade da sombra externa (%)** vai de **0% a 200%** e afeta
apenas a opacidade da sombra externa. O padrão **100%** usa exatamente a sombra
do Quick Settings, incluindo a diferença entre os temas claro e escuro. **0%**
remove a sombra; **200%** duplica sua opacidade, limitada a 100% de opacidade
real. O controle **Tamanho da sombra externa (%)**, novo na versão 20, ajusta
os deslocamentos, o desfoque e a expansão juntos, de **0% a 200%**. **100%**
preserva as dimensões do tema, valores menores reduzem a sombra e **200%**
duplica seu tamanho. **0%** remove a sombra. O tamanho é independente da cor
e da intensidade. Os dois controles ficam disponíveis com o estilo dos menus ativado.

## Tema do Shell e paletas do Ptyxis

Em **Preferências → Temas**, a lista **Paleta de cores** oferece **Tema do Shell**
e as 244 paletas incorporadas do Ptyxis 50.1, com busca por nome. As paletas com
variantes clara e escura acompanham o sistema. Não é necessário instalar o Ptyxis.

A opção **Usar as cores do tema selecionado** aplica a paleta ao fundo, ao
separador e ao hover. Com **Tema do Shell**, essas cores seguem os menus de
contexto dos ícones do dash. A opção vem ativada por padrão e funciona
independentemente dos controles de bordas, cantos e sombra, reunidos nessa aba.

A opacidade continua sendo a do dock: a cor dos menus não copia sua transparência.
Enquanto esse toggle está ativo, o controle de cor personalizada fica desabilitado.
Ao desativá-lo, a cor personalizada salva ou a cor padrão do dock volta a ser usada,
sem apagar os ajustes anteriores. Os ícones mantêm suas cores.

## Altura do dock

Em **Preferências → Posição e tamanho**, o controle **Altura do dock (px)**
move o dock verticalmente, de **−12 a +12 pixels lógicos**. Valores positivos
sobem e valores negativos descem; o padrão **0** restaura a posição original
do Dash to Dock, sem a margem adicional das versões anteriores. O deslocamento
pode ultrapassar as bordas do monitor. O tamanho dos ícones e a espessura
do fundo permanecem iguais. O controle funciona também nos docks laterais.

A versão 21 limita o controle e o schema ao intervalo de −12 a +12 px.
A alteração é aplicada ao vivo ao dock, ao blur e à geometria de ocultação
e reserva de espaço; voltar a 0 restaura a posição. Valores salvos em versões
anteriores fora desse intervalo usam o padrão 0.

## Estabilidade e organização das preferências

Abrir e fechar o Quick Settings não reaplica o tema do dock quando as cores,
o contorno, os cantos e a sombra do menu continuam iguais. Eventos de estilo são
agrupados e comparados depois de o estilo final estar disponível. A opacidade do
menu é independente da opacidade do dock. Isso evita reiniciar a transição de
transparência ao abrir o menu, inclusive com Gnome Extended ativo.

As páginas de preferências usam margens e espaçamento consistentes, rótulos à
esquerda, controles alinhados e colunas compartilhadas por página. Foram corrigidos
os controles de tamanho do dock e de prévia que ocupavam a célula de seus rótulos.
As opções novas de altura e sombra seguem o mesmo layout das outras escalas.

## Blur e transparência

O blur dinâmico herdado do Dash to Dock Extended vem **ativado**, com intensidade
**30**, opacidade fixa do fundo em **55%** e brilho de **85%**. Usa uma camada
separada com `BlurEffect` em modo `BACKGROUND`, preservando os ícones nítidos.
A transparência dinâmica e os demais ajustes herdados continuam disponíveis.

Na versão 19, o blur e a proteção de redesenho completo são ocultados quando
o fundo opaco cobre toda a camada, após a transição de cor e nos frames seguintes.
Ícones em hover não reativam um blur já encoberto. Se o blur ainda aparece nos
cantos, ele permanece ativo; voltar à transparência restaura a captura.
O filtro de janelas acompanha mudanças da geometria e da intensidade do blur.
A proteção contra artefatos continua ativa enquanto o blur está visível.
As propriedades do tema são lidas nas mudanças de estilo e reutilizadas nos frames.
Retirar a segunda camada em cantos opacos pode mudar a suavização do contorno.
As otimizações não adicionam timers periódicos; o ganho de GPU depende do cenário
e não foi quantificado.

Quando segue o visual dos menus, o recorte arredondado do blur acompanha o raio
real do fundo, incluindo a escala. O recorte do blur requer GNOME Rounded Blur
ou suporte nativo a `corner-radius`. Sem esse recurso, o blur funciona com cantos
retos, enquanto a superfície continua arredondada. A biblioteca é opcional e não
é incluída no ZIP; consulte o
[guia oficial](https://github.com/aunetx/blur-my-shell/blob/master/scripts/GUIDE.md).

## Instalar

```bash
gnome-extensions install --force dash-to-dock-extended@local_v32.zip
```

Encerre a sessão e entre novamente para carregar a atualização. Depois:

```bash
# Se usar o original, desative também dash-to-dock@micxgx.gmail.com.
gnome-extensions enable dash-to-dock-extended@local
gnome-extensions prefs dash-to-dock-extended@local
```

Ignore a desativação de uma extensão que não estiver instalada. Para atualizar
este fork, instale o ZIP com `gnome-extensions install --force`.

## Compilar e validar

Dependências: `make`, `glib-compile-schemas`, `sassc`, `gettext`, `python3` e `zip`.
Para lint, use ESLint 8; os testes de regressão usam Node.js.

```bash
make
make check
node tests/dock-effects.cjs
node tests/dock-redraw-recovery.cjs
make zip-file VERSION=32
```

O teste de integração inicia um GNOME Shell 50 headless em D-Bus e diretórios de
dados/configurações privados, sem instalar o fork na sessão de trabalho:

```bash
/usr/bin/python3 tests/shell-menu-headless.py
```

Requer GNOME Shell 50, PyGObject, GdkPixbuf e GJS/GTK/Adwaita. Compara o contorno, a sombra
e os cantos realmente renderizados nos temas claro/escuro, quatro posições,
escala 2×, alteração de estilos com o menu fechado, transparência dinâmica,
ocultação, ativação/desativação e repouso. Também testa os controles GTK novos.
Resultados e capturas em `validation/shell-menu-*`.
Os testes incluem raio nativo nos modos normal, compacto e estendido,
margens originais nas quatro posições e nos modos normal, compacto e estendido,
movimentação vertical sem redimensionar os ícones, tamanho da sombra entre 0% e
200% (incluindo escala 2×) e intensidade da sombra
em 0%, 50%, 100%, 150% e 200% nos dois temas, além dos vínculos dos controles GTK.
Também medem a opacidade durante aberturas
repetidas do Quick Settings e verificam o alinhamento das preferências em janelas reais.
A versão 17 acrescenta comparação de pixels da sombra fora do dock a meio caminho
da animação nos quatro lados, ausência de sombra ao ocultar e acompanhamento
do recorte em cada frame de uma animação real de autohide.
Para testar em conjunto com Gnome Extended:

```bash
SOFT_TEST_WITH_SHELL_SOFT=1 /usr/bin/python3 tests/shell-menu-headless.py
```

Compatibilidade declarada **45–51**, herdada da base. A validação de integração
usa **GNOME Shell 50.6**; as outras versões e a suspensão física precisam de
verificação nas respectivas sessões. O teste não comprova esses cenários.

## Créditos

Mantém o histórico, as funcionalidades e a licença GPL-2.0-or-later do
Dash to Dock e do Dash to Dock Extended. Veja `COPYING`, `AUTHORS.md` e o
[README da versão 15](README-Dash-to-Dock-Extended.md).
Os módulos de blur e recuperação são herdados do Dash to Dock Extended.
O novo módulo `shellMenuStyle.js` adapta as propriedades reais do tema dos menus.

## GNOME Shell 51

Esta versão inclui GNOME Shell 51 nos metadados. O teste integrado de menus, aparência, autohide, recuperação e preferências passou em uma sessão isolada do GNOME Shell 51.1, com Gnome Extended e Dash to Dock Extended ativos em conjunto.

## Renomeação

A extensão usa o novo nome e UUID. O caminho de armazenamento dconf foi preservado para manter as preferências existentes. Ao instalar o novo UUID, desative a extensão de nome antigo antes de ativar a nova.

A borda acompanha a paleta selecionada, preservando sua espessura e os cantos.
Com **Tema do Shell**, a borda usa novamente a cor do tema nativo.
