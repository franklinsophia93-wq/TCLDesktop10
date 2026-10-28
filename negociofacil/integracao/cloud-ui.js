  // Conta profissional remota: NAO confundir com o ADM local de testes.
  let cloud = {authenticated:false,hasBusiness:false,name:'',connected:false,account:'',status:''};
  function cloudBridge(){return bridge() && typeof bridge().cloudLogin==='function'}
  function cloudPage(){
    const status=cloud.status?'<div class="warning" role="status">'+h(cloud.status)+'</div>':'';
    if(!cloudBridge()) return heading('Meus recebimentos','Acesso pelo aplicativo Android')+'<div class="warning">Instale a versão Android com login financeiro integrado.</div>';
    if(!cloud.authenticated) return heading('Conta e recebimentos','Login seguro do profissional')+status+
      '<div class="card"><b>Entre ou crie uma conta</b><p class="tagline">Login de profissional separado do administrador de testes. Necessário para conectar a conta Mercado Pago.</p>'+
      '<form id="nf-cloud-login">'+field('Seu e-mail','email','email')+field('Senha (mínimo 8 caracteres)','password','password')+
      '<div class="mini-actions"><button class="btn" type="submit" name="intent" value="login">Entrar</button><button class="btn secondary" type="submit" name="intent" value="register">Criar conta</button></div></form></div>'+
      '<div class="warning">A conta é verificada pelo Supabase. Nesta homologação, o login não substitui os dados locais do aparelho e a sessão encerra ao fechar o aplicativo.</div>';
    if(!cloud.hasBusiness) return heading('Meu negócio','Cadastre sua empresa no servidor')+status+
      '<div class="card"><b>Login confirmado</b><p class="tagline">Informe seu negócio antes de conectar os recebimentos.</p><form id="nf-cloud-business">'+field('Nome do negócio','name','text',data.business.name)+
      '<button class="btn" type="submit">Cadastrar negócio</button></form><button class="btn outline" data-action="nf-cloud-logout">Sair</button></div>';
    return heading('Meus recebimentos','Conta Mercado Pago individual')+status+
      '<div class="stack"><div class="card"><b>Empresa: '+h(cloud.name)+'</b><p class="tagline">Apenas seu login pode gerenciar esta empresa.</p></div>'+
      '<div class="card"><b>Mercado Pago: '+(cloud.connected?'Conectado':'Não conectado')+'</b>'+
      (cloud.connected?'<p class="tagline">Conta autorizada: '+h(cloud.account)+'</p>':'<p class="tagline">Autorize seu próprio Mercado Pago. A plataforma não receberá comissão sobre suas vendas.</p>')+
      '<div class="mini-actions">'+(!cloud.connected?'<button class="btn" data-action="nf-cloud-connect">Conectar Mercado Pago</button>':'')+
      '<button class="btn secondary" data-action="nf-cloud-refresh">Atualizar conexão</button></div></div>'+
      '<div class="warning"><b>Pagamentos reais indisponíveis.</b> Ainda não há checkout e confirmação automática homologados. A conexão da conta não cria cobranças.</div>'+
      '<button class="btn outline" data-action="nf-cloud-logout">Sair da conta</button></div>';
  }
  window.NegocioFacilCloudEvent=function(raw){
    let event;
    try{event=JSON.parse(raw)}catch(e){return}
    if(!event||typeof event.type!=='string')return;
    if(event.type==='authenticated'){cloud.authenticated=true;cloud.status=event.message||'Login realizado.'}
    if(event.type==='business'){cloud.authenticated=true;cloud.hasBusiness=true;cloud.name=event.name||'Meu negócio';cloud.status='Empresa vinculada ao login.'}
    if(event.type==='no_business'){cloud.authenticated=true;cloud.hasBusiness=false;cloud.connected=false;cloud.status=event.message||'Cadastre sua empresa.'}
    if(event.type==='connection'){cloud.connected=!!event.connected;cloud.account=event.account||'';cloud.status=cloud.connected?'Mercado Pago conectado.':'Mercado Pago ainda não conectado.'}
    if(event.type==='logout'){cloud={authenticated:false,hasBusiness:false,name:'',connected:false,account:'',status:'Sessão encerrada.'}}
    if(event.type==='registered'||event.type==='error'||event.type==='info'){cloud.status=event.message||''}
    if(tab==='cloud')render(); else if(event.type==='error'||event.type==='registered')notice(cloud.status);
  };
