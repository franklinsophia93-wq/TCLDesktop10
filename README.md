# TCL Desktop 10 — TCL 40 NXTPAPER 4G

Projeto de APK Android com interface inicial no estilo Windows e execução de programas Windows compatíveis **via Wine e Box64**, usando código-fonte do Winlator como base técnica.

**Este repositório não contém o Windows 10 original.** Jogos pesados, anticheat e certos programas podem não funcionar. O alvo inicial é Android ARM64, TCL 40 NXTPAPER 4G (Helio G88 / Mali-G52).

## Compilar

Abra a aba **Actions** do repositório, selecione **TCL Desktop 10 - APK para testes** e verifique a execução mais recente. Também pode usar **Run workflow** manualmente.

Se a execução terminar com sucesso, baixe em **Artifacts** o arquivo **TCLDesktop10-APK-teste**. O ZIP conterá `TCLDesktop10-debug.apk`, assinado com uma chave debug, para instalação e testes no celular.

Se a execução falhar, **não existe APK válido dessa execução**; veja o log da etapa com erro.

## Arquitetura

1. `integration/winlator-overlay/build.sh`: baixa o Winlator de um commit fixo, aplica o overlay TCL e compila com Gradle.
2. `integration/winlator-overlay/prepare.py`: exige presença dos arquivos reais do Wine/Box64, Android .so e RootFS, aplica identidade própria e adiciona licenças.
3. `integration/winlator-overlay/TclDesktopActivity.java`: abre o desktop Wine de um contêiner existente ou mostra a etapa inicial de configuração.
4. `.github/workflows/build-apk.yml`: compila no GitHub Actions, publicando o APK **apenas após êxito**.

Na primeira execução, use **Configurar ambiente Windows** e crie um contêiner. Na abertura seguinte, o iniciador tenta entrar no primeiro contêiner diretamente.

## Créditos

O runtime é derivado da implementação pública de [Winlator](https://github.com/brunodev85/winlator-app). Cada componente mantém as respectivas licenças e avisos, inclusive LGPL do projeto-base. O código do iniciador TCL é personalizado. Não é produto oficial TCL nem Microsoft.

## Estado de verificação

Compilação no GitHub Actions e testes em aparelho devem ser confirmados pelos resultados da execução. Os testes estruturais isolados **não são provas de execução real** de arquivos .exe.
