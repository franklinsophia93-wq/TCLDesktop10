#!/usr/bin/env python3
"""NegócioFácil 0.6: login Supabase e OAuth para negócios; pagamentos ainda desativados.
Aplicar APÓS upgrade_v03, v04 e v05, usando fonte 0.2."""
from pathlib import Path
import sys
def replace_one(text,needle,replacement,description):
    n=text.count(needle)
    if n!=1: raise RuntimeError(f"{description}: esperava 1 ponto, encontrei {n}")
    return text.replace(needle,replacement,1)
def apply(root):
    root=Path(root)
    web=root/"web"
    native=root/"android/app/src/main/java/br/com/negociofacil/app/MainActivity.java"
    gradle=root/"android/app/build.gradle"
    htmlfile=web/"index.html"
    cssfile=web/"style.css"
    js_src=Path(__file__).with_name("web").joinpath("nf-cloud.js")
    if not js_src.exists():raise RuntimeError("Não foi encontrado o arquivo cloud nf-cloud.js")
    js=js_src.read_text(encoding="utf-8")
    if "NegocioFacilCloudStatus" not in js or "sb_publishable_" not in js: raise RuntimeError("Script cloud inválido")
    (web/"nf-cloud.js").write_text(js,encoding="utf-8")
    html=htmlfile.read_text(encoding="utf-8")
    html=replace_one(html,"connect-src 'self';","connect-src 'self' https://tlqcpfmkneohjleiynqe.supabase.co;","CSP backend seguro")
    html=replace_one(html,'  <script src="app.js" defer></script>', '  <script src="app.js" defer></script>\n  <script src="nf-cloud.js" defer></script>',"inclusão frontend")
    java=native.read_text(encoding="utf-8")
    old="""                if (APP_ORIGIN.equals(uri.getScheme()+"://"+uri.getHost())) {
                    return assetLoader.shouldInterceptRequest(uri);
                }
                // Nao renderizar conteudo remoto neste WebView com ponte JavaScript."""
    new="""                if (APP_ORIGIN.equals(uri.getScheme()+"://"+uri.getHost())) {
                    return assetLoader.shouldInterceptRequest(uri);
                }
                // Permitir apenas requisições HTTPS de API ao nosso projeto,
                // nunca carregar documentos, JS ou sites remotos no WebView.
                String p=uri.getPath()==null?"":uri.getPath();
                if ("https".equals(uri.getScheme())
                    && "tlqcpfmkneohjleiynqe.supabase.co".equals(uri.getHost())
                    && !request.isForMainFrame()
                    && ("GET".equals(request.getMethod())||"POST".equals(request.getMethod())||"OPTIONS".equals(request.getMethod()))
                    && (p.startsWith("/auth/v1/")
                        || p.equals("/rest/v1/nf_businesses")
                        || p.startsWith("/functions/v1/nf-mercadopago/"))) {
                    return null;
                }
                // Nao renderizar conteudo remoto neste WebView com ponte JavaScript."""
    java=replace_one(java,old,new,"WebView allowlist")
    newbridge="""    private final class LocalActions {
        /** Abre apenas a página de OAuth do Mercado Pago no navegador externo. */
        @JavascriptInterface public void openMercadoPagoOAuth(String value) {
            if (value == null || value.length() > 4096) return;
            try {
                Uri uri = Uri.parse(value);
                if (!"https".equals(uri.getScheme())
                    || !"auth.mercadopago.com".equals(uri.getHost())
                    || !"/authorization".equals(uri.getPath())
                    || uri.getUserInfo() != null) return;
                runOnUiThread(() -> openExternalUrl(value));
            } catch (Exception ignored) {
                show("Não foi possível abrir a autorização do Mercado Pago.");
            }
        }
"""
    java=replace_one(java,"    private final class LocalActions {",newbridge,"Bridge OAuth externo")
    g=gradle.read_text(encoding="utf-8")
    g=replace_one(g,"versionCode 5","versionCode 6","versionCode")
    g=replace_one(g,"versionName '0.5.0-compartilhamento-teste'",
        "versionName '0.6.0-conta-online-homologacao'","versionName")
    css=cssfile.read_text(encoding="utf-8")
    css += """
/* Conta Online: login individual + conta Mercado Pago, ainda sem cobranças reais. */
.nf-cloud-entry{font-size:19px}
#nf-cloud-overlay{position:fixed;inset:0;z-index:1000}
.nf-cloud-shade{position:absolute;inset:0;background:#020b18bb;display:flex;align-items:flex-end;justify-content:center}
.nf-cloud-panel-frame{background:var(--surface,#fff);color:var(--ink,#132538);border-radius:22px 22px 0 0;max-height:90dvh;overflow-y:auto;width:min(100%,480px);padding:24px 18px max(26px,env(safe-area-inset-bottom))}
.nf-cloud-panel-frame h2{font-size:23px;margin:16px 0 8px}
.nf-cloud-panel-frame p{font-size:13px;line-height:1.6}
.nf-cloud-head{display:flex;align-items:center;justify-content:space-between}
.nf-cloud-close{background:none;color:inherit;border:0;font-size:28px;cursor:pointer}
.nf-cloud-panel-frame label{display:block;font-size:13px;font-weight:700;margin:12px 0}
.nf-cloud-panel-frame input{width:100%;display:block;padding:13px;border:1px solid var(--line,#cad5df);border-radius:10px;background:var(--input,#fff);color:var(--ink,#152d45);margin-top:6px;font-size:16px}
.nf-cloud-panel-frame .btn{width:100%;margin-top:12px;min-height:45px}
.nf-cloud-panel-frame button[disabled]{opacity:.55}
.nf-cloud-panel{padding:14px;border-radius:12px;border:1px solid var(--line,#ccd);margin:14px 0}
.nf-cloud-note,.nf-cloud-sub{color:var(--muted,#789);font-size:12px!important}
.nf-cloud-error{margin:14px 0;background:#feefed;color:#8e1e15;border-radius:10px;padding:12px;font-size:13px}
.nf-online-ok{color:#0eab82}.nf-online-pending{color:#d58d20}
@media(min-width:600px){.nf-cloud-shade{align-items:center}.nf-cloud-panel-frame{border-radius:22px}}
"""
    htmlfile.write_text(html,encoding="utf-8")
    native.write_text(java,encoding="utf-8")
    gradle.write_text(g,encoding="utf-8")
    cssfile.write_text(css,encoding="utf-8")
    assert "versionCode 6" in g and "Intent.createChooser" in java
    assert "MP_USE_PKCE" not in html and "nf-cloud.js" in html
    print("NegocioFacil 0.6: login email, empresas e OAuth com allowlist WebView; cobranças desativadas")
if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("Uso: upgrade_v06_cloud.py /fonte")
    apply(sys.argv[1])
