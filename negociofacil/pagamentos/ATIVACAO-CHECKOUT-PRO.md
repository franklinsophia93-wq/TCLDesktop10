# NegócioFácil 0.7 — ativação controlada de pagamentos Mercado Pago

**Estado:** os serviços e o banco foram implantados, mas **nenhuma cobrança real foi criada ou validada**. Sem contas de vendedores conectadas e sem a chave secreta de Webhooks, o Checkout Pro fica bloqueado (HTTP 503).

## Serviços publicados
- Supabase próprio: https://supabase.com/dashboard/project/tlqcpfmkneohjleiynqe
- OAuth por vendedor: `https://tlqcpfmkneohjleiynqe.supabase.co/functions/v1/nf-mercadopago`
- Checkout Pro: `https://tlqcpfmkneohjleiynqe.supabase.co/functions/v1/nf-checkout`
- Diagnóstico sem segredos: `https://tlqcpfmkneohjleiynqe.supabase.co/functions/v1/nf-checkout/health`
- Webhook de pagamento: `https://tlqcpfmkneohjleiynqe.supabase.co/functions/v1/nf-checkout/webhook`

## Preparação da integração no Mercado Pago Developers (NÃO enviar chaves pelo chat)
1. Abra a aplicação **NegócioFácil** no Mercado Pago Developers.
2. Na configuração de **Webhooks**, selecione ambiente **Teste** e o evento **Pagamentos** (Checkout Pro / Preferences API).
3. Use a URL de Webhook acima e salve.
4. Na tela de Webhooks do Mercado Pago, revele a **Assinatura secreta** (NÃO confundir com Access Token, Client Secret ou Public Key).
5. Abra o painel Supabase do NegocioFacil > Edge Functions > Secrets; registre **MP_WEBHOOK_SECRET** com o valor da assinatura secreta, sem compartilhar, sem salvar em GitHub e sem colocá-lo no APK.
6. Enquanto não houver um pagamento de sandbox validado, mantenha `MP_PAYMENTS_ENABLED` **ausente ou igual a false** e `MP_PAYMENTS_MODE=test`. Os segredos de teste e produção podem ser diferentes; nunca misture.

## Requisitos adicionais antes de receber dinheiro real
- Criar login Supabase Auth e negócio de teste no APK Android com **assinatura permanente**.
- Conectar **duas contas de vendedor** via OAuth, confirmando o destinatário exato. Ainda existem 0 negócios e 0 contas Mercado Pago conectadas ao novo banco na etapa inicial.
- Testar checkout de teste, Webhook válido/inválido, Pix pendente/aprovado, cartão aprovado/rejeitado, idempotência de notificação, estorno e chargeback.
- Confirmar que a rotina de conciliação nunca admite saldo da empresa errada, valor errado ou webhook forjado.
- Confirmar no Mercado Pago se a aplicação está aprovada para modo produtivo e se os vendedores podem receber.
- Apenas após homologação técnica, armazenar no cofre do Supabase `MP_PAYMENTS_ENABLED=true` e `MP_PAYMENTS_MODE=production` junto à assinatura de Webhook de produção; **essa mudança ativa a solicitação de cobranças reais**, e somente deve ocorrer após a avaliação de risco e aceite explícito.
- A emissão de documentos fiscais oficiais e assinaturas de planos digitais são integrações separadas.

## Modelo de negócio
- Cada venda usa o **access token OAuth do próprio vendedor** para criar preferência `/checkout/preferences`.
- **Sem `marketplace_fee`**, sem `application_fee`, sem split ou comissão do NegócioFácil.
- Tarifas e prazos de liberação do Mercado Pago são determinados pelo contrato de cada profissional.
- O checkout abre página oficial Mercado Pago; o aplicativo não coleta números de cartão.
- Somente evento Webhook autenticado seguido de busca oficial do pagamento + correspondência de collector_id, external_reference, valor, moeda e ambiente poderá atualizar a venda.
- Banco de pagamentos tem RLS e serviço possui permissão exclusiva de reconciliação. Notificações duplicadas não registram nova receita.
- Vendas criadas no servidor são **separadas** dos cadastros locais antigos até desenvolver sincronização.

## Atualização do APK
Versões de teste 0.1-0.4 tinham certificados de depuração distintos. Compilar **com assinatura permanente** sob GitHub Secrets é obrigatório para que versões futuras se atualizem por cima.
A primeira migração de debug para a assinatura permanente poderá exigir reinstalação, **após backup local**; depois manter o certificado.
O APK compilado em CI de debug é de **validação técnica apenas**, NÃO instalar.

## Referências oficiais
- Checkout marketplace: https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-preferences/how-tos/integrate-marketplace
- Webhooks payment: https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-preferences/payment-notifications
- Supabase Secrets: https://supabase.com/docs/guides/functions/secrets
