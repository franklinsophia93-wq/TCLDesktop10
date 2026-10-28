package br.com.negociofacil.app;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.webkit.WebView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Login Supabase e autorização Mercado Pago em operações nativas.
 *  Acesso e senha nunca são salvos no JavaScript nem enviados ao NegócioFácil.
 *  A sessão desta primeira homologação é somente em memória.
 */
public final class NFCloudAccount {
    private static final String BASE = "https://tlqcpfmkneohjleiynqe.supabase.co";
    // Chave PUBLICÁVEL, adequada ao aplicativo cliente (nunca service_role).
    private static final String PUBLIC_KEY = "sb_publishable_mIK3OolINa099sL6T-PLlw_pee4klHr";
    private final Activity activity;
    private final WebView webView;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private volatile String accessToken;
    private volatile String businessId;

    public NFCloudAccount(Activity activity, WebView webView) {
        this.activity = activity;
        this.webView = webView;
    }

    private void message(String type, String message) {
        try {
            JSONObject envelope = new JSONObject();
            envelope.put("type", type);
            envelope.put("message", message);
            dispatch(envelope);
        } catch (Exception ignored) { }
    }
    private void dispatch(JSONObject value) {
        final String statement = "window.NegocioFacilCloudEvent && window.NegocioFacilCloudEvent("
            + JSONObject.quote(value.toString()) + ");";
        activity.runOnUiThread(() -> {
            if (!activity.isFinishing() && !activity.isDestroyed())
                webView.evaluateJavascript(statement, null);
        });
    }
    private JSONObject call(String path, String method, JSONObject body, String bearer) throws Exception {
        if (!path.startsWith("/auth/v1/") && !path.startsWith("/functions/v1/nf-account/")
                && !path.startsWith("/functions/v1/nf-mercadopago/")) throw new SecurityException("Rota não permitida");
        HttpURLConnection conn = (HttpURLConnection) new URL(BASE + path).openConnection();
        conn.setConnectTimeout(15000);
        conn.setReadTimeout(20000);
        conn.setRequestMethod(method);
        conn.setRequestProperty("Accept", "application/json");
        conn.setRequestProperty("apikey", PUBLIC_KEY);
        conn.setRequestProperty("Cache-Control", "no-store");
        if (bearer != null && !bearer.isEmpty()) conn.setRequestProperty("Authorization", "Bearer " + bearer);
        if (body != null) {
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            byte[] bytes = body.toString().getBytes(StandardCharsets.UTF_8);
            try(OutputStream out=conn.getOutputStream()) { out.write(bytes); }
        }
        int status = conn.getResponseCode();
        try(InputStream in=status < 400 ? conn.getInputStream() : conn.getErrorStream()) {
            byte[] raw = in == null ? new byte[0] : readLimited(in, 100_000);
            JSONObject result;
            try {result = new JSONObject(new String(raw, StandardCharsets.UTF_8));}
            catch (Exception e) {result=new JSONObject();}
            if(status >= 400) {
                String error = result.optString("msg", result.optString("error_description",
                    result.optString("error","Erro na conexão")));
                throw new Exception(status + ": " + error);
            }
            return result;
        } finally {conn.disconnect();}
    }
    private static byte[] readLimited(InputStream input, int max) throws Exception {
        java.io.ByteArrayOutputStream output = new java.io.ByteArrayOutputStream();
        byte[] chunk = new byte[4096];
        int size, total = 0;
        while((size=input.read(chunk))!=-1) {
            total+=size;
            if(total>max) throw new Exception("Resposta muito grande");
            output.write(chunk,0,size);
        }
        return output.toByteArray();
    }

    public void register(String email, String password) {
        executor.execute(() -> {
            try {
                if(!validCredentials(email,password)){message("error","Informe e-mail válido e senha com pelo menos 8 caracteres.");return;}
                JSONObject body=new JSONObject().put("email",email.trim()).put("password",password);
                JSONObject result=call("/auth/v1/signup","POST",body,null);
                String token=result.optString("access_token","");
                if(token.isEmpty()){message("registered","Cadastro solicitado. Confira seu e-mail para confirmar a conta antes de entrar.");return;}
                accessToken=token;
                message("authenticated","Conta criada. Consultando seu negócio…");
                loadBusinessesInternal();
            } catch(Exception e){message("error","Não foi possível cadastrar: "+safeError(e));}
        });
    }
    public void login(String email, String password) {
        executor.execute(() -> {
            try {
                if(!validCredentials(email,password)){message("error","Informe e-mail válido e senha com pelo menos 8 caracteres.");return;}
                JSONObject body=new JSONObject().put("email",email.trim()).put("password",password);
                JSONObject result=call("/auth/v1/token?grant_type=password","POST",body,null);
                String token=result.optString("access_token","");
                if(token.isEmpty())throw new Exception("Verifique o e-mail e a senha");
                accessToken=token;
                businessId=null;
                message("authenticated","Login confirmado. Consultando seu negócio…");
                loadBusinessesInternal();
            } catch(Exception e){message("error","Não foi possível entrar: "+safeError(e));}
        });
    }
    private static boolean validCredentials(String email,String password){
        return email!=null && email.trim().length()<255 && email.matches("^[^ @]+@[^ @]+\\.[^ @]+$")
                && password!=null && password.length()>=8 && password.length()<=128;
    }
    private static String safeError(Exception e){
        String m=e.getMessage()==null ? "Tente novamente" : e.getMessage();
        return m.length()>220 ? m.substring(0,220) : m;
    }
    public void loadBusinesses() {
        executor.execute(() -> {
            try { loadBusinessesInternal(); }
            catch(Exception e){message("error","Falha ao consultar o negócio: "+safeError(e));}
        });
    }
    private void loadBusinessesInternal() throws Exception {
        if(accessToken==null){message("error","Faça login primeiro.");return;}
        JSONObject result=call("/functions/v1/nf-account/businesses","GET",null,accessToken);
        JSONArray arr=result.optJSONArray("businesses");
        if(arr!=null&&arr.length()>0){
            JSONObject first=arr.getJSONObject(0);
            businessId=first.getString("id");
            JSONObject payload=new JSONObject().put("type","business")
                .put("name",first.optString("name","Meu negócio"))
                .put("connected",false);
            dispatch(payload);
            loadConnectionInternal();
        } else {
            businessId=null;
            message("no_business","Conta conectada. Informe o nome do negócio para ativar os recebimentos.");
        }
    }
    public void createBusiness(String name) {
        executor.execute(() -> {
            try {
                if(accessToken==null){message("error","Faça login primeiro.");return;}
                String clean=name==null?"":name.trim();
                if(clean.length()<2||clean.length()>120){message("error","Nome do negócio deve ter de 2 a 120 caracteres.");return;}
                JSONObject result=call("/functions/v1/nf-account/businesses","POST",new JSONObject().put("name",clean),accessToken);
                JSONObject b=result.getJSONObject("business");
                businessId=b.getString("id");
                dispatch(new JSONObject().put("type","business").put("name",b.optString("name","Meu negócio")).put("connected",false));
                message("info","Negócio cadastrado no servidor com segurança.");
            }catch(Exception e){message("error","Não foi possível criar o negócio: "+safeError(e));}
        });
    }
    private void loadConnectionInternal() throws Exception {
        if(accessToken==null||businessId==null){message("error","Entre e cadastre um negócio primeiro.");return;}
        String path="/functions/v1/nf-mercadopago/oauth/connection?business_id="+businessId;
        JSONObject result=call(path,"GET",null,accessToken);
        JSONObject view=new JSONObject().put("type","connection")
            .put("connected",result.optBoolean("connected",false))
            .put("account",result.optString("account_id",""))
            .put("reconnect",result.optBoolean("requires_reconnect",false));
        dispatch(view);
    }
    public void loadConnection() {
        executor.execute(() -> {
            try{loadConnectionInternal();}
            catch(Exception e){message("error","Falha ao consultar Mercado Pago: "+safeError(e));}
        });
    }
    public void startOAuth() {
        executor.execute(() -> {
            try {
                if(accessToken==null||businessId==null){message("error","Entre e cadastre seu negócio antes.");return;}
                JSONObject b=new JSONObject().put("business_id",businessId);
                JSONObject res=call("/functions/v1/nf-mercadopago/oauth/start","POST",b,accessToken);
                String target=res.optString("authorization_url","");
                Uri link=Uri.parse(target);
                if(!"https".equals(link.getScheme())||!"auth.mercadopago.com".equals(link.getHost()))
                    throw new Exception("Endereço de autorização inválido");
                activity.runOnUiThread(()-> {
                    try {activity.startActivity(new Intent(Intent.ACTION_VIEW,link));}
                    catch(ActivityNotFoundException ex){message("error","Instale um navegador para autorizar Mercado Pago.");}
                });
                message("info","Autorize a conta no navegador. Depois volte e toque em Atualizar conexão.");
            } catch(Exception e){message("error","Não foi possível conectar Mercado Pago: "+safeError(e));}
        });
    }
    public void logout() {
        executor.execute(()->{
            accessToken=null;
            businessId=null;
            message("logout","Sessão encerrada. Os dados locais do aplicativo foram preservados.");
        });
    }
    public void close() { executor.shutdownNow(); accessToken=null; businessId=null; }
}
