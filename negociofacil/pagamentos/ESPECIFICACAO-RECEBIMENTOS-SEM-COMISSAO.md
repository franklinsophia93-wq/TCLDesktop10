# NegócioFácil — recebimentos de cada profissional, sem comissão da plataforma

**Decisão do proprietário:** contas Mercado Pago individuais. Valor das vendas destinado a cada vendedor. **Comissão do NegócioFácil: zero**. Monetização da plataforma: AdMob no gratuito e assinaturas Pro/Empresarial, em fluxo separado.

**Estado atual:** definição de produto e núcleo de conciliação em `payment_core.mjs`; NÃO há backend multiempresa publicado, OAuth implantado nem pagamento real confirmado pelo APK. Não usar este código para mover dinheiro sem homologar.

## 1. Modelo do negócio

- O vendedor cadastra sua empresa no NegócioFácil e conecta **a sua própria conta** Mercado Pago.
- Nunca pedir a senha, access token, refresh token ou chave privada ao usuário no APK/chat. Autorizar via navegador e OAuth oficial, com callback **HTTPS** ao nosso backend.
- Usar Checkout Pro para a primeira etapa. O comprador paga no ambiente seguro Mercado Pago com os meios disponíveis para aquele vendedor (tipicamente Pix/cartão, dependendo de elegibilidade).
- A integração cria cobrança com **access token daquele vendedor**, não token da conta pessoal do proprietário do NegócioFácil.
- Nunca incluir `marketplace_fee` na preferência do Checkout Pro, nem `application_fee` em outros fluxos. Nenhum split para a plataforma.
- As **tarifas do Mercado Pago** continuam sendo responsabilidade da conta recebedora, conforme o produto/contrato.
- Não misturar assinaturas do software com dinheiro das vendas. Se publicado via Google Play, seguir requisitos de Google Play Billing para funcionalidades digitais Pro/Empresarial, salvo exceções autorizadas.

## 2. Telas (um APK para todos os planos)

**Meus recebimentos**
1. Estado da integração: Não conectado / Conectado à conta [nome verificado] / Reconectar / Desconectar.
2. "Conectar minha conta Mercado Pago" => autorização OAuth. O app não exibe nem armazena tokens.
3. Indicadores: valores aprovados, pendentes, estornados; período; extrato por venda.
4. "Cobrança de teste" visível apenas ao ADM em homologação, identificada como simulação/teste.
5. "Adicionar chave Pix manual" é opcional para controle externo, **sem confirmação automática**.

**Registrar venda**
1. Selecionar cliente e produtos/serviços e valor.
2. "Salvar" cria venda no servidor com `businessId` obtido da sessão autenticada, `amountCents` e `externalReference` únicas.
3. "Cobrar com Pix ou cartão" => servidor cria preferência com credencial daquele vendedor e retorna link HTTPS.
4. Abrir/compartilhar link de checkout. A volta do navegador **não** é comprovação de pagamento.
5. Status: Aguardando pagamento / Aprovado / Rejeitado / Cancelado / Reembolsado / Contestação. Em aprovado, atualizar financeiro e estoque conforme regras de confirmação e entrega.

**Planos Pro e Empresarial**
- As transações são do vendedor; a assinatura é da plataforma NegócioFácil.
- Não cobrar comissão por pagamento nem comissão adicional escondida.

## 3. Fluxo técnico

1. **Autenticação e autorização por empresa (obrigatória).** Cada pedido deve conferir quem pode gerir `businessId`. O banco deve negar acesso cruzado entre empresas.
2. **OAuth:** criar URL de autorização do Mercado Pago somente no servidor, com `state` criptograficamente aleatório, vencimento e amarração ao usuário/empresa. O callback valida `state` e `redirect_uri` e troca `code` por credenciais.
3. Persistir os tokens **criptografados no servidor**, com mecanismo de renovação, desconexão/revogação e registros de auditoria sem segredos.
4. **Checkout:** a partir de venda salva (valor em centavos e descrições sanitizadas), gerar preferência pela API Mercado Pago com access token da conta autorizada; adicionar `external_reference`, URL de retorno e Webhook HTTPS. Campo `marketplace_fee` **ausente**.
5. **Webhook:** validar `x-signature` e `x-request-id`; usar ID informado somente para consultar o recurso oficial na API. Conferir conta recebedora/`collector_id`, referência, valor exato, moeda BRL, modo live/test e status aprovado. Não confiar em informações do cliente, da URL de retorno ou no corpo não verificado.
6. **Idempotência e consistência:** `UNIQUE(provider, provider_payment_id)`. Efetuar mudança de status e lançamento financeiro na mesma transação do banco para impedir duplicidade de Webhooks.
7. **Atualizações:** lidar com eventos atrasados, rejeitados, expirados, estornos, reembolsos e chargebacks, com histórico e reversão contábil adequada. Reconciliar via consulta periódica casos de perda do Webhook.
8. **Privacidade e segurança:** conexões HTTPS, backups cifrados, limites de requisições, logs sem tokens, LGPD, política de privacidade e termos de uso.

## 4. Contratos sugeridos (pendentes de implementação)

| Endpoint de backend | Uso | Acesso |
|---|---|---|
| `POST /v1/mp/oauth/start` | Inicia autorização com `state` e fornece URL OAuth | Vendedor autenticado |
| `GET /v1/mp/oauth/callback` | Valida callback e armazena token cifrado | Callback Mercado Pago + estado válido |
| `GET /v1/mp/connection` | Exibe estado da conexão, sem tokens | Vendedor autenticado |
| `DELETE /v1/mp/connection` | Desconecta credenciais desta empresa | Dono/admin autorizado |
| `POST /v1/sales/:id/checkout` | Gera checkout com credencial do vendedor correspondente | Membro com direito de vender |
| `GET /v1/sales/:id/payment` | Status real confirmado pelo servidor | Membro da mesma empresa |
| `POST /v1/webhooks/mercadopago` | Recebe, valida, consulta e reconcilia eventos | Assinatura válida, sem sessão do app |

### Entidades mínimas de banco
- `businesses`, `users`, `memberships` (empresa e papel)
- `payment_connections` (business_id UNIQUE, provider_account_id, credenciais cifradas e validade)
- `sales` (business_id, id, amount_cents, external_reference UNIQUE, status)
- `provider_payments` (provider, provider_payment_id UNIQUE, business_id, sale_id, approved_amount_cents, status, approved_at)
- `webhook_events` (event_id UNIQUE, provider, processamento e falhas)
- `ledger_entries` (contabilidade idempotente, ajustes e estornos)

## 5. Homologação obrigatória antes de habilitar cobranças reais

- [ ] Aplicação Mercado Pago Developers com OAuth autorizada e callback HTTPS configurado.
- [ ] Domínio/backend e banco implantados; autenticação real do usuário e segregação entre empresas.
- [ ] Duas empresas fictícias autorizam contas distintas e **nenhum valor é direcionado à conta da plataforma**.
- [ ] Checkout Pix e cartão aprovados/rejeitados/pedidos pendentes em **ambiente de teste** conforme ferramentas do provedor.
- [ ] Webhooks validados com segredo, reenvio e duplicidade sem dobrar receitas.
- [ ] Cancelamento, expiração, reembolso, chargeback, falha de rede e renovação OAuth testados.
- [ ] Pix manual **não** reconhecido como pago automaticamente.
- [ ] Inventário/entrega só muda conforme regras de transação verificada, não pelo retorno do navegador.
- [ ] Política de privacidade, termos e divulgação clara das tarifas do Mercado Pago.
- [ ] Assinatura estável do APK para atualização sem reinstalação; backup restaurável.
- [ ] Google Play Billing/entitlements para assinaturas digitais conforme políticas vigentes.

## 6. Ponto de partida já existente

`payment_core.mjs`: `createCheckout` usa credencial do vendedor e **não** preenche comissão do marketplace; `verifyWebhookSignature`, `fetchPayment`, `reconcilePayment` e testes de validação inicial. Essas funções **não equivalem** a um serviço integrado ou homologado. Autenticação, persistência, OAuth, webhooks operacionais e instalação de servidor continuam pendentes.

## Referências oficiais
- OAuth: https://www.mercadopago.com.br/developers/pt/docs/security/oauth/creation
- Marketplace Checkout Pro: https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-preferences/how-tos/integrate-marketplace
- Webhooks: https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-preferences/payment-notifications
- Google Play Billing: https://support.google.com/googleplay/android-developer/answer/10281818?hl=pt-BR
