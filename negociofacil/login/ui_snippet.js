  // Conta ONLINE Supabase, distinta do ADM local usado nas previas dos planos.
  let cloud={authenticated:false,businesses:[]};
  const cloudBridge=()=>bridge()&&typeof bridge().cloudState==='function';
  const cloudParse=raw=>{try{return JSON.parse(raw)}catch(e){return{ok:false,message:'Resposta inválida do servidor.'}}};
  function cloudSync(){
    if(!cloudBridge())return;
    const state=cloudParse(bridge().cloudState());
    cloud=state&&typeof state.authenticated==='boolean'?state:{authenticated:false,businesses:[]};
  }
  cloudSync();
  function cloudCard(){
    const active=cloud.authenticated;
    return '<div class="card"><div class="row-between"><div><b>☁ Conta online e recebimentos</b><p class="tagline">'+
       (active?'Conectado: '+h(cloud.email||'Profissional')+' · '+(cloud.businesses||[]).length+' negócio(s)':
       'Entre com e-mail e senha para conectar seu negócio ao Mercado Pago.')+
       '</p></div><button class="btn secondary small" data-action="cloud-account">'+
       (active?'Gerenciar':'Entrar / criar')+'</button></div>'+
       '<p class="tagline">A conta online não sincroniza ainda os clientes, vendas ou agenda salvos neste aparelho.</p></div>';
  }
  function cloudModal(){
    if(!cloudBridge())return modal('Conta online','Disponível após instalar a versão Android com login Supabase.',
      '<div class="modal-footer"><button class="btn" data-action="close">Entendi</button></div>');
    if(!cloud.authenticated)return modal('Conta do profissional','Login em nuvem separado da conta ADM local.',
      '<form id="cloud-auth-form"><div class="field"><label>E-mail</label><input name="email" type="email" required autocomplete="username"></div>'+
      '<div class="field"><label>Senha (mínimo 8 caracteres)</label><input name="password" type="password" minlength="8" required autocomplete="current-password"></div>'+
      '<div class="field"><label>Operação</label><select name="operation"><option value="signin">Entrar</option><option value="signup">Criar conta</option></select></div>'+
      '<div class="modal-footer"><button class="btn secondary" type="button" data-action="close">Cancelar</button><button class="btn" type="submit">Continuar</button></div></form>');
    const businesses=(cloud.businesses||[]);
    const rows=businesses.map(b=>'<div class="card"><b>'+h(b.name)+'</b><p class="tagline">Conecte sua própria conta Mercado Pago para receber as vendas.</p>'+
      '<div class="mini-actions"><button class="btn small" data-action="cloud-connect" data-id="'+h(b.id)+'">Conectar Mercado Pago</button>'+
      '<button class="btn secondary small" data-action="cloud-status" data-id="'+h(b.id)+'">Verificar conexão</button>'+ 
      '<button class="btn secondary small" data-action="cloud-sales" data-id="'+h(b.id)+'">Cobranças online</button></div></div>').join('');
    return modal('Minha conta online',h(cloud.email||''),'<div class="stack">'+
      (businesses.length?rows:'<div class="warning">Cadastre seu primeiro negócio online.</div>')+
      '<div class="card"><b>Novo negócio</b><form id="cloud-business-form"><div class="field"><label>Nome da empresa</label>'+
      '<input name="businessName" type="text" maxlength="120" minlength="2" required></div>'+
      '<button class="btn" type="submit">Cadastrar negócio</button></form></div>'+
      '<div class="warning">As cobranças ficam no servidor. Enviar links e confirmar pagamentos somente após a homologação do Checkout Pro. Os dados locais ainda não são sincronizados.</div>'+
      '<div class="modal-footer"><button class="btn danger" data-action="cloud-logout">Sair da conta</button><button class="btn secondary" data-action="close">Fechar</button></div></div>');
  }

  let cloudSelectedBusiness='';
  function cloudPayments(businessId){
    cloudSelectedBusiness=businessId;
    const parsed=cloudParse(bridge().cloudSales(businessId));
    if(!parsed.ok)return notice(parsed.message||'Não foi possível consultar as vendas online.');
    const html=(parsed.sales||[]).map(x=>{
      const amount='R$ '+(Number(x.amount_cents)/100).toFixed(2).replace('.',',');
      const status=x.status==='paid'?'Pago':x.status==='refunded'?'Estornado':
         x.status==='charged_back'?'Contestado':'Aguardando';
      const canPay=x.status==='pending';
      return '<div class="list-row"><div class="list-main"><b>'+h(x.description)+'</b><small>'+amount+' • '+status+'</small></div>'+
         (canPay?'<button class="btn small" data-action="cloud-charge" data-id="'+h(x.id)+'">Cobrar</button>':'')+
         '</div>';
    }).join('');
    modal('Cobranças online','Essas vendas são cadastradas no servidor, não importadas das vendas locais.',
      '<div class="stack"><div class="warning">Pix e cartão são processados no Mercado Pago. A venda só é paga após confirmação do provedor. O checkout pode estar indisponível durante a homologação.</div>'+
      '<button class="btn" data-action="cloud-new-sale">+ Nova venda online</button>'+
      (html||'<p>Nenhuma cobrança online cadastrada.</p>')+
      '<div class="modal-footer"><button class="btn secondary" data-action="cloud-account">Voltar</button></div></div>');
  }
  function cloudNewSale(){
    modal('Nova venda online','O cliente pagará na própria conta Mercado Pago do profissional.',
      '<form id="cloud-sale-form"><div class="field"><label>Descrição</label><input name="description" maxlength="120" minlength="2" required></div>'+
      '<div class="field"><label>Valor (R$)</label><input name="amount" inputmode="decimal" placeholder="25,90" required></div>'+
      '<div class="modal-footer"><button type="button" class="btn secondary" data-action="cloud-sales" data-id="'+h(cloudSelectedBusiness)+'">Voltar</button><button class="btn" type="submit">Registrar venda</button></div></form>');
  }
  function cloudSubmit(event){
    event.preventDefault();
    if(!cloudBridge())return;
    const f=event.target,values=Object.fromEntries(new FormData(f));
    if(f.id==='cloud-sale-form'){
      const r=cloudParse(bridge().cloudNewSale(cloudSelectedBusiness,values.description||'',values.amount||''));
      if(!r.ok)return notice(r.message||'Não foi possível registrar a venda online.');
      close();cloudPayments(cloudSelectedBusiness);
      notice('Venda registrada. Gere o link de pagamento somente quando o servidor estiver homologado.');
      return;
    }
    const isBusiness=f.id==='cloud-business-form';
    const result=isBusiness?cloudParse(bridge().cloudAddBusiness(values.businessName||'')):
      cloudParse(values.operation==='signup'?bridge().cloudSignup(values.email||'',values.password||''):
      bridge().cloudSignin(values.email||'',values.password||''));
    f.querySelectorAll('input[type=password]').forEach(e=>e.value='');
    if(!result.ok)return notice(result.message||'Não foi possível completar a operação.');
    cloudSync();close();render();cloudModal();notice(result.message||'Concluído.');
  }
  function cloudAction(action,businessId){
    if(!cloudBridge())return notice('É necessário instalar o aplicativo Android.');
    if(action==='cloud-sales')return cloudPayments(businessId);
    if(action==='cloud-new-sale')return cloudNewSale();
    if(action==='cloud-charge'){
      if(!cloudSelectedBusiness)return notice('Escolha um negócio.');
      const r=cloudParse(bridge().cloudCheckout(cloudSelectedBusiness,businessId));
      if(!r.ok)return notice(r.message||'Checkout ainda não disponível.');
      const link=String(r.checkout_url||'');
      if(!/^https:\/\/([a-z0-9.-]+\.)?mercadopago\.com(\.br)?\//i.test(link))
        return notice('Endereço de cobrança inesperado.');
      bridge().shareText('Cobrança NegócioFácil',link);
      return notice('Escolha o aplicativo para enviar o link ao cliente.');
    }
    if(action==='cloud-logout'){
      const r=cloudParse(bridge().cloudSignout());cloudSync();close();render();notice(r.message||'Conta encerrada.');return;
    }
    if(action==='cloud-connect'){
      const r=cloudParse(bridge().cloudConnectMP(businessId));
      if(!r.ok)return notice(r.message||'Não foi possível conectar.');
      const url=String(r.authorization_url||'');
      if(!url.startsWith('https://auth.mercadopago.com/authorization?'))return notice('Endereço de autorização inválido.');
      bridge().openMercadoPagoOAuth(url);
      notice('Autorize sua conta no navegador. Depois retorne e verifique a conexão.');return;
    }
    if(action==='cloud-status'){
      const r=cloudParse(bridge().cloudMPStatus(businessId));
      if(!r.ok)return notice(r.message||'Não foi possível verificar.');
      return notice(r.connected?'Conta Mercado Pago conectada!':'Mercado Pago ainda não conectado.');
    }
  }
