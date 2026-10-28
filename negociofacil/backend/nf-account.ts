// NegócioFácil: onboarding de empresas. Não processa pagamentos, nem recebe credenciais privadas.
const API = Deno.env.get("SUPABASE_URL") || "";
const SERVICE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
function json(value: unknown, status = 200) {
 return new Response(JSON.stringify(value), {status, headers: {"content-type":"application/json; charset=utf-8","cache-control":"no-store","x-content-type-options":"nosniff"}});
}
async function caller(req: Request): Promise<string|null> {
 const auth = req.headers.get("authorization") || "";
 if(!/^Bearer [a-zA-Z0-9._-]{40,}$/.test(auth)) return null;
 const res = await fetch(API + "/auth/v1/user", {headers:{apikey: SERVICE,authorization:auth}});
 if(!res.ok) return null;
 const profile = await res.json();
 return typeof profile.id === "string" && UUID.test(profile.id) ? profile.id : null;
}
async function businessRequest(method: string, path: string, body?: unknown) {
 const result = await fetch(API+"/rest/v1/nf_businesses"+path, {
  method,
  headers: {apikey:SERVICE, authorization:"Bearer "+SERVICE, "content-type":"application/json",prefer:"return=representation"},
  body: body === undefined ? undefined : JSON.stringify(body)
 });
 const raw=await result.text();
 if(!result.ok) {console.error("nf_businesses db error",result.status); return {ok:false,status:result.status};}
 return {ok:true,status:result.status,rows:raw?JSON.parse(raw):[]};
}
Deno.serve(async (req:Request)=>{
 const url=new URL(req.url);
 if(req.method==="GET" && url.pathname.endsWith("/health")) return json({service:"NegocioFacil accounts",status:"online",payments_enabled:false});
 if(!API||!SERVICE) return json({error:"Serviço ainda indisponível"},503);
 if(!url.pathname.endsWith("/businesses")) return json({error:"Não encontrado"},404);
 if(req.method!=="GET" && req.method!=="POST") return json({error:"Método não permitido"},405);
 try {
  const userId=await caller(req);
  if(!userId) return json({error:"Faça login para gerenciar seu negócio"},401);
  const filter="?owner_user_id=eq."+encodeURIComponent(userId)+"&select=id,name,created_at&order=created_at.asc&limit=10";
  if(req.method==="GET") {
    const r=await businessRequest("GET",filter);
    return r.ok?json({businesses:r.rows}):json({error:"Falha ao consultar empresa"},503);
  }
  const body=await req.json().catch(()=>null);
  const name=typeof body?.name==="string"?body.name.trim():"";
  if(name.length<2||name.length>120) return json({error:"Informe nome do negócio de 2 a 120 caracteres"},400);
  // Primeira versão: um negócio por login. Futuras equipes exigirão autorização distinta.
  const existing=await businessRequest("GET",filter);
  if(!existing.ok) return json({error:"Falha ao consultar empresa"},503);
  if(existing.rows.length) return json({error:"Esta conta já tem uma empresa",business:existing.rows[0]},409);
  const created=await businessRequest("POST","",{owner_user_id:userId,name});
  if(!created.ok) return json({error:"Não foi possível cadastrar empresa"},503);
  return json({business:{id:created.rows[0].id,name:created.rows[0].name}},201);
 }catch(e) {
  console.error("nf-account error",String(e));
  return json({error:"Serviço indisponível. Tente novamente."},500);
 }
});
