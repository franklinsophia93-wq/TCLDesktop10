# NegócioFácil — backend OAuth Mercado Pago: situação de implementação

**Status:** preparado e testado em código independente, NÃO implantado e NÃO integrado ao APK. Nenhum Pix/cartão real é processado.

## Bloqueio de implantação

A conta Supabase possui apenas dois projetos **ORION**; ambos pertencem a outro aplicativo. Para segregar usuários, vendedores, tokens e dados financeiros, não use esses projetos para NegócioFácil. É necessário que o proprietário indique uma organização e autorize a criação de um **projeto dedicado NegócioFácil**, após verificar eventuais custos.

## Entregável preparado nesta etapa

Um pacote ZIP de fontes de backend, com:
- `schema.sql`: cadastro de empresas + RLS por proprietário, estados OAuth de uso único, conexões cifradas inacessíveis a usuários.
- `index.ts`: Edge Function com `/health`, `/oauth/start`, `/oauth/callback`, `/oauth/connection` e `/oauth/disconnect`.
- `auth_logic.mjs`: estado aleatório, hash SHA-256, PKCE S256 opcional, AES-GCM para cifrar tokens, verificação HTTPS.
- `auth_logic.test.mjs`: cinco testes automatizados passaram localmente.
- `README.md`: requisitos de implantação e restrições.

A fonte está pronta para ser implantada em um projeto Supabase próprio, **mas não é uma URL OAuth real**. Não informe endereços fictícios no painel Mercado Pago.

## Segredos obrigatórios (configure no backend, jamais no APK ou repo)

- `MP_CLIENT_ID`: ID público do aplicativo Developers;
- `MP_CLIENT_SECRET`: segredo privado;
- `MP_REDIRECT_URI`: endereço HTTPS exato da função *após* implantação;
- `MP_TOKEN_ENCRYPTION_KEY`: chave aleatória privada de 32 bytes;
- `MP_USE_PKCE`: ativar `true` somente após marcar "Sim" em PKCE no painel Mercado Pago.

`SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY` são fornecidos ao backend pela implantação, nunca à WebView.

## Próximos passos após escolher o projeto separado

1. Criar projeto, configurar Supabase Auth real e verificar custo.
2. Aplicar schema com revisão de políticas RLS, rodar advisors.
3. Implantar Edge Function; configurar segredos privadamente e conferir endpoint HTTPS.
4. Preencher **exatamente** essa URL em Mercado Pago Developers → OAuth URL.
5. Testar OAuth com uma conta autorizada usando PKCE, estado único, validade e revogação.
6. Implementar e testar checkout por vendedor e webhook idempotente. O núcleo existente `payment_core.mjs` testa simulações, **não** realiza pagamentos reais.
7. Integrar tela "Meus recebimentos" ao app, corrigir assinatura permanente do APK e homologar ponta-a-ponta.

O modelo comercial continua sendo **comissão zero** para NegócioFácil; só anúncios e assinaturas da plataforma produzem receita para o proprietário.

Documentação oficial: https://www.mercadopago.com.br/developers/pt/docs/security/oauth/creation
