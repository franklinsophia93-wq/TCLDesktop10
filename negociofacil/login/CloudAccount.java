package br.com.negociofacil.app;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import android.webkit.JavascriptInterface;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.util.Locale;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * Autenticacao REAL de profissionais, separada do ADM local de demonstracao.
 * Os tokens OAuth de vendedores ficam exclusivamente no servidor Supabase;
 * a sessao Supabase do profissional e cifrada pelo Android Keystore neste aparelho.
 * Nenhum segredo de Mercado Pago e incluido no APK.
 */
public final class CloudAccount {
    private static final String BASE = "https://tlqcpfmkneohjleiynqe.supabase.co";
    // Uma chave PUBLICAVEL, nao e credencial administrativa.
    private static final String API_KEY = "sb_publishable_mIK3OolINa099sL6T-PLlw_pee4klHr";
    private static final String KEY_ALIAS = "negociofacil.cloud-session.aes.v1";
    private static final String PREFS = "negociofacil.cloud-secure.v1";
    private final Context context;
    private final Object sessionLock = new Object();

    CloudAccount(Context context) { this.context = context.getApplicationContext(); }

    private JSONObject ok(String message) throws Exception {
        return new JSONObject().put("ok", true).put("message", message);
    }
    private String fail(String text) {
        try { return new JSONObject().put("ok",false).put("message",text).toString(); }
        catch(Exception ignored) { return "{\"ok\":false}"; }
    }
    private JSONObject read(String path, String method, JSONObject body, String token) throws Exception {
        HttpURLConnection conn = (HttpURLConnection)new URL(BASE + path).openConnection();
        conn.setConnectTimeout(12000);
        conn.setReadTimeout(12000);
        conn.setUseCaches(false);
        conn.setRequestMethod(method);
        conn.setRequestProperty("apikey", API_KEY);
        conn.setRequestProperty("Accept", "application/json");
        if (token != null) conn.setRequestProperty("Authorization", "Bearer "+token);
        if (body != null) {
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
            try (OutputStream out = conn.getOutputStream()) {
                out.write(body.toString().getBytes(StandardCharsets.UTF_8));
            }
        }
        int status = conn.getResponseCode();
        try (InputStream in = status >= 400 ? conn.getErrorStream() : conn.getInputStream()) {
            byte[] response = new byte[0];
            if (in != null) {
                ByteArrayOutputStream b = new ByteArrayOutputStream();
                byte[] buffer = new byte[4096];
                int n;
                while ((n = in.read(buffer)) != -1) {
                    if (b.size()+n > 180000) throw new Exception("Resposta muito grande");
                    b.write(buffer,0,n);
                }
                response = b.toByteArray();
            }
            String text = new String(response, StandardCharsets.UTF_8);
            if (status >= 400) {
                // Nao mostrar respostas do provedor com possiveis dados pessoais.
                if(status==400||status==401||status==422)throw new AuthError("Dados incorretos ou autorizacao invalida.");
                if(status==429)throw new AuthError("Muitas tentativas. Tente novamente depois.");
                throw new AuthError("Servico indisponivel (HTTP "+status+").");
            }
            if (text.startsWith("["))return new JSONObject().put("rows",new JSONArray(text));
            return text.isEmpty() ? new JSONObject() : new JSONObject(text);
        } finally { conn.disconnect(); }
    }
    private static final class AuthError extends Exception {
        AuthError(String message) { super(message); }
    }
    private SecretKey androidKey() throws Exception {
        KeyStore store=KeyStore.getInstance("AndroidKeyStore");
        store.load(null);
        if(!store.containsAlias(KEY_ALIAS)){
            KeyGenerator keygen=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
            keygen.init(new KeyGenParameterSpec.Builder(KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256).build());
            keygen.generateKey();
        }
        return (SecretKey)store.getKey(KEY_ALIAS,null);
    }
    private SharedPreferences prefs(){return context.getSharedPreferences(PREFS,Context.MODE_PRIVATE);}
    private void persist(JSONObject session) throws Exception {
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE,androidKey());
        byte[] payload=cipher.doFinal(session.toString().getBytes(StandardCharsets.UTF_8));
        byte[] iv=cipher.getIV();
        String value=Base64.encodeToString(iv,Base64.NO_WRAP)+"."+Base64.encodeToString(payload,Base64.NO_WRAP);
        if(!prefs().edit().putString("session",value).commit())
            throw new AuthError("Nao foi possivel guardar a sessao no celular.");
    }
    private JSONObject load() {
        String value=prefs().getString("session","");
        if(value.isEmpty())return null;
        try{
            String[] parts=value.split("\\.",2);
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE,androidKey(),
                new GCMParameterSpec(128,Base64.decode(parts[0],Base64.NO_WRAP)));
            byte[] bytes=cipher.doFinal(Base64.decode(parts[1],Base64.NO_WRAP));
            return new JSONObject(new String(bytes,StandardCharsets.UTF_8));
        }catch(Exception ignored){prefs().edit().remove("session").apply();return null;}
    }
    private void clear(){prefs().edit().remove("session").commit();}
    private void saveTokens(JSONObject result,JSONObject previous) throws Exception {
        String access=result.optString("access_token","");
        String refresh=result.optString("refresh_token","");
        if(access.isEmpty()||refresh.isEmpty())throw new AuthError("Sessao incompleta.");
        JSONObject u=result.optJSONObject("user");
        String userId=u!=null?u.optString("id",""):previous==null?"":previous.optString("user_id","");
        String email=u!=null?u.optString("email",""):previous==null?"":previous.optString("email","");
        if(userId.isEmpty())throw new AuthError("Conta nao identificada.");
        int expiry=Math.max(60,result.optInt("expires_in",3600));
        persist(new JSONObject()
            .put("access",access).put("refresh",refresh)
            .put("expires",System.currentTimeMillis()+expiry*1000L)
            .put("user_id",userId).put("email",email));
    }
    private JSONObject session() throws Exception {
        JSONObject s=load();if(s==null)return null;
        if(s.optLong("expires",0)>System.currentTimeMillis()+60000)return s;
        String refresh=s.optString("refresh","");
        if(refresh.isEmpty()){clear();return null;}
        try{
            JSONObject next=read("/auth/v1/token?grant_type=refresh_token","POST",
                new JSONObject().put("refresh_token",refresh),null);
            saveTokens(next,s);
            return load();
        }catch(Exception ex){clear();return null;}
    }
    private String error(Exception e) {
        return fail(e instanceof AuthError ? e.getMessage() : "Nao foi possivel conectar. Confira a internet.");
    }

    @JavascriptInterface public String signup(String email,String password) {
        synchronized(sessionLock){
            try {
                if(!isEmail(email)||!validPassword(password))return fail("Informe e-mail valido e senha de 8 a 128 caracteres.");
                JSONObject out=read("/auth/v1/signup","POST",
                    new JSONObject().put("email",email.trim().toLowerCase(Locale.ROOT)).put("password",password),null);
                if(!out.optString("access_token","").isEmpty()){
                    saveTokens(out,null);
                    return ok("Conta criada e autenticada.").toString();
                }
                return ok("Conta criada. Confirme o e-mail recebido e depois entre.").put("needs_confirmation",true).toString();
            }catch(Exception e){return error(e);}
        }
    }
    @JavascriptInterface public String signin(String email,String password){
        synchronized(sessionLock){
            try{
                if(!isEmail(email)||password==null)return fail("Informe e-mail e senha.");
                JSONObject res=read("/auth/v1/token?grant_type=password","POST",
                    new JSONObject().put("email",email.trim().toLowerCase(Locale.ROOT)).put("password",password),null);
                saveTokens(res,null);
                return ok("Login realizado.").toString();
            }catch(Exception e){return error(e);}
        }
    }
    @JavascriptInterface public String signout(){
        synchronized(sessionLock){
            try{
                JSONObject s=load();
                if(s!=null){
                    try{read("/auth/v1/logout","POST",null,s.optString("access"));}catch(Exception ignored){}
                }
                clear();return ok("Voce saiu da conta online.").toString();
            }catch(Exception e){clear();return "{\"ok\":true,\"message\":\"Sessao encerrada no aparelho.\"}";}
        }
    }
    private boolean isEmail(String email) {
        if(email==null||email.length()>254||email.length()<6)return false;
        String e=email.trim();
        int at=e.indexOf('@'),dot=e.lastIndexOf('.');
        return at>0&&dot>at+1&&dot<e.length()-1&&!e.contains(" ")&&!e.contains("\n");
    }
    private boolean validPassword(String pass) {return pass!=null&&pass.length()>=8&&pass.length()<=128;}
    private JSONArray businesses(String token) throws Exception{
        return read("/rest/v1/nf_businesses?select=id,name,created_at&order=created_at.asc",
                    "GET",null,token).getJSONArray("rows");
    }
    @JavascriptInterface public String state() {
        synchronized(sessionLock){
            try{
                JSONObject s=session();
                if(s==null)return new JSONObject().put("authenticated",false).toString();
                JSONArray rows=businesses(s.getString("access"));
                return new JSONObject().put("authenticated",true)
                    .put("email",s.optString("email",""))
                    .put("businesses",rows).toString();
            }catch(Exception e){return "{\"authenticated\":false}";}
        }
    }
    @JavascriptInterface public String addBusiness(String name) {
        synchronized(sessionLock){
            try{
                JSONObject s=session();if(s==null)return fail("Entre na sua conta online primeiro.");
                if(name==null||name.trim().length()<2||name.trim().length()>120)return fail("Digite o nome do negocio (2 a 120 caracteres).");
                JSONObject business=new JSONObject().put("name",name.trim()).put("owner_user_id",s.getString("user_id"));
                read("/rest/v1/nf_businesses","POST",business,s.getString("access"));
                return ok("Negocio cadastrado na sua conta online.").toString();
            }catch(Exception e){return error(e);}
        }
    }
    private boolean allowedBusiness(String businessId,String token) throws Exception{
        if(businessId==null||!businessId.matches("^[0-9a-fA-F-]{36}$"))return false;
        JSONArray rows=businesses(token);
        for(int i=0;i<rows.length();i++)if(businessId.equals(rows.getJSONObject(i).optString("id")))return true;
        return false;
    }
    @JavascriptInterface public String connectMercadoPago(String businessId){
        synchronized(sessionLock){
            try{
                JSONObject s=session();if(s==null)return fail("Entre na conta online primeiro.");
                String token=s.getString("access");
                if(!allowedBusiness(businessId,token))return fail("Esse negocio nao pertence a sua conta.");
                JSONObject auth=read("/functions/v1/nf-mercadopago/oauth/start","POST",
                    new JSONObject().put("business_id",businessId),token);
                String url=auth.optString("authorization_url","");
                if(!url.startsWith("https://auth.mercadopago.com/authorization?"))
                    return fail("O servidor nao devolveu um endereco oficial valido.");
                return ok("Abra a autorizacao no navegador.")
                    .put("authorization_url",url).toString();
            }catch(Exception e){return error(e);}
        }
    }

    /** Vendas ONLINE do negocio autenticado (separadas dos dados locais antigos). */
    @JavascriptInterface public String cloudSales(String businessId) {
        synchronized(sessionLock) {
            try {
                JSONObject current=session();
                if(current==null)return fail("Entre na conta online.");
                String token=current.getString("access");
                if(!allowedBusiness(businessId,token))return fail("Negocio nao autorizado.");
                JSONObject result=read("/functions/v1/nf-payments/sales?business_id="+businessId,
                   "GET",null,token);
                return result.put("ok",true).toString();
            }catch(Exception e){return error(e);}
        }
    }
    @JavascriptInterface public String cloudNewSale(String businessId,String description,String amount) {
        synchronized(sessionLock) {
            try {
                JSONObject current=session();
                if(current==null)return fail("Entre na conta online.");
                String token=current.getString("access");
                if(!allowedBusiness(businessId,token))return fail("Negocio nao autorizado.");
                if(description==null||description.trim().length()<2||description.trim().length()>120)
                    return fail("Informe uma descricao entre 2 e 120 caracteres.");
                if(amount==null||!amount.matches("^[0-9]{1,7}([.,][0-9]{1,2})?$"))
                    return fail("Informe um valor valido em reais.");
                java.math.BigDecimal value=new java.math.BigDecimal(amount.replace(',','.'));
                long cents=value.movePointRight(2).longValueExact();
                if(cents<100||cents>100000000)return fail("Valor permitido: R$ 1,00 a R$ 1.000.000,00.");
                JSONObject req=new JSONObject().put("business_id",businessId)
                    .put("description",description.trim()).put("amount_cents",cents);
                JSONObject result=read("/functions/v1/nf-payments/sales","POST",req,token);
                return result.put("ok",true).toString();
            }catch(Exception e){return error(e);}
        }
    }
    @JavascriptInterface public String cloudCheckout(String businessId,String saleId) {
        synchronized(sessionLock) {
            try {
                JSONObject current=session();
                if(current==null)return fail("Entre na conta online.");
                String token=current.getString("access");
                if(!allowedBusiness(businessId,token))return fail("Negocio nao autorizado.");
                if(saleId==null||!saleId.matches("^[a-f0-9A-F-]{36}$"))
                    return fail("Venda invalida.");
                JSONObject req=new JSONObject().put("business_id",businessId).put("sale_id",saleId);
                JSONObject result=read("/functions/v1/nf-payments/sales/"+saleId+"/checkout","POST",req,token);
                String url=result.optString("checkout_url","");
                try {
                    java.net.URI uri=new java.net.URI(url);
                    String host=uri.getHost();
                    if(!"https".equals(uri.getScheme())||host==null||
                         !("mercadopago.com".equals(host)||host.endsWith(".mercadopago.com")||
                         "mercadopago.com.br".equals(host)||host.endsWith(".mercadopago.com.br")))
                        return fail("Endereco do checkout inesperado.");
                }catch(Exception ex){return fail("Checkout sem link valido.");}
                return result.put("ok",true).toString();
            }catch(Exception e){return error(e);}
        }
    }

    @JavascriptInterface public String mpConnection(String businessId) {
        synchronized(sessionLock){
            try{
                JSONObject s=session();if(s==null)return fail("Login necessario.");
                String token=s.getString("access");
                if(!allowedBusiness(businessId,token))return fail("Negocio nao autorizado.");
                String path="/functions/v1/nf-mercadopago/oauth/connection?business_id="+businessId;
                JSONObject result=read(path,"GET",null,token);
                return result.put("ok",true).toString();
            }catch(Exception e){return error(e);}
        }
    }
}
