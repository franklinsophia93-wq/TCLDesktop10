// Serviço legado desativado para evitar dois fluxos de cobrança concorrentes.
// O único backend de pagamento é nf-payments; o OAuth permanece nf-mercadopago.
// Não geramos cobranças nem aceitamos confirmações por este endpoint.
const ORIGIN='https://appassets.androidplatform.net';
Deno.serve((req:Request)=>{
 const headers=new Headers({'content-type':'application/json; charset=utf-8','cache-control':'no-store'});
 if(req.headers.get('origin')===ORIGIN){headers.set('access-control-allow-origin',ORIGIN);headers.set('vary','Origin')}
 const pathname=new URL(req.url).pathname;
 if(pathname.endsWith('/health')&&req.method==='GET')
  return new Response(JSON.stringify({service:'NegocioFacil Checkout Pro',ready:false,payments_enabled:false,deprecated:true,canonical_service:'nf-payments'}),{status:200,headers});
 if(req.method==='OPTIONS')return new Response(null,{status:204,headers});
 return new Response(JSON.stringify({error:'Endpoint desativado. Use o aplicativo atualizado conectado ao servico nf-payments.'}),{status:410,headers});
});