# NegócioFácil — ativação de Pix e cartão, por vendedor, sem comissão

**Estado em 28/10/2026:** backend de pagamentos `nf-payments` implantado, bancos `nf_sales` e `nf_provider_payments` criados, API de login e recebimentos em homologação. **Cobranças reais NÃO liberadas até cumprir o checklist abaixo.** Não confundir API no ar com autorização do Mercado Pago ou dinheiro movimentado.

## Auditoria atual (28/10/2026)

- Servidor principal `nf-payments`: online. `nf-checkout` é legado e foi desativado.
- `NF_CHECKOUT_MODE=test`, `NF_CHECKOUT_ENABLED=false`.
- `MP_WEBHOOK_SECRET`: **ainda não configurado**; o health retorna `webhook_ready=false`.
- Banco Supabase: **0 empresas, 0 vendedores conectados, 0 vendas, 0 pagamentos conciliados** no momento da verificação.
- Teste GitHub: https://github.com/franklinsophia93-wq/TCLDesktop10/actions/runs/40663616725, aprovado.
- API bloqueia criação/consulta de venda sem login; webhook sem assinatura não marca pagamento.
- Função `nf_record_verified_payment`: apenas `service_role` pode executar; `anon` e `authenticated` não têm permissão. Tokens de vendedores não são expostos no APK.
- Os fluxos ainda precisam de **teste ponta a ponta** com contas Mercado Pago de homologação, notificações reais, estornos e autorização OAuth.
- **Não ativar** `NF_CHECKOUT_ENABLED=true` nem mudar `NF_CHECKOUT_MODE=live` antes desses testes.

### Configuração pendente no painel Mercado Pago

Em Mercado Pago Developers → aplicação NegócioFácil → **Webhooks**, selecione o evento de **Pagamentos**, configure a URL pública abaixo e copie a assinatura secreta gerada para o **Supabase → Edge Functions → Secrets**, na variável `MP_WEBHOOK_SECRET`.

```text
https://tlqcpfmkneohjleiynqe.supabase.co/functions/v1/nf-payments/webhook
```

**Atenção:** Webhooks NÃO são a mesma URL de redirecionamento OAuth. Esta última termina em `/nf-mercadopago/oauth/callback` e já foi salva. Não divulgue a assinatura secreta, Client Secret, chaves ou Access Tokens no chat.

## URLs
- Health do gateway: https://tlqcpfmkneohjleiynqe.supabase.co/functions/v1/nf-payments/health
- Webhook Pagamentos: https://tlqcpfmkneohjleiynqe.supabase.co/functions/v1/nf-payments/webhook
- OAuth callback (já configurado): https://tlqcpfmkneohjleiynqe.supabase.co/functions/v1/nf-mercadopago/oauth/callback
- Projeto: https://supabase.com/dashboard/project/tlqcpfmkneohjleiynqe

## Passo 1 — Proteção do webhook
No Mercado Pago Developers → NegócioFácil → Webhooks → Configurar notificações:
1. Escolher o **modo de testes** e a opção **Pagamentos**.
2. Colar a URL de Webhook acima, salvar e obter a **assinatura secreta do Webhook**.
3. No Supabase → NegocioFacil → Edge Functions → Secrets, inserir **MP_WEBHOOK_SECRET** com o valor da assinatura secreta (sem enviá-lo por chat ou repositório).
4. Os segredos antigos MP_CLIENT_ID, MP_CLIENT_SECRET, MP_REDIRECT_URI e MP_TOKEN_ENCRYPTION_KEY devem continuar protegidos; não gerar novas chaves de criptografia depois que contas estiverem conectadas, ou as credenciais cifradas perderão acesso.

## Passo 2 — ambiente de homologação
Manter:
- NF_CHECKOUT_MODE = test
- NF_CHECKOUT_ENABLED = false até a autorização OAuth de vendedor ser testada e a resposta do webhook ser verificada
- MP_USE_PKCE de acordo com o dashboard OAuth
- A versão do aplicativo precisa estar assinada pela chave permanente; não distribuir APK DEBUG do CI, nem exigir desinstalações repetidas de quem já tem dados.

Para executar um checkout sandbox, testar a conta autorizada e a geração de link sandbox. A autenticação do Mercado Pago para ambiente de teste e a geração de credenciais correspondentes devem seguir a documentação atual. **Pagamentos de teste não disparam Webhook automaticamente**; usar o simulador no painel de Webhooks para testar recepção, além de testes de API para verificar o status.

## Passo 3 — requisitos para PRODUÇÃO
- Autorização OAuth para **dois vendedores distintos** testada e tokens cifrados por empresa;
- Sem exposição de Access Tokens no APK;
- Testes de valores, conta recebedora, duplicidade e estornos com assinaturas HMAC;
- **Chave do Webhook de produção** salva, validada, com URL de produção cadastrada;
- Confirmar o produto integrado Checkout Pro habilitado no Mercado Pago;
- Configuração de servidor `NF_CHECKOUT_MODE=live` e `NF_CHECKOUT_ENABLED=true` somente depois da aprovação técnica e comercial;
- Conferir que não existe `marketplace_fee` nem `application_fee` em nenhuma cobrança. Taxas usuais do Mercado Pago continuam do vendedor.
- Monitorar divergências e falhas de Webhook; não marcar uma venda paga na tela de retorno.

## Isolamento das empresas
A API `nf-payments` protege:
- POST /sales para uma empresa pertencente ao usuário Supabase Auth;
- POST /sales/{sale_id}/checkout somente para o dono da venda;
- GET /sales?business_id={uuid} apenas para o dono;
- GET /sales/{sale_id} apenas para o dono;
- POST /webhook público mas exige assinatura válida HMAC, ID da transação e verificação da API oficial na conta do vendedor.
- Banco não expõe vendas ou tokens ao cliente diretamente; somente o servidor autorizado pode conciliar.

## Nota sobre o APK
A nova versão Android 0.7 possui interface de Cobranças online, mas NÃO está pronta para distribuição se ainda tiver certificado DEBUG. Não instalar por cima da versão antiga sem validar fingerprint da chave; fazer exportação JSON previamente.

Documentação oficial:
- https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-preferences/payment-notifications
- https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-preferences/how-tos/integrate-marketplace
- https://www.mercadopago.com.br/developers/pt/docs/security/oauth/creation
