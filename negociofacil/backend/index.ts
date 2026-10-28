// NegocioFacil / Mercado Pago OAuth. NENHUM pagamento é processado aqui.
// O servidor só permite conectar contas após configurar segredos via Supabase.
// Callback público; outras rotas exigem login Auth real + propriedade da empresa.
const API=Deno.env.get('SUPABASE_URL')||'';
const SERVICE=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
const CLIENT=Deno.env.get('MP_CLIENT_ID')||'';
const SECRET=Deno.env.get('MP_CLIENT_SECRET')||'';
const REDIRECT=Deno.env.get('MP_REDIRECT_URI')||'';
const KEY=Deno.env.get('MP_TOKEN_ENCRYPTION_KEY')||'';
const USE_PKCE=Deno.env.get('MP_USE_PKCE')==='true';
const ready=!!(API&&SERVICE&&CLIENT&&SECRET&&REDIRECT&&KEY);
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const enc=new TextEncoder();
const b64=(v:Uint8Array)=>btoa(String.fromCharCode(...v)).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'');
function response(data:unknown,status=200){return new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff'}})}
function page(message:string,status=200){return new Response('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NegócioFácil</title><body style="font:18px Arial;background:#f5f8ff;padding:30px;color:#13304c"><h1>NegócioFácil</h1><p>'+message+'</p></body></html>',{status,headers:{'content-type':'text/html;charset=utf-8','cache-control':'no-store','referrer-policy':'no-referrer'}})}
function random(length=32){return b64(crypto.getRandomValues(new Uint8Array(length)))}
async function hash(value:string){const x=new Uint8Array(await crypto.subtle.digest('SHA-256',enc.encode(value)));return Array.from(x,v=>v.toString(16).padStart(2,'0')).join('')}
async function challenge(verifier:string){return b64(new Uint8Array(await crypto.subtle.digest('SHA-256',enc.encode(verifier))))}
async function encrypt(value:string){const bytes=Uint8Array.from(atob(KEY.replaceAll('-','+').replaceAll('_','/')+'='.repeat((4-KEY.length%4)%4)),v=>v.charCodeAt(0));if(bytes.length!==32)throw Error('Invalid encryption key');const key=await crypto.subtle.importKey('raw',bytes,'AES-GCM',false,['encrypt']);const iv=crypto.getRandomValues(new Uint8Array(12));const cipher=new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv},key,enc.encode(value)));return b64(iv)+'.'+b64(cipher)}
async function db(table:string, method='GET', filter='', body?:unknown, prefer='return=representation'){
 if(!/^nf_[a-z_]+$/.test(table))throw Error('Tabela invalida');
 const url=API+'/rest/v1/'+table+(filter?'?'+filter:'');
 const res=await fetch(url,{method,headers:{apikey:SERVICE,authorization:'Bearer '+SERVICE,'content-type':'application/json',prefer},body:body===undefined?undefined:JSON.stringify(body)});
 if(!res.ok){console.error('Database',table,res.status);throw Error('Persistencia indisponivel');}
 const txt=await res.text();return txt?JSON.parse(txt):null;
}
async function caller(req:Request){
 const token=req.headers.get('authorization')||'';
 if(!/^Bearer [a-zA-Z0-9._-]{40,}$/.test(token))return null;
 const res=await fetch(API+'/auth/v1/user',{headers:{apikey:SERVICE,authorization:token}});
 if(!res.ok)return null;
 const u=await res.json();return typeof u.id==='string'&&uuid.test(u.id)?u.id:null;
}
async function owner(business:string,user:string){const filter=new URLSearchParams({select:'id',id:'eq.'+business,owner_user_id:'eq.'+user,limit:'1'}).toString();const rows=await db('nf_businesses','GET',filter);return rows.length===1}
async function getBusiness(req:Request){
 if(req.method==='POST'){const body=await req.json().catch(()=>null);return body&&typeof body.business_id==='string'&&uuid.test(body.business_id)?body.business_id:null}
 const val=new URL(req.url).searchParams.get('business_id')||'';return uuid.test(val)?val:null;
}
function configCheck(){const x=new URL(REDIRECT);if(x.protocol!=='https:'||x.username||x.password||x.search||x.hash)throw Error('Redirect deve ser HTTPS sem query ou fragment')}
async function start(req:Request){
 const user=await caller(req);if(!user)return response({error:'Login do NegócioFácil obrigatório'},401);
 const business=await getBusiness(req);if(!business)return response({error:'Empresa inválida'},400);
 if(!await owner(business,user))return response({error:'Sem permissão nesta empresa'},403);
 const state=random(32),stateHash=await hash(state),verifier=USE_PKCE?random(48):null;
 await db('nf_mp_oauth_states','POST','',{state_hash:stateHash,business_id:business,code_verifier:verifier,expires_at:new Date(Date.now()+600000).toISOString()});
 const url=new URL('https://auth.mercadopago.com/authorization');
 url.searchParams.set('client_id',CLIENT);url.searchParams.set('response_type','code');url.searchParams.set('platform_id','mp');
 url.searchParams.set('redirect_uri',REDIRECT);url.searchParams.set('state',state);
 if(verifier){url.searchParams.set('code_challenge',await challenge(verifier));url.searchParams.set('code_challenge_method','S256')}
 return response({authorization_url:url.toString(),expires_in:600});
}
async function callback(req:Request){
 const u=new URL(req.url),state=u.searchParams.get('state')||'',code=u.searchParams.get('code')||'';
 if(u.searchParams.has('error'))return page('Autorização cancelada.',400);
 if(!/^[a-zA-Z0-9_-]{35,100}$/.test(state)||!code||code.length>300)return page('Autorização inválida. Reinicie pelo aplicativo.',400);
 const stateHash=await hash(state);
 const filter=new URLSearchParams({state_hash:'eq.'+stateHash,expires_at:'gt.'+new Date().toISOString(),select:'business_id,code_verifier'}).toString();
 const rows=await db('nf_mp_oauth_states','DELETE',filter);
 if(rows.length!==1)return page('Autorização já usada ou expirada.',400);
 const payload=new URLSearchParams({grant_type:'authorization_code',client_id:CLIENT,client_secret:SECRET,code,redirect_uri:REDIRECT});
 if(rows[0].code_verifier)payload.set('code_verifier',rows[0].code_verifier);
 const res=await fetch('https://api.mercadopago.com/oauth/token',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:payload});
 if(!res.ok){console.error('OAuth exchange failed',res.status);return page('Não foi possível autorizar a conta. Tente novamente.',502)}
 const data=await res.json();if(!data.access_token||!data.user_id)return page('Dados de autorização incompletos.',502);
 await db('nf_mp_connections','POST','on_conflict=business_id',{business_id:rows[0].business_id,mp_user_id:String(data.user_id),access_token_enc:await encrypt(String(data.access_token)),refresh_token_enc:data.refresh_token?await encrypt(String(data.refresh_token)):null,expires_at:typeof data.expires_in==='number'&&data.expires_in>0?new Date(Date.now()+data.expires_in*1000).toISOString():null,updated_at:new Date().toISOString()},'resolution=merge-duplicates,return=representation');
 return page('Sua conta Mercado Pago foi conectada. Volte ao NegócioFácil para conferir.');
}
async function connection(req:Request,remove:boolean){
 const user=await caller(req);if(!user)return response({error:'Login obrigatório'},401);
 const business=await getBusiness(req);if(!business)return response({error:'Empresa inválida'},400);
 if(!await owner(business,user))return response({error:'Sem permissão'},403);
 if(remove){await db('nf_mp_connections','DELETE',new URLSearchParams({business_id:'eq.'+business}).toString());return response({disconnected:true,notice:'Revogue o acesso também no Mercado Pago.'})}
 const filter=new URLSearchParams({select:'mp_user_id,connected_at,expires_at',business_id:'eq.'+business,limit:'1'}).toString();
 const rows=await db('nf_mp_connections','GET',filter);
 return response({connected:rows.length===1,...(rows.length?{account_id:rows[0].mp_user_id,connected_at:rows[0].connected_at,requires_reconnect:!!rows[0].expires_at&&Date.parse(rows[0].expires_at)<Date.now()}: {})});
}
async function handleRequest(req:Request):Promise<Response>{
 try{
  const path=new URL(req.url).pathname;
  if(path.endsWith('/health')&&req.method==='GET')return response({service:'NegocioFacil Mercado Pago OAuth',stage:'homologacao',configured:ready,payments_enabled:false});
  if(!ready)return response({error:'OAuth ainda não configurado; pagamentos desativados'},503);
  configCheck();
  if(path.endsWith('/oauth/start')&&req.method==='POST')return await start(req);
  if(path.endsWith('/oauth/callback')&&req.method==='GET')return await callback(req);
  if(path.endsWith('/oauth/connection')&&req.method==='GET')return await connection(req,false);
  if(path.endsWith('/oauth/disconnect')&&req.method==='POST')return await connection(req,true);
  return response({error:'Rota não disponível; cobranças reais desativadas'},404);
 }catch(e){console.error('OAuth backend error',String(e));return response({error:'Falha no serviço. Tente novamente.'},500)}
}
const APP_WEB_ORIGIN = 'https://appassets.androidplatform.net';
Deno.serve(async (req:Request)=>{
 const origin=req.headers.get('origin');
 const permitted=origin===APP_WEB_ORIGIN;
 if(req.method==='OPTIONS'){
   if(!permitted)return response({error:'Origem não autorizada'},403);
   return new Response(null,{status:204,headers:{
     'access-control-allow-origin':APP_WEB_ORIGIN,
     'access-control-allow-methods':'GET,POST,OPTIONS',
     'access-control-allow-headers':'authorization,apikey,content-type,x-client-info',
     'access-control-max-age':'3600',
     'vary':'Origin',
   }});
 }
 const result=await handleRequest(req);
 if(permitted){
   result.headers.set('access-control-allow-origin',APP_WEB_ORIGIN);
   result.headers.set('vary','Origin');
 }
 return result;
});