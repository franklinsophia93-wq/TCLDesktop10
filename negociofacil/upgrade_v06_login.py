#!/usr/bin/env python3
"""Passo 0.6: incorpora login Supabase em Java seguro sem modificar ADM local."""
from pathlib import Path
import sys

def once(source, before, after, message):
    count=source.count(before)
    if count!=1: raise RuntimeError(f'{message}: esperado 1 ponto, encontrado {count}')
    return source.replace(before,after,1)

def patch(root, assets):
    base=Path(root)
    repo=Path(assets)
    src=repo/'login'
    js_path=base/'web/app.js'
    java_path=base/'android/app/src/main/java/br/com/negociofacil/app/MainActivity.java'
    gradle_path=base/'android/app/build.gradle'
    class_path=java_path.parent/'CloudAccount.java'
    js=js_path.read_text()
    native=java_path.read_text()
    gradle=gradle_path.read_text()

    source=src/'ui_snippet.js'
    if not source.is_file():raise RuntimeError('Trecho UI Supabase ausente')
    cloud_source=src/'CloudAccount.java'
    if not cloud_source.is_file():raise RuntimeError('Classe CloudAccount ausente')
    snippet=source.read_text()
    js=once(js,'  function settings(){',snippet+'  function settings(){','Adicionar conta em nuvem')
    cards='$'+'{adminCard()}'
    if js.count(cards)!=2:raise RuntimeError('O app deve conter duas visoes do cartao ADM')
    js=js.replace(cards,'$'+'{cloudCard()}'+cards)
    js=once(js,"    if(action==='admin')return adminModal();",
        """    if(action==='admin')return adminModal();
    if(action==='cloud-account')return cloudModal();
    if(action==='cloud-logout'||action==='cloud-connect'||action==='cloud-status')return cloudAction(action,id);""",
        'Acoes conta online')
    js=once(js,"if(form.id==='admin-form')return adminSubmit(e);",
        "if(form.id==='admin-form')return adminSubmit(e);if(form.id==='cloud-auth-form'||form.id==='cloud-business-form')return cloudSubmit(e);",
        'Formularios de login em nuvem')
    js=js.replace('Não possui anúncios ativos, pagamentos, login de usuários em nuvem nem sincronização.',
        'Login em nuvem disponível para conectar Mercado Pago; pagamentos, assinaturas e sincronização de dados locais ainda indisponíveis.')
    native=once(native,'    private WebView webView;', '    private WebView webView;\n    private CloudAccount cloudAccount;', 'Referencia de conta online')
    native=once(native,'        super.onCreate(state);','        super.onCreate(state);\n        cloudAccount = new CloudAccount(this);','Inicializacao segura')
    native=once(native,'    private final class LocalActions {',
"""    private final class LocalActions {
        @JavascriptInterface public void openMercadoPagoOAuth(String value) {
            if (value == null || value.length() > 4096) return;
            try {
                android.net.Uri u = android.net.Uri.parse(value);
                if (!"https".equals(u.getScheme())
                    || !"auth.mercadopago.com".equals(u.getHost())
                    || !"/authorization".equals(u.getPath())
                    || u.getUserInfo() != null) return;
                runOnUiThread(() -> openExternalUrl(value));
            } catch (Exception e) {
                show("Falha ao abrir autorização do Mercado Pago.");
            }
        }
        @JavascriptInterface public String cloudState(){return cloudAccount.state();}
        @JavascriptInterface public String cloudSignup(String email,String password){return cloudAccount.signup(email,password);}
        @JavascriptInterface public String cloudSignin(String email,String password){return cloudAccount.signin(email,password);}
        @JavascriptInterface public String cloudSignout(){return cloudAccount.signout();}
        @JavascriptInterface public String cloudAddBusiness(String name){return cloudAccount.addBusiness(name);}
        @JavascriptInterface public String cloudConnectMP(String id){return cloudAccount.connectMercadoPago(id);}
        @JavascriptInterface public String cloudMPStatus(String id){return cloudAccount.mpConnection(id);}
""",'Interface JavaScript protegida')
    gradle=once(gradle,'versionCode 5','versionCode 6','VersionCode Android')
    gradle=once(gradle,"versionName '0.5.0-compartilhamento-teste'",
        "versionName '0.6.0-login-supabase-teste'",'VersionName')
    js_path.write_text(js)
    java_path.write_text(native)
    gradle_path.write_text(gradle)
    class_path.write_text(cloud_source.read_text())
    assert 'cloudAccount' in native and 'cloudAddBusiness' in native
    assert 'cloudSignup' in js and 'versionCode 6' in gradle
    print('0.6 - login Supabase + OAuth por negocio incorporados, compras ainda desativadas')

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('upgrade_v06_login.py /build-src /repo/negociofacil')
    patch(sys.argv[1],sys.argv[2])
