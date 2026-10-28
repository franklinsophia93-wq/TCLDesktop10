# NegócioFácil — assinatura e lançamento seguro

## Situação em 27/10/2026 — revisão 0.5 compilada para homologação
- As versões APK 0.1 a 0.5 de CI foram criadas com certificado **temporário de depuração**. A revisão 0.5 corrigiu o compartilhamento Android e compilou com sucesso, mas ainda não tem chave de distribuição definitiva.
- O núcleo de validação Mercado Pago fica em `negociofacil/pagamentos`. Seus testes passaram, porém **não existe integração com servidor publicado, OAuth por profissional ou atualização de vendas no APK**.
- O build passou no CI, mas **não foi homologado em aparelho físico**.
- Os banners do Google são de **teste** e não geram receita.
- Os documentos PDF gerados são **recibos e orçamentos não fiscais**, não NFS-e/NF-e autorizadas.
- **Não desinstale sem exportar o backup JSON**: os dados atuais são locais à WebView.
- Os planos Pro e Empresarial são acessos locais de *demonstração ADM*, ainda sem compra validada.

## Como fixar uma chave de assinatura para atualizações

A atualização direta do Android requer mesmo `applicationId`, código de versão suficiente
e **mesmo certificado de assinatura**, salvo rotação de chaves suportada.

1. Crie e mantenha uma única chave privada (somente no dispositivo do proprietário, ou num cofre). Exemplo, em computador com JDK:

   ```bash
   keytool -genkeypair -v -keystore negociofacil-release.jks -storetype PKCS12 -alias negociofacil -keyalg RSA -keysize 3072 -validity 9125
   ```

2. Gere o conteúdo Base64 sem quebras de linha no computador local:

   ```bash
   base64 -w0 negociofacil-release.jks
   ```

   Não publique a chave, nem sua versão em Base64, em repositórios, chats públicos ou releases.

3. No repositório GitHub, configure **Settings → Secrets and variables → Actions → New repository secret**, usando:
   - `NF_KEYSTORE_B64`: conteúdo Base64 da chave **PRIVADA**;
   - `NF_KEYSTORE_PASSWORD`: senha da chave;
   - `NF_KEY_ALIAS`: `negociofacil`, ou o alias escolhido;
   - `NF_KEY_PASSWORD`: senha do alias.

4. Execute o workflow **NegocioFacil - APK com assinatura permanente** na branch `negociofacil-android`. Ele somente compila e publica o artifact se todos os segredos estiverem configurados e a assinatura for verificada.
5. Guarde o certificado SHA-256 impresso na etapa de validação e CONFIRA o mesmo SHA nas próximas versões.
6. Faça a última migração da instalação antiga, se assinada com a chave debug, via **backup JSON, desinstalação, instalação do primeiro APK com chave permanente e importação do backup**. Após isso, futuras versões assinadas com a mesma chave podem ser atualizadas por cima (número de versão incrementado).

**Importante:** perder a chave de assinatura privada pode impedir que novas versões substituam versões instaladas. Não confundir a senha ADM do aplicativo com a chave de assinatura Android.

## Antes de monetizar de verdade
- Criar conta AdMob, obter IDs **próprios** e implementar requisitos de privacidade e consentimento por região. **Remover IDs de demonstração.**
- Fazer testes de anúncios com unidades de teste até a liberação da produção; não clicar em anúncios reais.
- Integrar Google Play Billing e validar as compras no servidor; não usar apenas a seleção do ADM como direito a plano pago.
- Para NFS-e/NF-e: confirmar o enquadramento de cada emissor, credenciamento, credenciais/certificado quando cabível, homologação com sistema fiscal e recebimento do número/protocolo da autorização oficial.
- Incluir política de privacidade, canal de suporte, backup/restauração e segurança de dados pessoais antes da distribuição pública.

## Bloqueios antes da comercialização
- Confirmar conta Google Play Console, publicar versão de loja, aderir às regras aplicáveis de Google Play Billing para as assinaturas digitais Pro/Empresarial.
- AdMob: app publicado em loja compatível e marcado como **Pronto** após revisão antes de habilitar a unidade de anúncios real. Usar apenas unidades de demonstração durante os testes.
- Mercado Pago: criar integração OAuth, registrar cada recebedor, disponibilizar servidor HTTPS, armazenar tokens em cofre, validar `x-signature` e conciliar pagamentos pelo provedor.
- Fiscal: credenciamento e testes de homologação de NFS-e e/ou NF-e; comprovantes comerciais **não fiscais** não valem como notas.
- Garantir backup e migração de dados. A primeira instalação assinada com a chave permanente provavelmente requer desinstalar o APK de teste com backup prévio; versões seguintes devem manter certificado e versão crescente.

## Ajuste confirmado do build release (28/10/2026)

O workflow `.github/workflows/negociofacil-signed-production.yml` foi corrigido para:
- compilar `app-release-unsigned.apk` sem assinatura;
- alinhar o APK com `zipalign`;
- assinar com `apksigner`, usando SOMENTE a chave guardada em GitHub Actions Secrets;
- verificar a assinatura, o pacote `br.com.negociofacil.app` e `versionCode=5`;
- guardar o SHA-256 do certificado em `certificado-sha256.txt` junto ao APK;
- comparar o certificado com a variável opcional `NF_SIGNING_CERT_SHA256` do repositório, que deve ser fixada após a primeira assinatura. Compilações seguintes com certificado diferente serão bloqueadas.

**A chave JKS/PKCS12 ainda NÃO foi criada nem cadastrada neste repositório.** O workflow está preparado, não há APK permanente produzido ainda.

Para o primeiro teste, o proprietário cria uma chave e guarda uma cópia de segurança privada, configura quatro Secrets: `NF_KEYSTORE_B64`, `NF_KEYSTORE_PASSWORD`, `NF_KEY_ALIAS`, `NF_KEY_PASSWORD`. Após rodar o workflow pela primeira vez, deve abrir o arquivo `certificado-sha256.txt` do artifact e configurar `NF_SIGNING_CERT_SHA256` em GitHub Settings → Secrets and variables → Actions → Variables. Isso previne que um futuro APK seja publicado por acidente com outra chave.

**Não colocar a chave, senhas nem conteúdo Base64 em conversa, issue ou arquivo público do GitHub.** Senhas e keyfiles precisam ficar fora do repositório e ter backup separado. Se a chave for perdida e não houver mecanismo de migração compatível, atualizações sobre a instalação antiga podem deixar de funcionar.

### Migração da versão debug atual

Como as versões anteriores foram assinadas com chaves debug efêmeras do CI, o primeiro APK assinado com a chave definitiva provavelmente NÃO poderá ser atualizado por cima da instalação atual. A sequência é: **exportar backup JSON e verificar o arquivo → desinstalar somente se a atualização for rejeitada → instalar o primeiro release com assinatura permanente → restaurar dados → conferir cadastros**. A partir daí, manter a assinatura e incrementar `versionCode` em todas as versões. Não publicar novamente APKs debug para quem migrou para a versão definitiva.
