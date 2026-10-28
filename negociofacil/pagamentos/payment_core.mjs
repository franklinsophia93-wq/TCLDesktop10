import {createHmac,timingSafeEqual} from 'node:crypto';

// Funciona somente no servidor. NUNCA empacotar segredos de pagamentos no APK.
export function verifyWebhookSignature({signature,requestId,dataId,secret,now=Date.now()}) {
  if (![signature,requestId,dataId,secret].every(x=>typeof x==='string'&&x)) return false;
  const pieces=Object.fromEntries(signature.split(',').map(p=>p.trim().split('=',2)));
  const ts=pieces.ts, digest=pieces.v1;
  if(!/^\d{10,16}$/.test(ts||'')||!/^[0-9a-f]{64}$/i.test(digest||''))return false;
  const milliseconds=Number(ts)<1e12?Number(ts)*1000:Number(ts);
  if(!Number.isFinite(milliseconds)||Math.abs(now-milliseconds)>20*60*1000)return false;
  const expected=createHmac('sha256',secret)
    .update('id:'+dataId.toLowerCase()+';request-id:'+requestId+';ts:'+ts+';').digest();
  const actual=Buffer.from(digest,'hex');
  return actual.length===expected.length && timingSafeEqual(actual,expected);
}

export function brlCents(value) {
  if(!/^\d+(\.\d{1,2})?$/.test(String(value)))throw new Error('Valor inválido');
  const [whole,fraction='']=String(value).split('.');
  const cents=Number(whole)*100+Number(fraction.padEnd(2,'0'));
  if(!Number.isSafeInteger(cents)||cents<=0)throw new Error('Valor fora da faixa');
  return cents;
}

// Não confiar no webhook isoladamente: obtenha o pagamento pelo token
// de cada vendedor e compare os campos oficiais com a venda autenticada.
export function reconcilePayment(payment,sale,seller,seenIds=[]) {
  const rejected=reason=>({accepted:false,reason});
  if(!payment||!sale||!seller)return rejected('missing_fields');
  if(!seller.providerAccountId||String(payment.collector_id)!==String(seller.providerAccountId))return rejected('wrong_seller');
  if(!sale.externalReference||payment.external_reference!==sale.externalReference)return rejected('wrong_reference');
  if(payment.currency_id!=='BRL')return rejected('wrong_currency');
  try{if(brlCents(payment.transaction_amount)!==sale.amountCents)return rejected('wrong_amount');}
  catch{return rejected('wrong_amount');}
  if(payment.status!=='approved')return rejected('not_approved');
  if(payment.live_mode!==seller.liveMode)return rejected('wrong_environment');
  if(!/^\d{1,24}$/.test(String(payment.id)))return rejected('bad_payment_id');
  return {accepted:true,duplicate:seenIds.includes(String(payment.id)),record:{
    saleId:sale.id,businessId:sale.businessId,provider:'mercado_pago',
    providerPaymentId:String(payment.id),amountCents:sale.amountCents,
    status:'paid',method:payment.payment_type_id||'unknown',paidAt:payment.date_approved||null
  }};
}

export async function fetchPayment({paymentId,sellerAccessToken,fetchImpl=fetch}) {
  if(!/^\d{1,24}$/.test(String(paymentId)))throw new Error('ID inválido');
  if(!sellerAccessToken)throw new Error('Conta do vendedor ainda não conectada');
  const response=await fetchImpl('https://api.mercadopago.com/v1/payments/'+paymentId,{
    headers:{Authorization:'Bearer '+sellerAccessToken}
  });
  if(!response.ok)throw new Error('Erro na API Mercado Pago: '+response.status);
  return response.json();
}

export async function createCheckout({sale,seller,accessToken,backendUrl,fetchImpl=fetch}) {
  if(!sale||!seller||sale.businessId!==seller.businessId)throw new Error('Vendedor inválido');
  if(!accessToken||!/^https:\/\//.test(backendUrl||''))throw new Error('Backend HTTPS e OAuth obrigatórios');
  if(!Number.isSafeInteger(sale.amountCents)||sale.amountCents<=0||!sale.externalReference)throw new Error('Venda inválida');
  const payload={
    items:[{id:String(sale.id),title:String(sale.description||'Venda').slice(0,120),
      quantity:1,currency_id:'BRL',unit_price:sale.amountCents/100}],
    external_reference:sale.externalReference,
    notification_url:backendUrl.replace(/\/$/,'')+'/webhooks/mercado-pago'
  };
  const response=await fetchImpl('https://api.mercadopago.com/checkout/preferences',{
    method:'POST',headers:{Authorization:'Bearer '+accessToken,'Content-Type':'application/json'},
    body:JSON.stringify(payload)
  });
  if(!response.ok)throw new Error('Falha ao criar cobrança: '+response.status);
  const preference=await response.json();
  if(!/^https:\/\//.test(preference.init_point||''))throw new Error('Checkout não retornou HTTPS');
  return {preferenceId:preference.id,checkoutUrl:preference.init_point};
}
