/**
 * NegócioFácil — Checkout Pro Mercado Pago por vendedor.
 * Status: HOMOLOGAÇÃO. A cobrança requer NF_CHECKOUT_ENABLED=true,
 * MP_WEBHOOK_SECRET, uma conta Mercado Pago autorizada e login do dono.
 * Sem comissão da plataforma. Sem segredos no APK.
 */
const API=Deno.env.get("SUPABASE_URL")||"";
const SERVICE=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")||"";
const CLIENT=Deno.env.get("MP_CLIENT_ID")||"";
const SECRET=Deno.env.get("MP_CLIENT_SECRET")||"";
const KEY=Deno.env.get("MP_TOKEN_ENCRYPTION_KEY")||"";
const WEBHOOK_SECRET=Deno.env.get("MP_WEBHOOK_SECRET")||"";
const CHECKOUT_ENABLED=Deno.env.get("NF_CHECKOUT_ENABLED")==="true";
const MODE=Deno.env.get("NF_CHECKOUT_MODE")==="live"?"live":"test";
const PROJECT="https://tlqcpfmkneohjleiynqe.supabase.co";
const NOTIFICATION=PROJECT+"/functions/v1/nf-payments/webhook";
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const digits=/^[0-9]{1,24}$/;
const encoder=new TextEncoder();

function resp(data:unknown,status=200){return new Response(JSON.stringify(data),{status,headers:{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}})}
function str(x:unknown){return typeof x==="string"?x:"";}
function fail(message:string,status=400){return resp({error:message},status)}
function b64d(s:string){const str=s.replaceAll("-","+").replaceAll("_","/");return Uint8Array.from(atob(str+"=".repeat((4-str.length%4)%4)),x=>x.charCodeAt(0))}
function b64e(bytes:Uint8Array){return btoa(String.fromCharCode(...bytes)).replaceAll("+","-").replaceAll("/","_").replace(/=+$/,"")}
async function aesKey(){
 const key=b64d(KEY);if(key.length!==32)throw Error("Invalid MP key");
 return crypto.subtle.importKey("raw",key,"AES-GCM",false,["decrypt","encrypt"]);
}
async function decrypt(value:string){const [iv,cipher]=value.split(".");if(!iv||!cipher)throw Error("Bad encrypted token");return new TextDecoder().decode(await crypto.subtle.decrypt({name:"AES-GCM",iv:b64d(iv)},await aesKey(),b64d(cipher)))}
async function encrypt(value:string){const iv=crypto.getRandomValues(new Uint8Array(12));const bytes=new Uint8Array(await crypto.subtle.encrypt({name:"AES-GCM",iv},await aesKey(),encoder.encode(value)));return b64e(iv)+"."+b64e(bytes)}
async function db(table:string,method="GET",query="",data?:unknown,prefer="return=representation"){
 if(!/^nf_(?:businesses|sales|mp_connections|provider_payments)$/.test(table))throw Error("Invalid table");
 const u=API+"/rest/v1/"+table+(query?"?"+query:"");
 const r=await fetch(u,{method,headers:{apikey:SERVICE,Authorization:"Bearer "+SERVICE,"Content-Type":"application/json",Prefer:prefer},body:data===undefined?undefined:JSON.stringify(data)});
 if(!r.ok){console.error("Database failure",table,r.status);throw Error("Database unavailable")}
 const text=await r.text();return text?JSON.parse(text):null;
}
async function rpc(method:string,body:unknown){
 const r=await fetch(API+"/rest/v1/rpc/"+method,{method:"POST",headers:{apikey:SERVICE,Authorization:"Bearer "+SERVICE,"Content-Type":"application/json"},body:JSON.stringify(body)});
 if(!r.ok){console.error("Database transaction failure",r.status);throw Error("Transaction unavailable")}
 return r.json();
}
async function caller(req:Request){
 const token=req.headers.get("authorization")||"";
 if(!/^Bearer [a-zA-Z0-9._-]{40,}$/.test(token))return null;
 const r=await fetch(API+"/auth/v1/user",{headers:{apikey:SERVICE,authorization:token}});
 if(!r.ok)return null;
 const u=await r.json();return uuid.test(str(u.id))?u.id:null;
}
function q(obj:Record<string,string>){return new URLSearchParams(obj).toString()}
async function businessOwner(businessId:string,user:string){
 if(!uuid.test(businessId))return false;
 const rows=await db("nf_businesses","GET",q({select:"id",id:"eq."+businessId,owner_user_id:"eq."+user,limit:"1"}));
 return rows.length===1;
}
async function connection(businessId:string){
 const rows=await db("nf_mp_connections","GET",q({select:"business_id,mp_user_id,access_token_enc,refresh_token_enc,expires_at",business_id:"eq."+businessId,limit:"1"}));
 return rows[0]||null;
}
async function refreshedToken(conn:Record<string,any>){
 if(!conn)throw Error("Not connected");
 if(!conn.expires_at||Date.parse(conn.expires_at)>Date.now()+120000)return decrypt(conn.access_token_enc);
 if(!conn.refresh_token_enc||!CLIENT||!SECRET)throw Error("Reconnect required");
 const refresh=await decrypt(conn.refresh_token_enc);
 const r=await fetch("https://api.mercadopago.com/oauth/token",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({client_id:CLIENT,client_secret:SECRET,grant_type:"refresh_token",refresh_token:refresh})});
 if(!r.ok){console.error("MP refresh failed",r.status);throw Error("Reconnect required")}
 const data=await r.json();
 if(!data.access_token||String(data.user_id)!==String(conn.mp_user_id))throw Error("Invalid MP refresh");
 const update={access_token_enc:await encrypt(String(data.access_token)),refresh_token_enc:data.refresh_token?await encrypt(String(data.refresh_token)):conn.refresh_token_enc,expires_at:data.expires_in?new Date(Date.now()+Number(data.expires_in)*1000).toISOString():null,updated_at:new Date().toISOString()};
 await db("nf_mp_connections","PATCH",q({business_id:"eq."+conn.business_id}),update,"return=minimal");
 return String(data.access_token);
}
async function createSale(req:Request,user:string){
 const data=await req.json().catch(()=>null);
 const businessId=str(data?.business_id),description=str(data?.description).trim();
 const cents=data?.amount_cents;
 if(!uuid.test(businessId)||description.length<1||description.length>120||!Number.isSafeInteger(cents)||cents<100||cents>100000000)
  return fail("Informe empresa, descrição e valor em centavos (mínimo R$ 1,00).");
 if(!await businessOwner(businessId,user))return fail("Empresa não autorizada",403);
 const id=crypto.randomUUID(),reference="nf_"+id;
 const rows=await db("nf_sales","POST","",{id,business_id:businessId,description,amount_cents:cents,external_reference:reference}, "return=representation");
 return resp({sale_id:rows[0].id,status:"pending",amount_cents:cents,description},201);
}
async function ownedSale(id:string,user:string){
 const rows=await db("nf_sales","GET",q({select:"id,business_id,description,amount_cents,currency_id,external_reference,status,checkout_preference_id,checkout_url,created_at",id:"eq."+id,limit:"1"}));
 const sale=rows[0];if(!sale)return null;
 if(!await businessOwner(sale.business_id,user))return null;
 return sale;
}
async function listSales(req:Request,user:string){
 const businessId=str(new URL(req.url).searchParams.get("business_id"));
 if(!uuid.test(businessId)||!await businessOwner(businessId,user))return fail("Negócio não autorizado",403);
 const rows=await db("nf_sales","GET",q({select:"id,description,amount_cents,status,created_at",business_id:"eq."+businessId,order:"created_at.desc",limit:"30"}));
 return resp({sales:rows});
}
async function checkout(id:string,user:string){
 if(!CHECKOUT_ENABLED)return fail("Checkout não liberado: homologação de segurança pendente",503);
 if(!WEBHOOK_SECRET)return fail("Webhook ainda não configurado",503);
 if(!CLIENT||!SECRET||!KEY)return fail("Credenciais indisponíveis",503);
 const sale=await ownedSale(id,user);if(!sale)return fail("Venda não encontrada",404);
 if(sale.status==="paid")return fail("Esta venda já foi paga.",409);
 if(sale.checkout_url&&sale.checkout_preference_id)return resp({sale_id:id,checkout_url:sale.checkout_url,preference_id:sale.checkout_preference_id,mode:MODE});
 const conn=await connection(sale.business_id);if(!conn)return fail("Conecte a conta Mercado Pago deste profissional.",409);
 const accessToken=await refreshedToken(conn);
 const details={
  items:[{id:sale.id,title:sale.description,quantity:1,currency_id:"BRL",unit_price:sale.amount_cents/100}],
  external_reference:sale.external_reference,
  notification_url:NOTIFICATION,
  back_urls:{
   success:PROJECT+"/functions/v1/nf-payments/return",
   failure:PROJECT+"/functions/v1/nf-payments/return",
   pending:PROJECT+"/functions/v1/nf-payments/return"
  }
  // Proibido: marketplace_fee, application_fee ou split_payment
 };
 const r=await fetch("https://api.mercadopago.com/checkout/preferences",{
  method:"POST",headers:{Authorization:"Bearer "+accessToken,"Content-Type":"application/json","X-Idempotency-Key":sale.id},
  body:JSON.stringify(details)
 });
 if(!r.ok){console.error("MP checkout HTTP",r.status);return fail("Não foi possível gerar o link de pagamento.",502)}
 const data=await r.json();
 const url=MODE==="test"?data.sandbox_init_point:data.init_point;
 if(!url||!/^https:\/\//.test(url))return fail("Link do Mercado Pago indisponível no ambiente "+MODE,502);
 const target=new URL(url);
 if(!/(^|\.)mercadopago\.com(\.br)?$/.test(target.hostname)&&!/(^|\.)mercadolibre\.com(\.br)?$/.test(target.hostname))
  return fail("Domínio do checkout inesperado",502);
 await db("nf_sales","PATCH",q({id:"eq."+id,status:"in.(pending,checkout_created)"}),{status:"checkout_created",checkout_preference_id:String(data.id),checkout_url:url,updated_at:new Date().toISOString()},"return=minimal");
 return resp({sale_id:id,checkout_url:url,preference_id:String(data.id),mode:MODE});
}
function cents(amount:unknown){
 const s=String(amount);
 if(!/^\d+(\.\d{1,2})?$/.test(s))return null;
 const [whole,dec=""]=s.split(".");
 const result=Number(whole)*100+Number(dec.padEnd(2,"0"));
 return Number.isSafeInteger(result)?result:null;
}
async function verifySignature(req:Request,dataId:string){
 if(!WEBHOOK_SECRET)return false;
 const signature=req.headers.get("x-signature")||"",requestId=req.headers.get("x-request-id")||"";
 const parts=Object.fromEntries(signature.split(",").map(x=>x.trim().split("=",2)));
 const ts=parts.ts||"",digest=parts.v1||"";
 if(!/^\d{10,16}$/.test(ts)||!/^[0-9a-f]{64}$/i.test(digest)||!requestId||requestId.length>100)return false;
 const millis=Number(ts)<1e12?Number(ts)*1000:Number(ts);
 if(Math.abs(Date.now()-millis)>20*60*1000)return false;
 const message="id:"+dataId.toLowerCase()+";request-id:"+requestId+";ts:"+ts+";";
 const key=await crypto.subtle.importKey("raw",encoder.encode(WEBHOOK_SECRET),{name:"HMAC",hash:"SHA-256"},false,["sign"]);
 const expected=new Uint8Array(await crypto.subtle.sign("HMAC",key,encoder.encode(message)));
 const supplied=Uint8Array.from(digest.match(/../g)!,x=>parseInt(x,16));
 let mismatch=0;for(let i=0;i<32;i++)mismatch|=expected[i]^supplied[i];
 return mismatch===0;
}
async function webhook(req:Request){
 if(!WEBHOOK_SECRET)return fail("Webhook not configured",503);
 const url=new URL(req.url),id=str(url.searchParams.get("data.id"));
 if(!digits.test(id))return fail("Data ID inválido",400);
 if(!await verifySignature(req,id))return fail("Assinatura de webhook inválida",401);
 const body=await req.json().catch(()=>null);
 if(!body||String(body.data?.id)!==id||body.type!=="payment"||!digits.test(String(body.user_id||"")))return fail("Notificação inválida",400);
 const merchants=await db("nf_mp_connections","GET",q({select:"business_id,mp_user_id,access_token_enc,refresh_token_enc,expires_at",mp_user_id:"eq."+body.user_id,limit:"20"}));
 if(!merchants.length)return resp({ignored:true,reason:"no_connected_seller"});
 // Query payment only with a credential belonging to the notified seller.
 let payment:any=null;
 for(const conn of merchants){
  const token=await refreshedToken(conn);
  const r=await fetch("https://api.mercadopago.com/v1/payments/"+id,{headers:{Authorization:"Bearer "+token}});
  if(r.ok){payment=await r.json();break}
 }
 if(!payment)return fail("Não foi possível consultar o pagamento no Mercado Pago",502);
 if(String(payment.id)!==id||String(payment.collector_id)!==String(body.user_id))return fail("Pagamento de outro recebedor",403);
 const ref=str(payment.external_reference);
 if(!/^nf_[0-9a-f-]{36}$/i.test(ref))return resp({ignored:true,reason:"foreign_reference"});
 const sales=await db("nf_sales","GET",q({select:"id,business_id,amount_cents,currency_id,external_reference",external_reference:"eq."+ref,limit:"1"}));
 const sale=sales[0];
 if(!sale)return resp({ignored:true,reason:"sale_not_found"});
 const authorizedMerchant=merchants.find((c:any)=>c.business_id===sale.business_id);
 if(!authorizedMerchant||String(authorizedMerchant.mp_user_id)!==String(body.user_id))return fail("Empresa divergente",409);
 const amount=cents(payment.transaction_amount);
 if(amount!==sale.amount_cents||payment.currency_id!=="BRL"||payment.external_reference!==sale.external_reference)
  return fail("Valor, moeda ou referência não conferem",409);
 if(typeof payment.live_mode!=="boolean"||payment.live_mode!==(MODE==="live"))
  return fail("Ambiente de pagamento não corresponde",409);
 const statuses=["approved","pending","rejected","cancelled","refunded","charged_back","in_process","authorized"];
 if(!statuses.includes(payment.status))return resp({ignored:true,reason:"unhandled_status"});
 const next=await rpc("nf_record_verified_payment",{
  p_payment_id:id,p_sale_id:sale.id,p_business_id:sale.business_id,
  p_amount_cents:sale.amount_cents,p_account_id:String(body.user_id),
  p_currency_id:"BRL",p_status:payment.status,p_live_mode:payment.live_mode,
  p_paid_at:payment.date_approved||null
 });
 return resp({ok:true,status:next});
}
async function main(req:Request){
 const path=new URL(req.url).pathname;
 if(path.endsWith("/health")&&req.method==="GET")return resp({service:"NegocioFacil Checkout Pro",mode:MODE,checkout_enabled:CHECKOUT_ENABLED,webhook_ready:!!WEBHOOK_SECRET,secret_values_exposed:false});
 if(path.endsWith("/return")&&req.method==="GET")return new Response('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>NegócioFácil</title><body style="font:18px Arial;padding:25px"><h1>NegócioFácil</h1><p>Retorno do checkout recebido. Volte ao aplicativo para consultar a confirmação do pagamento. Esta tela NÃO confirma que a venda foi paga.</p></body></html>',{headers:{"Content-Type":"text/html;charset=utf-8","Cache-Control":"no-store"}});
 if(path.endsWith("/webhook")&&req.method==="POST")return await webhook(req);
 const user=await caller(req);
 if(!user)return fail("Login obrigatório",401);
 if(path.endsWith("/sales")&&req.method==="POST")return await createSale(req,user);
 if(path.endsWith("/sales")&&req.method==="GET")return await listSales(req,user);
 const match=path.match(/\/sales\/([0-9a-f-]{36})(\/checkout)?$/i);
 if(match&&uuid.test(match[1])){
  if(match[2]&&req.method==="POST")return await checkout(match[1],user);
  if(!match[2]&&req.method==="GET"){
   const sale=await ownedSale(match[1],user);
   return sale?resp({sale_id:sale.id,description:sale.description,amount_cents:sale.amount_cents,status:sale.status,created_at:sale.created_at}):fail("Venda não encontrada",404);
  }
 }
 return fail("Rota não encontrada",404);
}
Deno.serve(async req=>{
 try{return await main(req)}
 catch(error){console.error("Payment gateway error",String(error));return fail("Erro interno no serviço de pagamentos",500)}
});
