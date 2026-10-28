# NegocioFacil — Backend Mercado Pago criado no Supabase
Status em 28/10/2026: PROJETO ativo e FUNÇÃO publicada; OAuth AINDA BLOQUEADO POR AUSÊNCIA DE SEGREDOS; PIX/CARTÃO REAL DESATIVADOS.

Projeto separado dos projetos ORION:
- Projeto Supabase: NegocioFacil
- Regiao: sa-east-1 (Sao Paulo)
- Referência: tlqcpfmkneohjleiynqe
- Dashboard: https://supabase.com/dashboard/project/tlqcpfmkneohjleiynqe
- Função: nf-mercadopago, versão 1 publicada
- URL exata para adicionar em Mercado Pago Developers -> OAuth -> URLs de redirecionamento:
  https://tlqcpfmkneohjleiynqe.supabase.co/functions/v1/nf-mercadopago/oauth/callback
- Rota de diagnóstico: https://tlqcpfmkneohjleiynqe.supabase.co/functions/v1/nf-mercadopago/health

## O que foi criado
- public.nf_businesses: empresa por proprietário, RLS
- public.nf_mp_oauth_states: estado OAuth de uso único, acesso só do servidor
- public.nf_mp_connections: conta conectada e tokens cifrados, acesso só do servidor
- Função OAuth: /oauth/start, /oauth/callback, /oauth/connection e /oauth/disconnect;
  /health informa status e nunca divulga segredos. /oauth/* retorna 503 enquanto faltarem segredos.

## Para habilitar autorização (NÃO pagamentos)
No Supabase > Edge Functions > Secrets, adicionar diretamente, sem copiar para chat, GitHub ou APK:
1. MP_CLIENT_ID (identificador numérico PÚBLICO da aplicação Mercado Pago)
2. MP_CLIENT_SECRET (privado; copiar exclusivamente na tela segura de Secrets)
3. MP_REDIRECT_URI = https://tlqcpfmkneohjleiynqe.supabase.co/functions/v1/nf-mercadopago/oauth/callback
4. MP_TOKEN_ENCRYPTION_KEY (32 bytes aleatórios em Base64 URL safe, privado)
5. MP_USE_PKCE = false enquanto no Mercado Pago estiver configurado "Não"; mudar para true quando ativar PKCE nos dois lados e revalidar o fluxo.

Segredos nunca podem ser compartilhados no chat. O campo de redirecionamento deve ter a MESMA URL no Mercado Pago e no servidor.

## Segurança / testes
- API OAuth bloqueada enquanto faltam credenciais.
- Função é de callback público (verify_jwt=false); rotas privadas requerem Supabase Auth e verificam proprietário do negócio na tabela com RLS.
- Banco: as três tabelas têm RLS. nf_mp_oauth_states e nf_mp_connections não têm políticas de acesso cliente de propósito; apenas service_role pode usá-las.
- O assistente verificou status ativo da função por ferramenta do Supabase e a proteção do banco por SQL. Uma tentativa de HTTP externo falhou devido à limitação de resolução DNS do ambiente de teste; não foi possível provar a resposta pelo navegador.
- Não existe integração deste backend no APK nem status de pagamentos no celular.
- Não há tela de login Supabase Auth, conexões reais, checkout, webhook, cobranças nem assinatura permanente de APK.
- O primeiro teste real OAuth deverá utilizar conta de teste e não criar pagamentos reais.

## Para completar o sistema
1. Cadastrar URL OAuth no Mercado Pago Developers; guardar segredos no Supabase.
2. Vincular login real Supabase Auth à interface do NegocioFacil; criar empresas por user.id; não confiar no ADM local como autenticacao.
3. Implementar checkout e webhook, reconciliação idempotente e reembolsos em backend após autenticação.
4. Testar com duas contas de vendedor (sandbox) para garantir que o dinheiro da venda se destina à conta respectiva e não gera comissão da plataforma.
5. Assinar APK com chave permanente protegida e integrar API ao Android; não apagar dados sem backup.

Nota: a cotação para criacao do projeto foi US$ 0/mês segundo o Supabase na data da criacao; limites e cobranças por uso dependem do plano/consumo.
