/* NegócioFácil: Conta Online (homologação, sem cobranças).
   Supabase publishable key é pública. Tokens MP nunca passam pelo navegador.
   Os cadastros do aplicativo atual permanecem SOMENTE neste dispositivo. */
(()=>{'use strict';
const ORIGIN='https://tlqcpfmkneohjleiynqe.supabase.co';
const KEY='sb_publishable_mIK3OolINa099sL6T-PLlw_pee4klHr';
const CLOUD_KEY='negociofacil.cloud.session.v1';
const UUID=/^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i;
const els=()=>document.getElementById('nf-cloud-overlay');
let session=null,user=null,business=null,connected=false,busy=false;
try{const stored=JSON.parse(localStorage.getItem(CLOUD_KEY)||'null');if(stored&&stored.access_token&&stored.refresh_token)session=stored;}catch(_){}
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const notice=(msg)=>{const el=document.getElementById('nf-cloud-msg');if(el){el.textContent=msg;el.hidden=false;}else window.alert(msg)};
const headers=(signed=false)=>({apikey:KEY, ...(signed&&session?{Authorization:'Bearer '+session.access_token}:{})});
function saveSession(s){session={access_token:s.access_token,refresh_token:s.refresh_token,expires_at:Math.floor(Date.now()/1000)+Number(s.expires_in||3600)};localStorage.setItem(CLOUD_KEY,JSON.stringify(session));}
function clearSession(){localStorage.removeItem(CLOUD_KEY);session=null;user=null;business=null;connected=false;}
async function api(path,{method='GET',body,auth=false,accept='application/json'}={}){
 const h={...headers(auth),Accept:accept};if(body!==undefined)h['Content-Type']='application/json';
 const response=await fetch(ORIGIN+path,{method,headers:h,body:body===undefined?undefined:JSON.stringify(body),cache:'no-store'});
 const data=await response.json().catch(()=>({}));
 if(!response.ok)throw new Error((data.error_description||data.message||data.msg||data.error||'Serviço indisponível').toString().slice(0,180));
 return data;
}
async function ensureSession(){
 if(!session)return false;
 if(session.expires_at>Date.now()/1000+90)return true;
 try{const s=await api('/auth/v1/token?grant_type=refresh_token',{method:'POST',body:{refresh_token:session.refresh_token}});
  if(!s.access_token)throw Error('Sessão expirada');saveSession(s);return true;
 }catch(_){clearSession();return false;}
}
async function load(){
 if(!await ensureSession())return false;
 try{
  user=await api('/auth/v1/user',{auth:true});
  if(!UUID.test(user.id))throw Error('Usuário inválido');
  const filter=new URLSearchParams({select:'id,name',owner_user_id:'eq.'+user.id,limit:'1'}).toString();
  const b=await api('/rest/v1/nf_businesses?'+filter,{auth:true});
  business=Array.isArray(b)&&b.length?b[0]:null;connected=false;
  if(business)await getConnection();
  return true;
 }catch(err){clearSession();return false;}
}
async function getConnection(){
 if(!business)return;
 const filter=new URLSearchParams({business_id:business.id}).toString();
 const x=await api('/functions/v1/nf-mercadopago/oauth/connection?'+filter,{auth:true});
 connected=!!x.connected;
 return x;
}
function addEntry(){
 const top=document.querySelector('.top-actions');
 if(top&&!top.querySelector('[data-nf-cloud]')){
  const btn=document.createElement('button');
  btn.type='button';btn.className='circle-icon nf-cloud-entry';btn.setAttribute('aria-label','Conta online e Mercado Pago');btn.setAttribute('data-nf-cloud','open');btn.textContent='☁';
  top.appendChild(btn);
 }
}
const domObserver=new MutationObserver(addEntry);
const app=document.getElementById('app');if(app){domObserver.observe(app,{childList:true,subtree:true});addEntry();}
function showLogin(register=false){
 renderPanel('<h2>Conta Online</h2><p class="nf-cloud-sub">Use um e-mail e senha para vincular seu negócio ao servidor. O ADM local continua apenas para prévias.</p>'+
 '<form id="nf-cloud-login-form" data-register="'+(register?'1':'0')+'">'+
 '<label>E-mail<input name="email" type="email" autocomplete="email" inputmode="email" required maxlength="254"></label>'+
 '<label>Senha<input name="password" type="password" autocomplete="'+(register?'new-password':'current-password')+'" required minlength="8" maxlength="128"></label>'+
 '<button class="btn" type="submit">'+(register?'Criar conta':'Entrar')+'</button></form>'+
 '<button type="button" class="btn secondary nf-secondary" data-nf-cloud="'+(register?'switch-login':'switch-register')+'">'+(register?'Já tenho conta':'Criar uma conta')+'</button>'+
 '<p class="nf-cloud-note">Pode ser necessário confirmar o e-mail. Seus clientes e vendas atuais continuam armazenados neste celular e não são enviados automaticamente.</p>');
}
function showBusiness(){
 renderPanel('<h2>Meu negócio na nuvem</h2><p class="nf-cloud-sub">Conta autenticada: '+esc(user?.email||'')+'</p>'+
 '<p>Cadastre a empresa que ficará associada à sua própria conta Mercado Pago.</p>'+
 '<form id="nf-cloud-business-form"><label>Nome da empresa<input type="text" name="name" required maxlength="120" placeholder="Nome do meu negócio"></label>'+
 '<button type="submit" class="btn">Cadastrar negócio</button></form>'+
 '<button type="button" class="btn secondary nf-secondary" data-nf-cloud="logout">Sair da conta</button>');
}
function showDashboard(){
 const status=connected?'<b class="nf-online-ok">Conectado</b>':'<b class="nf-online-pending">Não conectado</b>';
 renderPanel('<h2>Conta Online</h2><p class="nf-cloud-sub">'+esc(user?.email||'')+'</p>'+
 '<div class="nf-cloud-panel"><b>'+esc(business?.name||'Empresa')+'</b><p>Mercado Pago: '+status+'</p>'+
 '<p class="nf-cloud-note">Cada profissional conecta e recebe na própria conta. Nenhuma comissão para o NegócioFácil.</p></div>'+
 (!connected?'<button type="button" class="btn" data-nf-cloud="connect">Conectar Mercado Pago</button>':
 '<button type="button" class="btn secondary" data-nf-cloud="disconnect">Desconectar Mercado Pago</button>')+
 '<button type="button" class="btn secondary nf-secondary" data-nf-cloud="refresh">Atualizar situação da conexão</button>'+
 '<button type="button" class="btn secondary nf-secondary" data-nf-cloud="logout">Sair da conta</button>'+
 '<p class="nf-cloud-note">O Mercado Pago pode abrir no navegador. Ao autorizar, volte ao NegócioFácil e toque em Atualizar. Nenhuma cobrança real está habilitada.</p>');
}
function renderPanel(content){
 let root=els();if(!root){root=document.createElement('div');root.id='nf-cloud-overlay';document.body.appendChild(root);}
 root.innerHTML='<div class="nf-cloud-shade"><section class="nf-cloud-panel-frame" role="dialog" aria-modal="true" aria-label="Conta Online">'+
 '<div class="nf-cloud-head"><b>NegócioFácil</b><button type="button" class="nf-cloud-close" data-nf-cloud="close" aria-label="Fechar">×</button></div>'+
 '<div id="nf-cloud-msg" class="nf-cloud-error" hidden></div>'+content+'</section></div>';
}
async function open(){
 if(busy)return;
 renderPanel('<h2>Conta Online</h2><p>Verificando sua sessão...</p>');
 try{const ok=await load();if(ok){if(business)showDashboard();else showBusiness();}else showLogin();}
 catch(_){showLogin();}
}
async function authenticate(form){
 if(busy)return;busy=true;const btn=form.querySelector('button[type=submit]');btn.disabled=true;
 const email=form.elements.namedItem('email').value.trim().toLowerCase(),password=form.elements.namedItem('password').value;
 try{
  const registering=form.dataset.register==='1';
  const result=await api(registering?'/auth/v1/signup':'/auth/v1/token?grant_type=password',{method:'POST',body:{email,password}});
  form.elements.namedItem('password').value='';
  if(result.access_token){saveSession(result);await open();return;}
  if(registering){showLogin(false);notice('Cadastro solicitado. Confirme o e-mail recebido antes de entrar.');}
  else notice('Login não confirmado. Verifique seu e-mail e sua senha.');
 }catch(e){form.elements.namedItem('password').value='';notice('Não foi possível entrar: '+e.message);}
 finally{busy=false;if(btn.isConnected)btn.disabled=false;}
}
async function createBusiness(form){
 if(busy)return;busy=true;const btn=form.querySelector('button[type=submit]');btn.disabled=true;
 try{
  if(!await ensureSession()||!user)throw Error('Faça login novamente.');
  const name=form.elements.namedItem('name').value.trim();
  if(name.length<1||name.length>120)throw Error('Nome inválido');
  const rows=await api('/rest/v1/nf_businesses',{method:'POST',auth:true,accept:'application/json',body:{owner_user_id:user.id,name}});
  // Supabase PostgREST uses minimal return unless Prefer header is provided.
  await load();if(!business)throw Error('Cadastro não confirmado. Atualize a conta.');
  showDashboard();
 }catch(e){notice('Cadastro não concluído: '+e.message)}
 finally{busy=false;if(btn.isConnected)btn.disabled=false;}
}
async function connect(){
 if(busy||!business)return;busy=true;
 try{
  if(!await ensureSession())throw Error('Sessão expirada. Entre novamente.');
  const result=await api('/functions/v1/nf-mercadopago/oauth/start',{method:'POST',body:{business_id:business.id},auth:true});
  const u=new URL(result.authorization_url);
  if(u.protocol!=='https:'||u.hostname!=='auth.mercadopago.com'||u.pathname!=='/authorization')throw Error('URL de autorização inesperada');
  if(window.AndroidBridge?.openMercadoPagoOAuth)window.AndroidBridge.openMercadoPagoOAuth(u.toString());
  else window.open(u.toString(),'_blank','noopener,noreferrer');
  notice('Autorize no navegador e volte aqui para atualizar.');
 }catch(e){notice('Autorização não iniciada: '+e.message)}
 finally{busy=false;}
}
async function refresh(){
 if(busy)return;busy=true;
 try{if(!await ensureSession())throw Error('Sessão expirada. Faça login.');await getConnection();showDashboard();}
 catch(e){notice('Não foi possível consultar: '+e.message)}
 finally{busy=false;}
}
async function disconnect(){
 if(!business||!confirm('Desconectar a conta Mercado Pago deste negócio?'))return;
 try{if(!await ensureSession())throw Error('Faça login novamente.');await api('/functions/v1/nf-mercadopago/oauth/disconnect',{method:'POST',body:{business_id:business.id},auth:true});connected=false;showDashboard();notice('Conta desconectada. Revogue também no Mercado Pago.')}
 catch(e){notice('Falha: '+e.message)}
}
document.addEventListener('click',event=>{
 const btn=event.target.closest('[data-nf-cloud]');if(!btn)return;event.preventDefault();
 switch(btn.dataset.nfCloud){
 case 'open':void open();break;case 'close':els()?.remove();break;
 case 'switch-register':showLogin(true);break;case 'switch-login':showLogin(false);break;
 case 'logout':clearSession();showLogin();break;
 case 'connect':void connect();break;case 'refresh':void refresh();break;
 case 'disconnect':void disconnect();break;
 }
});
document.addEventListener('submit',event=>{
 if(event.target.id==='nf-cloud-login-form'){event.preventDefault();void authenticate(event.target);}
 if(event.target.id==='nf-cloud-business-form'){event.preventDefault();void createBusiness(event.target);}
});
window.NegocioFacilCloudStatus=()=>({signedIn:!!user,businessId:business?.id||null,connected,stage:'homologacao'});
})();