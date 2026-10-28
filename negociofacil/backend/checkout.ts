// NegocioFacil | Checkout Pro marketplace SEM COMISSAO.
// Build de homologacao: exige segredo de Webhook e habilitacao explicita no cofre
// para aceitar cobrancas. Nenhum segredo MP entra no APK.
const API=Deno.env.get('SUPABASE_URL')||'';
const SR=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
const ENC_KEY=Deno.env.get('MP_TOKEN_ENCRYPTION_KEY')||'';
const WH_SECRET=Deno.env.get('MP_WEBHOOK_SECRET')||'';
const MODE=Deno.env.get('MP_PAYMENTS_MODE')||'test';
const ENABLED=Deno.env.get('MP_PAYMENTS_ENABLED')==='true';
const READY=Boolean(API&&SR&&ENC_KEY&&WH_SECRET&&ENABLED&&['test','production'].includes(MODE));
const BASE=API+'/functions/v1/nf-checkout';
const UUID=/^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i;
const PAYMENT=/^[0-9]{1,24}$/;
const ORIGIN='https://appassets.androidplatform.net';
const encode=new TextEncoder();
function json(value:unknown,status=200){return new Response(JSON.stringify(value),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff'}})}
const deny=(message:string,status:number)=>json({error:message},status);
function decode(x:string){return Uint8Array.from(atob(x.replaceAll('-','+').replaceAll('_','/')+'='.repeat((4-x.length%4)%4)),c=>c.charCodeAt(0))}
async function decrypt(ciphertext:string){
 const k=decode(ENC_KEY);if(k.length!==32)throw Error('Chave de cifragem invalida');
 const parts=ciphertext.split('.');if(parts.length!==2)throw Error('Credencial cifrada invalida');
 const key=await crypto.subtle.importKey('raw',k,{name:'AES-GCM'},false,['decrypt']);
 const out=await crypto.subtle.decrypt({name:'AES-GCM',iv:decode(parts[0])},key,decode(parts[1]));
 return new TextDecoder().decode(out);
}
async function rest(table:string,method='GET',filters='',data?:unknown,prefer='return=representation'){
 if(!/^nf_[a-z_]+$/.test(table))throw Error('Tabela invalida');
 const res=await fetch(API+'/rest/v1/'+table+(filters?'?'+filters:''),{
  method,headers:{apikey:SR,authorization:'Bearer '+SR,'content-type':'application/json',prefer},
  body:data===undefined?undefined:JSON.stringify(data)});
 if(!res.ok){console.error('DB status',res.status,table);throw Error('Banco indisponivel');}
 const text=await res.text();return text?JSON.parse(text):null;
}
async function rpc(name:string,data:unknown){
 if(name!=='nf_apply_mp_payment')throw Error('RPC invalida');
 const res=await fetch(API+'/rest/v1/rpc/'+name,{method:'POST',
 headers:{apikey:SR,authorization:'Bearer '+SR,'content-type':'application/json'},body:JSON.stringify(data)});
 if(!res.ok){console.error('RPC status',res.status);throw Error('Conciliacao indisponivel');}
 return res.json();
}
async function user(req:Request){
 const auth=req.headers.get('authorization')||'';
 if(!/^Bearer [a-zA-Z0-9._-]{40,}$/.test(auth))return null;
 const res=await fetch(API+'/auth/v1/user',{headers:{apikey:SR,authorization:auth}});
 if(!res.ok)return null;
 const data=await res.json();return UUID.test(data?.id||'')?data.id:null;
}
function filter(params:Record<string,string>){return new URLSearchParams(params).toString()}
async function owner(business:string,userId:string){
 if(!UUID.test(business)||!UUID.test(userId))return false;
 const rows=await rest('nf_businesses','GET',filter({select:'id',id:'eq.'+business,owner_user_id:'eq.'+userId,limit:'1'}));
 return Array.isArray(rows)&&rows.length===1;
}
async function sale(business:string,saleId:string){
 if(!UUID.test(business)||!UUID.test(saleId))return null;
 const rows=await rest('nf_sales','GET',filter({select:'id,business_id,description,amount_cents,status,external_reference,checkout_preference_id,checkout_url,provider_payment_id,paid_at,created_at',business_id:'eq.'+business,id:'eq.'+saleId,limit:'1'}));
 return rows?.[0]||null;
}
async function seller(business:string){
 const rows=await rest('nf_mp_connections','GET',filter({select:'mp_user_id,access_token_enc,expires_at',business_id:'eq.'+business,limit:'1'}));
 const row=rows?.[0];if(!row)throw Error('Vendedor nao conectado');
 if(row.expires_at&&Date.parse(row.expires_at)<Date.now()+30000)throw Error('Reconecte conta Mercado Pago');
 return {account:String(row.mp_user_id),token:await decrypt(row.access_token_enc)};
}
async function body(req:Request){
 const text=await req.text();if(text.length>20000)throw Error('Requisicao grande demais');
 const parsed=JSON.parse(text);if(!parsed||typeof parsed!=='object'||Array.isArray(parsed))throw Error('Corpo invalido');
 return parsed;
}
async function createSale(req:Request){
 const uid=await user(req);if(!uid)return deny('Login necessario',401);
 const input=await body(req);
 const business=String(input.business_id||'');
 if(!await owner(business,uid))return deny('Negocio nao autorizado',403);
 const desc=String(input.description||'').trim();
 const cents=input.amount_cents;
 if(desc.length<2||desc.length>120||!Number.isSafeInteger(cents)||cents<100||cents>100000000)return deny('Descricao/valor invalido',400);
 const saleId=crypto.randomUUID();
 const rows=await rest('nf_sales','POST','',{
  id:saleId,business_id:business,created_by:uid,description:desc,amount_cents:cents,
  currency:'BRL',external_reference:'nf:'+saleId,status:'pending'
 });
 if(!rows?.length)return deny('Nao foi possivel registrar a venda',502);
 return json({sale_id:saleId,status:'pending',amount_cents:cents});
}
async function listSales(req:Request){
 const uid=await user(req);if(!uid)return deny('Login necessario',401);
 const business=new URL(req.url).searchParams.get('business_id')||'';
 if(!await owner(business,uid))return deny('Negocio nao autorizado',403);
 const rows=await rest('nf_sales','GET',filter({select:'id,description,amount_cents,status,checkout_url,paid_at,created_at',business_id:'eq.'+business,order:'created_at.desc',limit:'50'}));
 return json({sales:rows});
}
async function createCheckout(req:Request){
 if(!READY)return deny('Pagamentos nao habilitados: aguarde homologacao e assinatura Webhook.',503);
 const uid=await user(req);if(!uid)return deny('Login necessario',401);
 const input=await body(req),business=String(input.business_id||''),id=String(input.sale_id||'');
 if(!await owner(business,uid))return deny('Negocio nao autorizado',403);
 const s=await sale(business,id);
 if(!s)return deny('Venda nao encontrada',404);
 if(s.status!=='pending')return deny('Esta venda nao aceita nova cobranca',409);
 if(s.checkout_preference_id&&s.checkout_url)return json({checkout_url:s.checkout_url,preference_id:s.checkout_preference_id,reused:true});
 const cred=await seller(business);
 const endpoint='https://api.mercadopago.com/checkout/preferences';
 const callback=new URL(BASE+'/webhook');callback.searchParams.set('business_id',business);callback.searchParams.set('sale_id',id);
 const payload={
  items:[{id:s.id,title:s.description,quantity:1,currency_id:'BRL',unit_price:s.amount_cents/100}],
  external_reference:s.external_reference,notification_url:callback.toString()
  // Intencionalmente sem marketplace_fee, application_fee ou split.
 };
 const resp=await fetch(endpoint,{method:'POST',
 headers:{authorization:'Bearer '+cred.token,'content-type':'application/json','x-idempotency-key':s.id},
 body:JSON.stringify(payload)});
 if(!resp.ok){console.error('MP preferencia HTTP',resp.status);return deny('Mercado Pago recusou a geracao da cobranca',502);}
 const created=await resp.json();
 const link=MODE==='production'?created.init_point:created.sandbox_init_point;
 let uri:URL;try{uri=new URL(link)}catch{return deny('Mercado Pago nao retornou checkout HTTPS valido',502)}
 if(uri.protocol!=='https:'||!/(^|\.)mercadopago\.com(\.br)?$/.test(uri.hostname))
    return deny('Checkout retornou endereco inesperado',502);
 if(!created.id)return deny('Preferencia sem identificador',502);
 const filterStr=filter({id:'eq.'+id,business_id:'eq.'+business,status:'eq.pending',checkout_preference_id:'is.null'});
 const rows=await rest('nf_sales','PATCH',filterStr,{checkout_preference_id:String(created.id),checkout_url:uri.toString(),updated_at:new Date().toISOString()});
 if(rows?.length===0){const current=await sale(business,id);return json({checkout_url:current?.checkout_url||null,preference_id:current?.checkout_preference_id||null,reused:true});}
 return json({checkout_url:uri.toString(),preference_id:String(created.id),reused:false});
}
async function validSignature(req:Request,paymentId:string){
 const signature=req.headers.get('x-signature')||'';
 const requestId=req.headers.get('x-request-id')||'';
 if(!requestId||requestId.length>200||!signature||!WH_SECRET)return false;
 const parts=Object.fromEntries(signature.split(',').map(x=>x.trim().split('=',2)));
 const ts=parts.ts,digest=parts.v1;
 if(!/^\d{10,16}$/.test(ts||'')||!/^[a-f0-9]{64}$/i.test(digest||''))return false;
 const time=Number(ts)<1e12?Number(ts)*1000:Number(ts);
 if(Math.abs(Date.now()-time)>20*60*1000)return false;
 const manifest='id:'+paymentId.toLowerCase()+';request-id:'+requestId+';ts:'+ts+';';
 const key=await crypto.subtle.importKey('raw',encode.encode(WH_SECRET),{name:'HMAC',hash:'SHA-256'},false,['sign']);
 const hash=Array.from(new Uint8Array(await crypto.subtle.sign('HMAC',key,encode.encode(manifest))),b=>b.toString(16).padStart(2,'0')).join('');
 // Fixed-length hexadecimal compare: no digest details exposed in response.
 let difference=0;for(let i=0;i<64;i++)difference|=hash.charCodeAt(i)^digest.toLowerCase().charCodeAt(i);
 return difference===0;
}
async function webhook(req:Request){
 if(!READY)return deny('Webhook ainda nao configurado',503);
 const u=new URL(req.url);
 const business=u.searchParams.get('business_id')||'',id=u.searchParams.get('sale_id')||'';
 const paymentId=u.searchParams.get('data.id')||u.searchParams.get('id')||'';
 if(!PAYMENT.test(paymentId))return deny('ID da notificacao invalido',400);
 if(!await validSignature(req,paymentId))return deny('Assinatura do Webhook invalida',401);
 const event=await body(req);
 if(event.type!=='payment'||String(event.data?.id||'')!==paymentId)return deny('Evento nao suportado',400);
 if(Boolean(event.live_mode)!==(MODE==='production'))return deny('Ambiente incorreto',409);
 // O teste do painel pode enviar uma notificacao ASSINADA sem contexto da
 // venda. Aceitamos o teste, mas NUNCA criamos recibo, venda ou pagamento.
 if(!UUID.test(business)||!UUID.test(id))return json({received:true,reconciled:false,reason:'sem_venda_vinculada'});
 const s=await sale(business,id);if(!s)return deny('Venda nao encontrada',404);
 const cred=await seller(business);
 const res=await fetch('https://api.mercadopago.com/v1/payments/'+paymentId,{headers:{authorization:'Bearer '+cred.token}});
 if(!res.ok)return deny('Nao foi possivel consultar status oficial',502);
 const payment=await res.json();
 if(String(payment.id)!==paymentId||String(payment.collector_id)!==cred.account
 ||payment.external_reference!==s.external_reference
 ||payment.currency_id!=='BRL'
 ||!Number.isSafeInteger(Math.round(Number(payment.transaction_amount)*100))
 ||Math.abs(Number(payment.transaction_amount)*100-s.amount_cents)>0.001
 ||Boolean(payment.live_mode)!==(MODE==='production'))return deny('Pagamento nao corresponde a venda autorizada',422);
 const record=await rpc('nf_apply_mp_payment',{
  p_sale_id:id,p_business_id:business,p_payment_id:paymentId,
  p_collector_id:String(payment.collector_id),p_reference:String(payment.external_reference),
  p_currency:'BRL',p_amount_cents:s.amount_cents,p_status:String(payment.status),
  p_method:String(payment.payment_type_id||''),p_paid_at:payment.date_approved||null
 });
 if(!record?.accepted)return deny('Conciliacao rejeitada',422);
 return json({received:true});
}
async function handler(req:Request):Promise<Response>{
 const path=new URL(req.url).pathname;
 if(path.endsWith('/health')&&req.method==='GET')return json({
  service:'NegocioFacil Checkout Pro',ready:READY,payments_enabled:READY,
  webhook_signature_configured:!!WH_SECRET,mode:MODE,
  note:'Pagamentos precisam de conta Mercado Pago autorizada por vendedor'
 });
 if(path.endsWith('/webhook')&&req.method==='POST')return webhook(req);
 if(path.endsWith('/sales')&&req.method==='POST')return createSale(req);
 if(path.endsWith('/sales')&&req.method==='GET')return listSales(req);
 if(path.endsWith('/checkout')&&req.method==='POST')return createCheckout(req);
 return deny('Rota nao encontrada',404);
}
Deno.serve(async(req:Request)=>{
 const origin=req.headers.get('origin');
 if(req.method==='OPTIONS'){
  if(origin!==ORIGIN)return deny('Origem nao autorizada',403);
  return new Response(null,{status:204,headers:{'access-control-allow-origin':ORIGIN,'access-control-allow-methods':'GET,POST,OPTIONS','access-control-allow-headers':'authorization,apikey,content-type','vary':'Origin'}});
 }
 try{
  const res=await handler(req);
  if(origin===ORIGIN){res.headers.set('access-control-allow-origin',ORIGIN);res.headers.set('vary','Origin');}
  return res;
 }catch(e){console.error('Checkout error',String(e));return deny('Falha no servico. Tente novamente.',500);}
});
