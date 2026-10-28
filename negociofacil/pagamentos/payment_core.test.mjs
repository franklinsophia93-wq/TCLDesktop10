import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHmac} from 'node:crypto';
import {verifyWebhookSignature,reconcilePayment,createCheckout,fetchPayment,brlCents} from './payment_core.mjs';
const sale={id:'sale-1',businessId:'tenant-1',externalReference:'tenant-1:sale-1:random',amountCents:2599};
const seller={businessId:'tenant-1',providerAccountId:'owner-123',liveMode:false};
const payment={id:321,collector_id:'owner-123',external_reference:sale.externalReference,transaction_amount:25.99,currency_id:'BRL',status:'approved',live_mode:false,payment_type_id:'credit_card'};
test('webhook requer HMAC válido e rejeita adulteração',()=>{
 const ts=String(Date.now()), requestId='a-b-c', dataId='321',secret='segredo-test';
 const digest=createHmac('sha256',secret).update('id:321;request-id:a-b-c;ts:'+ts+';').digest('hex');
 const base={signature:'ts='+ts+',v1='+digest,requestId,dataId,secret};
 assert.equal(verifyWebhookSignature(base),true);
 assert.equal(verifyWebhookSignature({...base,dataId:'322'}),false);
 assert.equal(verifyWebhookSignature({...base,signature:'ts=1111111111,v1='+digest}),false);
});
test('centavos e valores válidos',()=>{
 assert.equal(brlCents('25.99'),2599);assert.equal(brlCents('1.01'),101);
 assert.throws(()=>brlCents('12.345'));
});
test('rejeita pendente, vendedor errado, valor, referência e moeda falsos',()=>{
 assert.equal(reconcilePayment(payment,sale,seller).accepted,true);
 for(const tampered of [
  {...payment,status:'pending'},{...payment,collector_id:'other'},
  {...payment,transaction_amount:1},{...payment,external_reference:'fake'},
  {...payment,currency_id:'USD'},{...payment,live_mode:true}
 ])assert.equal(reconcilePayment(tampered,sale,seller).accepted,false);
});
test('webhook repetido não gera crédito duplicado',()=>{
 assert.equal(reconcilePayment(payment,sale,seller,['321']).duplicate,true);
});
test('checkout usa valor da venda no backend e somente token do servidor',async()=>{
 const result=await createCheckout({sale,seller,accessToken:'token-teste',backendUrl:'https://backend.example.org',fetchImpl:async(url,request)=>{
  assert.equal(url,'https://api.mercadopago.com/checkout/preferences');
  assert.equal(request.headers.Authorization,'Bearer token-teste');
  assert.equal(JSON.parse(request.body).items[0].unit_price,25.99);
  return {ok:true,json:async()=>({id:'pref123',init_point:'https://www.mercadopago.com.br/checkout'})};
 }});
 assert.equal(result.preferenceId,'pref123');
});
test('busca status oficial no Mercado Pago',async()=>{
 const result=await fetchPayment({paymentId:321,sellerAccessToken:'token-teste',fetchImpl:async(url,request)=>{
  assert.equal(url,'https://api.mercadopago.com/v1/payments/321');
  assert.equal(request.headers.Authorization,'Bearer token-teste');
  return {ok:true,json:async()=>payment};
 }});
 assert.equal(result.id,321);
});
