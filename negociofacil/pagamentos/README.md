# NegócioFácil — conciliação Pix e cartão (fase de integração)

**Situação:** núcleo validado por testes locais, sem servidor publicado, sem autenticação multiempresa e sem acesso a dinheiro real. **Não existe recebimento automático no APK 0.4**.

## Objetivo
Cada profissional vincula sua **própria** conta Mercado Pago por autorização OAuth. O NegócioFácil não recebe recursos financeiros em nome de outras empresas. O cliente conclui o pagamento em um checkout hospedado pelo Mercado Pago. Os webhooks HTTPS são assinados, consultados e conciliados com vendas que já existem no servidor.

## Fluxo seguro
1. Autenticar a empresa no servidor (ainda depende de um sistema real de login e permissão). Nunca confiar no `businessId` enviado isoladamente pelo APK.
2. Guardar venda, valores em centavos e referência aleatória/única em um banco de dados transacional. O aplicativo não pode escolher o valor final da cobrança depois de criá-la.
3. Vincular conta Mercado Pago de cada profissional por OAuth, guardar o token **criptografado no servidor** e vincular ao `providerAccountId` (nunca em JavaScript, localStorage nem no APK).
4. Criar checkout para a venda e mostrar o link `init_point` do provedor, que pode oferecer Pix e cartão. Não coletar nem guardar dados de cartões no NegócioFácil.
5. Mercado Pago POST no endpoint HTTPS `/webhooks/mercado-pago` com assinatura `x-signature`. Conferir assinatura, timestamp e `x-request-id` usando o SDK oficial; consultar o ID do pagamento via API do provedor antes de tomar uma ação.
6. Comparar conta recebedora, `external_reference`, valor, moeda `BRL`, ambiente e status. Somente `approved` pode ser contabilizado como recebido.
7. Salvar status, ID de pagamento, método e comprovante em transação no banco; impor UNIQUE(`provider`, `provider_payment_id`) para evitar duplicações em reenvios de webhook.
8. Disponibilizar status atualizado ao celular por consulta autenticada ou realtime. Lidar com reembolso, cancelamento, estorno e chargeback com registros reversíveis/auditáveis. Nunca remover uma venda historicamente.

## O que o núcleo atual cobre
O arquivo `payment_core.mjs` contém funções puras para assinatura HMAC, criação de checkout, consulta oficial e reconciliação de valores. Os testes `payment_core.test.mjs` simulam o provedor sem enviar qualquer pagamento real. Eles não substituem testes end-to-end.

## Requisitos para ativação
- Conta Mercado Pago Developers e aplicação OAuth Marketplace, credenciais guardadas em gerenciador de segredos.
- Domínio HTTPS e backend com banco, autenticação por empresa e autorização do usuário.
- Webhook real com segredo próprio, testes de replay, idempotência, mudanças de status e resiliência a indisponibilidade.
- Contrato de tratamento de dados LGPD e separação de empresas (RLS ou ACL). Backups seguros, logs com retenção limitada.
- Para as **assinaturas digitais Pro/Empresarial do aplicativo distribuído na Google Play**, a cobrança é separada, geralmente **Google Play Billing**, não deve utilizar Checkout Pro sem verificar a política aplicável.

## Teste
```sh
node --test backend/payment_core.test.mjs
```

Não enviar access tokens ou webhook secrets por mensagens. IDs públicos do AdMob são diferentes de segredos Mercado Pago.